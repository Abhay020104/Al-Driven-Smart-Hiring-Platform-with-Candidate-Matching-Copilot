"""
AI endpoint request / response schemas.
"""

from typing import Optional

from pydantic import BaseModel

# ── JD Analyser ───────────────────────────────────────────────────────────────

class JDAnalyseRequest(BaseModel):
    jd_text: str


class JDAnalyseResponse(BaseModel):
    skills: list[str] = []
    seniority: str = "Any level"
    level_color: str = "#64748b"
    exp_years: int = 0
    flags: list[str] = []
    salary: str = "Unknown"
    word_count: int = 0
    tone_score: int = 50
    rewrite: str = "N/A"


# ── Resume parsing ────────────────────────────────────────────────────────────

class ResumeParseRequest(BaseModel):
    resume_text: str


class ResumeParseResponse(BaseModel):
    skills: list[str] = []
    exp_years: int = 0
    education: str = "Not specified"
    certifications: list[str] = []


# ── Resume scoring ────────────────────────────────────────────────────────────

class ResumeScoreRequest(BaseModel):
    resume_text: str
    role_id: int
    required_skills_override: Optional[list[str]] = None


class ResumeScoreResponse(BaseModel):
    match_score: int = 0
    coverage: int = 0
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    exp_ok: bool = False
    verdict: str = ""
    v_class: str = ""


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None  # optional extra context (e.g. candidate data)


class ChatResponse(BaseModel):
    reply: str


# ── Email generation ──────────────────────────────────────────────────────────

class EmailGenerateRequest(BaseModel):
    template_key: str  # interview_invite | offer_letter | rejection | follow_up
    candidate_id: int


class EmailGenerateResponse(BaseModel):
    subject: str
    body: str


# ── Hiring recommendation ────────────────────────────────────────────────────

class HiringRecommendationRequest(BaseModel):
    candidate_id: int


class HiringRecommendationResponse(BaseModel):
    recommendation: str  # Recommend | Waitlist | Decline
    confidence: str
    rationale: str


# ── Report generation ─────────────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    report_type: str  # recruitment_summary | pipeline_health | diversity | talent_gap
    format: str = "markdown"  # markdown | text


class ReportGenerateResponse(BaseModel):
    title: str
    content: str
