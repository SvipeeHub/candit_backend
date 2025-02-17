from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from fastapi import Form, UploadFile, File  # Move FastAPI imports here



class CreatePostRequest(BaseModel):
    post_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    caption: Optional[str] = Form(None),
    is_anonymous: bool = Form(False),
    hash_tags: str = Form("[]"),  
    language: str = Form("[]"),   
    thumbnail: Optional[UploadFile] = File(None),
    
    class Config:
        from_attributes = True


class HighlightPostsRequest(BaseModel):
    post_ids: List[str]


class PostResponse(BaseModel):
    id: int
    post_id:str
    post_type: str
    post_url: str | None = None
    caption: str | None = None
    thumbnail: str | None = None,
    shareCount:int
    created_at: datetime
    hash_tags: List[str] = []
    language: List[str] = []

    class Config:
        from_attributes = True

class MonthlyPosts(BaseModel):
    month: int
    month_name: str
    posts: List[PostResponse]

class YearlyPosts(BaseModel):
    year: int
    months: List[MonthlyPosts]

class HighlightedPostsResponse(BaseModel):
    status: str
    message: str
    status_code: str
    data: List[YearlyPosts]