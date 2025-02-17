from sqlalchemy import Column, Integer, String, DateTime,ForeignKey,Boolean,event
from datetime import datetime, timedelta
from app.database import Base,SessionLocal

class Dank(Base):
    __tablename__ = "danks"
    
    id = Column(Integer, primary_key=True)
    dank_id= Column(String,unique=True)
    sender_id = Column(String, ForeignKey("users.candidate_id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(String, ForeignKey("users.candidate_id", ondelete="CASCADE"), nullable=False)
    post_id = Column(String, ForeignKey("posts.post_id", ondelete='CASCADE'), nullable=True)
    message = Column(String, nullable=True)  # For message-type danks
    is_read = Column(Boolean, default=False)
    send_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=12*2))

@event.listens_for(Dank, 'before_insert')
def set_candidate_id(mapper, connection, target):
    with SessionLocal() as db:
        last_school = db.query(Dank).order_by(Dank.id.desc()).first()
        if last_school:
            last_number = int(last_school.dank_id.replace('DANK', ''))
            target.dank_id = f'DANK{last_number + 1}'
        else:
            target.dank_id = 'DANK100'