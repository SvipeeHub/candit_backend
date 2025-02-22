from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Enum, Index,Boolean,Text
from datetime import datetime
import enum
from app.database import Base
from sqlalchemy.orm import relationship



class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone_number = Column(String)
    user_id = Column(String, ForeignKey("users.candidate_id"))
    owner = relationship("User", back_populates="contacts")