"""
AI-powered endpoints — JD analysis, resume parsing/scoring, chat, email, recommendations, reports.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user, require_role
from backend.database import get_db
from backend.models.candidate import Candidate
from backend.models.role import Role
from backend.models.user import User
from backend.schemas.ai import (
    ChatRequest,
    ChatResponse,
    EmailGenerateRequest,
    EmailGenerateResponse,
    HiringRecommendationRequest,
    HiringRecommendationResponse,
    JDAnalyseRequest,
    JDAnalyseResponse,
    ReportGenerateRequest,
    ReportGenerateResponse,
    ResumeParseRequest,
    ResumeParseResponse,
    ResumeScoreRequest,
    ResumeScoreResponse,
)
from backend.services import ai_service

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/analyse-jd", response_model=JDAnalyseResponse)
async def analyse_jd(
    body: JDAnalyseRequest,
    user: User = Depends(require_role("recruiter")),
):
    result = await ai_service.analyse_jd(body.jd_text)
    return JDAnalyseResponse(**result)


@router.post("/parse-resume", response_model=ResumeParseResponse)
async def parse_resume(
    body: ResumeParseRequest,
    user: User = Depends(get_current_user),
):
    result = ai_service.parse_resume_text(body.resume_text)
    return ResumeParseResponse(**result)


@router.post("/score-resume", response_model=ResumeScoreResponse)
async def score_resume(
    body: ResumeScoreRequest,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == body.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    resume = ai_service.parse_resume_text(body.resume_text)
    result = await ai_service.score_resume_vs_role(
        resume, role, body.required_skills_override
    )
    return ResumeScoreResponse(**result)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
):
    reply = await ai_service.build_copilot_reply(
        body.message,
        context=body.context or "",
        user_role=user.role,
    )
    return ChatResponse(reply=reply)


@router.post("/generate-email", response_model=EmailGenerateResponse)
async def generate_email(
    body: EmailGenerateRequest,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(Candidate.id == body.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    subject, email_body = await ai_service.generate_email(body.template_key, candidate)
    return EmailGenerateResponse(subject=subject, body=email_body)


@router.post("/hiring-recommendation", response_model=HiringRecommendationResponse)
async def hiring_recommendation(
    body: HiringRecommendationRequest,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(Candidate.id == body.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    verdict, confidence, rationale = await ai_service.build_hiring_recommendation(candidate)
    return HiringRecommendationResponse(
        recommendation=verdict,
        confidence=confidence,
        rationale=rationale,
    )


@router.post("/generate-report", response_model=ReportGenerateResponse)
async def generate_report(
    body: ReportGenerateRequest,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    # Build summary data from database
    roles = db.query(Role).all()
    total_app = sum(r.applicants for r in roles)
    total_hire = sum(r.hired for r in roles)

    candidates = db.query(Candidate).all()
    avg_match = round(sum(c.match for c in candidates) / max(len(candidates), 1), 1)

    roles_data = {
        "total_applicants": total_app,
        "total_hired": total_hire,
        "avg_match": avg_match,
        "selected_roles": [r.role for r in roles],
    }

    title, content = await ai_service.generate_report(
        body.report_type, roles_data, "Current Period"
    )
    return ReportGenerateResponse(title=title, content=content)
