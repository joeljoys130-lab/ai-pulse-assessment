from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MIN_PRIVACY_THRESHOLD = 5


def level_for(avg):
    if avg is None:
        return "Not assessed"
    if avg < 1.5:
        return "Beginner"
    if avg < 2.5:
        return "Exploring"
    if avg < 3.5:
        return "Practitioner"
    return "Leader"


@router.get("")
def org_dashboard(org_id: int, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")
    if m.org_id != org_id:
        raise HTTPException(403, "Cannot access data for another organization")

    org = db.get(models.Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")

    members = db.query(models.Membership).filter_by(org_id=org_id).all()
    departments = []
    all_flags = {}

    other_employees = 0
    other_responded = 0
    other_scores = []
    has_small_depts = False

    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        dept_member_ids = [x.id for x in dept_members]

        dept_scores = []
        responded_member_ids = set()

        if dept_member_ids:
            responses = (
                db.query(models.Response)
                .filter(models.Response.membership_id.in_(dept_member_ids))
                .all()
            )
            for r in responses:
                responded_member_ids.add(r.membership_id)
                if r.score is not None:
                    dept_scores.append(r.score)
                for f in r.flags or []:
                    all_flags[f] = all_flags.get(f, 0) + 1

        responded_count = len(responded_member_ids)

        # Department-level privacy threshold:
        # If fewer than 5 people completed the diagnostic, do not display individually.
        if responded_count >= MIN_PRIVACY_THRESHOLD:
            avg = sum(dept_scores) / len(dept_scores) if dept_scores else None
            departments.append({
                "department": dept.name,
                "employees": len(dept_members),
                "responded": responded_count,
                "average_score": round(avg, 2) if avg is not None else None,
                "level": level_for(avg),
            })
        else:
            has_small_depts = True
            other_employees += len(dept_members)
            other_responded += responded_count
            other_scores.extend(dept_scores)

    # Include unassigned members (e.g. admins or members without a department) in other_teams
    unassigned_members = [x for x in members if x.department_id is None]
    if unassigned_members:
        unassigned_ids = [x.id for x in unassigned_members]
        unassigned_responses = (
            db.query(models.Response)
            .filter(models.Response.membership_id.in_(unassigned_ids))
            .all()
        )
        unassigned_responded = {r.membership_id for r in unassigned_responses}
        for r in unassigned_responses:
            if r.score is not None:
                other_scores.append(r.score)
            for f in r.flags or []:
                all_flags[f] = all_flags.get(f, 0) + 1
        other_employees += len(unassigned_members)
        other_responded += len(unassigned_responded)

    if has_small_depts or (unassigned_members and other_employees > 0):
        # Prevent leakage: only calculate and reveal scores if aggregate group meets privacy threshold
        if other_responded >= MIN_PRIVACY_THRESHOLD and other_scores:
            other_avg = round(sum(other_scores) / len(other_scores), 2)
            other_level = level_for(other_avg)
        else:
            other_avg = None
            other_level = "Not assessed"

        departments.append({
            "department": "Other teams",
            "employees": other_employees,
            "responded": other_responded,
            "average_score": other_avg,
            "level": other_level,
        })

    # Total diagnostic respondents across the organization
    total_org_responded = sum(d["responded"] for d in departments)

    # Privacy protection for top risks:
    # If the organization as a whole has fewer than 5 respondents, do not expose top risks
    top_risks = (
        sorted(all_flags.items(), key=lambda kv: -kv[1])[:5]
        if total_org_responded >= MIN_PRIVACY_THRESHOLD
        else []
    )

    return {
        "organization": org.name,
        "departments": departments,
        "top_risks": top_risks,
    }
