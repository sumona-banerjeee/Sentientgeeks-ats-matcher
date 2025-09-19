from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
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
    processing_status = Column(String(50), default="uploaded")  # uploaded, processed, analyzed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    matching_results = relationship("MatchingResult", back_populates="resume")
    score_history = relationship("ATSScoreHistory", back_populates="resume")

class MatchingResult(Base):
    __tablename__ = "matching_results"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("matching_sessions.session_id"), index=True)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    overall_score = Column(Float)
    skill_match_score = Column(Float)
    experience_score = Column(Float)
    detailed_analysis = Column(JSON)
    rank_position = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("MatchingSession", back_populates="results")
    resume = relationship("Resume", back_populates="matching_results")
    job_description = relationship("JobDescription", back_populates="matching_results")
