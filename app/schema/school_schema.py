from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SchoolData(BaseModel):
    schoolName:str
    schoolAddress:str
    pupil:str


class CreateSchoolRequest(BaseModel):
    school_name : str
    school_address : str
    school_city : str
    school_state : str
    
    class Config:
        from_attributes = True
    
