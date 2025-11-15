import os
import shutil
import uvicorn
import hashlib
import json
from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
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
import sys
import importlib.util

# Import quiz generator from make_quiz.py
try:
    spec = importlib.util.spec_from_file_location("make_quiz", "make_quiz.py")
    make_quiz_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make_quiz_module)
    AdvancedEnglishQuizGenerator = make_quiz_module.AdvancedEnglishQuizGenerator
    quiz_generator = None  # Will be initialized on first use
except Exception as e:
    print(f"Warning: Could not load quiz generator: {e}")
    AdvancedEnglishQuizGenerator = None
    quiz_generator = None

# Import summarizer from summarizer.py
try:
    spec_summarizer = importlib.util.spec_from_file_location("summarizer", "summarizer.py")
    summarizer_module = importlib.util.module_from_spec(spec_summarizer)
    spec_summarizer.loader.exec_module(summarizer_module)
    ExtendedLectureSummarizer = summarizer_module.ExtendedLectureSummarizer
    summarizer = None  # Will be initialized on first use
except Exception as e:
    print(f"Warning: Could not load summarizer: {e}")
    ExtendedLectureSummarizer = None
    summarizer = None

# Import keyword extractor from keywords.py
try:
    spec_keywords = importlib.util.spec_from_file_location("keywords", "keywords.py")
    keywords_module = importlib.util.module_from_spec(spec_keywords)
    spec_keywords.loader.exec_module(keywords_module)
    KeywordExtractor = keywords_module.KeywordExtractor
    keyword_extractor = None  # Will be initialized on first use
except Exception as e:
    print(f"Warning: Could not load keyword extractor: {e}")
    KeywordExtractor = None
    keyword_extractor = None

# PDF text extraction
PDF_AVAILABLE = False
PDF_LIBRARY = None
try:
    import PyPDF2
    PDF_AVAILABLE = True
    PDF_LIBRARY = "PyPDF2"
except ImportError:
    try:
        import pdfplumber
        PDF_AVAILABLE = True
        PDF_LIBRARY = "pdfplumber"
    except ImportError:
        PDF_AVAILABLE = False
        PDF_LIBRARY = None
        print("Warning: No PDF library available. Install PyPDF2 or pdfplumber for quiz generation.")


# --- MongoDB Configuration (for Upload) ---
MONGO_CONNECTION_STRING = "mongodb://localhost:27017"
DB_NAME = "UniHub_Courses"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- SQL Server Configuration (for Users) ---
SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", r"localhost")
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
    uploaded_by: Optional[str] = Field(default=None, index=True)  # User ID who uploaded
    summary: Optional[str] = Field(default=None)  # AI-generated summary
    keywords: List[str] = Field(default_factory=list)  # Extracted keywords
    class Settings:
        name = "Courses"

# --- Model for MongoDB (Comment) ---
class Comment(beanie.Document):
    document_id: str = Field(..., index=True)
    author_id: str
    author_name: str
    text: str
    created_at: datetime = Field(default_factory=datetime.now)
    class Settings:
        name = "Comments"

# --- Model for MongoDB (Vote) ---
class Vote(beanie.Document):
    document_id: str = Field(..., index=True)
    user_id: str = Field(..., index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    class Settings:
        name = "Votes"
        indexes = [
            [("document_id", 1), ("user_id", 1)],  # Compound index to prevent duplicate votes
        ]

# --- Model for MongoDB (Download) ---
class Download(beanie.Document):
    document_id: str = Field(..., index=True)
    user_id: str = Field(..., index=True)
    downloaded_at: datetime = Field(default_factory=datetime.now)
    class Settings:
        name = "Downloads"
        indexes = [
            [("document_id", 1), ("user_id", 1)],  # Compound index
        ]

# --- Model for MongoDB (Favorite) ---
class Favorite(beanie.Document):
    document_id: str = Field(..., index=True)
    user_id: str = Field(..., index=True)
    favorited_at: datetime = Field(default_factory=datetime.now)
    class Settings:
        name = "Favorites"
        indexes = [
            [("document_id", 1), ("user_id", 1)],  # Compound index to prevent duplicate favorites
        ]

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

class ProfileUpdate(BaseModel):
    fullname: Optional[str] = None
    university: Optional[str] = None
    major: Optional[str] = None
    bio: Optional[str] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)
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
            # Check if major column exists
            try:
                await cur.execute("""
                    SELECT COUNT(*) FROM sys.columns 
                    WHERE object_id = OBJECT_ID('users') AND name = 'major'
                """)
                major_exists = (await cur.fetchone())[0] > 0
            except Exception:
                major_exists = False
            
            # Select with or without major column
            if major_exists:
                await cur.execute(
                    "SELECT id, fullname, email, university, password, created_at, major FROM users WHERE email = ?",
                    (email,)
                )
            else:
                await cur.execute(
                    "SELECT id, fullname, email, university, password, created_at FROM users WHERE email = ?",
                    (email,)
                )
            row = await cur.fetchone()
    
    if row is None:
        raise credentials_exception
    
    if major_exists and len(row) > 6:
        user = {
            "id": row[0], "fullname": row[1], "email": row[2],
            "university": row[3], "password": row[4], "created_at": row[5], "major": row[6]
        }
    else:
        user = {
            "id": row[0], "fullname": row[1], "email": row[2],
            "university": row[3], "password": row[4], "created_at": row[5], "major": None
        }
    
    return {
        "_id": str(user["id"]), "fullname": user["fullname"], "email": user["email"],
        "university": user["university"], "password": user["password"], 
        "created_at": user["created_at"], "major": user.get("major")
    }

async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)):
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Bắt đầu khởi động server...")
    global pool

    # Connect MongoDB (Beanie)
    app.mongodb_client = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
    await beanie.init_beanie(
        database=app.mongodb_client[DB_NAME],
        document_models=[Document, Comment, Vote, Download, Favorite] 
    )
    print(f" Collection Beanie và MongoDB sucessful!")
    print(f"   - Database: {DB_NAME}")
    print(f"   - Collection: {Document.Settings.name}")

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
    current_user: Optional[dict] = Depends(get_current_user_optional)
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
    
    # Get user ID if authenticated
    uploaded_by = None
    if current_user:
        uploaded_by = str(current_user["_id"])
    
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
        uploaded_by = uploaded_by
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

@app.get("/documents/")  # Removed response_model to allow custom fields
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
        
        # 4. Convert to list of dictionaries and ensure id is included
        result = []
        for doc in courses:
            # Get base dictionary from document
            doc_dict = doc.dict()
            # Ensure id is present as both 'id' and '_id' for compatibility
            doc_id = str(doc.id)
            
            # Get vote count and comment count for priority calculation
            try:
                vote_count = await Vote.find(Vote.document_id == doc_id).count()
            except Exception as e:
                print(f"Error counting votes for {doc_id}: {e}")
                vote_count = 0
            
            try:
                comment_count = await Comment.find(Comment.document_id == doc_id).count()
            except Exception as e:
                print(f"Error counting comments for {doc_id}: {e}")
                comment_count = 0
            
            # Ensure these are integers
            vote_count_int = int(vote_count) if vote_count else 0
            comment_count_int = int(comment_count) if comment_count else 0
            
            # Ensure uploaded_at is serializable (convert datetime to ISO string if needed)
            if 'uploaded_at' in doc_dict and isinstance(doc_dict['uploaded_at'], datetime):
                doc_dict['uploaded_at'] = doc_dict['uploaded_at'].isoformat()
            
            # Create a new dictionary with all fields, ensuring vote_count and comment_count are included
            final_dict = {
                **doc_dict,  # Include all original document fields
                'id': doc_id,
                '_id': doc_id,
                'vote_count': vote_count_int,
                'comment_count': comment_count_int,
                'priority_score': vote_count_int * 2 + comment_count_int,
                'has_voted': False  # Default, will be updated if user is logged in
            }
        
            
            result.append(final_dict)
        
        # 5. Sort by priority score (highest first), then by upload date (newest first)
        def get_sort_key(x):
            priority = -x.get('priority_score', 0)
            # Handle uploaded_at - could be datetime object or string
            uploaded_at = x.get('uploaded_at')
            if isinstance(uploaded_at, datetime):
                date_score = -uploaded_at.timestamp()
            elif isinstance(uploaded_at, str):
                try:
                    date_obj = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                    date_score = -date_obj.timestamp()
                except:
                    date_score = 0
            else:
                date_score = 0
            return (priority, date_score)
        
        result.sort(key=get_sort_key)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper function to load comments from JSON file
def load_comments_from_file(document_id: str) -> list:
    """Load comments from JSON file"""
    try:
        COMMENTS_DIR = "public/data/comments"
        comments_file = os.path.join(COMMENTS_DIR, f"{document_id}.json")
        if os.path.exists(comments_file):
            with open(comments_file, 'r', encoding='utf-8') as f:
                comments_data = json.load(f)
                return comments_data.get('comments', [])
        return []
    except Exception as e:
        print(f"Error loading comments: {e}")
        return []

@app.get("/api/my-uploads")
async def get_my_uploads(current_user: dict = Depends(get_current_user)):
    """Get all documents uploaded by the current user"""
    try:
        user_id = str(current_user["_id"])
        documents = await Document.find(Document.uploaded_by == user_id).sort(-Document.uploaded_at).to_list()
        
        result = []
        for doc in documents:
            doc_dict = doc.dict()
            doc_id = str(doc.id)
            
            # Get vote and comment counts
            try:
                vote_count = await Vote.find(Vote.document_id == doc_id).count()
            except:
                vote_count = 0
            
            try:
                comment_count = len(load_comments_from_file(doc_id))
            except:
                comment_count = 0
            
            # Convert datetime to ISO string
            if 'uploaded_at' in doc_dict and isinstance(doc_dict['uploaded_at'], datetime):
                doc_dict['uploaded_at'] = doc_dict['uploaded_at'].isoformat()
            
            result.append({
                **doc_dict,
                'id': doc_id,
                '_id': doc_id,
                'vote_count': vote_count,
                'comment_count': comment_count
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/my-downloads")
async def get_my_downloads(current_user: dict = Depends(get_current_user)):
    """Get all documents downloaded by the current user"""
    try:
        user_id = str(current_user["_id"])
        # Get all download records for this user
        downloads = await Download.find(Download.user_id == user_id).sort(-Download.downloaded_at).to_list()
        
        if not downloads:
            return []
        
        # Get unique document IDs
        document_ids = list(set([d.document_id for d in downloads]))
        
        # Fetch documents
        result = []
        for doc_id in document_ids:
            try:
                doc = await Document.get(PydanticObjectId(doc_id))
                if doc:
                    doc_dict = doc.dict()
                    doc_id_str = str(doc.id)
                    
                    # Get vote and comment counts
                    try:
                        vote_count = await Vote.find(Vote.document_id == doc_id_str).count()
                    except:
                        vote_count = 0
                    
                    try:
                        comment_count = len(load_comments_from_file(doc_id_str))
                    except:
                        comment_count = 0
                    
                    # Get download date for this user
                    user_download = next((d for d in downloads if d.document_id == doc_id), None)
                    downloaded_at = user_download.downloaded_at.isoformat() if user_download else None
                    
                    # Convert datetime to ISO string
                    if 'uploaded_at' in doc_dict and isinstance(doc_dict['uploaded_at'], datetime):
                        doc_dict['uploaded_at'] = doc_dict['uploaded_at'].isoformat()
                    
                    result.append({
                        **doc_dict,
                        'id': doc_id_str,
                        '_id': doc_id_str,
                        'vote_count': vote_count,
                        'comment_count': comment_count,
                        'downloaded_at': downloaded_at
                    })
            except Exception as e:
                print(f"Error fetching document {doc_id}: {e}")
                continue
        
        # Sort by downloaded_at (most recent first)
        result.sort(key=lambda x: x.get('downloaded_at', ''), reverse=True)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/my-favorites")
async def get_my_favorites(current_user: dict = Depends(get_current_user)):
    """Get all documents favorited by the current user"""
    try:
        user_id = str(current_user["_id"])
        # Get all favorite records for this user
        favorites = await Favorite.find(Favorite.user_id == user_id).sort(-Favorite.favorited_at).to_list()
        
        if not favorites:
            return []
        
        # Get unique document IDs
        document_ids = list(set([f.document_id for f in favorites]))
        
        # Fetch documents
        result = []
        for doc_id in document_ids:
            try:
                doc = await Document.get(PydanticObjectId(doc_id))
                if doc:
                    doc_dict = doc.dict()
                    doc_id_str = str(doc.id)
                    
                    # Get vote and comment counts
                    try:
                        vote_count = await Vote.find(Vote.document_id == doc_id_str).count()
                    except:
                        vote_count = 0
                    
                    try:
                        comment_count = len(load_comments_from_file(doc_id_str))
                    except:
                        comment_count = 0
                    
                    # Get favorite date for this user
                    user_favorite = next((f for f in favorites if f.document_id == doc_id), None)
                    favorited_at = user_favorite.favorited_at.isoformat() if user_favorite else None
                    
                    # Convert datetime to ISO string
                    if 'uploaded_at' in doc_dict and isinstance(doc_dict['uploaded_at'], datetime):
                        doc_dict['uploaded_at'] = doc_dict['uploaded_at'].isoformat()
                    
                    result.append({
                        **doc_dict,
                        'id': doc_id_str,
                        '_id': doc_id_str,
                        'vote_count': vote_count,
                        'comment_count': comment_count,
                        'favorited_at': favorited_at
                    })
            except Exception as e:
                print(f"Error fetching document {doc_id}: {e}")
                continue
        
        # Sort by favorited_at (most recent first)
        result.sort(key=lambda x: x.get('favorited_at', ''), reverse=True)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/{document_id}/download")
async def track_download(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Track document download"""
    try:
        user_id = str(current_user["_id"])
        
        # Check if download already exists
        existing = await Download.find_one(
            Download.document_id == document_id,
            Download.user_id == user_id
        )
        
        if not existing:
            # Create new download record
            download = Download(
                document_id=document_id,
                user_id=user_id
            )
            await download.insert()
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/{document_id}/favorite")
async def toggle_favorite(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Toggle favorite status for a document"""
    try:
        user_id = str(current_user["_id"])
        
        # Check if favorite already exists
        existing = await Favorite.find_one(
            Favorite.document_id == document_id,
            Favorite.user_id == user_id
        )
        
        if existing:
            # Remove favorite
            await existing.delete()
            return {"status": "removed", "is_favorited": False}
        else:
            # Add favorite
            favorite = Favorite(
                document_id=document_id,
                user_id=user_id
            )
            await favorite.insert()
            return {"status": "added", "is_favorited": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    # Return user data including major if available
    user_data = {
        "id": str(current_user["_id"]),
        "fullname": current_user["fullname"],
        "email": current_user["email"],
        "university": current_user["university"],
        "created_at": current_user["created_at"]
    }
    if "major" in current_user and current_user["major"]:
        user_data["major"] = current_user["major"]
    
    # Check if avatar file exists
    avatar_dir = "public/data/avatars"
    user_id = str(current_user["_id"])
    # Try common image extensions
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        avatar_path = os.path.join(avatar_dir, f"{user_id}{ext}")
        if os.path.exists(avatar_path):
            user_data["avatar_url"] = f"/data/avatars/{user_id}{ext}"
            break
    
    return user_data

@app.put("/api/profile/update")
async def update_profile(
    current_user: dict = Depends(get_current_user),
    fullname: Optional[str] = Form(None),
    university: Optional[str] = Form(None),
    major: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None)
):
    """Update user profile information"""
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        update_fields = []
        update_values = []
        
        if fullname:
            update_fields.append("fullname = ?")
            update_values.append(fullname)
        
        if university:
            update_fields.append("university = ?")
            update_values.append(university)
        
        # Try to update major if provided
        if major:
            update_fields.append("major = ?")
            update_values.append(major)
        
        if not update_fields:
            return JSONResponse(content={"message": "No fields to update"})
        
        update_values.append(current_user["email"])
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Try to add major column if it doesn't exist and major is being updated
                if major:
                    try:
                        await cur.execute("""
                            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'major')
                            BEGIN
                                ALTER TABLE users ADD major NVARCHAR(255) NULL
                            END
                        """)
                    except Exception:
                        pass  # Column might already exist or error occurred
                
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE email = ?"
                await cur.execute(query, tuple(update_values))
        
        # Handle avatar upload if provided
        avatar_url = None
        if avatar:
            avatar_dir = "public/data/avatars"
            os.makedirs(avatar_dir, exist_ok=True)
            file_extension = os.path.splitext(avatar.filename)[1] or '.jpg'
            avatar_filename = f"{current_user['_id']}{file_extension}"
            avatar_path = os.path.join(avatar_dir, avatar_filename)
            
            # Delete old avatar if exists (different extension)
            user_id = str(current_user['_id'])
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                old_avatar = os.path.join(avatar_dir, f"{user_id}{ext}")
                if os.path.exists(old_avatar) and old_avatar != avatar_path:
                    try:
                        os.remove(old_avatar)
                    except Exception:
                        pass
            
            with open(avatar_path, "wb") as buffer:
                shutil.copyfileobj(avatar.file, buffer)
            
            avatar_url = f"/data/avatars/{avatar_filename}"
        
        return JSONResponse(content={
            "message": "Profile updated successfully",
            "avatar_url": avatar_url
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )

@app.post("/api/profile/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: dict = Depends(get_current_user)
):
    """Change user password"""
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        hashed_password = get_password_hash(password_data.new_password)
        
        # Update password in database
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET password = ? WHERE email = ?",
                    (hashed_password, current_user["email"])
                )
        
        return JSONResponse(content={"message": "Password changed successfully"})
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )

# --- API for Comments ---

@app.get("/api/documents/{document_id}/comments")
async def get_comments(document_id: str):
    """Get all comments for a document"""
    try:
        comments = await Comment.find(Comment.document_id == document_id).sort(-Comment.created_at).to_list()
        return [{
            "id": str(comment.id),
            "author_name": comment.author_name,
            "text": comment.text,
            "created_at": comment.created_at.isoformat()
        } for comment in comments]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching comments: {str(e)}"
        )

class CommentCreate(BaseModel):
    text: str

@app.post("/api/documents/{document_id}/comments")
async def create_comment(
    document_id: str,
    comment_data: CommentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new comment for a document"""
    try:
        # Verify document exists
        try:
            doc = await Document.get(PydanticObjectId(document_id))
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Create comment
        comment = Comment(
            document_id=document_id,
            author_id=str(current_user["_id"]),
            author_name=current_user["fullname"],
            text=comment_data.text
        )
        await comment.insert()
        
        return {
            "id": str(comment.id),
            "author_name": comment.author_name,
            "text": comment.text,
            "created_at": comment.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating comment: {str(e)}"
        )

# --- API for Votes ---

@app.get("/api/documents/{document_id}/votes")
async def get_vote_count(document_id: str):
    """Get vote count for a document"""
    try:
        vote_count = await Vote.find(Vote.document_id == document_id).count()
        return {"vote_count": vote_count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching vote count: {str(e)}"
        )

@app.get("/api/documents/{document_id}/votes/check")
async def check_user_vote(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if current user has voted for this document"""
    try:
        vote = await Vote.find_one(
            Vote.document_id == document_id,
            Vote.user_id == str(current_user["_id"])
        )
        return {"has_voted": vote is not None}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking vote: {str(e)}"
        )

@app.post("/api/documents/{document_id}/votes")
async def toggle_vote(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Toggle vote for a document (vote if not voted, unvote if voted)"""
    try:
        # Verify document exists
        try:
            doc = await Document.get(PydanticObjectId(document_id))
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        user_id = str(current_user["_id"])
        
        # Check if user already voted
        existing_vote = await Vote.find_one(
            Vote.document_id == document_id,
            Vote.user_id == user_id
        )
        
        if existing_vote:
            # Unvote: remove the vote
            await existing_vote.delete()
            action = "unvoted"
        else:
            # Vote: create new vote
            vote = Vote(
                document_id=document_id,
                user_id=user_id
            )
            await vote.insert()
            action = "voted"
        
        # Get updated vote count
        vote_count = await Vote.find(Vote.document_id == document_id).count()
        
        return {
            "action": action,
            "vote_count": vote_count,
            "has_voted": action == "voted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling vote: {str(e)}"
        )

# Allow downloading files from the 'uploads' directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# --- Helper Functions for Quiz Generation ---

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    if not PDF_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF library not available. Please install PyPDF2 or pdfplumber."
        )
    
    text = ""
    try:
        if PDF_LIBRARY == "pdfplumber":
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        else:
            # Use PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text from PDF: {str(e)}"
        )
    
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from PDF. The file might be image-based or corrupted."
        )
    
    return text

def get_quiz_generator():
    """Get or initialize quiz generator"""
    global quiz_generator
    if quiz_generator is None and AdvancedEnglishQuizGenerator:
        try:
            quiz_generator = AdvancedEnglishQuizGenerator()
        except Exception as e:
            print(f"Error initializing quiz generator: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Quiz generator initialization failed: {str(e)}"
            )
    return quiz_generator

def get_summarizer():
    """Get or initialize summarizer"""
    global summarizer
    if summarizer is None and ExtendedLectureSummarizer:
        try:
            summarizer = ExtendedLectureSummarizer()
        except Exception as e:
            print(f"Error initializing summarizer: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Summarizer initialization failed: {str(e)}"
            )
    return summarizer

def get_keyword_extractor():
    """Get or initialize keyword extractor"""
    global keyword_extractor
    if keyword_extractor is None and KeywordExtractor:
        try:
            keyword_extractor = KeywordExtractor()
        except Exception as e:
            print(f"Error initializing keyword extractor: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Keyword extractor initialization failed: {str(e)}"
            )
    return keyword_extractor

# --- API for Quiz Generation ---

class QuizGenerateRequest(BaseModel):
    num_questions: int = Field(default=10, ge=1, le=50)
    include_summary: bool = Field(default=True)
    include_keywords: bool = Field(default=True)

class ProcessPDFRequest(BaseModel):
    num_questions: int = Field(default=10, ge=1, le=50)
    include_summary: bool = Field(default=True)
    include_keywords: bool = Field(default=True)

@app.post("/api/generate-quiz-from-file")
async def generate_quiz_from_file(
    file: UploadFile = File(...),
    num_questions: int = Form(10),
    current_user: dict = Depends(get_current_user)
):
    """Generate quiz from uploaded PDF file"""
    try:
        # Check if file is PDF
        if not file.content_type or "pdf" not in file.content_type.lower():
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only PDF files are supported for quiz generation"
                )
        
        # Save temporary file
        temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")
        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()
        
        # Extract text from PDF
        text = extract_text_from_pdf(temp_file_path)
        
        # Clean up temp file
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        # Generate quiz
        generator = get_quiz_generator()
        if not generator:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Quiz generator not available"
            )
        
        quiz_data = generator.generate_complete_quiz(text, num_questions=num_questions)
        
        # Format quiz data to match expected format
        formatted_quiz = {
            "quiz_title": quiz_data.get("quiz_title", f"Quiz from {file.filename}"),
            "source_document": file.filename,
            "total_questions": quiz_data.get("total_questions", 0),
            "questions": []
        }
        
        for q in quiz_data.get("questions", []):
            # Convert correct_answer from label to text if needed
            correct_answer = q.get("correct_answer", "")
            options = q.get("options", {})
            
            # If correct_answer is a label (A, B, C, D), get the text
            if correct_answer in options:
                correct_answer_text = options[correct_answer]
            else:
                # Assume correct_answer is already text
                correct_answer_text = correct_answer
            
            formatted_quiz["questions"].append({
                "id": q.get("id", len(formatted_quiz["questions"]) + 1),
                "question": q.get("question", ""),
                "options": options,
                "correct_answer": correct_answer,  # Keep label for frontend
                "correct_answer_text": correct_answer_text,  # Add text version
                "explanation": q.get("explanation", "")
            })
        
        return formatted_quiz
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quiz: {str(e)}"
        )

@app.post("/api/documents/{document_id}/generate-quiz")
async def generate_quiz_from_document(
    document_id: str,
    request: QuizGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate quiz from existing document"""
    try:
        # Get document
        doc = await Document.get(PydanticObjectId(document_id))
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if document is PDF
        if not doc.content_type or "pdf" not in doc.content_type.lower():
            if not doc.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only PDF documents are supported for quiz generation"
                )
        
        # Extract text from PDF
        file_path = doc.saved_path
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
        
        text = extract_text_from_pdf(file_path)
        
        # Generate quiz
        generator = get_quiz_generator()
        if not generator:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Quiz generator not available"
            )
        
        quiz_data = generator.generate_complete_quiz(text, num_questions=request.num_questions)
        
        # Format quiz data
        formatted_quiz = {
            "quiz_title": quiz_data.get("quiz_title", f"Quiz from {doc.documentTitle}"),
            "source_document": doc.documentTitle or doc.filename,
            "total_questions": quiz_data.get("total_questions", 0),
            "questions": []
        }
        
        for q in quiz_data.get("questions", []):
            correct_answer = q.get("correct_answer", "")
            options = q.get("options", {})
            
            if correct_answer in options:
                correct_answer_text = options[correct_answer]
            else:
                correct_answer_text = correct_answer
            
            formatted_quiz["questions"].append({
                "id": q.get("id", len(formatted_quiz["questions"]) + 1),
                "question": q.get("question", ""),
                "options": options,
                "correct_answer": correct_answer,
                "correct_answer_text": correct_answer_text,
                "explanation": q.get("explanation", "")
            })
        
        return formatted_quiz
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quiz: {str(e)}"
        )

@app.post("/api/documents/{document_id}/process-pdf")
async def process_pdf_document(
    document_id: str,
    request: ProcessPDFRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process PDF document: Extract text, summarize, extract keywords, and generate quiz
    """
    try:
        # Get document
        doc = await Document.get(PydanticObjectId(document_id))
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if document is PDF
        if not doc.content_type or "pdf" not in doc.content_type.lower():
            if not doc.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only PDF documents are supported"
                )
        
        # Extract text from PDF
        file_path = doc.saved_path
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
        
        text = extract_text_from_pdf(file_path)
        
        result = {
            "document_id": document_id,
            "document_title": doc.documentTitle or doc.filename,
            "summary": None,
            "keywords": [],
            "quiz": None
        }
        
        # 1. Generate Summary
        if request.include_summary:
            try:
                summarizer_obj = get_summarizer()
                if summarizer_obj:
                    summary_text = summarizer_obj.get_summary_text(file_path)
                    result["summary"] = summary_text
            except Exception as e:
                print(f"Error generating summary: {e}")
                result["summary"] = None
        
        # 2. Extract Keywords (from summary if available, otherwise from original text)
        if request.include_keywords:
            try:
                keyword_extractor_obj = get_keyword_extractor()
                if keyword_extractor_obj:
                    # Use summary if available, otherwise use original text
                    text_for_keywords = result["summary"] if result["summary"] else text
                    keywords = keyword_extractor_obj.extract_from_text(text_for_keywords, top_n=10)
                    result["keywords"] = keywords
            except Exception as e:
                print(f"Error extracting keywords: {e}")
                result["keywords"] = []
        
        # 3. Generate Quiz (use summary if available for better quality)
        try:
            generator = get_quiz_generator()
            if generator:
                # Use summary if available, otherwise use original text
                text_for_quiz = result["summary"] if result["summary"] else text
                quiz_data = generator.generate_complete_quiz(text_for_quiz, num_questions=request.num_questions)
                
                # Format quiz data
                formatted_quiz = {
                    "quiz_title": quiz_data.get("quiz_title", f"Quiz from {doc.documentTitle}"),
                    "source_document": doc.documentTitle or doc.filename,
                    "total_questions": quiz_data.get("total_questions", 0),
                    "questions": []
                }
                
                for q in quiz_data.get("questions", []):
                    correct_answer = q.get("correct_answer", "")
                    options = q.get("options", {})
                    
                    if correct_answer in options:
                        correct_answer_text = options[correct_answer]
                    else:
                        correct_answer_text = correct_answer
                    
                    formatted_quiz["questions"].append({
                        "id": q.get("id", len(formatted_quiz["questions"]) + 1),
                        "question": q.get("question", ""),
                        "options": options,
                        "correct_answer": correct_answer,
                        "correct_answer_text": correct_answer_text,
                        "explanation": q.get("explanation", "")
                    })
                
                result["quiz"] = formatted_quiz
        except Exception as e:
            print(f"Error generating quiz: {e}")
            result["quiz"] = None
        
        # Save summary and keywords to document in MongoDB
        try:
            if result["summary"]:
                doc.summary = result["summary"]
            if result["keywords"]:
                doc.keywords = result["keywords"]
            
            if result["summary"] or result["keywords"]:
                await doc.save()
                print(f"Saved summary and keywords for document {document_id}")
        except Exception as e:
            print(f"Error saving summary/keywords to database: {e}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )

@app.post("/api/generate-quiz-from-file-complete")
async def process_pdf_from_file(
    file: UploadFile = File(...),
    num_questions: int = Form(10),
    include_summary: bool = Form(True),
    include_keywords: bool = Form(True),
    current_user: dict = Depends(get_current_user)
):
    """
    Process uploaded PDF file: Extract text, summarize, extract keywords, and generate quiz
    """
    try:
        # Check if file is PDF
        if not file.content_type or "pdf" not in file.content_type.lower():
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only PDF files are supported"
                )
        
        # Save temporary file
        temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")
        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()
        
        # Extract text from PDF
        text = extract_text_from_pdf(temp_file_path)
        
        result = {
            "document_title": file.filename,
            "summary": None,
            "keywords": [],
            "quiz": None
        }
        
        # 1. Generate Summary
        if include_summary:
            try:
                summarizer_obj = get_summarizer()
                if summarizer_obj:
                    summary_text = summarizer_obj.get_summary_text(temp_file_path)
                    result["summary"] = summary_text
            except Exception as e:
                print(f"Error generating summary: {e}")
                result["summary"] = None
        
        # 2. Extract Keywords
        if include_keywords:
            try:
                keyword_extractor_obj = get_keyword_extractor()
                if keyword_extractor_obj:
                    text_for_keywords = result["summary"] if result["summary"] else text
                    keywords = keyword_extractor_obj.extract_from_text(text_for_keywords, top_n=10)
                    result["keywords"] = keywords
            except Exception as e:
                print(f"Error extracting keywords: {e}")
                result["keywords"] = []
        
        # 3. Generate Quiz
        try:
            generator = get_quiz_generator()
            if generator:
                text_for_quiz = result["summary"] if result["summary"] else text
                quiz_data = generator.generate_complete_quiz(text_for_quiz, num_questions=num_questions)
                
                formatted_quiz = {
                    "quiz_title": quiz_data.get("quiz_title", f"Quiz from {file.filename}"),
                    "source_document": file.filename,
                    "total_questions": quiz_data.get("total_questions", 0),
                    "questions": []
                }
                
                for q in quiz_data.get("questions", []):
                    correct_answer = q.get("correct_answer", "")
                    options = q.get("options", {})
                    
                    if correct_answer in options:
                        correct_answer_text = options[correct_answer]
                    else:
                        correct_answer_text = correct_answer
                    
                    formatted_quiz["questions"].append({
                        "id": q.get("id", len(formatted_quiz["questions"]) + 1),
                        "question": q.get("question", ""),
                        "options": options,
                        "correct_answer": correct_answer,
                        "correct_answer_text": correct_answer_text,
                        "explanation": q.get("explanation", "")
                    })
                
                result["quiz"] = formatted_quiz
        except Exception as e:
            print(f"Error generating quiz: {e}")
            result["quiz"] = None
        
        # Clean up temp file
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )

# Allow accessing avatar images - create directory if it doesn't exist
AVATAR_DIR = "public/data/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)
app.mount("/data/avatars", StaticFiles(directory=AVATAR_DIR), name="avatars")

app.mount("/", StaticFiles(directory="public", html=True), name="public")


if __name__ == "__main__":
    print(f"Server is running at http://127.0.0.1:8000")
    print(f"Uploaded files will be saved in the directory: {os.path.abspath(UPLOAD_DIR)}")
    uvicorn.run(app, host="127.0.0.1", port=8000)