"""
AI Interview model.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.database import Base


class AIInterview(Base):
    __tablename__ = "ai_interviews"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    candidate_id = Column(Integer, nullable=False)
    role_id = Column(Integer, nullable=False)
    
    # Generation parameters
    jd_skills = Column(String, default="")
    difficulty = Column(String, default="Intermediate")
    focus_area = Column(String, default="Technical Skills")
    num_questions = Column(Integer, default=5)
    
    # Data payloads (JSON stored as text)
    questions = Column(Text, nullable=True)
    answers = Column(Text, nullable=True)
    report = Column(Text, nullable=True)
    
    # State
    status = Column(String, default="pending")  # pending, completed
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
