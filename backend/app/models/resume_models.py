from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from .database import Base
from datetime import datetime

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    extracted_text = Column(Text)
    structured_data = Column(JSON)
    skills_extracted = Column(JSON)
    experience_years = Column(Float)
    session_id = Column(String(100), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MatchingResult(Base):
    __tablename__ = "matching_results"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    jd_id = Column(Integer)
    resume_id = Column(Integer)
    overall_score = Column(Float)
    skill_match_score = Column(Float)
    experience_score = Column(Float)
    detailed_analysis = Column(JSON)
    rank_position = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)