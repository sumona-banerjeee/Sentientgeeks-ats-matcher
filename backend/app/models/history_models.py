from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class MatchingSession(Base):
    """Main session tracking table"""
    __tablename__ = "matching_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True)
    session_name = Column(String(255), nullable=True)  # User-friendly name
    jd_title = Column(String(255), nullable=True)
    total_resumes = Column(Integer, default=0)
    processed_resumes = Column(Integer, default=0)
    status = Column(String(50), default="active")  # active, completed, deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    histories = relationship("MatchingHistory", back_populates="session", cascade="all, delete-orphan")
    results = relationship("MatchingResult", back_populates="session", cascade="all, delete-orphan")

class MatchingHistory(Base):
    """Detailed history of all matching operations"""
    __tablename__ = "matching_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("matching_sessions.session_id"), index=True)
    action_type = Column(String(50))  # 'jd_upload', 'jd_structure', 'resume_upload', 'matching_complete', 'result_view'
    action_description = Column(String(255))
    details = Column(JSON)  # Store detailed action data
    timestamp = Column(DateTime, default=datetime.utcnow)
    execution_time = Column(Float, nullable=True)  # Time taken for action
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    session = relationship("MatchingSession", back_populates="histories")

class ATSScoreHistory(Base):
    """Track ATS scores over time"""
    __tablename__ = "ats_score_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    jd_id = Column(Integer, ForeignKey("job_descriptions.id"))
    overall_score = Column(Float)
    skill_match_score = Column(Float)
    experience_score = Column(Float)
    education_score = Column(Float, nullable=True)
    keyword_match_score = Column(Float, nullable=True)
    detailed_breakdown = Column(JSON)  # Detailed scoring breakdown
    matching_algorithm_version = Column(String(50), default="v1.0")
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    resume = relationship("Resume")
    job_description = relationship("JobDescription")

class ExportHistory(Base):
    """Track file exports"""
    __tablename__ = "export_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    export_type = Column(String(50))  # 'json', 'csv', 'pdf'
    file_name = Column(String(255))
    file_path = Column(String(500), nullable=True)
    export_data = Column(JSON)  # What data was exported
    created_at = Column(DateTime, default=datetime.utcnow)
    downloaded = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
