import json
from . import llm

VALID_FLAGS = {
    "customer_data_shared",
    "confidential_data_shared",
    "unreviewed_output",
    "policy_unaware",
}


def clean_llm_json(raw: str) -> str:
    """Strips markdown code fences and extracts the JSON object."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Drop first line (``` or ```json)
        if len(lines) >= 2 and lines[0].startswith("```"):
            lines = lines[1:]
        # Drop last line if closing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Locate enclosing curly braces
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end >= start:
        cleaned = cleaned[start : end + 1]
    return cleaned


def parse_and_validate(raw_text: str) -> dict:
    """Parses model output and validates against schema, rubric (1-5), and allowed flags."""
    try:
        json_str = clean_llm_json(raw_text)
        data = json.loads(json_str)
    except Exception:
        return {
            "score": None,
            "reason": "Scoring unavailable: malformed model response",
            "flags": [],
        }

    if not isinstance(data, dict):
        return {
            "score": None,
            "reason": "Scoring unavailable: unexpected model response type",
            "flags": [],
        }

    # Validate flags
    raw_flags = data.get("flags")
    valid_flags = []
    if isinstance(raw_flags, list):
        for f in raw_flags:
            if isinstance(f, str) and f.strip() in VALID_FLAGS:
                valid_flags.append(f.strip())

    # Validate reason
    raw_reason = data.get("reason")
    if isinstance(raw_reason, str) and raw_reason.strip():
        reason = raw_reason.strip()
    else:
        reason = "No explanation provided"

    # Validate score
    raw_score = data.get("score")
    score = None
    if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool):
        if 1.0 <= raw_score <= 5.0:
            score = float(raw_score)
        else:
            reason = f"Scoring unavailable: score {raw_score} outside permitted range (1-5)"
    elif isinstance(raw_score, str):
        try:
            val = float(raw_score.strip())
            if 1.0 <= val <= 5.0:
                score = val
            else:
                reason = f"Scoring unavailable: score {val} outside permitted range (1-5)"
        except ValueError:
            reason = "Scoring unavailable: non-numeric score returned"
    else:
        reason = "Scoring unavailable: missing or invalid score"

    return {
        "score": score,
        "reason": reason,
        "flags": valid_flags,
    }


def score_open_answer(question_text: str, answer: str) -> dict:
    """Scores an open-ended answer via LLM (or mock) and safely validates output."""
    try:
        raw = llm.score_answer(question_text, answer)
    except Exception as e:
        return {
            "score": None,
            "reason": f"Scoring unavailable: {str(e)}",
            "flags": [],
        }
    return parse_and_validate(raw)
