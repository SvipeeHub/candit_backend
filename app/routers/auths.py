from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Otp_model as models,User_model as userModels
from app.util.generateJwt import create_jwt_token,verify_jwt_token
from app.schema import auth_schema as schemas
from app.database import get_db
from datetime import datetime
import random
import string
import httpx
import os
router = APIRouter(prefix="/auth", tags=["auth"])

API_KEY = os.getenv("TWOFACTOR_API_KEY")
BASE_URL = "https://2factor.in/API/V1"

async def send_otp(phone: str, otp: str) -> bool:
    '''
        Sending OTP to the user phone using 2 Factor 
    '''
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/{API_KEY}/SMS/{phone}/{otp}/OTP1"
            )
            return response.status_code == 200
        except Exception as e:
            print(f"OTP sending failed: {str(e)}")
            return False

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


@router.post("/generate", response_model=schemas.OtpResponse)
async def generate_otp_route(request: schemas.PhoneInput, db: Session = Depends(get_db)):
    '''
            We generate the OTP and first save it to data base and then send message 
            to the user phone.
    '''
    existing_otp = db.query(models.OTP).filter(
       models.OTP.phone == request.phone,
       models.OTP.expires_at > datetime.utcnow()
            ).first()
   
    if existing_otp:
       return {
           "status": "SUCCESS",
           "alreadyValid": True,
           
       }

    otp_code = generate_otp()
    
    # Delete existing OTPs for this email
    db.query(models.OTP).filter(models.OTP.phone == request.phone).delete()

    success = await send_otp(request.phone, otp_code)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send OTP")


    # Create new OTP
    db_otp = models.OTP(
        phone=request.phone,
        otp_code=otp_code
    )
    db.add(db_otp)
    db.commit()
    
    # In production, send OTP via email
    return {
        "status":"SUCCESS",
        "alreadyValid":False
        }

@router.post("/verify", response_model=schemas.VerifyOtpResonponse)
def verify_otp(request: schemas.VerifyOtpRequest, db: Session = Depends(get_db)):
   existing_user = db.query(userModels.User).filter(
       userModels.User.phone == request.phone
   ).first()

   otp = db.query(models.OTP).filter(
       models.OTP.phone == request.phone,
       models.OTP.otp_code == request.otp
   ).first()

   if not otp:
       raise HTTPException(status_code=400, detail="Invalid OTP")

   if datetime.utcnow() > otp.expires_at:
       db.delete(otp)
       db.commit()
       raise HTTPException(status_code=400, detail="OTP expired")

   db.delete(otp)
   db.commit()

   if existing_user:
       jwt_token = create_jwt_token(existing_user.candidate_id)
       return {
           "status": schemas.result.SUCCESS,
           "type": schemas.verfiyType.LOGIN,
           "token": jwt_token,
           
       }
   
   return {
       "status": schemas.result.SUCCESS,
       "type": schemas.verfiyType.REGISTER
   }


@router.get("/protected_test")
def protected_route(user_id: int = Depends(verify_jwt_token)):
    '''
      just testing the jwt token
    '''
    return {"user_id": user_id}