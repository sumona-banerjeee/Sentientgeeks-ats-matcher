from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey
from .database import Base
from datetime import datetime

class MatchingHistory(Base):
    __tablename__ = "matching_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    user_name = Column(String(255)) 
    
    job_title = Column(String(500))
    company_name = Column(String(500))
    total_resumes = Column(Integer)
    successful_matches = Column(Integer)
    top_candidate_name = Column(String(255))
    top_candidate_score = Column(Float)
    matching_summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'user_name': self.user_name,  
            'job_title': self.job_title,
            'company_name': self.company_name,
            'total_resumes': self.total_resumes,
            'successful_matches': self.successful_matches,
            'top_candidate_name': self.top_candidate_name,
            'top_candidate_score': self.top_candidate_score,
            'matching_summary': self.matching_summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }