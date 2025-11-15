import os
import shutil
import uvicorn
import hashlib
from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, EmailStr
import beanie
from typing import List, Optional
from beanie import PydanticObjectId
import aioodbc
from passlib.context import CryptContext
from jose import JWTError, jwt

# ===================================================================
# === CẤU HÌNH DATABASE ===
# ===================================================================

# MongoDB Configuration
MONGO_CONNECTION_STRING = "mongodb://localhost:27017"
DB_NAME = "UniHub_Courses"

# SQL Server Configuration
SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", "localhost")
SQL_SERVER_PORT = os.getenv("SQL_SERVER_PORT", "1433")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER", "sa")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "123456789")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE", "unihub")
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 17 for SQL Server")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ===================================================================
# === MODELS ===
# ===================================================================

# MongoDB Document Model
class Document(beanie.Document):
    filename: str = Field(..., index=True)
    saved_path: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=datetime.now)
    university: str
    faculty: str
    course: str
    documentTitle: str
    description: str
    documentType: str
    tags: str
    class Settings:
        name = "Courses"

# Pydantic Models for Authentication
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

# ===================================================================
# === GLOBAL VARIABLES ===
# ===================================================================

# SQL Server connection pool
pool: Optional[aioodbc.Pool] = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# ===================================================================
# === LIFESPAN: Khởi tạo cả MongoDB và SQL Server ===
# ===================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    
    print("Bắt đầu khởi động server...")
    
    # 1. Khởi tạo MongoDB
    try:
        app.mongodb_client = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
        await beanie.init_beanie(
            database=app.mongodb_client[DB_NAME],
            document_models=[Document]
        )
        print(f"✅ Collection Beanie và MongoDB successful!")
        print(f"   - Database: {DB_NAME}")
        print(f"   - Collection: {Document.Settings.name}")
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        raise
    
    # 2. Khởi tạo SQL Server
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
            dsn=conn_str,
            minsize=1,
            maxsize=10,
            autocommit=True
        )
        print(f"✅ Connected to SQL Server database: {SQL_SERVER_DATABASE}")
        
        # Test connection
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
    except Exception as e:
        print(f"❌ Error connecting to SQL Server: {e}")
        print("Make sure SQL Server is running and the ODBC driver is installed")
        raise
    
    yield
    
    # Shutdown
    print("Starting to shut down the server...")
    
    # Close MongoDB
    if hasattr(app, 'mongodb_client'):
        app.mongodb_client.close()
        print("Disconnected from MongoDB.")
    
    # Close SQL Server
    if pool:
        pool.close()
        await pool.wait_closed()
        print("Disconnected from SQL Server.")

# ===================================================================
# === KHỞI TẠO APP FASTAPI ===
# ===================================================================

app = FastAPI(
    title="UniHub API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ===================================================================
# === HELPER FUNCTIONS (Authentication) ===
# ===================================================================

def _preprocess_password(password: str) -> str:
    """Preprocess password to handle bcrypt's 72-byte limit."""
    if not password:
        raise ValueError("Password cannot be empty")
    
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        return hashlib.sha256(password_bytes).hexdigest()
    return password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password. Handles passwords that may have been preprocessed."""
    try:
        if not plain_password or not hashed_password:
            return False
        preprocessed = _preprocess_password(plain_password)
        return pwd_context.verify(preprocessed, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Hash password. Preprocesses if password is longer than 72 bytes."""
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
        "id": row[0],
        "fullname": row[1],
        "email": row[2],
        "university": row[3],
        "password": row[4],
        "created_at": row[5]
    }
    
    return {
        "_id": str(user["id"]),
        "fullname": user["fullname"],
        "email": user["email"],
        "university": user["university"],
        "password": user["password"],
        "created_at": user["created_at"]
    }

# ===================================================================
# === API ROUTES ===
# ===================================================================

# Health Check
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    sql_server_connected = False
    mongo_connected = False
    
    # Check SQL Server
    if pool:
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
                    sql_server_connected = True
        except Exception:
            pass
    
    # Check MongoDB
    if hasattr(app, 'mongodb_client'):
        try:
            await app.mongodb_client.admin.command('ping')
            mongo_connected = True
        except Exception:
            pass
    
    return {
        "status": "healthy",
        "message": "UniHub API is running",
        "sql_server_connected": sql_server_connected,
        "mongo_connected": mongo_connected
    }

@app.get("/")
async def root():
    return {"message": "UniHub API is running"}

# ===================================================================
# === AUTHENTICATION ROUTES ===
# ===================================================================

@app.post("/api/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    try:
        if pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (user_data.email,)
                )
                existing_user = await cur.fetchone()
                if existing_user:
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
                if not hashed_password:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Password hashing failed"
                    )
                
                created_at = datetime.utcnow()
                await cur.execute(
                    "INSERT INTO users (fullname, email, university, password, created_at) OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?)",
                    (user_data.fullname, user_data.email, user_data.university, hashed_password, created_at)
                )
                result = await cur.fetchone()
                user_id = result[0] if result else None
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    try:
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
            "id": row[0],
            "fullname": row[1],
            "email": row[2],
            "university": row[3],
            "password": row[4],
            "created_at": row[5]
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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

# ===================================================================
# === DOCUMENT ROUTES (MongoDB) ===
# ===================================================================

@app.post("/uploadfile/")
async def create_upload_file(
    file: UploadFile = File(...),
    university: str = Form(...),
    faculty: str = Form(...),
    course: str = Form(...),
    documentTitle: str = Form(...),
    description: str = Form(...),
    documentType: str = Form(...),
    tags: str = Form(default="")
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Do not save: {e}"})
    finally:
        file.file.close()
    
    doc = Document(
        filename=file.filename,
        saved_path=file_path,
        content_type=file.content_type,
        size_bytes=file_size,
        university=university,
        faculty=faculty,
        course=course,
        documentTitle=documentTitle,
        description=description,
        documentType=documentType,
        tags=tags
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
async def get_all_documents():
    """Get ALL documents in the 'Courses' collection."""
    try:
        courses = await Document.find_all().to_list()
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===================================================================
# === STATIC FILES ===
# ===================================================================

# Serve static files (frontend) - must be after all API routes
try:
    app.mount("/", StaticFiles(directory="public", html=True), name="static")
except Exception:
    pass

# ===================================================================
# === RUN SERVER ===
# ===================================================================

if __name__ == "__main__":
    print(f"Server is running at http://127.0.0.1:8000")
    print(f"Uploaded files will be saved in the directory: {os.path.abspath(UPLOAD_DIR)}")
    uvicorn.run(app, host="127.0.0.1", port=8000)