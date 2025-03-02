from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, event
from sqlalchemy.orm import relationship
from app.database import Base, SessionLocal
import datetime
from app.models.Friendship_model import Friendship
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, unique=True)
    email = Column(String, unique=True)
    phone=Column(String,unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user_name = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    anonymous_id = Column(String)
    profile_image_url = Column(String)
    dob = Column(String)
    batch = Column(String)
    course = Column(String)
    gender=Column(String)
    school_id = Column(String, ForeignKey("schools.school_id"))
    
    school = relationship("School", back_populates="users")
    posts = relationship("Post", back_populates="user")
    friendships = relationship("Friendship",foreign_keys=[Friendship.user_id]  ,back_populates="user")
    friend_of = relationship("Friendship",foreign_keys=[Friendship.friend_id] ,back_populates="friend")
    sent_chats = relationship("Chat", foreign_keys="Chat.sender_id", back_populates="sender")
    received_chats = relationship("Chat", foreign_keys="Chat.receiver_id", back_populates="receiver")
    messages = relationship("Message", back_populates="sender")
    # comments = relationship("Comment", back_populates="user")

@event.listens_for(User, 'before_insert')
def set_candidate_id(mapper, connection, target):
    with SessionLocal() as db:
        last_user = db.query(User).order_by(User.id.desc()).first()
        if last_user:
            last_number = int(last_user.candidate_id.replace('CANDIT', ''))
            target.candidate_id = f'CANDIT{last_number + 1}'
        else:
            target.candidate_id = 'CANDIT100'