from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Enum, Index,Boolean
from datetime import datetime
import enum
from app.database import Base
from sqlalchemy.orm import relationship


class FriendshipStatus(enum.Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'

class Friendship(Base):
    __tablename__ = "friendships"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.candidate_id"), nullable=False)
    friend_id = Column(String, ForeignKey("users.candidate_id"), nullable=False)
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING)
    action_user_id = Column(String, ForeignKey("users.candidate_id"))  # Who performed the last action
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    isHomies = Column(Boolean,default=False)
    isBolcked = Column(Boolean,default=False)
    isRestricted = Column(Boolean,default=False)
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="friendships")
    friend = relationship("User", foreign_keys=[friend_id], back_populates="friend_of")
    
    # Indexes for faster queries
    __table_args__ = (
        Index('idx_friendship_users', user_id, friend_id, unique=True),
        Index('idx_friendship_status', status),
    )