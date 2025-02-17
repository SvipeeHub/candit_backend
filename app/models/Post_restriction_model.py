from sqlalchemy import Column, String, Integer, ARRAY, ForeignKey
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from app.database import Base

class PostRestriction(Base):
    __tablename__ = "userpostrestriction"
    
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(String, ForeignKey("users.candidate_id", ondelete="CASCADE"), nullable=False)
    comrades_hidden_from = Column(ARRAY(String), nullable=True, server_default="{}") 
    public_hidden_from = Column(ARRAY(String), nullable=True, server_default="{}")  # Array of user IDs
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))