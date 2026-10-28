from tests.conftest import login


def test_employee_can_delete_own_responses(client):
    headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")

    # Verify Vikram currently has answered responses and a report
    r = client.get("/reports/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["answered"] > 0
    assert r.json()["average_score"] is not None

    # Delete responses via DELETE /reports/me
    del_res = client.delete("/reports/me", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] > 0

    # Verify report is immediately empty
    r_after = client.get("/reports/me", headers=headers)
    assert r_after.status_code == 200
    assert r_after.json()["answered"] == 0
    assert r_after.json()["average_score"] is None
    assert r_after.json()["level"] == "Not assessed"
    assert r_after.json()["risks"] == []


def test_delete_via_diagnostic_endpoint(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    r = client.get("/reports/me", headers=headers)
    assert r.json()["answered"] > 0

    # Delete via DELETE /diagnostic/responses
    del_res = client.delete("/diagnostic/responses", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] > 0

    # Verify report is cleared
    r_after = client.get("/reports/me", headers=headers)
    assert r_after.json()["answered"] == 0


def test_deleted_responses_disappear_from_dashboard(client):
    admin_headers, admin_data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = admin_data["organizations"][0]["org_id"]

    # Initial dashboard
    r1 = client.get(f"/dashboard?org_id={org_id}", headers=admin_headers)
    init_responded = sum(d["responded"] for d in r1.json()["departments"])

    # Vikram deletes his answers
    vikram_headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    client.delete("/reports/me", headers=vikram_headers)

    # Subsequent dashboard
    r2 = client.get(f"/dashboard?org_id={org_id}", headers=admin_headers)
    after_responded = sum(d["responded"] for d in r2.json()["departments"])

    # Responded count decreases by 1
    assert after_responded == init_responded - 1


def test_unauthorized_deletion_rejected(client):
    # Missing token
    r1 = client.delete("/reports/me")
    assert r1.status_code == 401
    assert r1.json()["detail"] == "Missing token"

    # Token without organization
    login_res = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "pulse123"})
    token_no_org = login_res.json()["token"]
    r2 = client.delete("/reports/me", headers={"Authorization": f"Bearer {token_no_org}"})
    assert r2.status_code == 400


def test_repeated_deletion_idempotent(client):
    headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    # First deletion
    del1 = client.delete("/reports/me", headers=headers)
    assert del1.status_code == 200
    assert del1.json()["deleted"] > 0

    # Second deletion when already deleted
    del2 = client.delete("/reports/me", headers=headers)
    assert del2.status_code == 200
    assert del2.json()["deleted"] == 0


def test_deletion_does_not_affect_other_employees(client):
    vikram_headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")
    priya_headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    priya_before = client.get("/reports/me", headers=priya_headers).json()["answered"]
    assert priya_before > 0

    # Vikram deletes his data
    client.delete("/reports/me", headers=vikram_headers)

    # Priya's report data is completely untouched
    priya_after = client.get("/reports/me", headers=priya_headers).json()["answered"]
    assert priya_after == priya_before
