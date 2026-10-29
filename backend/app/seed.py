"""Creates demo data. Run: python -m app.seed

All passwords are: pulse123
"""
from .db import Base, engine, SessionLocal
from . import models
from .auth import hash_password

PEOPLE_NORTHWIND = [
    # name, email, department, role, job_role, seniority
    ("Asha Rao", "asha@northwind.test", None, "admin", "manager", "lead"),
    ("Vikram Shah", "vikram@northwind.test", "Sales", "employee", "sales", "senior"),
    ("Neha Gupta", "neha@northwind.test", "Sales", "employee", "sales", "junior"),
    ("Rohan Mehta", "rohan@northwind.test", "Sales", "employee", "sales", "mid"),
    ("Priya Nair", "priya@northwind.test", "Support", "employee", "support", "junior"),
    ("Arjun Iyer", "arjun@northwind.test", "Support", "employee", "support", "senior"),
    ("Kavitha Menon", "kavitha@northwind.test", "Support", "employee", "support", "mid"),
    ("Dev Malhotra", "dev@northwind.test", "Engineering", "employee", "engineering", "lead"),
    ("Sara Thomas", "sara@northwind.test", "Engineering", "employee", "engineering", "mid"),
    ("Imran Khan", "imran@northwind.test", "HR", "employee", "manager", "senior"),
]
PEOPLE_BLUEPEAK = [
    ("Meera Pillai", "meera@bluepeak.test", None, "admin", "manager", "lead"),
    ("Tom Fernandes", "tom@bluepeak.test", "Stores", "employee", "sales", "mid"),
    ("Lina George", "lina@bluepeak.test", "Stores", "employee", "sales", "junior"),
    ("Kabir Das", "kabir@bluepeak.test", "Customer Care", "employee", "support", "senior"),
]


def seed_missing_demo_data(db):
    """Safely and idempotently seed missing demo organizations, departments,
    users, memberships, and baseline responses.

    Does NOT drop tables, overwrite existing passwords, delete records,
    or overwrite existing user responses/actions.
    """
    try:
        def get_or_create_org(name, depts):
            org = db.query(models.Organization).filter_by(name=name).first()
            is_new = False
            if not org:
                org = models.Organization(name=name)
                db.add(org)
                db.flush()
                is_new = True

            dept_map = {}
            for dn in depts:
                dept = db.query(models.Department).filter_by(org_id=org.id, name=dn).first()
                if not dept:
                    dept = models.Department(org_id=org.id, name=dn)
                    db.add(dept)
                    db.flush()
                dept_map[dn] = dept.id
            return org, dept_map, is_new

        nw, nw_depts, nw_is_new = get_or_create_org("Northwind Logistics", ["Sales", "Support", "Engineering", "HR"])
        bp, bp_depts, bp_is_new = get_or_create_org("Bluepeak Retail", ["Stores", "Customer Care"])

        users = {}

        def ensure_people(org, dept_map, people):
            for name, email, dept, role, job_role, seniority in people:
                clean_email = email.strip().lower()
                u = users.get(clean_email)
                if not u:
                    u = db.query(models.User).filter_by(email=clean_email).first()
                if not u:
                    u = models.User(name=name, email=clean_email, password_hash=hash_password("pulse123"))
                    db.add(u)
                    db.flush()
                users[clean_email] = u

                dept_id = dept_map.get(dept) if dept else None
                m = (
                    db.query(models.Membership)
                    .filter_by(user_id=u.id, org_id=org.id)
                    .first()
                )
                if not m:
                    m = models.Membership(
                        user_id=u.id,
                        org_id=org.id,
                        department_id=dept_id,
                        role=role,
                        job_role=job_role,
                        seniority=seniority,
                    )
                    db.add(m)
                    db.flush()

        ensure_people(nw, nw_depts, PEOPLE_NORTHWIND)
        ensure_people(bp, bp_depts, PEOPLE_BLUEPEAK)

        # A consultant who works with both companies
        ensure_people(nw, nw_depts, [("Ravi Kapoor", "ravi@consult.test", "HR", "employee", "manager", "senior")])
        ensure_people(bp, bp_depts, [("Ravi Kapoor", "ravi@consult.test", None, "admin", "manager", "senior")])

        # Some existing results so dashboards aren't empty (only on initial org creation)
        def answer(email, org, is_org_new, qid, text, score, reason=None, flags=None):
            if not is_org_new:
                return
            u = users.get(email.strip().lower())
            if not u:
                return
            m = db.query(models.Membership).filter_by(user_id=u.id, org_id=org.id).first()
            if not m:
                return
            existing = db.query(models.Response).filter_by(membership_id=m.id, question_id=qid).first()
            if not existing:
                db.add(models.Response(
                    membership_id=m.id,
                    question_id=qid,
                    answer=text,
                    score=score,
                    reason=reason,
                    flags=flags or [],
                ))

        answer("vikram@northwind.test", nw, nw_is_new, "common-freq", "Daily", 4)
        answer("vikram@northwind.test", nw, nw_is_new, "common-open", "Used ChatGPT to draft 20 follow-up emails and edited each one.", 4, "Regular use with editing.", [])
        answer("priya@northwind.test", nw, nw_is_new, "common-freq", "A few times a month", 2)
        answer("priya@northwind.test", nw, nw_is_new, "common-open", "Pasted a customer's complaint thread into ChatGPT to summarise it.", 3, "Useful summary but shared customer data.", ["customer_data_shared"])
        answer("tom@bluepeak.test", bp, bp_is_new, "common-freq", "A few times a week", 3)
        answer("kabir@bluepeak.test", bp, bp_is_new, "common-open", "Uploaded our full customer refund list to an AI tool to find patterns.", 3, "Good idea, unsafe data handling.", ["customer_data_shared", "confidential_data_shared"])
        answer("kabir@bluepeak.test", bp, bp_is_new, "common-freq", "Daily", 4)

        db.commit()
    except Exception:
        db.rollback()
        raise


def run():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_missing_demo_data(db)
    print("Seeded. Log in with any seeded email and password 'pulse123'.")


if __name__ == "__main__":
    run()
