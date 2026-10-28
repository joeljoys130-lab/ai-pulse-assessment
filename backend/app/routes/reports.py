from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level
from ..services.actions import generate_action_plan

router = APIRouter(prefix="/reports", tags=["reports"])

NEXT_STEPS = {
    "support": ["Use AI to draft first replies, then edit", "Summarise long ticket threads before escalating", "Never paste customer details into public chatbots"],
    "engineering": ["Use a code assistant for tests and refactors", "Review every AI suggestion before merging", "Keep secrets and customer data out of prompts"],
    "sales": ["Draft outreach emails with AI and personalise them", "Summarise call notes into CRM updates", "Check AI-written claims before sending"],
    "manager": ["Agree an AI usage policy with your team", "Pick one workflow per quarter to improve with AI", "Track time saved, not tool licences"],
}


@router.get("/me")
def my_report(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    scores = [r.score for r in rows if r.score is not None]
    avg = sum(scores) / len(scores) if scores else None
    flags = sorted({f for r in rows for f in (r.flags or [])})
    return {
        "name": m.user.name,
        "organization": m.org.name,
        "answered": len(rows),
        "average_score": round(avg, 2) if avg is not None else None,
        "level": maturity_level(avg),
        "risks": flags,
        "next_steps": NEXT_STEPS.get(m.job_role, NEXT_STEPS["manager"]),
    }


@router.get("/actions")
def my_action_plan(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Returns 3 deterministic, prioritized improvement actions tailored to the employee's diagnostic results."""
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    actions = generate_action_plan(rows, m.job_role)

    # Check which actions this employee has marked completed
    completed_rows = db.query(models.CompletedAction).filter_by(membership_id=m.id).all()
    completed_map = {c.action_id: c.completed_at.isoformat() for c in completed_rows}

    for action in actions:
        action["completed"] = action["id"] in completed_map
        action["completed_at"] = completed_map.get(action["id"])

    return actions


@router.post("/actions/{action_id}/toggle")
def toggle_action_completion(action_id: str, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Toggles completion state of a recommended action for the authenticated employee."""
    existing = (
        db.query(models.CompletedAction)
        .filter_by(membership_id=m.id, action_id=action_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        return {"action_id": action_id, "completed": False}
    else:
        new_entry = models.CompletedAction(membership_id=m.id, action_id=action_id)
        db.add(new_entry)
        db.commit()
        return {"action_id": action_id, "completed": True}


@router.delete("/me")
def delete_my_report(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Delete all diagnostic answers and report data for the authenticated employee in this organization."""
    try:
        deleted = db.query(models.Response).filter_by(membership_id=m.id).delete()
        db.query(models.CompletedAction).filter_by(membership_id=m.id).delete()
        db.commit()
        return {
            "deleted": deleted,
            "message": "All diagnostic answers and report data deleted",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to delete report data: {str(e)}")
