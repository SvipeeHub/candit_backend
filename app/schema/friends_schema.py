# schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import enum

class FriendshipStatus(enum.Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'

class UserBasicInfo(BaseModel):
    id: int
    username: str
    profile_image_url: Optional[str]

    class Config:
        orm_mode = True

class FriendRequestItem(BaseModel):
    id: int
    username: str
    first_name:str
    last_name:str
    isAnonymous:str
    profile_image_url: Optional[str]=None
    last_seen: Optional[datetime]=None
    # is_online: bool

    class Config:
        orm_mode = True

class FriendResponse(BaseModel):
    items: List[FriendRequestItem]
    total: int
    page: int
    pages: int

    class Config:
        orm_mode = True

class FriendRequestResponse(BaseModel):
    status: str
    message: str

    class Config:
        orm_mode = True

class FriendSuggestionResponse(BaseModel):
    id: int
    username: str
    profile_image_url: Optional[str]

    class Config:
        orm_mode = True

# Additional response models for success/error messages
class MessageResponse(BaseModel):
    message: str

    class Config:
        orm_mode = True