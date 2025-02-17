from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean,event
from sqlalchemy.orm import relationship
from app.database import Base,SessionLocal
import datetime

class School(Base):
    __tablename__ = "schools"
    
    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(String,index=True,unique=True)
    school_name = Column(String,index=True)
    school_address = Column(String)
    school_city = Column(String)
    school_state = Column(String)
    
    users = relationship("User", back_populates="school")


@event.listens_for(School, 'before_insert')
def set_candidate_id(mapper, connection, target):
    with SessionLocal() as db:
        last_school = db.query(School).order_by(School.id.desc()).first()
        if last_school:
            last_number = int(last_school.school_id.replace('SCH', ''))
            target.school_id = f'SCH{last_number + 1}'
        else:
            target.school_id = 'SCH100'