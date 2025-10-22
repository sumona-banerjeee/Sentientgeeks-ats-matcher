from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from .database import Base
from datetime import datetime

class JDLibrary(Base):
    """
    Stores reusable job descriptions for multiple matching sessions
    """
    __tablename__ = "jd_library"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User who created this JD
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    user_name = Column(String(255))  # For display purposes
    
    # JD Basic Info
    jd_name = Column(String(500), nullable=False)  # Custom name for easy identification
    job_title = Column(String(500))
    company_name = Column(String(500))
    location = Column(String(500))
    job_type = Column(String(100))  # Full-time, Part-time, Contract, etc.
    
    # JD Content
    original_text = Column(Text, nullable=False)  # Original JD text
    structured_data = Column(JSON)  # Structured JD data
    skills_weightage = Column(JSON)  # Pre-configured skills weightage
    
    # Metadata
    is_active = Column(Boolean, default=True)  # Can be archived
    usage_count = Column(Integer, default=0)  # How many times used
    last_used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Tags for easy search
    tags = Column(JSON)  # ["python", "senior", "remote", etc.]
    notes = Column(Text)  # Private notes for HR
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'jd_name': self.jd_name,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'location': self.location,
            'job_type': self.job_type,
            'structured_data': self.structured_data,
            'skills_weightage': self.skills_weightage,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': self.tags,
            'notes': self.notes
        }


class JDUsageHistory(Base):
    """
    Tracks which sessions used which library JDs
    """
    __tablename__ = "jd_usage_history"
    
    id = Column(Integer, primary_key=True, index=True)
    jd_library_id = Column(Integer, ForeignKey('jd_library.id'), index=True)
    session_id = Column(String(100), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    resumes_processed = Column(Integer, default=0)
    top_candidate_score = Column(Integer, nullable=True)
    
    used_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'jd_library_id': self.jd_library_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'resumes_processed': self.resumes_processed,
            'top_candidate_score': self.top_candidate_score,
            'used_at': self.used_at.isoformat() if self.used_at else None
        }