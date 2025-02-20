from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Enum, Index,Boolean,Text
from datetime import datetime
import enum
from app.database import Base
from sqlalchemy.orm import relationship


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    sender_id = Column(String, ForeignKey("users.candidate_id"))
    chat_id = Column(Integer, ForeignKey("chats.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    sender = relationship("User", back_populates="messages")
    chat = relationship("Chat", back_populates="messages")