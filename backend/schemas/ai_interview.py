"""
AI Interview schemas.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel


class AIInterviewGenerateRequest(BaseModel):
    candidate_id: int
    role_id: int
    num_questions: int = 5
    difficulty: str = "Intermediate"
    focus_area: str = "Technical Skills"


class AIInterviewGenerateResponse(BaseModel):
    token: str
    test_url: str
    questions: List[str]
    status: str


class AIInterviewTestOut(BaseModel):
    candidate_name: str
    role_name: str
    difficulty: str
    focus_area: str
    questions: List[str]


class AIInterviewSubmitRequest(BaseModel):
    answers: List[str]


class AIInterviewSubmitResponse(BaseModel):
    message: str


class AIInterviewListItem(BaseModel):
    id: int
    candidate_name: str
    role_name: str
    difficulty: str
    focus_area: str
    status: str
    created_at: datetime


class AIInterviewReportOut(BaseModel):
    id: int
    candidate_name: str
    role_name: str
    questions: List[str]
    answers: List[str]
    report: dict
