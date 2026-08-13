"""
Role (job requisition) schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RoleBase(BaseModel):
    req_id: str
    role: str
    business_unit: str
    location: str
    openings: int = 1
    applicants: int = 0
    screened: int = 0
    shortlisted: int = 0
    interview: int = 0
    offer: int = 0
    hired: int = 0
    days_open: int = 0
    target_days: int = 30
    risk: str = "Low"
    priority: str = "Medium"
    required_skills: str = ""
    experience_min: int = 0
    salary_band: str = ""


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    role: Optional[str] = None
    business_unit: Optional[str] = None
    location: Optional[str] = None
    openings: Optional[int] = None
    applicants: Optional[int] = None
    screened: Optional[int] = None
    shortlisted: Optional[int] = None
    interview: Optional[int] = None
    offer: Optional[int] = None
    hired: Optional[int] = None
    days_open: Optional[int] = None
    target_days: Optional[int] = None
    risk: Optional[str] = None
    priority: Optional[str] = None
    required_skills: Optional[str] = None
    experience_min: Optional[int] = None
    salary_band: Optional[str] = None


class RoleOut(RoleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RolePublicOut(BaseModel):
    """Limited fields visible to candidates browsing open positions."""
    id: int
    req_id: str
    role: str
    business_unit: str
    location: str
    openings: int
    required_skills: str
    experience_min: int
    salary_band: str

    class Config:
        from_attributes = True
