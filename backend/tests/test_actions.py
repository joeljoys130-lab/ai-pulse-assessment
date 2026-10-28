from tests.conftest import login
from app.services.actions import generate_action_plan
from app import models


def test_empty_responses_yields_no_actions():
    actions = generate_action_plan([], "engineering")
    assert actions == []


def test_skill_gap_targeting_customer_data():
    class FakeResponse:
        flags = ["customer_data_shared"]
        question_id = "common-open"
        score = 3.0

    actions = generate_action_plan([FakeResponse()], "support")
    assert len(actions) == 3
    action_ids = [a["id"] for a in actions]
    assert "data_sanitization" in action_ids
    # Verification of schema fields
    for a in actions:
        assert "title" in a and len(a["title"]) > 0
        assert "explanation" in a and len(a["explanation"]) > 0
        assert "next_step" in a and len(a["next_step"]) > 0


def test_skill_gap_targeting_confidential_and_unreviewed():
    class FakeResp1:
        flags = ["confidential_data_shared"]
        question_id = "common-open"
        score = 2.0

    class FakeResp2:
        flags = ["unreviewed_output"]
        question_id = "common-review"
        score = 2.0

    actions = generate_action_plan([FakeResp1(), FakeResp2()], "engineering")
    assert len(actions) == 3
    action_ids = [a["id"] for a in actions]
    assert "confidential_data_protection" in action_ids
    assert "output_verification" in action_ids


def test_get_action_plan_api(client):
    # Priya has seeded responses with 'customer_data_shared'
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/reports/actions", headers=headers)
    assert r.status_code == 200
    actions = r.json()
    assert len(actions) == 3
    assert any(a["id"] == "data_sanitization" for a in actions)
    assert all(a["completed"] is False for a in actions)


def test_action_completion_tracking_and_toggle(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # Mark action completed
    r1 = client.post("/reports/actions/data_sanitization/toggle", headers=headers)
    assert r1.status_code == 200
    assert r1.json()["completed"] is True

    # Verify action plan shows it as completed
    r2 = client.get("/reports/actions", headers=headers)
    action = next(a for a in r2.json() if a["id"] == "data_sanitization")
    assert action["completed"] is True
    assert action["completed_at"] is not None

    # Toggle again -> should unmark
    r3 = client.post("/reports/actions/data_sanitization/toggle", headers=headers)
    assert r3.status_code == 200
    assert r3.json()["completed"] is False

    r4 = client.get("/reports/actions", headers=headers)
    action_after = next(a for a in r4.json() if a["id"] == "data_sanitization")
    assert action_after["completed"] is False


def test_action_completion_isolation_between_employees(client):
    priya_headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    vikram_headers, _ = login(client, "vikram@northwind.test", "Northwind Logistics")

    # Priya completes an action
    client.post("/reports/actions/data_sanitization/toggle", headers=priya_headers)

    # Vikram checks his actions: none should be marked completed by Priya
    vikram_actions = client.get("/reports/actions", headers=vikram_headers).json()
    for a in vikram_actions:
        assert a["completed"] is False


def test_deleting_report_clears_action_completions(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # Complete action
    client.post("/reports/actions/data_sanitization/toggle", headers=headers)

    # Employee exercises Right to Delete
    del_res = client.delete("/reports/me", headers=headers)
    assert del_res.status_code == 200

    # Actions list is now empty because diagnostic responses were wiped
    actions_after = client.get("/reports/actions", headers=headers).json()
    assert actions_after == []
