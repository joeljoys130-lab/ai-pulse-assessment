from unittest.mock import patch
from app.services.scoring import parse_and_validate, score_open_answer
from tests.conftest import login


def test_valid_scoring_response():
    raw = '{"score": 4, "reason": "Uses AI weekly and reviews results.", "flags": ["customer_data_shared"]}'
    res = parse_and_validate(raw)
    assert res["score"] == 4.0
    assert res["reason"] == "Uses AI weekly and reviews results."
    assert res["flags"] == ["customer_data_shared"]


def test_markdown_code_fences_stripped():
    raw = '```json\n{"score": 3, "reason": "Basic usage.", "flags": []}\n```'
    res = parse_and_validate(raw)
    assert res["score"] == 3.0
    assert res["reason"] == "Basic usage."
    assert res["flags"] == []


def test_missing_reason_field():
    raw = '{"score": 5, "flags": []}'
    res = parse_and_validate(raw)
    assert res["score"] == 5.0
    assert res["reason"] == "No explanation provided"


def test_out_of_range_score_rejected():
    # Score 7 is above 5
    raw_high = '{"score": 7, "reason": "Super advanced.", "flags": []}'
    res_high = parse_and_validate(raw_high)
    assert res_high["score"] is None
    assert "outside permitted range" in res_high["reason"]

    # Score 0 is below 1
    raw_low = '{"score": 0, "reason": "Zero usage.", "flags": []}'
    res_low = parse_and_validate(raw_low)
    assert res_low["score"] is None
    assert "outside permitted range" in res_low["reason"]


def test_non_numeric_score_rejected():
    raw = '{"score": "four", "reason": "Good regular use.", "flags": []}'
    res = parse_and_validate(raw)
    assert res["score"] is None
    assert "non-numeric" in res["reason"]


def test_boolean_score_rejected():
    raw = '{"score": true, "reason": "Yes.", "flags": []}'
    res = parse_and_validate(raw)
    assert res["score"] is None


def test_invalid_flags_filtered_out():
    raw = '{"score": 3, "reason": "Average.", "flags": ["customer_data_shared", "invalid_flag", "made_up"]}'
    res = parse_and_validate(raw)
    assert res["score"] == 3.0
    # Only the approved rubric flag is preserved
    assert res["flags"] == ["customer_data_shared"]


def test_malformed_json_handled_safely():
    raw = 'This is not valid JSON at all: {"score": 4'
    res = parse_and_validate(raw)
    assert res["score"] is None
    assert "malformed" in res["reason"]
    assert res["flags"] == []


def test_unexpected_response_type_handled_safely():
    # Model returns a JSON array instead of object
    raw = '["score", 4, "great"]'
    res = parse_and_validate(raw)
    assert res["score"] is None
    assert "unexpected" in res["reason"]


def test_ai_provider_error_handled_safely():
    with patch("app.services.llm.score_answer", side_effect=RuntimeError("Connection timed out")):
        res = score_open_answer("Some question", "Some answer")
        assert res["score"] is None
        assert "Connection timed out" in res["reason"]
        assert res["flags"] == []


def test_diagnostic_submit_with_open_answer(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    payload = {
        "answers": [
            {"question_id": "common-open", "answer": "Used Claude to draft release notes and reviewed all items."}
        ]
    }
    r = client.post("/diagnostic/submit", json=payload, headers=headers)
    assert r.status_code == 200
    assert r.json()["saved"] == 1
