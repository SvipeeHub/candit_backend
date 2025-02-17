import os
from fastapi import UploadFile
import aiofiles
from uuid import uuid4
from datetime import datetime

UPLOAD_DIR = "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/mpeg", "video/quicktime"}

def create_upload_dir():
    """
    Create upload directories if they don't exist
    
    """
    for dir_type in ["images", "videos", "thumbnails"]:
        dir_path = os.path.join(UPLOAD_DIR, dir_type)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

async def save_upload_file(file: UploadFile, file_type: str) -> str:
    """
    Save uploaded file and return the file path
    
    """
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid4())[:8]
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{timestamp}_{unique_id}{file_extension}"
    
    # Determine directory based on file type
    sub_dir = "images" if file_type == "image" else "videos"
    save_dir = os.path.join(UPLOAD_DIR, sub_dir)
    file_path = os.path.join(save_dir, new_filename)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    return file_path
