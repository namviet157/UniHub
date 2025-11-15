from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import aioodbc
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
import hashlib

SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", "localhost")
SQL_SERVER_PORT = os.getenv("SQL_SERVER_PORT", "1433")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER", "sa")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "123456789")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE", "unihub")
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 17 for SQL Server")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Initialize FastAPI app
app = FastAPI(title="UniHub API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# SQL Server connection pool
pool: Optional[aioodbc.Pool] = None


# Pydantic models
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


# SQL Server connection
@app.on_event("startup")
async def startup_db_client():
    global pool
    try:
        # Build connection string for SQL Server
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
        print(f"Connected to SQL Server database: {SQL_SERVER_DATABASE}")
        
        # Test connection
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
    except Exception as e:
        print(f"Error connecting to SQL Server: {e}")
        print("Make sure SQL Server is running and the ODBC driver is installed")
        raise


@app.on_event("shutdown")
async def shutdown_db_client():
    global pool
    if pool:
        pool.close()
        await pool.wait_closed()
        print("Disconnected from SQL Server")


# Helper functions
def _preprocess_password(password: str) -> str:
    """
    Preprocess password to handle bcrypt's 72-byte limit.
    If password is longer than 72 bytes, hash it with SHA256 first.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Hash with SHA256 if password is too long for bcrypt
        return hashlib.sha256(password_bytes).hexdigest()
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password. Handles passwords that may have been preprocessed.
    """
    try:
        if not plain_password or not hashed_password:
            return False
        # Always use preprocessed password for consistency
        preprocessed = _preprocess_password(plain_password)
        return pwd_context.verify(preprocessed, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash password. Preprocesses if password is longer than 72 bytes.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    try:
        # Preprocess password first to handle 72-byte limit
        preprocessed = _preprocess_password(password)
        
        # Ensure preprocessed password is not longer than 72 bytes
        preprocessed_bytes = preprocessed.encode('utf-8') if isinstance(preprocessed, str) else preprocessed
        if len(preprocessed_bytes) > 72:
            # If still too long (shouldn't happen), truncate
            preprocessed = preprocessed_bytes[:72].decode('utf-8', errors='ignore')
        
        hashed = pwd_context.hash(preprocessed)
        if not hashed:
            raise ValueError("Password hashing returned empty result")
        return hashed
    except ValueError:
        raise
    except Exception as e:
        error_msg = str(e)
        # If error is about password length, try preprocessing again
        if "72 bytes" in error_msg.lower() or "too long" in error_msg.lower():
            try:
                # Force SHA256 preprocessing
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
    
    # Convert row tuple to dict format compatible with old code
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


# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
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
        "sql_server_connected": sql_server_connected
    }

@app.get("/")
async def root():
    return {"message": "UniHub API is running"}


@app.post("/api/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    try:
        # Check if database is connected
        if pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Check if user already exists
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
                
                # Hash password
                try:
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
                except HTTPException:
                    raise
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error processing password: {str(e)}"
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error processing password: {str(e)}"
                    )
                
                # Insert user into database
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
                        detail="Error saving user to database"
                    )
        
        # Create access token
        try:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_data.email}, expires_delta=access_token_expires
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating access token"
            )
        
        # Return user data (without password)
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
        # Check if database is connected
        if pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Find user by email
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "SELECT id, fullname, email, university, password, created_at FROM users WHERE email = ?",
                        (credentials.email,)
                    )
                    row = await cur.fetchone()
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error accessing database"
                    )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Convert row tuple to dict
        user = {
            "id": row[0],
            "fullname": row[1],
            "email": row[2],
            "university": row[3],
            "password": row[4],
            "created_at": row[5]
        }
        
        # Verify password
        try:
            if not verify_password(credentials.password, user["password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error verifying password"
            )
        
        # Create access token
        try:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": credentials.email}, expires_delta=access_token_expires
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating access token"
            )
        
        # Return user data (without password)
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


# Serve static files (frontend) - must be after all API routes
try:
    app.mount("/", StaticFiles(directory="public", html=True), name="static")
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

