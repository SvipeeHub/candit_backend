from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from app.schema import api_response_schema as ApiSchema

class User(BaseModel):
    email:str
    userName:str
    firstName:str
    lastName:str
    anonymousId:str
    dob:str
    schoolId:str
    batch:str
    course:str
    phone:str
    gender:str

    class Config:
        from_attributes = True


class CreateUserResponse(BaseModel):
    status:str
    message:str
    status_code:str


class HiddenUsersRequest(BaseModel):
    hidden_user_ids: List[str]


class ContactBase(BaseModel):
    name: str
    phone_number: str

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

class ContactListCreate(BaseModel):
    contacts: List[ContactCreate]



class NameSuggestion(BaseModel):
    user_id: str
    name: str
    suggestion_type: str  # 'stalked', 'comrade', 'contact', 'friend_of_friend'
    gender: str
    profile_image_url: Optional[str]
    is_app_user: bool = True

class NameSuggestionResponse(ApiSchema.ApiResponse):
    data: List[NameSuggestion]