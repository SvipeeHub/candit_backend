from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, ARRAY, event
from sqlalchemy.orm import relationship
from app.database import Base, SessionLocal
import datetime

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True)
    post_type = Column(String, index=True, default="text")
    post_url = Column(String)
    caption = Column(String)
    thumbnail=Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_anonymous = Column(Boolean, default=False)
    hash_tags = Column(ARRAY(String), default=[])
    language = Column(ARRAY(String), default=[])
    isHighlighted=Column(Boolean,default=False)
    shareCount = Column(Integer,default=0)
    user_id = Column(String, ForeignKey("users.candidate_id"))
    
    user = relationship("User", back_populates="posts")

@event.listens_for(Post, 'before_insert')
def set_post_id(mapper, connection, target):
    with SessionLocal() as db:
        last_post = db.query(Post).order_by(Post.id.desc()).first()
        if last_post:
            last_number = int(last_post.post_id.replace('CANDITPOST', ''))
            target.post_id = f'CANDITPOST{last_number + 1}'
        else:
            target.post_id = 'CANDITPOST100'