from datetime import datetime, timedelta, timezone
import jwt
from app.config import SECRET_KEY
from tests.conftest import login


def test_valid_login(client):
    r = client.post("/auth/login", json={"email": "asha@northwind.test", "password": "pulse123"})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert data["name"] == "Asha Rao"
    assert len(data["organizations"]) == 1
    assert data["organizations"][0]["org_name"] == "Northwind Logistics"


def test_login_invalid_password(client):
    r = client.post("/auth/login", json={"email": "asha@northwind.test", "password": "wrongpassword"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Wrong email or password"


def test_login_unknown_email(client):
    r = client.post("/auth/login", json={"email": "unknown@northwind.test", "password": "pulse123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Wrong email or password"


def test_login_email_case_insensitive(client):
    r = client.post("/auth/login", json={"email": "ASHA@NORTHWIND.TEST", "password": "pulse123"})
    assert r.status_code == 200
    assert r.json()["name"] == "Asha Rao"


def test_select_org_authorized(client):
    r = client.post("/auth/login", json={"email": "asha@northwind.test", "password": "pulse123"})
    token = r.json()["token"]
    org_id = r.json()["organizations"][0]["org_id"]
    sel_res = client.post(
        "/auth/select-org",
        json={"org_id": org_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sel_res.status_code == 200
    assert sel_res.json()["org_id"] == org_id
    assert "token" in sel_res.json()


def test_select_org_unauthorized(client):
    # Asha belongs to org 1 (Northwind), not org 2 (Bluepeak)
    r = client.post("/auth/login", json={"email": "asha@northwind.test", "password": "pulse123"})
    token = r.json()["token"]
    sel_res = client.post(
        "/auth/select-org",
        json={"org_id": 999},  # non-existent or unassociated org
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sel_res.status_code == 403
    assert sel_res.json()["detail"] == "Not a member of this organization"


def test_access_without_token(client):
    r = client.get("/diagnostic/questions")
    assert r.status_code == 401
    assert r.json()["detail"] == "Missing token"


def test_access_with_invalid_token(client):
    r = client.get("/diagnostic/questions", headers={"Authorization": "Bearer not-a-valid-jwt"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"


def test_access_with_expired_token(client):
    expired_payload = {
        "sub": "1",
        "org": 1,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm="HS256")
    r = client.get("/diagnostic/questions", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"


def test_access_without_selecting_org(client):
    # Initial login token does not have 'org' set
    r = client.post("/auth/login", json={"email": "asha@northwind.test", "password": "pulse123"})
    login_token = r.json()["token"]
    r = client.get("/diagnostic/questions", headers={"Authorization": f"Bearer {login_token}"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Select an organization first"


def test_employee_cannot_access_dashboard(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/dashboard?org_id=1", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "Admins only"


def test_admin_cannot_cross_access_another_org(client):
    # Asha is admin of Northwind Logistics (org_id=1)
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    # Tries to access Bluepeak Retail (org_id=2)
    r = client.get("/dashboard?org_id=2", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "Cannot access data for another organization"


def test_multi_org_user_scoped_access(client):
    # Ravi is employee at Northwind (org 1) and admin at Bluepeak (org 2)
    nw_headers, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    bp_headers, _ = login(client, "ravi@consult.test", "Bluepeak Retail")

    # At Northwind, Ravi is an employee -> cannot access dashboard
    r_nw = client.get("/dashboard?org_id=1", headers=nw_headers)
    assert r_nw.status_code == 403
    assert r_nw.json()["detail"] == "Admins only"

    # At Bluepeak, Ravi is admin -> can access Bluepeak dashboard
    r_bp = client.get("/dashboard?org_id=2", headers=bp_headers)
    assert r_bp.status_code == 200

    # But Bluepeak token cannot access Northwind dashboard
    r_cross = client.get("/dashboard?org_id=1", headers=bp_headers)
    assert r_cross.status_code == 403
    assert r_cross.json()["detail"] == "Cannot access data for another organization"
