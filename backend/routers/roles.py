"""
Roles (job requisition) CRUD routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_role
from backend.database import get_db
from backend.models.role import Role
from backend.models.user import User
from backend.schemas.role import RoleCreate, RoleOut, RolePublicOut, RoleUpdate

router = APIRouter(prefix="/api/roles", tags=["Roles"])


# ── Public endpoint for candidates browsing open jobs ─────────────────────────

@router.get("/public", response_model=list[RolePublicOut])
def list_public_roles(db: Session = Depends(get_db)):
    """Open positions visible to anyone (including candidates)."""
    return db.query(Role).order_by(Role.created_at.desc()).all()


# ── Full CRUD (recruiter) ─────────────────────────────────────────────────────────

@router.get("", response_model=list[RoleOut])
def list_roles(
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    return db.query(Role).order_by(Role.created_at.desc()).all()


@router.get("/{role_id}", response_model=RoleOut)
def get_role(
    role_id: int,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    body: RoleCreate,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    existing = db.query(Role).filter(Role.req_id == body.req_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Req ID already exists")
    role = Role(**body.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    body: RoleUpdate,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
