from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class JobDescription(Base):
    __tablename__ = "job_descriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    original_text = Column(Text, nullable=False)
    structured_data = Column(JSON)
    skills_weightage = Column(JSON)
    is_structured = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    session_id = Column(String(100), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matching_results = relationship("MatchingResult", back_populates="job_description")
    score_history = relationship("ATSScoreHistory", back_populates="job_description")

class JDStructuringSession(Base):
    __tablename__ = "jd_structuring_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True)
    jd_id = Column(Integer, index=True)
    current_structure = Column(JSON)
    revision_count = Column(Integer, default=0)
    user_feedback = Column(Text)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
