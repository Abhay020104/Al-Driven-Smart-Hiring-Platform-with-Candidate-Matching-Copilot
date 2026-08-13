"""
Candidate model.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from backend.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # FK to users.id if candidate registered
    candidate = Column(String, nullable=False)  # display name
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=False)
    location = Column(String, default="")
    experience = Column(Float, default=0.0)
    match = Column(Integer, default=0)
    skills_match = Column(Integer, default=0)
    stage = Column(String, default="Screening")
    availability = Column(String, default="")
    salary_fit = Column(String, default="")
    risk = Column(String, default="Low")
    skills = Column(String, default="")
    source = Column(String, default="")
    last_touch = Column(String, default="")
    education = Column(String, default="")
    certifications = Column(String, default="")
    summary = Column(String, default="")
    resume_filename = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
