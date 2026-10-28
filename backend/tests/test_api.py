from tests.conftest import login


def test_login_lists_organizations(client):
    _, data = login(client, "ravi@consult.test")
    names = {o["org_name"] for o in data["organizations"]}
    assert names == {"Northwind Logistics", "Bluepeak Retail"}


def test_employee_sees_questions(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/diagnostic/questions", headers=headers)
    assert r.status_code == 200
    assert any(q["id"] == "sup-drafts" for q in r.json())


def test_admin_dashboard(client):
    headers, data = login(client, "asha@northwind.test", "Northwind Logistics")
    org_id = data["organizations"][0]["org_id"]
    r = client.get(f"/dashboard?org_id={org_id}", headers=headers)
    assert r.status_code == 200
    depts = r.json()["departments"]
    # Seeded Northwind departments each have < 5 completed participants, so they are grouped under "Other teams"
    assert len(depts) == 1
    assert depts[0]["department"] == "Other teams"
    assert depts[0]["responded"] == 2
    assert depts[0]["average_score"] is None


def test_admin_cannot_see_other_org(client):
    headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    # Bluepeak Retail is org_id=2; Asha is admin only at Northwind Logistics (org_id=1)
    r = client.get("/dashboard?org_id=2", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "Cannot access data for another organization"


def test_employee_with_responses_routing_contract(client):
    # Employee with existing responses gets answered > 0 -> frontend routes to personal report
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/reports/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["answered"] > 0


def test_employee_without_responses_routing_contract(client):
    # Employee with no responses gets answered == 0 -> frontend routes to diagnostic
    headers, _ = login(client, "neha@northwind.test", "Northwind Logistics")
    r = client.get("/reports/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["answered"] == 0
