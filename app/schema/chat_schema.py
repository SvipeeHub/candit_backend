
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class ChatCreate(BaseModel):
    receiver_id: str

class ChatResponse(BaseModel):
    id: int
    sender_id: str
    receiver_id: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class MessageCreate(BaseModel):
    content: str
    chat_id: int

class MessageResponse(BaseModel):
    id: int
    content: str
    sender_id: str
    chat_id: int
    created_at: datetime
    is_read: bool
    
    class Config:
        orm_mode = True
