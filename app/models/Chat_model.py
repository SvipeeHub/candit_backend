from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Enum, Index,Boolean
from datetime import datetime
import enum
from app.database import Base
from sqlalchemy.orm import relationship




class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String, ForeignKey("users.candidate_id"))
    receiver_id = Column(String, ForeignKey("users.candidate_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_chats")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_chats")
    messages = relationship("Message", back_populates="chat")
