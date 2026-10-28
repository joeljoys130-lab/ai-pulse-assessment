# AI Pulse — Enterprise Engineering Assessment

AI Pulse is an organizational diagnostic platform designed to help companies assess, measure, and improve AI maturity and safety practices across departments.

* **Employees** sign in, select their organization, take a role-adapted diagnostic, receive a personal maturity score, and access a personalized **Diagnostic Action Planner** to turn identified skill gaps into concrete habits.
* **Admins & Leadership** view aggregated AI maturity dashboards across departments and identify high-risk usage patterns, protected by minimum respondent thresholds ($k \ge 5$) and small-group suppression.
* **Privacy & Data Rights** are implemented through application-level
authorization, data-deletion operations, and dashboard aggregation controls.
Departments with fewer than 5 respondents are grouped under "Other teams"
with small-group score suppression to reduce re-identification risks.
These controls do not guarantee absolute anonymity or constitute formal
differential privacy.
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

### Pre-Seeded Demo Accounts

All demo accounts are populated during database seeding (`backend/app/seed.py`) with shared demo password: `pulse123`

| Name | Email | Organization | Department | System Role (`role`) | Job Role (`job_role`) | Seniority | Testing & Evaluation Focus |
|---|---|---|---|---|---|---|---|
| Asha Rao | `asha@northwind.test` | Northwind Logistics | *(None)* | `admin` | `manager` | `lead` | Admin dashboard access & tenant isolation checks |
| Vikram Shah | `vikram@northwind.test` | Northwind Logistics | Sales | `employee` | `sales` | `senior` | Pre-seeded responses on record; test Right to Delete |
| Priya Nair | `priya@northwind.test` | Northwind Logistics | Support | `employee` | `support` | `junior` | 14 responses; test Action Planner & state persistence |
| Neha Gupta | `neha@northwind.test` | Northwind Logistics | Sales | `employee` | `sales` | `junior` | Zero responses; test first-time diagnostic flow |
| Dev Malhotra | `dev@northwind.test` | Northwind Logistics | Engineering | `employee` | `engineering` | `lead` | Seniority question filtering & lead role verification |
| Ravi Kapoor | `ravi@consult.test` | Northwind Logistics<br>Bluepeak Retail | HR<br>*(None)* | `employee`<br>`admin` | `manager`<br>`manager` | `senior`<br>`senior` | Multi-org membership & role-scoped token switching |

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
| `SECRET_KEY` | HMAC secret for signing and validating JWT tokens. | `pulse-dev-secret-change-in-production` |
| `DATABASE_URL` | SQLAlchemy connection string. | `sqlite:///./aipulse.db` |
| `AI_MODE` | Scoring mode: `mock` (deterministic canned JSON) or `live` (external API). | `mock` |
| `LLM_API_URL` | Endpoint URL for OpenAI-compatible chat completions (live mode only). | *(Empty)* |
| `LLM_API_KEY` | Bearer token for LLM API (live mode only). | *(Empty)* |
| `LLM_MODEL` | Target LLM model name (live mode only). | *(Empty)* |

---

## 3. Discovered Defects, Fixes & Regression Verification

During the initial code audit and setup, several critical architectural, security, and algorithmic defects were uncovered and resolved:

### 1. Seniority Ranking Alphabetical Comparison Bug
* **Defect:** In `backend/app/services/questions.py`, questions were filtered by seniority using lexicographical string comparison (`seniority < q.get("min_seniority", "junior")`). In Python, `"lead" < "senior"` evaluates to `True`, inappropriately excluding questions requiring senior seniority from lead managers.
* **Fix:** Introduced an explicit numeric rank mapping (`{"junior": 1, "mid": 2, "senior": 3, "lead": 4}`) and compared numeric values.
* **Verification:** Tested by `test_seniority_ordering_hierarchy` and role-filtering tests in `backend/tests/test_questions.py`.

### 2. Broken Object-Level Authorization (BOLA / IDOR) in Dashboard
* **Defect:** In `backend/app/routes/dashboard.py`, `org_dashboard` accepted an `org_id` query parameter and verified `m.role == "admin"`, but failed to verify whether `m.org_id == org_id`. An admin belonging to Organization 1 could query `?org_id=2` and receive Organization 2's sensitive departmental metrics. Furthermore, the existing test `test_admin_cannot_see_other_org` tested `org_id=1` (their own org) and asserted `200`.
* **Fix:** Added tenant-isolation validation: `if m.org_id != org_id: raise HTTPException(403, "Cannot access data for another organization")`. Corrected `test_admin_cannot_see_other_org` to query `org_id=2` and assert `403`.
* **Verification:** Tested by `test_admin_cannot_see_other_org` in `backend/tests/test_api.py` and `test_admin_cannot_cross_access_another_org` in `backend/tests/test_auth.py`.

### 3. Unchecked Scoped Token Issuance
* **Defect:** In `backend/app/routes/auth_routes.py`, `select_org` issued an organization-scoped token for any arbitrary `org_id` requested in the request payload without verifying whether the user was a member of that organization.
* **Fix:** Added database validation to ensure the authenticated user possesses an active `Membership` in the target organization before issuing the scoped token.
* **Verification:** Tested by `test_select_org_unauthorized` in `backend/tests/test_auth.py`.

### 4. Department Average Score Calculation Bug
* **Defect:** `dashboard.py` originally computed department averages as `sum(scores) / len(dept_members)`. Dividing total question score points by total department staff (including non-respondents) yielded mathematically meaningless fractional averages.
* **Fix:** Corrected the calculation to `sum(scores) / len(scores)` across answered questions for respondents in that group.
* **Verification:** Tested by `test_suppressed_group_aggregation_prevents_individual_score_leakage` in `backend/tests/test_privacy.py`.

### 5. Fragile AI Scoring Engine
* **Defect:** `backend/app/services/scoring.py` performed raw `json.loads()` on model outputs. Canned responses in `mock_ai_responses.json` containing markdown code fences (```````json...```````), missing explanation fields, out-of-rubric scores (e.g. `score: 7`), non-numeric scores (`"four"`), or made-up flags caused unhandled exceptions and database corruption.
* **Fix:** Implemented `clean_llm_json()` to strip code fences and extract `{...}` blocks. Added strict rubric bounds checking ($1.0 \le \text{score} \le 5.0$), flag sanitization against approved labels, default fallback explanations, and defensive exception handling for AI provider timeouts.
* **Verification:** Tested by 11 unit and integration tests in `backend/tests/test_scoring.py`.

### 6. Parent Directory PostCSS Collision in Vite
* **Defect:** Vite recursively traversed parent directories looking for PostCSS configurations and picked up an unrelated `postcss.config.mjs` on the user's Desktop directory.
* **Fix:** Configured `css: { postcss: {} }` in `frontend/vite.config.js` to instruct Vite to use project-local PostCSS options and halt directory traversal.
* **Verification:** Verified by clean `npm run build` compilation in `frontend/`.

### 7. Password Hash Verification Timing Attacks
* **Defect:** `verify_password` compared hashes with Python's standard `==` operator, exposing the verification routine to timing side-channel analysis.
* **Fix:** Updated comparison to use `hmac.compare_digest`.
* **Verification:** Tested by `test_valid_login` and `test_login_invalid_password` in `backend/tests/test_auth.py`.

### 8. Frontend Session State Loss & Indiscriminate Employee Routing on Reload
* **Defect:** `frontend/src/App.jsx` initialized its step to `"login"` and held user session and organization objects purely in React memory. Reloading the page (`Ctrl+R`) reset the application to the login screen even though valid JWT tokens remained in `localStorage`. Furthermore, when an employee logged in and picked an organization, `App.jsx` unconditionally navigated to `"diagnostic"` without inspecting whether the employee had already answered the diagnostic.
* **Fix:** Added localStorage persistence helpers (`setStoredSession`, `setStoredOrg`, `clearAuth`) in `frontend/src/api.js`. On startup/reload, `App.jsx` rehydrates the session and re-verifies organization authorization against the backend (`/dashboard` for admins, `/reports/me` for employees). For employees, if `answered > 0`, they are routed directly to their personalized report; if `answered === 0`, they are routed to the blank diagnostic form. Auth failures (401/403) cleanly clear storage and reset to login, while network errors are displayed visibly.
* **Verification:** Tested by `test_employee_with_responses_routing_contract` and `test_employee_without_responses_routing_contract` in `backend/tests/test_api.py`.

---

## 4. Client Request Implementation: Privacy Thresholds & Right to Delete

The implementation directly addresses both business and legal requirements stated in the Northwind HR memo (`CLIENT_REQUEST.md`):

> *"1. No small groups on the dashboard. If a department has fewer than 5 people who completed the diagnostic, leadership must not see that department's scores or risks on their own. Group them under 'Other teams' or hide them, but individuals must never be identifiable.*
> *2. Right to delete. Any employee must be able to delete all their answers and their report themselves, and it must disappear from every dashboard immediately."*

### A. Small-Group Privacy Protections & Minimum Respondent Thresholds ($k \ge 5$)

Rather than formal differential privacy (which mathematically bounds information leakage by injecting calibrated random noise into query results, such as via Laplace or Gaussian mechanisms under an $\epsilon$-privacy budget), the platform implements a heuristic $k$-anonymity-style minimum respondent threshold ($k = 5$) with small-group aggregation and multi-layer suppression:

> [!NOTE]
> **Privacy Architecture & Limitations Notice:**
> Enforcing a minimum respondent threshold of five, aggregating small cohorts under "Other teams", and suppressing group averages and organization-wide risk flags significantly **reduce re-identification risks** in routine dashboard reporting. However, these deterministic aggregation controls **do not guarantee absolute anonymity** (for example, if an internal observer possesses auxiliary external knowledge of exact survey submission times or department rosters) and **do not constitute formal differential privacy**. This pragmatic thresholding design was implemented because it directly fulfills Northwind HR's operational request without introducing mathematical noise or statistical distortion into small organizational team scores.

1. **Accurate Participant Counting:** Rather than counting response rows, the backend computes distinct completed participants (`len(responded_member_ids)`). Repeated or multiple submissions by a single employee do not inflate the participant count.
2. **"Other teams" Aggregation:**
   * Departments with $\ge 5$ completed participants are rendered as individual line items.
   * Departments with $< 5$ completed participants are suppressed from individual display and grouped under `"Other teams"`.
3. **Suppressed Group Leakage Prevention:** If the aggregate `"Other teams"` group itself contains $< 5$ respondents total, `average_score` is set to `None` and `level` to `"Not assessed"` to ensure individual or small-group scores cannot be deduced.
4. **Top Risks Protection:** If total completed participants across the entire organization is $< 5$, `top_risks` returns `[]` so that individual risk flags are never exposed to leadership.
5. **Verification:** Tested by 7 tests in `backend/tests/test_privacy.py` covering participant counts of 0, 1, 4, 5, and >5, duplicate submission isolation, and score suppression.

### B. Employee Right to Delete

Per Northwind HR legal requirements, employees can delete all their diagnostic answers and reports at will:

1. **Endpoints:** Added `DELETE /reports/me` and `DELETE /diagnostic/responses`.
2. **Strict Authorization:** Deletion operates strictly on `m.id` extracted from the authenticated JWT session. An employee can never delete another employee's records.
3. **Immediate Dashboard Propagation:** When `Response` records are deleted, the employee is no longer identified as a respondent. Department respondent counts, score averages, and organization top risks update immediately on the next dashboard query.
4. **Action Planner Integration:** Cascades deletion to the employee's `CompletedAction` records, resetting personalized action completions.
5. **Account & Membership Preservation:** Only diagnostic responses and action completions are deleted; user accounts and organization memberships remain intact so employees can retake the diagnostic later.
6. **Idempotency:** Repeated calls safely return `{"deleted": 0}` with status `200`.
7. **Verification:** Tested by 6 tests in `backend/tests/test_delete.py`.

---

## 5. Original Feature: Diagnostic Action Planner

### Problem Solved
While AI Pulse previously diagnosed maturity and flagged risks, employees lacked actionable guidance on how to improve. Knowing that one shared customer data or lacks prompt verification does not provide a concrete plan. The **Diagnostic Action Planner** closes this loop by transforming diagnostic assessment findings into actionable, tracked professional habits.

### Architectural Decision & Scope
The action planner was selected because it naturally builds on the diagnostic results without requiring alterations to the core scoring rubric or database constraints. It operates deterministically, ensuring that recommendations are predictable, auditable, and easily explained to both employees and evaluators.

### Priority & Recommendation Engine
Implemented in `backend/app/services/actions.py`, the recommendation engine evaluates diagnostic response flags and question scores against a hierarchical priority model:

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
5. **Priority 5 (Excellence/Mentorship Fallback):**
   * Triggered when an employee excels with no risks &rarr; **Department Knowledge Sharing**.

The engine deduplicates actions in priority order and returns the top 3 items.

### Data Storage & Completion Tracking
* Backed by a dedicated `CompletedAction` database table (`membership_id`, `action_id`, `completed_at`).
* Toggle endpoint: `POST /reports/actions/{action_id}/toggle`.
* Scoped strictly to the employee's active organization membership.
* Cleanly wiped when an employee exercises their **Right to Delete**.
* Diagnostic scores are never modified by action completions.
* **Verification:** Tested by 7 tests in `backend/tests/test_actions.py`.

---

## 6. Testing & Verification Summary

All verification results documented below were reproduced locally in the assessment environment:

### Automated Backend Tests
* **Total Tests:** 56 passed (0 failures) in 4.14 seconds.
* **Test Breakdown:**
  * `test_auth.py` (13 tests): Login credential verification, case-insensitivity, invalid password rejection, unauthorized org selection (403), missing tokens (401), invalid tokens (401), expired tokens (401), pre-org token restrictions (400), admin dashboard role checks (403), cross-tenant isolation (403), multi-org switching.
  * `test_privacy.py` (7 tests): Participant counts for 0, 1, 4, 5, and >5 employees, duplicate response handling, small group aggregation under "Other teams", suppressed group score masking, and top risks suppression.
  * `test_delete.py` (6 tests): Successful response deletion via `/reports/me` and `/diagnostic/responses`, immediate dashboard aggregate update, unauthorized deletion rejection, idempotency on repeated deletion, and employee data isolation.
  * `test_scoring.py` (11 tests): Markdown code fence stripping, missing reason fallbacks, out-of-range score rejection, non-numeric score handling, boolean rejection, invalid flag filtering, malformed JSON recovery, and provider timeout resilience.
  * `test_actions.py` (7 tests): Recommendation generation, empty response handling, targeted risk actions, action completion toggling, cross-user isolation, and deletion integration.
  * `test_questions.py` (6 tests): Role and seniority question filtering across junior, mid, senior, and lead levels.
  * `test_api.py` (6 tests): Baseline API workflows, dashboard verification, and employee report/diagnostic routing contracts (`answered > 0` vs `answered == 0`).

### Frontend Verification
* **Production Build:** `npm run build` executed via Vite 5.4.11; compiled in 621ms with zero errors and zero warnings.
* **Manual UI Verification:**
  * Tested employee login, organization switching, diagnostic submission, and personal report visualization.
  * Tested browser reload (`Ctrl+R`) state rehydration and dynamic routing.
  * Verified "Delete My Diagnostic Data" prompt, deletion confirmation banner, and dashboard respondent count decrements.
  * Verified admin dashboard rendering: table columns, maturity badges, "Other teams" aggregation, and privacy notices.

---

## 7. Deliberate Omissions & Deferred Architectural Work

To balance assessment scope, portability, and zero-configuration grading against production requirements, several architectural enhancements were deliberately deferred:

| Area | Inherited State | Implemented Hardening | Reason Full Upgrade Was Deferred | Recommended Production Solution |
|---|---|---|---|---|
| **Password Hashing** | Unsalted SHA-256 (`hash_password`) | Hardened with `hmac.compare_digest` to prevent timing attacks | Upgrading hash algorithm in-place would invalidate existing seed accounts (`seed.py`) without an interactive login migration pipeline | Migrate to Argon2id with automatic re-hashing on successful login |
| **Session Invalidation** | Stateless JWT (12h TTL) | Client `clearAuth()` on logout and 401/403 detection | In-memory token revocation sets do not survive server restarts or scale across uvicorn workers; Redis introduces external dependencies | Implement Redis-backed token blocklist or DB token versioning column |
| **Database Concurrency** | SQLite file (`aipulse.db`) | Scoped sessions with transaction commits | SQLite requires zero setup for local assessment grading; running PostgreSQL requires Docker or local daemon | Migrate to managed PostgreSQL with connection pooling (e.g. PgBouncer) and Alembic migrations |
| **Rate Limiting** | No request throttling | Fast rejection of invalid inputs | In-process rate limiters create race conditions across multi-worker ASGI processes | Deploy Nginx / Cloudflare reverse proxy with IP and token rate-limiting rules |
| **CSRF Protection** | None (Bearer tokens) | Bearer JWT stored in `localStorage` | Bearer tokens in `Authorization` headers are not ambiently attached by browsers, mitigating classic cross-site request forgery | Keep Bearer token architecture; avoid cookie session storage |

### Technical Details of Deferred Work

#### 1. Password Hashing Limitations
* **Implementation:** `backend/app/auth.py` hashes passwords with `hashlib.sha256(password.encode()).hexdigest()` without salt or key stretching. Verification uses `hmac.compare_digest` to protect against timing side-channel attacks.
* **Limitation:** Unsalted SHA-256 is computationally trivial to brute-force with modern GPUs and vulnerable to precomputed rainbow tables if the database file is accessed.
* **Rationale for Deferral:** Upgrading the hashing algorithm immediately would break authentication for existing pre-seeded users in `seed.py`. Production deployment should adopt an adaptive salted algorithm (Argon2id or PBKDF2) paired with an on-login hash migration pipeline.

#### 2. Stateless JWT Token Revocation
* **Implementation:** `make_token()` generates stateless HMAC-SHA256 JWTs with a 12-hour lifespan (`TOKEN_HOURS = 12`). In `_decode()`, validation is purely cryptographic. When an employee signs out, the client deletes the token from `localStorage` via `clearAuth()`.
* **Limitation:** If a token is intercepted before sign-out, it remains valid on the server until the 12-hour expiration window lapses because the backend does not maintain a server-side revocation registry.
* **Rationale for Deferral:** An in-memory token blocklist would reset on server restart and fail across multiple uvicorn worker processes, while a Redis dependency would hinder zero-configuration assessment evaluation. Production should back token invalidation with a Redis cluster or a `token_version` column on the `User` model.

#### 3. Database Concurrency & Write Contention
* **Implementation:** SQLite (`aipulse.db`) accessed via SQLAlchemy with `connect_args={"check_same_thread": False}`.
* **Limitation:** SQLite enforces database-level write locks. Under high concurrency with simultaneous diagnostic submissions across large departments, write contention can result in `sqlite3.OperationalError: database is locked`.
* **Rationale for Deferral:** SQLite requires zero environment setup for evaluators. Production deployment should transition to PostgreSQL with row-level locking (MVCC), PgBouncer connection pooling, and Alembic database migrations.

#### 4. Rate Limiting & Abuse Prevention
* **Implementation:** Neither `/auth/login` nor `/diagnostic/submit` includes request rate limiting at the application layer.
* **Limitation:** The authentication endpoint is exposed to credential-stuffing brute force, and the diagnostic submission endpoint could be abused to trigger excessive external LLM API costs.
* **Rationale for Deferral:** In-process rate limiters create state drift across multi-worker ASGI instances. Standard enterprise practice delegates rate limiting to the ingress / reverse proxy layer (e.g. Nginx `limit_req_zone`, Cloudflare WAF, or AWS API Gateway).

---

## 8. Client Clarifications & Open Product Decisions

Before rolling out the AI Pulse pilot into Northwind Logistics production, the following business questions should be resolved with HR and Legal:

1. **Audit Logging vs. Right to Delete:** Under GDPR Art. 17 and compliance regulations, should an anonymized audit log entry be preserved (e.g., recording that *an* employee deleted their diagnostic data on date $T$, without recording identity or answers) to provide compliance audit trails?
2. **Dynamic Unbundling of "Other teams":** When a department currently has 4 participants (grouped under "Other teams") and a 5th employee completes the diagnostic, should that department immediately unbundle into its own row on active dashboards, or should results be locked to predetermined survey assessment cycles?
3. **Diagnostic Retake Policy:** Can an employee immediately retake the diagnostic after deleting their responses, or should there be a mandatory cooldown period?
4. **Action Planner History Retention:** When an employee exercises their Right to Delete, the current implementation wipes their `CompletedAction` records alongside their diagnostic responses. HR should confirm whether completed habit records should be deleted or preserved as an employee-owned development record.

---

## 9. AI Tool Usage & Documented AI Error

AI assistance was utilized as a pair-programming partner during development to explore codebase structure, draft test skeletons, and analyze edge cases.

### Specific Documented AI Error
During the creation of the department privacy test suite ([`backend/tests/test_privacy.py`](file:///C:/Users/Joel%20Joy/OneDrive/Desktop/Interview-assesment/assessment/ai-pulse/backend/tests/test_privacy.py)), an AI-suggested test helper function was initially implemented to seed mock departments:

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
* **The Correction:** The flaw was investigated and corrected by storing `dept_id = dept.id` while the session was open and active prior to `db.commit()` and `db.close()`, as seen in lines 14 and 46 of `backend/tests/test_privacy.py`.

---

## 10. Production-Readiness Considerations

To transition AI Pulse from assessment demonstration to production:

* **Secret Management:** Move `SECRET_KEY` and LLM credentials out of `.env` files into an enterprise key management service (e.g., AWS Secrets Manager, HashiCorp Vault, or GCP Secret Manager).
* **CORS Restrictions:** Restrict `CORSMiddleware` in `backend/app/main.py` from `allow_origins=["*"]` to explicit, validated enterprise domain origins.
* **Database Migration:** Replace SQLite with a managed PostgreSQL instance and introduce Alembic for schema migrations instead of `Base.metadata.create_all()`.
* **Security Headers & Reverse Proxy:** Deploy behind an Nginx or Cloudflare reverse proxy enforcing TLS 1.3, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, and `Content-Security-Policy`.
* **Automated CI/CD Pipeline:** Enforce backend linting (Ruff/Flake8), type checking (Mypy), and the 56-test Pytest suite on all pull requests prior to deployment.
