from app import models
from app.db import SessionLocal
from app.auth import hash_password
from tests.conftest import login


def _seed_custom_department(client, dept_name, participant_count, responses_per_user=1):
    """Helper to seed a department with an exact number of completed participants."""
    db = SessionLocal()
    org = db.query(models.Organization).filter_by(name="Northwind Logistics").first()
    dept = models.Department(org_id=org.id, name=dept_name)
    db.add(dept)
    db.flush()
    dept_id = dept.id

    for i in range(participant_count):
        email = f"{dept_name.lower().replace(' ', '_')}_{i}@northwind.test"
        u = models.User(name=f"User {i}", email=email, password_hash=hash_password("pulse123"))
        db.add(u)
        db.flush()

        m = models.Membership(
            user_id=u.id,
            org_id=org.id,
            department_id=dept_id,
            role="employee",
            job_role="engineering",
            seniority="mid",
        )
        db.add(m)
        db.flush()

        # Add responses (possibly multiple to test distinct counting)
        for r_idx in range(responses_per_user):
            resp = models.Response(
                membership_id=m.id,
                question_id=f"q_{r_idx}",
                answer="Sample answer",
                score=4.0,
                flags=["unreviewed_output"] if i == 0 else [],
            )
            db.add(resp)

    db.commit()
    db.close()
    return dept_id


def test_department_with_0_participants(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    _seed_custom_department(client, "Research0", participant_count=0)
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    # 0 participants should not appear individually
    assert "Research0" not in depts
    assert "Other teams" in depts


def test_department_with_1_participant(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    _seed_custom_department(client, "Research1", participant_count=1)
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    assert "Research1" not in depts
    assert "Other teams" in depts


def test_department_with_4_participants(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    _seed_custom_department(client, "Research4", participant_count=4)
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    # 4 participants is below threshold 5 -> must not be exposed individually
    assert "Research4" not in depts


def test_department_with_5_participants_is_exposed(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    _seed_custom_department(client, "QualityAssurance5", participant_count=5)
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    # Exactly 5 participants -> visible individually
    assert "QualityAssurance5" in depts
    qa = depts["QualityAssurance5"]
    assert qa["responded"] == 5
    assert qa["average_score"] == 4.0
    assert qa["level"] == "Leader"


def test_department_with_greater_than_5_participants(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    _seed_custom_department(client, "Operations7", participant_count=7)
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    assert "Operations7" in depts
    op = depts["Operations7"]
    assert op["responded"] == 7
    assert op["average_score"] == 4.0


def test_duplicate_answers_do_not_inflate_participant_count(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    # 3 participants, but each participant answers 5 times (total 15 rows)
    _seed_custom_department(client, "DevOps3", participant_count=3, responses_per_user=5)
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    # Despite 15 response rows, there are only 3 distinct participants -> below threshold 5
    assert "DevOps3" not in depts


def test_suppressed_group_aggregation_prevents_individual_score_leakage(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    # Only 2 participants total in small departments
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = {d["department"]: d for d in r.json()["departments"]}
    other = depts.get("Other teams")
    assert other is not None
    # Because total in other_teams is 2 (< 5), average score must be None
    assert other["average_score"] is None
    assert other["level"] == "Not assessed"
    # And top_risks must be empty to avoid attributing flags to those 2 individuals
    assert r.json()["top_risks"] == []
