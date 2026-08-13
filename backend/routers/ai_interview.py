"""
AI Interview generation and submission routes.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_role
from backend.database import get_db
from backend.models.ai_interview import AIInterview
from backend.models.candidate import Candidate
from backend.models.role import Role
from backend.models.user import User
from backend.schemas.ai_interview import (
    AIInterviewGenerateRequest,
    AIInterviewGenerateResponse,
    AIInterviewListItem,
    AIInterviewReportOut,
    AIInterviewSubmitRequest,
    AIInterviewSubmitResponse,
    AIInterviewTestOut,
)
from backend.services import ai_service

router = APIRouter(prefix="/api/ai-interview", tags=["AI Interview"])


@router.post("/generate", response_model=AIInterviewGenerateResponse)
async def generate_interview(
    body: AIInterviewGenerateRequest,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    # Verify candidate and role exist
    candidate = db.query(Candidate).filter(Candidate.id == body.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    role = db.query(Role).filter(Role.id == body.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Generate questions via LLM
    questions = await ai_service.generate_interview_questions(
        role_name=role.role,
        skills=candidate.skills,
        num_questions=body.num_questions,
        difficulty=body.difficulty,
        focus_area=body.focus_area,
    )

    # Create DB entry
    token = str(uuid.uuid4())
    interview = AIInterview(
        token=token,
        candidate_id=body.candidate_id,
        role_id=body.role_id,
        jd_skills=candidate.skills,
        difficulty=body.difficulty,
        focus_area=body.focus_area,
        num_questions=body.num_questions,
        questions=json.dumps(questions),
        status="pending",
    )
    db.add(interview)
    db.commit()
    
    test_url = f"/?page=ai_test&token={token}"
    
    return AIInterviewGenerateResponse(
        token=token,
        test_url=test_url,
        questions=questions,
        status="pending"
    )


@router.get("/test/{token}", response_model=AIInterviewTestOut)
def get_test_questions(token: str, db: Session = Depends(get_db)):
    """Public endpoint for candidates to fetch questions."""
    interview = db.query(AIInterview).filter(AIInterview.token == token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Test not found")
        
    if interview.status != "pending":
        raise HTTPException(status_code=400, detail="Test has already been completed")

    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    role = db.query(Role).filter(Role.id == interview.role_id).first()
    
    questions = json.loads(interview.questions) if interview.questions else []
    
    return AIInterviewTestOut(
        candidate_name=candidate.candidate if candidate else "Candidate",
        role_name=role.role if role else "Role",
        difficulty=interview.difficulty,
        focus_area=interview.focus_area,
        questions=questions,
    )


@router.post("/submit/{token}", response_model=AIInterviewSubmitResponse)
async def submit_test(
    token: str,
    body: AIInterviewSubmitRequest,
    db: Session = Depends(get_db),
):
    """Public endpoint for candidates to submit answers."""
    interview = db.query(AIInterview).filter(AIInterview.token == token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Test not found")
        
    if interview.status != "pending":
        raise HTTPException(status_code=400, detail="Test has already been completed")

    questions = json.loads(interview.questions) if interview.questions else []
    if len(body.answers) != len(questions):
        raise HTTPException(status_code=400, detail="Number of answers does not match number of questions")

    role = db.query(Role).filter(Role.id == interview.role_id).first()
    role_name = role.role if role else "Unknown Role"

    # Evaluate answers using LLM
    report = await ai_service.evaluate_interview_answers(
        questions=questions,
        answers=body.answers,
        role_name=role_name,
        skills=interview.jd_skills
    )

    # Update DB
    interview.answers = json.dumps(body.answers)
    interview.report = json.dumps(report)
    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return AIInterviewSubmitResponse(message="Test submitted successfully")


@router.get("/list", response_model=List[AIInterviewListItem])
def list_interviews(
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Recruiter endpoint to see all generated tests."""
    interviews = db.query(AIInterview).order_by(AIInterview.created_at.desc()).all()
    
    results = []
    for interview in interviews:
        candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
        role = db.query(Role).filter(Role.id == interview.role_id).first()
        
        results.append(
            AIInterviewListItem(
                id=interview.id,
                candidate_name=candidate.candidate if candidate else "Unknown",
                role_name=role.role if role else "Unknown",
                difficulty=interview.difficulty,
                focus_area=interview.focus_area,
                status=interview.status,
                created_at=interview.created_at,
            )
        )
    return results


@router.get("/report/{interview_id}", response_model=AIInterviewReportOut)
def get_report(
    interview_id: int,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Recruiter endpoint to view test report."""
    interview = db.query(AIInterview).filter(AIInterview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Test not found")
        
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    role = db.query(Role).filter(Role.id == interview.role_id).first()
    
    questions = json.loads(interview.questions) if interview.questions else []
    answers = json.loads(interview.answers) if interview.answers else []
    report = json.loads(interview.report) if interview.report else {}
    
    return AIInterviewReportOut(
        id=interview.id,
        candidate_name=candidate.candidate if candidate else "Unknown",
        role_name=role.role if role else "Unknown",
        questions=questions,
        answers=answers,
        report=report,
    )
