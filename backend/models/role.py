"""
Role (job requisition) model.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from backend.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    req_id = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)
    business_unit = Column(String, nullable=False)
    location = Column(String, nullable=False)
    openings = Column(Integer, default=1)
    applicants = Column(Integer, default=0)
    screened = Column(Integer, default=0)
    shortlisted = Column(Integer, default=0)
    interview = Column(Integer, default=0)
    offer = Column(Integer, default=0)
    hired = Column(Integer, default=0)
    days_open = Column(Integer, default=0)
    target_days = Column(Integer, default=30)
    risk = Column(String, default="Low")
    priority = Column(String, default="Medium")
    required_skills = Column(String, nullable=False)
    experience_min = Column(Integer, default=0)
    salary_band = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
