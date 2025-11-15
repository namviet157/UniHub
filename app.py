import os
import shutil
import uvicorn
from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
import beanie
from typing import List
from beanie import PydanticObjectId 

MONGO_CONNECTION_STRING = "mongodb://localhost:27017"
DB_NAME = "UniHub_Courses"


class Document(beanie.Document):
    # ... (Model của bạn giữ nguyên) ...
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
    class Settings:
        name = "Courses"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... (Lifespan của bạn giữ nguyên) ...
    print("Bắt đầu khởi động server...")
    app.mongodb_client = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
    await beanie.init_beanie(
        database=app.mongodb_client[DB_NAME],
        document_models=[Document] 
    )
    print(f" Collection Beanie và MongoDB sucessful!")
    print(f"   - Database: {DB_NAME}")
    print(f"   - Collection: {Document.Settings.name}")
    yield 
    print("Starting to shut down the server...")
    app.mongodb_client.close()
    print("Disconnected from MongoDB.")


app = FastAPI(lifespan=lifespan)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
        university = university,
        faculty = faculty,
        course = course,
        documentTitle = documentTitle,
        description = description,
        documentType = documentType,
        tags = tags 
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



# === 1. API To get all data ===
@app.get("/documents/", response_model=List[Document])
async def get_all_documents():
    """
    Get ALL documents in the 'Courses' collection.
    """
    try:
        courses = await Document.find_all().to_list()
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/", StaticFiles(directory="public", html=True), name="public")


if __name__ == "__main__":
    print(f"Server is running at http://127.0.0.1:8000")
    print(f"Uploaded files will be saved in the directory: {os.path.abspath(UPLOAD_DIR)}")
    uvicorn.run(app, host="127.0.0.1", port=8000)