# import os
# import shutil
# import uvicorn
# from fastapi import FastAPI, File, UploadFile
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import JSONResponse, RedirectResponse

# app = FastAPI()

# # Thư mục để lưu file upload
# UPLOAD_DIR = "uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# # Form trong 'public/upload.html' sẽ gọi đến đường dẫn này
# @app.post("/uploadfile/")
# async def create_upload_file(file: UploadFile = File(...)):
    
#     # Tạo đường dẫn an toàn để lưu file
#     file_path = os.path.join(UPLOAD_DIR, file.filename)
    
#     try:
#         # Lưu file vào thư mục 'uploads'
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#     except Exception as e:
#         # Nếu có lỗi, trả về JSON lỗi
#         return JSONResponse(status_code=500, content={"detail": f"Do not save file: {e}"})
#     finally:
#         file.file.close() # Luôn đóng file sau khi xử lý

#     # Trả về JSON thông báo thành công
#     # (JavaScript trong upload.html sẽ nhận và hiển thị)
#     return JSONResponse(content={
#         "filename": file.filename, 
#         "status": "has been uploaded successfully", 
#         "saved_path": file_path
#     })



# app.mount("/", StaticFiles(directory="public", html=True), name="public")


# if __name__ == "__main__":
#     print(f"Server is running at http://127.0.0.1:8000")
#     print(f"Uploaded files will be saved in the directory: {os.path.abspath(UPLOAD_DIR)}")
#     uvicorn.run(app, host="127.0.0.1", port=8000)

import os
import shutil
import uvicorn
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
import beanie

# ===================================================================
# === CẤU HÌNH DATABASE (ĐÃ CẬP NHẬT) ===
# ===================================================================

# THAY ĐỔI 1: Đây là chuỗi kết nối tới server local của bạn
MONGO_CONNECTION_STRING = "mongodb://localhost:27017"

# THAY ĐỔI 2: Đây là tên Database bạn đã tạo
DB_NAME = "UniHub_Courses"

# ===================================================================
# === 1. ĐỊNH NGHĨA MODEL (SCHEMA) ===
# ===================================================================

class Document(beanie.Document):
    # Model này định nghĩa cấu trúc dữ liệu cho file upload
    filename: str = Field(..., index=True)
    saved_path: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        # THAY ĐỔI 3: Đây là tên Collection bạn đã tạo
        name = "Courses"

# ===================================================================
# === 2. LIFESPAN: Khởi tạo Beanie ===
# ===================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Bắt đầu khởi động server...")
    
    # 1. Khởi tạo MongoDB client (dùng chuỗi kết nối mới)
    app.mongodb_client = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
    
    # 2. Khởi tạo Beanie (dùng tên DB mới)
    await beanie.init_beanie(
        database=app.mongodb_client[DB_NAME],
        document_models=[Document]  # Báo cho Beanie dùng model 'Document'
    )
    
    print(f"🎉 Kết nối Beanie và MongoDB thành công!")
    print(f"   - Database: {DB_NAME}")
    print(f"   - Collection: {Document.Settings.name}")

    yield 

    print("Bắt đầu tắt server...")
    app.mongodb_client.close()
    print("Đã ngắt kết nối MongoDB.")


# ===================================================================
# === KHỞI TẠO APP FASTAPI ===
# ===================================================================

app = FastAPI(lifespan=lifespan)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ===================================================================
# === 3. API ENDPOINT (Giữ nguyên) ===
# ===================================================================

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    """
    Lưu file vào thư mục 'uploads' VÀ
    lưu thông tin vào Collection 'Courses' trong DB 'UniHub_Courses'.
    """
    
    # 1. Lưu file vào thư mục
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Không thể lưu file: {e}"})
    finally:
        file.file.close()

    # 2. Tạo một đối tượng Document (dùng Model)
    doc = Document(
        filename=file.filename,
        saved_path=file_path,
        content_type=file.content_type,
        size_bytes=file_size
    )

    # 3. Thêm vào MongoDB
    try:
        await doc.insert()
        
        return JSONResponse(content={
            "status": "đã upload thành công",
            "filename": doc.filename, 
            "mongo_id": str(doc.id) 
        })
        
    except Exception as e:
        print(f"Lỗi khi lưu vào MongoDB: {e}")
        return JSONResponse(status_code=500, content={
            "detail": f"Lưu file thành công nhưng không thể lưu vào database: {e}"
        })

# ===================================================================
# === PHỤC VỤ FILE TĨNH (HTML, CSS, JS) ===
# ===================================================================
app.mount("/", StaticFiles(directory="public", html=True), name="public")


# ===================================================================
# === CHẠY SERVER ===
# ===================================================================
if __name__ == "__main__":
    print(f"Server đang chạy tại http://127.0.0.1:8000")
    print(f"File upload sẽ được lưu tại thư mục: {os.path.abspath(UPLOAD_DIR)}")
    uvicorn.run(app, host="127.0.0.1", port=8000)