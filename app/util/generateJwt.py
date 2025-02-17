from jose import jwt
import datetime

from fastapi import HTTPException,Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SECRET_KEY = "klasdfoi20oasdlkfjaasdlafiqfpa"
ALGORITHM = "HS256" 

security = HTTPBearer()

def create_jwt_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except JWTError:
        raise HTTPExcetpion(status_code=401, detail="Invalid token")