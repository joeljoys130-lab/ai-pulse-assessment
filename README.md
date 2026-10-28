# AI Pulse — Enterprise Engineering Assessment

AI Pulse is an organizational diagnostic platform designed to help companies assess, measure, and improve AI maturity and safety practices across departments.

* **Employees** sign in, select their organization, take a role-adapted diagnostic, receive a personal maturity score, and access a personalized **Diagnostic Action Planner** to turn identified skill gaps into concrete habits.
* **Admins & Leadership** view aggregated AI maturity dashboards across departments and identify high-risk usage patterns, protected by strict differential privacy thresholds.
* **Privacy & Data Rights** are enforced at the database level: employees maintain an unequivocal **Right to Delete**, and departments with fewer than 5 respondents are aggregated under "Other teams" to prevent individual re-identification.

---

## 1. Project Overview & Architecture

### High-Level Architecture

```
                 ┌────────────────────────────────┐
                 │       React Frontend (Vite)    │
                 │   Login | OrgPicker | Report   │
                 │    Diagnostic | Dashboard      │
                 └───────────────┬────────────────┘
                                 │ HTTP / JSON
                                 │ Bearer JWT (org-scoped)
                                 ▼
                 ┌────────────────────────────────┐
                 │       FastAPI Backend API      │
                 │  /auth  /diagnostic  /reports  │
                 │          /dashboard            │
                 └───────┬───────────────┬────────┘
                         │               │
        SQLAlchemy (ORM) │               │ OpenAI Chat Completions API
                         ▼               ▼ (or Deterministic Mock Engine)
              ┌─────────────┐     ┌──────────────┐
              │  SQLite DB  │     │   LLM API    │
              └─────────────┘     └──────────────┘
```

### Technology Stack

* **Backend:** Python 3.10+, FastAPI 0.115.6, Uvicorn 0.32.1, Pydantic 2.10.4, PyJWT 2.10.1, HTTPX 0.28.1.
* **Database & ORM:** SQLAlchemy 2.0.36 with SQLite (`sqlite:///./aipulse.db`).
* **Frontend:** React 18.3.1, Vite 5.4.11, Vanilla CSS.
* **AI Integration:** OpenAI-compatible chat completions interface with deterministic mock fallback (`AI_MODE=mock`).
* **Test Suite:** Pytest 8.3.4 (56 unit and integration tests).

---

## 2. Setup & Execution Instructions

### Prerequisites

* Python 3.10 or higher
* Node.js v18 or higher (tested on Node v24) and npm
* Git

### Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   * **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure local environment variables from template:
   * **Windows (PowerShell):**
     ```powershell
     Copy-Item .env.example .env
     ```
   * **macOS / Linux:**
     ```bash
     cp .env.example .env
     ```
5. Seed demo data (creates initial organizations, departments, accounts, and sample responses):
   ```bash
   python -m app.seed
   ```
6. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```
   * The API will be accessible at `http://localhost:8000`.
   * Interactive API documentation is available at `http://localhost:8000/docs`.

### Frontend Setup

1. In a separate terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   * Open your browser at `http://localhost:5173`.

### Running Automated Tests and Builds

* **Run Backend Automated Test Suite:**
  ```bash
  cd backend
  python -m pytest -v
  ```
  *(Expected result: 56 passed in ~5s)*

* **Run Frontend Production Build:**
  ```bash
  cd frontend
  npm run build
  ```
  *(Expected result: `dist/` bundle created with 0 errors)*

### Environment Variables

Configuration is loaded from `backend/.env`. Key settings:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | HMAC secret for signing and validating JWT tokens. | `ai-pulse-dev-secret` |
| `DATABASE_URL` | SQLAlchemy connection string. | `sqlite:///./aipulse.db` |
| `AI_MODE` | Scoring mode: `mock` (deterministic canned JSON) or `live` (external API). | `mock` |
| `LLM_API_URL` | Endpoint URL for OpenAI-compatible chat completions (live mode only). | *(Empty)* |
| `LLM_API_KEY` | Bearer token for LLM API (live mode only). | *(Empty)* |
| `LLM_MODEL` | Target LLM model name (live mode only). | *(Empty)* |

---

## 3. Discovered Defects & Verified Fixes

During the initial code audit and setup, several critical architectural, security, and algorithmic bugs were uncovered and resolved:

### 1. Seniority Ranking Alphabetical Comparison Bug
* **Defect:** In `backend/app/services/questions.py`, questions were filtered by seniority using lexicographical comparison (`seniority < q.get("min_seniority", "junior")`). In Python, `"lead" < "senior"` evaluates to `True`, inappropriately excluding questions requiring senior seniority from lead managers.
* **Fix:** Introduced an explicit rank hierarchy mapping (`{"junior": 1, "mid": 2, "senior": 3, "lead": 4}`) and compared numeric values. Added regression tests verifying hierarchy progression.

### 2. Broken Object-Level Authorization (BOLA / IDOR) in Dashboard
* **Defect:** In `backend/app/routes/dashboard.py`, `org_dashboard` accepted an `org_id` query parameter and verified `m.role == "admin"`, but failed to verify whether `m.org_id == org_id`. An admin belonging to Organization A could query `?org_id=2` and receive Organization B's metrics. Additionally, the existing test `test_admin_cannot_see_other_org` tested `org_id=1` (their own org) and asserted `200`.
* **Fix:** Added tenant isolation enforcement: `if m.org_id != org_id: raise HTTPException(403)`. Corrected `test_admin_cannot_see_other_org` to query `org_id=2` and assert `403`.

### 3. Unchecked Scoped Token Issuance
* **Defect:** In `backend/app/routes/auth_routes.py`, `select_org` issued an organization-scoped token for any arbitrary `org_id` requested in the request payload without verifying user membership.
* **Fix:** Added database validation to ensure the authenticated user possesses an active `Membership` in the target organization before issuing the scoped token.

### 4. Department Average Score Calculation Bug
* **Defect:** `dashboard.py` originally computed department averages as `sum(scores) / len(dept_members)`. Dividing total question score points by total department staff (including non-respondents) yielded mathematically meaningless fractional averages.
* **Fix:** Corrected the calculation to `sum(scores) / len(scores)` across answered questions for respondents in that group.

### 5. Fragile AI Scoring Engine
* **Defect:** `backend/app/services/scoring.py` performed raw `json.loads()` on model outputs. Canned responses in `mock_ai_responses.json` containing markdown code fences (```````json...```````), missing explanation fields, out-of-rubric scores (e.g. `score: 7`), non-numeric scores (`"four"`), or made-up flags caused unhandled exceptions and database corruption.
* **Fix:** Implemented `clean_llm_json()` to strip code fences and extract `{...}` blocks. Added strict rubric bounds checking ($1.0 \le \text{score} \le 5.0$), flag sanitization against approved labels, default fallback explanations, and defensive exception handling for AI provider timeouts.

### 6. Parent Directory PostCSS Collision in Vite
* **Defect:** Vite recursively traversed parent directories looking for PostCSS configurations and picked up an unrelated `postcss.config.mjs` on the user's Desktop directory.
* **Fix:** Configured `css: { postcss: {} }` in `frontend/vite.config.js` to instruct Vite to use project-local PostCSS options and halt directory traversal.

### 7. Password Hash Verification Timing Attacks
* **Defect:** `verify_password` compared hashes with Python's standard `==` operator, exposing the verification routine to timing side-channel analysis.
* **Fix:** Updated comparison to use `hmac.compare_digest`.

### 8. Frontend Session State Loss & Indiscriminate Employee Routing on Reload
* **Defect:** `frontend/src/App.jsx` initialized its step to `"login"` and held user session and organization objects purely in React memory. Reloading the page (`Ctrl+R`) reset the application to the login screen even though valid JWT tokens remained in `localStorage`. Furthermore, when an employee logged in and picked an organization, `App.jsx` unconditionally navigated to `"diagnostic"` without inspecting whether the employee had already answered the diagnostic.
* **Fix:** Added localStorage persistence helpers (`setStoredSession`, `setStoredOrg`, `clearAuth`) in `frontend/src/api.js`. On startup/reload, `App.jsx` rehydrates the session and re-verifies organization authorization against the backend (`/dashboard` for admins, `/reports/me` for employees). For employees, if `answered > 0`, they are routed directly to their personalized report; if `answered === 0`, they are routed to the blank diagnostic form. Auth failures (401/403) cleanly clear storage and reset to login, while network errors are displayed visibly.

---

## 4. Client Requirements Implementation

### A. Department Privacy Threshold ($k \ge 5$)

Per Northwind HR legal requirements (`CLIENT_REQUEST.md`), departments with fewer than 5 completed participants must not have their individual scores or risks exposed on leadership dashboards:

1. **Accurate Participant Counting:** Rather than counting response rows, the backend computes distinct completed participants (`len(responded_member_ids)`). Repeated or multiple submissions by a single employee do not inflate the participant count.
2. **"Other teams" Aggregation:**
   * Departments with $\ge 5$ completed participants are rendered as individual line items.
   * Departments with $< 5$ completed participants are suppressed from individual display and grouped under `"Other teams"`.
3. **Suppressed Group Leakage Prevention:** If the aggregate `"Other teams"` group itself contains $< 5$ respondents total, `average_score` is set to `None` and `level` to `"Not assessed"` to ensure individual or small-group scores cannot be deduced.
4. **Top Risks Protection:** If total completed participants across the entire organization is $< 5$, `top_risks` returns `[]` so that individual risk flags are never exposed to leadership.

### B. Employee Right to Delete

Per Northwind HR legal requirements, employees can delete all their diagnostic answers and reports at will:

1. **Endpoints:** Added `DELETE /reports/me` and `DELETE /diagnostic/responses`.
2. **Strict Authorization:** Deletion operates strictly on `m.id` extracted from the authenticated JWT session. An employee can never delete another employee's records.
3. **Immediate Dashboard Propagation:** When `Response` records are deleted, the employee is no longer identified as a respondent. Department respondent counts, score averages, and organization top risks update immediately on the next dashboard query.
4. **Account & Membership Preservation:** Only diagnostic responses and action completions are deleted; user accounts and organization memberships remain intact so employees can retake the diagnostic later.
5. **Idempotency:** Repeated calls safely return `{"deleted": 0}` with status `200`.

---

## 5. Original Feature: Diagnostic Action Planner

### Purpose
While AI Pulse previously diagnosed maturity and risks, employees lacked concrete guidance on how to improve. The **Diagnostic Action Planner** closes this loop by transforming diagnostic assessment findings into actionable, tracked professional habits.

### Architecture & Priority Logic
The planner uses a deterministic recommendation engine (`backend/app/services/actions.py`) that evaluates diagnostic response flags and question scores:

1. **Priority 1 (Critical Security/Privacy):**
   * Triggered by `customer_data_shared` or score $\le 2$ on `common-data` &rarr; **Data Sanitization & Privacy Shield**.
   * Triggered by `confidential_data_shared` &rarr; **Confidential Information Protection**.
2. **Priority 2 (Quality & Governance):**
   * Triggered by `unreviewed_output` or score $\le 2$ on `common-review` &rarr; **Output Fact-Checking & Code Verification**.
   * Triggered by `policy_unaware` or score $\le 2$ on `common-policy` &rarr; **Company AI Policy Familiarization**.
3. **Priority 3 (Adoption Frequency):**
   * Triggered by score $\le 2$ on `common-freq` &rarr; **Establish a Daily AI Assistant Routine**.
4. **Priority 4 (Role-Specific Workflows):**
   * Engineering &rarr; **Pair Programming with Code Assistants**.
   * Support &rarr; **Customer Response Drafting & Summarization**.
   * Sales &rarr; **Personalized Client Prospecting**.
   * Management &rarr; **Team AI Guidance & Workflow Alignment**.
5. **Priority 5 (Excellence/Mentorship):**
   * Triggered when an employee excels with no risks &rarr; **Department Knowledge Sharing**.

### Data Storage & Completion Tracking
* Backed by a dedicated `CompletedAction` database table (`membership_id`, `action_id`, `completed_at`).
* Toggle endpoint: `POST /reports/actions/{action_id}/toggle`.
* Scoped strictly to the employee's active organization membership.
* Cleanly wiped when an employee exercises their **Right to Delete**.
* Diagnostic scores are never modified by action completions.

---

## 6. Testing & Verification Summary

All verification results documented below were reproduced locally in the assessment environment:

### Automated Backend Tests
* **Total Tests:** 56 passed (0 failures) in 4.34 seconds.
* **Test Breakdown:**
  * `test_auth.py` (13 tests): Login credential verification, case-insensitivity, invalid password rejection, unauthorized org selection (403), missing tokens (401), invalid tokens (401), expired tokens (401), pre-org token restrictions (400), admin dashboard role checks (403), cross-tenant isolation (403), multi-org switching.
  * `test_privacy.py` (7 tests): Participant counts for 0, 1, 4, 5, and >5 employees, duplicate response handling, small group aggregation under "Other teams", suppressed group score masking, and top risks suppression.
  * `test_delete.py` (6 tests): Successful response deletion via `/reports/me` and `/diagnostic/responses`, immediate dashboard aggregate update, unauthorized deletion rejection, idempotency on repeated deletion, and employee data isolation.
  * `test_scoring.py` (11 tests): Markdown code fence stripping, missing reason fallbacks, out-of-range score rejection, non-numeric score handling, boolean rejection, invalid flag filtering, malformed JSON recovery, and provider timeout resilience.
  * `test_actions.py` (7 tests): Recommendation generation, empty response handling, targeted risk actions, action completion toggling, cross-user isolation, and deletion integration.
  * `test_questions.py` (6 tests): Role and seniority question filtering across junior, mid, senior, and lead levels.
  * `test_api.py` (6 tests): Baseline API workflows, dashboard verification, and employee report/diagnostic routing contracts (`answered > 0` vs `answered == 0`).

### Frontend Verification
* **Production Build:** `npm run build` executed via Vite 5.4.11; compiled in 1.42 seconds with zero errors or warnings.
* **Manual UI Verification:**
  * Tested employee login, organization switching, diagnostic submission, and personal report visualization.
  * Verified "Delete My Diagnostic Data" prompt, deletion confirmation banner, and dashboard respondent count decrements.
  * Verified admin dashboard rendering: table columns, maturity badges, "Other teams" aggregation, and privacy notices.

---

## 7. Known Limitations & Deferred Work

While the application is robust for assessment demonstration, several areas should be addressed before enterprise production:

1. **Password Hashing Algorithm:** Passwords currently use unsalted SHA-256 (hardened with `hmac.compare_digest`). While functional and compatible with existing seed data, production requires upgrading to a salted, adaptive algorithm such as Argon2id or PBKDF2-HMAC-SHA256 with an automatic re-hashing migration on user login.
2. **Stateless JWT Invalidation:** Tokens use a 12-hour expiration window. Once issued, a token remains valid until expiry. Implementing a Redis-backed token revocation blocklist or token generation timestamp checks would allow immediate session revocation on logout.
3. **Database Concurrency:** SQLite is currently utilized as the default database. For multi-tenant production concurrency with simultaneous diagnostic submissions, migration to PostgreSQL with connection pooling (e.g., PgBouncer) is required.
4. **Rate Limiting:** Endpoints currently lack rate limiting on `/auth/login` and `/diagnostic/submit`, leaving them vulnerable to automated brute-force attempts without a reverse-proxy rate limiter.

---

## 8. Client Clarifications & Open Product Decisions

Before deploying this pilot into Northwind Logistics production, the following business questions should be confirmed with HR and Legal:

1. **Audit Logging vs. Right to Delete:** When an employee deletes their diagnostic responses, does legal compliance require an anonymized audit log entry (e.g., recording that *an* employee deleted their data on date $T$, without recording identity or answers) for compliance audit trails?
2. **Dynamic Unbundling of "Other teams":** If a department currently has 4 participants (grouped under "Other teams") and a 5th employee completes the diagnostic, should the department immediately unbundle into its own row on active dashboards, or should results be locked to quarterly assessment cycles?
3. **Diagnostic Retake Policy:** Can an employee immediately retake the diagnostic after deleting their responses, or should there be a mandatory cooldown period?

---

## 9. AI Tool Usage & Documented AI Error

AI assistance was utilized as a pair-programming partner to explore codebase structure, generate initial test skeletons, and analyze edge cases.

### Specific Documented AI Error
During the creation of the department privacy test suite ([`backend/tests/test_privacy.py`](file:///c:/Users/Joel%20Joy/OneDrive/Desktop/Interview-assesment/assessment/ai-pulse/backend/tests/test_privacy.py)), an AI-suggested test helper function was implemented to seed mock departments:

```python
# AI-generated snippet:
dept = models.Department(org_id=org.id, name=dept_name)
db.add(dept)
db.flush()
# ... user seeding loop ...
db.commit()
db.close()
return dept.id  # <-- Error: Accessing attribute on closed session
```

* **The Problem:** In SQLAlchemy, `db.commit()` expires active model attributes by default. Calling `db.close()` immediately disconnected the session. When `return dept.id` executed on the following line, SQLAlchemy attempted to lazy-load the expired attribute on a detached object, resulting in:
  `sqlalchemy.orm.exc.DetachedInstanceError: Instance <Department at ...> is not bound to a Session; attribute refresh operation cannot proceed`.
* **The Correction:** The flaw was investigated and corrected by storing `dept_id = dept.id` while the session was open and active prior to `db.commit()` and `db.close()`.

---

## 10. Production-Readiness Considerations

To transition AI Pulse from development to production:

* **Secret Management:** Move `SECRET_KEY` and LLM credentials out of `.env` files into an enterprise key management service (e.g., AWS Secrets Manager, HashiCorp Vault, or GCP Secret Manager).
* **CORS Restrictions:** Restrict `CORSMiddleware` in `backend/app/main.py` from `allow_origins=["*"]` to explicit, validated enterprise domain origins.
* **Database Migration:** Replace SQLite with a managed PostgreSQL instance and introduce Alembic for schema migrations instead of `Base.metadata.create_all()`.
* **Security Headers & Reverse Proxy:** Deploy behind an Nginx or Cloudflare reverse proxy enforcing TLS 1.3, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, and `Content-Security-Policy`.
* **Automated CI/CD Pipeline:** Enforce backend linting (Ruff/Flake8), type checking (Mypy), and the 56-test Pytest suite on all pull requests prior to deployment.
