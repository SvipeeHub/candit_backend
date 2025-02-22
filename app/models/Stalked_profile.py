from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Enum, Index,Boolean,Text
from datetime import datetime
import enum
from app.database import Base
from sqlalchemy.orm import relationship



class UserStalk(Base):
    __tablename__ = "user_stalks"
    
    id = Column(Integer, primary_key=True, index=True)
    stalker_id = Column(String, ForeignKey("users.candidate_id"))
    stalked_id = Column(String, ForeignKey("users.candidate_id"))
    stalk_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)