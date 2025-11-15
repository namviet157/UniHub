import os
import shutil
import uvicorn
import hashlib
from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, EmailStr
import beanie
from typing import List
from typing import List, Optional
from beanie import PydanticObjectId
from passlib.context import CryptContext
from jose import JWTError, jwt
import aioodbc
from typing import List, Optional
from fastapi import Query
from beanie.operators import Or, In
from fastapi import Query, Path

# --- MongoDB Configuration (for Upload) ---
MONGO_CONNECTION_STRING = "mongodb://localhost:27017"
DB_NAME = "UniHub_Courses"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- SQL Server Configuration (for Users) ---

SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", r"DESKTOP-CI5IA7D\SQLEXPRESS")
SQL_SERVER_PORT = os.getenv("SQL_SERVER_PORT", "1433")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER", "sa")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "123456789")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE", "unihub")
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 17 for SQL Server")

# --- Security Configuration (for Users) ---
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# --- Model for MongoDB (Document) ---

class Document(beanie.Document):
    filename: str = Field(..., index=True)
    saved_path: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=datetime.now)
    university : str
    faculty : str
    course : str
    documentTitle : str
    description : str
    documentType : str
    tags : str
    user_id: str  # Để lưu ID của người dùng từ SQL Server

    class Settings:
        name = "Courses"
        json_encoders = {
            PydanticObjectId: str
        }

# --- (THÊM VÀO ĐÂY) ---
# Model cho collection DownloadRecords
class DownloadRecord(beanie.Document):
    user_id: str                    # ID của người dùng (từ SQL Server) đã tải
    document_id: PydanticObjectId   # ID của tài liệu (từ collection 'Courses') đã được tải
    downloaded_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "DownloadRecord"    # Tên của collection trong MongoDB
# --- (KẾT THÚC PHẦN THÊM MỚI) ---


# --- Models for SQL Server (User) ---
class UserRegister(BaseModel):
    fullname: str
    email: EmailStr
    university: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    fullname: str
    email: str
    university: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
pool: Optional[aioodbc.Pool] = None # SQL connection pool

def _preprocess_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        return hashlib.sha256(password_bytes).hexdigest()
    return password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not plain_password or not hashed_password:
            return False
        preprocessed = _preprocess_password(plain_password)
        return pwd_context.verify(preprocessed, hashed_password)

    except Exception:
        return False

def get_password_hash(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    try:
        preprocessed = _preprocess_password(password)
        preprocessed_bytes = preprocessed.encode('utf-8') if isinstance(preprocessed, str) else preprocessed
        if len(preprocessed_bytes) > 72:
            preprocessed = preprocessed_bytes[:72].decode('utf-8', errors='ignore')
        hashed = pwd_context.hash(preprocessed)
        if not hashed:
            raise ValueError("Password hashing returned empty result")
        return hashed
    except ValueError:
        raise
    except Exception as e:
        error_msg = str(e)
        if "72 bytes" in error_msg.lower() or "too long" in error_msg.lower():
            try:
                password_bytes = password.encode('utf-8')
                preprocessed = hashlib.sha256(password_bytes).hexdigest()
                return pwd_context.hash(preprocessed)
            except Exception:
                pass
        raise ValueError(f"Failed to hash password: {error_msg}")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"

        )

   
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, fullname, email, university, password, created_at FROM users WHERE email = ?",
                (email,)
            )
            row = await cur.fetchone()

    if row is None:
        raise credentials_exception

    user = {
        "id": row[0], "fullname": row[1], "email": row[2],
        "university": row[3], "password": row[4], "created_at": row[5]
    }

    return {
        "_id": str(user["id"]), "fullname": user["fullname"], "email": user["email"],
        "university": user["university"], "password": user["password"], "created_at": user["created_at"]
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Bắt đầu khởi động server...")
    global pool

    # Connect MongoDB (Beanie)
    app.mongodb_client = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
    await beanie.init_beanie(
        database=app.mongodb_client[DB_NAME],
        # document_models=[Document] TRUE
        document_models=[Document, DownloadRecord] # Testing
    )
    print(f" Collection Beanie và MongoDB sucessful!")
    print(f"   - Database: {DB_NAME}")
    print(f"   - Collection: {Document.Settings.name}")

    # --- (THÊM VÀO ĐÂY) ---
    print(f"Đã kết nối Beanie tới MongoDB: {DB_NAME}")
    print("Các collection đã được khởi tạo:")
    # Vòng lặp này sẽ tự động in ra tên của tất cả các model bạn đăng ký
    for model in [Document, DownloadRecord]: 
        print(f"  -> {model.Settings.name}")
    # --- (KẾT THÚC PHẦN THÊM MỚI) ---

    # Connect SQL Server (aioodbc)
    try:
        conn_str = (
            f"DRIVER={{{SQL_SERVER_DRIVER}}};"
            f"SERVER={SQL_SERVER_HOST},{SQL_SERVER_PORT};"
            f"DATABASE={SQL_SERVER_DATABASE};"
            f"UID={SQL_SERVER_USER};"
            f"PWD={SQL_SERVER_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )
        pool = await aioodbc.create_pool(
            dsn=conn_str, minsize=1, maxsize=10, autocommit=True
        )
        print(f"Connected to SQL Server database: {SQL_SERVER_DATABASE}")
        # Test connection
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()

    except Exception as e:
        print(f"Error connecting to SQL Server: {e}")
        pool = None

    yield

    print("Starting to shut down the server...")
    app.mongodb_client.close()
    print("Disconnected from MongoDB.")
    if pool:

        pool.close()

        await pool.wait_closed()

        print("Disconnected from SQL Server")





app = FastAPI(
    title="UniHub API",
    version="1.0.0",
    lifespan=lifespan

)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API for Document (MongoDB) ---

@app.post("/uploadfile/")
async def create_upload_file(
    file: UploadFile = File(...),
    university: str = Form(...),
    faculty: str = Form(...),
    course: str = Form(...),
    documentTitle: str = Form(...),
    description: str = Form(...),
    documentType: str = Form(...),
    tags: str = Form(default=""),

    current_user: dict = Depends(get_current_user)
):

    local_file_path = os.path.join(UPLOAD_DIR, file.filename)
    db_save_path = os.path.join(UPLOAD_DIR, file.filename).replace("\\", "/")

    try:
        with open(local_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(local_file_path)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Do not save: {e}"})
    finally:
        file.file.close()
    doc = Document(
        filename=file.filename,
        saved_path=db_save_path,  
        content_type=file.content_type,
        size_bytes=file_size,
        university = university,
        faculty = faculty,
        course = course,
        documentTitle = documentTitle,
        description = description,
        documentType = documentType,
        tags = tags,
        user_id = current_user["_id"]
    )
    try:
        await doc.insert()
        return JSONResponse(content={
            "status": "uploaded successfully",
            "filename": doc.filename,
            "mongo_id": str(doc.id)
        })
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")
        return JSONResponse(status_code=500, content={
            "detail": f"File saved successfully but could not save to database: {e}"
        })

@app.get("/documents/", response_model=List[Document])
async def get_all_documents(
    university: Optional[str] = Query(None),
    faculty: Optional[str] = Query(None),
    course: Optional[str] = Query(None)
):
    """
    Get documents in the 'Courses' collection.
    Can be filtered by university, faculty, or course using query parameters.
    (e.g., /documents/?course=CS101)
    """
    try:
        # 1. Create an empty dictionary to hold search criteria
        search_criteria = {}

        # 2. Add criteria if they are provided
        if university:
            search_criteria["university"] = university
        if faculty:
            search_criteria["faculty"] = faculty
        if course:
            search_criteria["course"] = course
        # 3. Search
        if search_criteria:
            # If there are filters, search by criteria
            courses = await Document.find(search_criteria).to_list()
        else:
            # If no filters, get all
            courses = await Document.find_all().to_list()
        
        return courses
       
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# (Đây là code mới để thêm vào app.py)
@app.get("/api/me/documents", response_model=List[Document])
async def get_my_documents(current_user: dict = Depends(get_current_user)):
    try:
        user_id_str = current_user["_id"]  # Đây là String (ví dụ: "1")
        # 1. Tạo danh sách các điều kiện tìm kiếm
        query_conditions = [
            Document.user_id == user_id_str  # Tìm dạng CHUỖI (ví dụ: "1")
        ]

        # 2. Cố gắng thêm điều kiện tìm dạng SỐ
        try:
            user_id_num = int(user_id_str)
            # Nếu thành công, thêm điều kiện tìm SỐ (ví dụ: 1)
            query_conditions.append(Document.user_id == user_id_num)
        except (ValueError, TypeError):
            # Bỏ qua nếu user_id không phải là số (ví dụ: nó là UUID)
            pass

        # 3. Tìm bằng toán tử $or
        # (Tìm bất kỳ tài liệu nào khớp với bất kỳ điều kiện nào trong danh sách)
        documents = await Document.find(
            Or(*query_conditions)
        ).to_list()

        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint để download file và ghi log vào DownloadRecord
@app.get("/api/documents/{document_id}/download")
async def download_document(
    document_id: str = Path(..., title="The ID of the document to download"),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Log để debug
        print(f"Received document_id: {repr(document_id)}, type: {type(document_id)}")
        
        # Chuyển string → PydanticObjectId
        # Loại bỏ khoảng trắng và kiểm tra độ dài
        document_id = document_id.strip() if document_id else ""
        
        if not document_id:
            print("Error: Document ID is empty")
            raise HTTPException(status_code=400, detail="Document ID is required")
        
        # MongoDB ObjectId phải có 24 ký tự hex
        if len(document_id) != 24:
            print(f"Error: Document ID length is {len(document_id)}, expected 24")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid document ID format: expected 24 characters, got {len(document_id)}. Document ID: {document_id[:20]}..."
            )
        
        try:
            doc_id = PydanticObjectId(document_id)
            print(f"Successfully converted to PydanticObjectId: {doc_id}")
        except (ValueError, TypeError) as e:
            print(f"Error converting document_id to PydanticObjectId: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid document ID format: {str(e)}"
            )

        # Tìm document
        document = await Document.get(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Kiểm tra file có tồn tại không
        file_path = document.saved_path
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")

        # Ghi log vào DownloadRecord
        # Kiểm tra xem đã có record chưa (tránh duplicate)
        existing_record = await DownloadRecord.find_one(
            DownloadRecord.user_id == current_user["_id"],
            DownloadRecord.document_id == doc_id
        )
        
        if not existing_record:
            # Chỉ tạo record mới nếu chưa có
            download_log = DownloadRecord(
                user_id=current_user["_id"],
                document_id=doc_id
            )
            await download_log.insert()

        # Trả về file để download
        return FileResponse(
            path=file_path,
            filename=document.filename,
            media_type=document.content_type
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Could not download file: {e}")

# Endpoint để lấy danh sách documents đã download
@app.get("/api/me/downloads", response_model=List[Document])
async def get_my_downloads(current_user: dict = Depends(get_current_user)):
    try:
        user_id_str = current_user["_id"]
        
        # Tìm tất cả DownloadRecord của user này
        download_records = await DownloadRecord.find(
            DownloadRecord.user_id == user_id_str
        ).to_list()
        
        if not download_records:
            return []
        
        # Lấy danh sách document_id từ download_records
        document_ids = [record.document_id for record in download_records]
        
        # Lấy thông tin documents từ collection Courses
        # Sử dụng In operator từ beanie
        documents = await Document.find(
            In(Document.id, document_ids)
        ).to_list()
        
        # Sắp xếp theo thời gian download (mới nhất trước)
        # Tạo dict để map document_id -> downloaded_at
        download_time_map = {str(record.document_id): record.downloaded_at for record in download_records}
        
        # Sắp xếp documents theo thời gian download
        documents.sort(key=lambda doc: download_time_map.get(str(doc.id), datetime.min), reverse=True)
        
        return documents
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# --- API for User (SQL Server) ---


@app.get("/api/health")# 
# --- API for User (SQL Server) ---
@app.get("/api/health")
async def health_check():
    sql_server_connected = False
    if pool:
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
                    sql_server_connected = True
        except Exception:
            pass
    return {
        "status": "healthy",
        "message": "UniHub API is running",
        "mongo_connected": app.mongodb_client is not None,
        "sql_server_connected": sql_server_connected
    }

@app.post("/api/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
            if await cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            if not user_data.password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password cannot be empty"
                )
            hashed_password = get_password_hash(user_data.password)
            created_at = datetime.utcnow()
            try:
                await cur.execute(
                    "INSERT INTO users (fullname, email, university, password, created_at) OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?)",
                    (user_data.fullname, user_data.email, user_data.university, hashed_password, created_at)
                )
                result = await cur.fetchone()
                user_id = result[0] if result else None
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error saving user to database: {e}"
                )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.email}, expires_delta=access_token_expires
    )
    user_response = UserResponse(
        id=str(user_id),
        fullname=user_data.fullname,
        email=user_data.email,
        university=user_data.university,
        created_at=created_at
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@app.post("/api/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, fullname, email, university, password, created_at FROM users WHERE email = ?",
                (credentials.email,)
            )
            row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    user = {
        "id": row[0], "fullname": row[1], "email": row[2],
        "university": row[3], "password": row[4], "created_at": row[5]
    }
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.email}, expires_delta=access_token_expires
    )
    user_response = UserResponse(
        id=str(user["id"]),
        fullname=user["fullname"],
        email=user["email"],
        university=user["university"],
        created_at=user["created_at"]
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@app.get("/api/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user["_id"]),
        fullname=current_user["fullname"],
        email=current_user["email"],
        university=current_user["university"],
        created_at=current_user["created_at"]
    )

# Allow downloading files from the 'uploads' directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/", StaticFiles(directory="public", html=True), name="public")

if __name__ == "__main__":
    print(f"Server is running at http://127.0.0.1:8000")
    print(f"Uploaded files will be saved in the directory: {os.path.abspath(UPLOAD_DIR)}")
    uvicorn.run(app, host="127.0.0.1", port=8000)
