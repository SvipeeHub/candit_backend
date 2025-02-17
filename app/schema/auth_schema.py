from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum

class result(Enum):
    SUCCESS='sucess',
    FAILED='failed',
    PROCESSING='processing'

class verfiyType(Enum):
    LOGIN='login',
    REGISTER='register'



class PhoneInput(BaseModel):
    phone:str

class OtpResponse(BaseModel):
    status:str
    alreadyValid:bool

class VerifyOtpRequest(BaseModel):
    otp:str
    phone:str

class VerifyOtpResonponse(BaseModel):
    status:result
    type:verfiyType
    token: Optional[str] = None