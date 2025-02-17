from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


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