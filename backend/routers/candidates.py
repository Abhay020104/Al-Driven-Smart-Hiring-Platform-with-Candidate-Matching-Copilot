"""
Candidates CRUD routes + self-service apply for Candidate role.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user, require_role
from backend.database import get_db
from backend.models.candidate import Candidate
from backend.models.user import User
from backend.schemas.candidate import (
    CandidateApplyRequest,
    CandidateCreate,
    CandidateOut,
    CandidateUpdate,
)

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


# ── Self-service for Candidate users ──────────────────────────────────────────

@router.post("/apply", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
def apply_for_job(
    body: CandidateApplyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A logged-in candidate applies for a job."""
    candidate = Candidate(
        user_id=user.id,
        candidate=user.name,
        role=body.role,
        location=body.location,
        experience=body.experience,
        availability=body.availability,
        skills=body.skills,
        education=body.education,
        certifications=body.certifications,
        summary=body.summary,
        match=body.match,
        skills_match=body.skills_match,
        resume_filename=body.resume_filename,
        source="Self-applied",
        stage="Screening",
        last_touch="Today",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/my-applications", response_model=list[CandidateOut])
def my_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View own applications (Candidate role)."""
    return (
        db.query(Candidate)
        .filter(Candidate.user_id == user.id)
        .order_by(Candidate.created_at.desc())
        .all()
    )


# ── Full CRUD (recruiter) ─────────────────────────────────────────────────────────

@router.get("", response_model=list[CandidateOut])
def list_candidates(
    role: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    q = db.query(Candidate)
    if role:
        q = q.filter(Candidate.role == role)
    if stage:
        q = q.filter(Candidate.stage.ilike(f"%{stage}%"))
    return q.order_by(Candidate.created_at.desc()).all()


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: int,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.post("", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
def create_candidate(
    body: CandidateCreate,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    candidate = Candidate(**body.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.put("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int,
    body: CandidateUpdate,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(candidate)
    db.commit()
