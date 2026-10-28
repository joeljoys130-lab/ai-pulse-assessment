ACTION_CATALOG = {
    "data_sanitization": {
        "id": "data_sanitization",
        "priority": 1,
        "title": "Data Sanitization & Privacy Shield",
        "explanation": "Customer or sensitive personal details were detected or risk being exposed in your AI interactions.",
        "next_step": "Practice anonymizing prompt inputs by replacing real customer names, account numbers, and identifiers with synthetic placeholders before querying AI tools.",
    },
    "confidential_data_protection": {
        "id": "confidential_data_protection",
        "priority": 1,
        "title": "Confidential Information Protection",
        "explanation": "Confidential business data or proprietary source code has been flagged in your AI interactions.",
        "next_step": "Review your organization's data classification tiers and ensure non-public financial records, keys, and internal secrets are never submitted to public LLMs.",
    },
    "output_verification": {
        "id": "output_verification",
        "priority": 2,
        "title": "Output Fact-Checking & Code Verification",
        "explanation": "AI responses are occasionally used with limited verification, creating risk of inaccuracies or hallucinations reaching work output.",
        "next_step": "Establish a personal review habit: independently verify calculations, check generated code with unit tests, and cross-check claims against authoritative sources.",
    },
    "policy_compliance": {
        "id": "policy_compliance",
        "priority": 2,
        "title": "Company AI Policy Familiarization",
        "explanation": "Your responses suggest uncertainty regarding organization-sanctioned AI tools and compliance policies.",
        "next_step": "Read your organization's official AI usage policy and confirm that every AI service in your day-to-day workflow is approved.",
    },
    "daily_ai_exploration": {
        "id": "daily_ai_exploration",
        "priority": 3,
        "title": "Establish a Daily AI Assistant Routine",
        "explanation": "Your current AI usage is infrequent. Regular practice on low-stakes routine work builds foundational fluency.",
        "next_step": "Pick one repetitive workflow this week (such as summarizing meeting notes or structuring draft outlines) and use an AI tool to assist you.",
    },
    "eng_code_assistant": {
        "id": "eng_code_assistant",
        "priority": 4,
        "title": "Pair Programming with Code Assistants",
        "explanation": "Level up your software engineering workflow by incorporating AI into testing, refactoring, and code comprehension.",
        "next_step": "Use your code assistant to generate unit test suites for your next feature branch, reviewing and testing each suggested assertion.",
    },
    "support_ticket_drafting": {
        "id": "support_ticket_drafting",
        "priority": 4,
        "title": "Customer Response Drafting & Summarization",
        "explanation": "Accelerate customer response times while preserving empathy, personal voice, and company standards.",
        "next_step": "Build a library of 3 reusable prompt templates for standard customer inquiries, always editing the draft before sending.",
    },
    "sales_personalization": {
        "id": "sales_personalization",
        "priority": 4,
        "title": "Personalized Client Prospecting",
        "explanation": "Leverage AI to research prospect businesses and draft tailored outreach sequences without sounding generic.",
        "next_step": "Use AI to research your next 3 target accounts and draft personalized value propositions tailored to their industry pain points.",
    },
    "manager_policy_rollout": {
        "id": "manager_policy_rollout",
        "priority": 4,
        "title": "Team AI Guidance & Workflow Alignment",
        "explanation": "Support your team in safely leveraging AI tools while establishing clear boundaries and tracking business value.",
        "next_step": "Hold a 30-minute team session to agree on team AI norms and identify one common team process to streamline with AI.",
    },
    "ai_champion": {
        "id": "ai_champion",
        "priority": 5,
        "title": "Department Knowledge Sharing",
        "explanation": "You exhibit thoughtful, safe AI practices. Help raise team-wide AI maturity by mentoring colleagues.",
        "next_step": "Document one effective prompt or workflow you use and present it in your next team knowledge-sharing session.",
    },
}

ROLE_FALLBACK_MAP = {
    "engineering": "eng_code_assistant",
    "support": "support_ticket_drafting",
    "sales": "sales_personalization",
    "manager": "manager_policy_rollout",
}


def generate_action_plan(responses: list, job_role: str) -> list[dict]:
    """Deterministically derives up to 3 prioritized improvement actions from responses."""
    if not responses:
        return []

    flags = set()
    scores_by_q = {}
    for r in responses:
        if r.flags:
            flags.update(r.flags)
        if r.score is not None:
            scores_by_q[r.question_id] = r.score

    selected_ids = []

    # Priority 1: Critical data safety risks
    if "customer_data_shared" in flags or scores_by_q.get("common-data", 5) <= 2:
        selected_ids.append("data_sanitization")
    if "confidential_data_shared" in flags:
        selected_ids.append("confidential_data_protection")

    # Priority 2: Quality & Governance risks
    if "unreviewed_output" in flags or scores_by_q.get("common-review", 5) <= 2:
        selected_ids.append("output_verification")
    if "policy_unaware" in flags or scores_by_q.get("common-policy", 5) <= 2:
        selected_ids.append("policy_compliance")

    # Priority 3: Low adoption frequency
    if scores_by_q.get("common-freq", 5) <= 2:
        selected_ids.append("daily_ai_exploration")

    # Priority 4: Role-specific action
    role_action = ROLE_FALLBACK_MAP.get(job_role)
    if role_action and role_action not in selected_ids:
        selected_ids.append(role_action)

    # Priority 5: Fallback champion action
    if "ai_champion" not in selected_ids:
        selected_ids.append("ai_champion")

    # Deduplicate while preserving priority order, then select top 3
    final_ids = []
    for aid in selected_ids:
        if aid not in final_ids:
            final_ids.append(aid)
        if len(final_ids) == 3:
            break

    return [dict(ACTION_CATALOG[aid]) for aid in final_ids]
