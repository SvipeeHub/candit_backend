from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class DankBase(BaseModel):
    receiver_id: str

class PostDankCreate(DankBase):
    post_id:Optional[str] = None
    message:Optional[str] = None

class MessageDankCreate(DankBase):
    message: str

class DankResponse(BaseModel):
    id: int
    sender_id: str
    receiver_id: str
    post_id: Optional[str]
    message: Optional[str]
    is_read: bool
    send_at: datetime
    expires_at: datetime
    
    class Config:
        from_attributes = True