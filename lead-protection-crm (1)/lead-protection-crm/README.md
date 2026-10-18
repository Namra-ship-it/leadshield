# Lead Protection CRM - Hackathon MVP

> **Core Promise**: An inbound lead is guaranteed to have exactly one accountable owner at all times. If ignored, it escalates on a visible countdown timer, alerts backup reps via Telegram/Slack, and every state change is permanently recorded in an immutable audit log.

---

## 🏗️ Architecture & Stack
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0, Pydantic V2, Argon2 password hashing
- **Database**: PostgreSQL (with automatic SQLite fallback for zero-friction local development)
- **Frontend**: React, Vite, Tailwind CSS, Lucide Icons
- **Isolation Guarantee**: Multi-tenant workspace isolation enforced at every server endpoint
- **Modular Codebase**:
  - `backend/app/business_rules/`: Core business logic & permissions matrix
  - `backend/app/data_access/`: Data access layer with tenant scoping
  - `backend/app/core/`: Security (Argon2, JWT), database engine, dependencies
  - `backend/app/models/`: SQLAlchemy models
  - `backend/app/schemas/`: Pydantic V2 request/response validation
  - `backend/app/api/v1/`: RESTful routes
  - `backend/tests/`: Automated unit & isolation integration test suite
  - `frontend/`: React + Vite client

---

## 🚀 Step 1 Completed: Auth & Workspaces
- Workspace Signup, Argon2 password hashing, RBAC (Owner/Admin/User), and server-side workspace isolation.

---

## 🎯 Step 2 Completed: CRM Core & Pipeline Board
- Contacts, Companies, Opportunities, visual Kanban pipeline board with stage moves, and dynamic custom fields.

---

## ⚡ Step 3 Completed: Lead Engine & Timed Escalation

### Features Implemented:
1. **Public Web Form Capture**:
   - `POST /api/v1/leads/public` allows unauthenticated lead capture directly from web forms / landing pages.
   - Automatically finds or creates the `Contact` and auto-routes the lead.
2. **Round Robin with Availability & Open-Lead Cap**:
   - Routes among reps whose status is `Available`.
   - Never routes to employees marked `Busy`, `On leave`, or `Offline`.
   - Enforces `max_open_leads_per_rep` (e.g. 5 leads cap).
3. **Visible Countdown Acknowledgement Window**:
   - Every lead assigned has an exact countdown deadline (`acknowledgement_deadline`).
   - The UI shows live ticking countdown timer bars (`⏱ 18s left`).
   - One-click **"Acknowledge Lead"** stops the timer and confirms accountability.
4. **Escalation Chain When Ignored**:
   - When a timer expires without acknowledgement:
     - **Level 0 ➔ Level 1**: Auto-escalates to the next available backup rep.
     - **Level 1 ➔ Level 2**: Auto-escalates to the workspace Manager or Owner.
     - **Level 2 ➔ Level 3**: Moves to the **Recovery Queue**.
   - Timers are persisted in the database via **APScheduler SQLAlchemyJobStore** so they survive server restarts.
5. **Atomic Escalation Guarantee (No Double Escalation)**:
   - Uses atomic conditional updates (`expected_level`) so two timers firing at the exact same millisecond can never escalate a lead twice.
6. **Automatic Reassignment on Leave**:
   - When any employee toggles their status to `On leave`, the engine immediately reassigns all their unacknowledged leads to active team members with fresh timers.
7. **Recovery Queue & Claiming**:
   - `GET /api/v1/leads/recovery-queue` lists leads requiring manager intervention.
   - Any available rep or manager can claim a recovered lead with one click (`POST /api/v1/leads/{id}/claim`).

---

## 🛠️ Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- Node.js 18+

### 2. Backend Setup
```bash
# Navigate to project root
cd lead-protection-crm

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
# On Linux/macOS: source .venv/bin/activate

# Install dependencies (if needed)
pip install -r backend/requirements.txt

# Run backend server
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```
Backend will be live at: `http://localhost:8000` (Docs: `http://localhost:8000/docs`)

### 3. Frontend Setup
```bash
# In a new terminal:
cd lead-protection-crm/frontend

# Install dependencies
npm install

# Run frontend dev server
npm run dev
```
Frontend will be live at: `http://localhost:5173`

---

## 🧪 Running Automated Tests

Run the workspace isolation and permission test suite:
```bash
# In lead-protection-crm directory
$env:PYTHONPATH="backend"
.\.venv\Scripts\pytest backend\tests -v
```

### Verified Test Cases:
- `test_signup_creates_workspace_and_owner`: Verifies workspace creation, Owner role, and Argon2 password hash.
- `test_login_success_and_invalid_credentials`: Verifies JWT issuance and 401 on bad credentials.
- `test_workspace_isolation_between_tenants`: Proves two workspaces (Workspace A & B) cannot read each other's data even by guessing IDs.
- `test_rbac_roles_and_permissions`: Proves Owner vs Admin vs User authorization boundaries.
