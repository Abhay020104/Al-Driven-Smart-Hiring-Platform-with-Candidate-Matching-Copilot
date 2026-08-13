# AI-Driven Smart Hiring Platform Copilot

An AI-powered end-to-end recruitment platform built with **Streamlit** (frontend) and **FastAPI** (backend), integrated with **Ollama / Llama 3.2** for local AI inference — zero cloud API costs.

## Architecture

```
┌─────────────────────────┐      ┌──────────────────────────┐      ┌──────────────┐
│   Streamlit Frontend    │─────▶│   FastAPI Backend         │─────▶│   Ollama      │
│   (app.py, port 8501)   │ REST │   (backend/, port 8000)   │ HTTP │  (port 11434) │
│   Custom CSS + Plotly   │ API  │   SQLAlchemy + JWT Auth   │      │  Llama 3.2    │
└─────────────────────────┘      └──────────────────────────┘      └──────────────┘
                                          │
                                          ▼
                                 ┌──────────────────┐
                                 │  SQLite Database  │
                                 │  recruitment.db   │
                                 └──────────────────┘
```

## Quick Start

### Option A — Unified Launcher (Recommended)

Start both backend and frontend in a single terminal:

```bash
pip install -r requirements.txt
cp .env.example .env        # adjust values if needed
python start.py
```

The launcher will:
1. Check if Ollama is running on port 11434
2. Kill any stale processes on ports 8000 and 8501
3. Start the FastAPI backend (auto-creates tables & seeds demo data)
4. Wait for the backend to become healthy
5. Start the Streamlit frontend
6. Print URLs for all services

### Option B — Manual Start (3 Terminals)

**Terminal 1 — Backend:**
```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Ollama:**
```bash
ollama serve
ollama pull llama3.2:latest
```

**Terminal 3 — Frontend:**
```bash
streamlit run app.py
```

### URLs

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:8501         |
| Backend   | http://localhost:8000         |
| Swagger   | http://localhost:8000/docs    |
| ReDoc     | http://localhost:8000/redoc   |

## Default Demo Accounts

| Role      | Email                   | Password       |
|-----------|-------------------------|----------------|
| Recruiter | recruiter@infosys.com   | recruiter123   |
| Candidate | candidate@example.com   | candidate123   |

## Features

### Role-Based Access (RBAC)

**Candidate Portal:**
- 🏠 Browse Jobs — view open positions with skills, location & salary band
- 📄 My Applications — track submitted applications and their stages
- 📤 Upload Resume — upload PDF/DOCX/TXT, AI extracts text automatically
- 🤖 Chat with AI — recruitment-scoped AI copilot

**Recruiter Dashboard (10 modules):**
- 🏠 Overview — real-time pipeline metrics, KPI cards, active roles overview
- 📋 JD Analyser — paste a job description, AI extracts skills, seniority, flags & rewrites it
- 🔍 Find Candidates — filter by role/stage/match, AI hiring recommendations, comparisons
- 📄 Resume AI — upload resumes, AI parses skills & scores against open roles
- 🗓️ Interviews — schedule & track multi-stage interviews and generate AI-driven technical tests
- 🎓 Onboarding — convert hired candidates with AI document verification
- 📊 Recruitment Insights — funnel analytics, pipeline velocity, interactive Plotly charts
- 📧 Communications — AI-generated emails (offer, rejection, follow-up, interview invite)
- 📑 Reports — AI-generated recruitment reports with executive summaries
- 🤖 Chat with AI — context-aware recruiter assistant with full pipeline data

### AI Capabilities (Powered by Llama 3.2 via Ollama)

| Feature                | Description                                                              |
|------------------------|--------------------------------------------------------------------------|
| JD Analysis            | Extracts skills, seniority, experience, red flags, salary & rewrites JD  |
| Resume Parsing         | Local keyword extraction for skills, education, certifications, experience |
| Resume Scoring         | LLM matches candidate skills vs role requirements with % score & verdict |
| AI Chat Copilot        | Role-aware contextual assistant, strictly scoped to HR/recruitment topics |
| Email Generation       | Professional emails (offer, rejection, follow-up) tailored per candidate |
| Hiring Recommendation  | Verdict (Recommend/Waitlist/Decline) with confidence & rationale         |
| Report Generation      | Markdown reports: executive summary, metrics, bottlenecks, recommendations |
| AI Interviews          | Automatically generates technical questions and evaluates candidate answers |
| Document Verification  | AI verifies onboarding documents (ID proof, salary slips, certificates)  |

## API Endpoints

### Auth (`/api/auth`)
| Endpoint               | Method | Auth       | Description               |
|------------------------|--------|------------|---------------------------|
| `/api/auth/register`   | POST   | Public     | Create account            |
| `/api/auth/login`      | POST   | Public     | Login, get JWT token      |
| `/api/auth/me`         | GET    | Any role   | Current user profile      |
| `/api/auth/users`      | GET    | Recruiter  | List all users            |

### Roles (`/api/roles`)
| Endpoint               | Method | Auth       | Description               |
|------------------------|--------|------------|---------------------------|
| `/api/roles`           | GET    | Recruiter  | All roles (full detail)   |
| `/api/roles/public`    | GET    | Public     | Open positions (limited)  |
| `/api/roles/{id}`      | GET    | Recruiter  | Single role detail        |
| `/api/roles`           | POST   | Recruiter  | Create new role           |
| `/api/roles/{id}`      | PUT    | Recruiter  | Update role               |
| `/api/roles/{id}`      | DELETE | Recruiter  | Delete role               |

### Candidates (`/api/candidates`)
| Endpoint                          | Method | Auth       | Description               |
|-----------------------------------|--------|------------|---------------------------|
| `/api/candidates`                 | GET    | Recruiter  | All candidates (filterable by role/stage) |
| `/api/candidates/{id}`            | GET    | Recruiter  | Single candidate detail   |
| `/api/candidates`                 | POST   | Recruiter  | Create candidate          |
| `/api/candidates/{id}`            | PUT    | Recruiter  | Update candidate          |
| `/api/candidates/{id}`            | DELETE | Recruiter  | Delete candidate          |
| `/api/candidates/apply`           | POST   | Any role   | Self-service job apply    |
| `/api/candidates/my-applications` | GET    | Any role   | Own applications          |

### AI (`/api/ai`)
| Endpoint                          | Method | Auth       | Description               |
|-----------------------------------|--------|------------|---------------------------|
| `/api/ai/analyse-jd`             | POST   | Recruiter  | Analyze job description   |
| `/api/ai/parse-resume`           | POST   | Any role   | Extract skills from text  |
| `/api/ai/score-resume`           | POST   | Recruiter  | Score resume vs role      |
| `/api/ai/chat`                   | POST   | Any role   | AI copilot chat           |
| `/api/ai/generate-email`        | POST   | Recruiter  | Generate recruitment email |
| `/api/ai/hiring-recommendation` | POST   | Recruiter  | AI hiring recommendation  |
| `/api/ai/generate-report`       | POST   | Recruiter  | Generate recruitment report |

### AI Interview (`/api/ai-interview`)
| Endpoint                                   | Method | Auth       | Description               |
|--------------------------------------------|--------|------------|---------------------------|
| `/api/ai-interview/generate`               | POST   | Recruiter  | Generate AI interview     |
| `/api/ai-interview/test/{token}`           | GET    | Public     | Get test questions        |
| `/api/ai-interview/submit/{token}`         | POST   | Public     | Submit test answers       |
| `/api/ai-interview/list`                   | GET    | Recruiter  | List all interviews       |
| `/api/ai-interview/report/{interview_id}`  | GET    | Recruiter  | View test report          |

### Uploads (`/api/uploads`)
| Endpoint                        | Method | Auth       | Description               |
|---------------------------------|--------|------------|---------------------------|
| `/api/uploads/resume`           | POST   | Any role   | Upload resume (PDF/DOCX/TXT) |
| `/api/uploads/resume/{filename}`| GET    | Recruiter  | Download uploaded resume  |

### Onboarding (`/api/onboarding`)
| Endpoint                            | Method | Auth       | Description                    |
|-------------------------------------|--------|------------|--------------------------------|
| `/api/onboarding/verify-document`   | POST   | Recruiter  | AI document verification       |
| `/api/onboarding/convert`           | POST   | Recruiter  | Mark candidate as onboarded    |

## Project Structure

```
├── app.py                     # Streamlit frontend (10 modules)
├── style.css                  # Custom CSS theme 
├── start.py                   # Unified launcher (backend + frontend)
├── requirements.txt           # Python dependencies
├── recruitment.db             # SQLite database (auto-created)
├── .env.example               # Environment variable template
├── .env                       # Local environment config (not in git)
├── .gitignore                 # Git ignore rules
├── .streamlit/
│   └── config.toml            # Streamlit theme & server config
├── uploads/                   # Uploaded resumes & onboarding documents
└── backend/
    ├── __init__.py
    ├── main.py                # FastAPI app entry point, CORS, router registration
    ├── config.py              # Pydantic settings (loaded from .env)
    ├── database.py            # SQLAlchemy engine, session, Base
    ├── seed.py                # Demo data seeder (users, roles, candidates)
    ├── auth/
    │   ├── __init__.py
    │   ├── security.py        # bcrypt hashing, JWT encode/decode
    │   └── dependencies.py    # get_current_user, require_role
    ├── models/
    │   ├── __init__.py        # Exports: User, Role, Candidate
    │   ├── user.py            # User model (candidate | recruiter)
    │   ├── role.py            # Role / job requisition model
    │   ├── candidate.py       # Candidate model (20+ fields)
    │   ├── ai_interview.py    # AI Interview model
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth.py            # Register, Login, Token, UserOut
    │   ├── role.py            # RoleCreate, RoleUpdate, RoleOut, RolePublicOut
    │   ├── candidate.py       # CandidateCreate, CandidateUpdate, CandidateOut, CandidateApplyRequest
    │   ├── ai.py              # JD, Resume, Chat, Email, Hiring, Report schemas
    │   ├── ai_interview.py    # AIInterview requests and responses
    │   └── onboarding.py      # DocumentVerifyResponse, OnboardConvertRequest/Response
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py            # Register, login, profile, user list
    │   ├── roles.py           # Full CRUD + public listing
    │   ├── candidates.py      # Full CRUD + self-service apply + my-applications
    │   ├── ai.py              # 7 AI endpoints
    │   ├── ai_interview.py    # AI Interview endpoints
    │   ├── uploads.py         # Resume upload & download
    │   └── onboarding.py      # Document verification + candidate onboarding
    └── services/
        ├── __init__.py
        ├── llm.py             # Async Ollama REST client (httpx, 120s timeout)
        ├── ai_service.py      # AI business logic (JD, resume, chat, email, hiring, report)
        └── file_parser.py     # PDF/DOCX/TXT text extraction
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable                     | Default                          | Description                    |
|------------------------------|----------------------------------|--------------------------------|
| `DATABASE_URL`               | `sqlite:///./recruitment.db`     | SQLAlchemy database URL        |
| `OLLAMA_BASE_URL`            | `http://localhost:11434`         | Ollama API base URL            |
| `OLLAMA_MODEL`               | `llama3.2:latest`                | LLM model to use               |
| `JWT_SECRET_KEY`             | `change-me-to-a-random-secret`   | Secret key for JWT tokens      |
| `JWT_ALGORITHM`              | `HS256`                          | JWT signing algorithm          |
| `JWT_EXPIRE_MINUTES`         | `1440`                           | Token expiry (24 hours)        |
| `UPLOAD_DIR`                 | `./uploads`                      | File upload storage directory  |
| `CORS_ORIGINS`               | `http://localhost:8501`          | Allowed CORS origins           |
| `GOOGLE_WORKSPACE_EMAIL`     | `(empty)`                        | Email for calendar/email AI integr. |
| `GOOGLE_WORKSPACE_PASSWORD`  | `(empty)`                        | App Password for Workspace     |

## Database Models

| Table        | Key Fields                                                                 |
|-------------|----------------------------------------------------------------------------|
| `users`      | id, name, email, hashed_password, role (candidate/recruiter), is_active   |
| `roles`        | id, req_id, role, business_unit, location, openings, applicants, screened, shortlisted, interview, offer, hired, days_open, risk, priority, required_skills, experience_min, salary_band |
| `candidates`   | id, user_id, candidate, role, location, experience, match, skills_match, stage, availability, salary_fit, risk, skills, source, education, certifications, summary, resume_filename |
| `ai_interviews`| id, token, candidate_id, role_id, jd_skills, difficulty, focus_area, num_questions, questions, answers, report, status |

All tables include `created_at` and `updated_at` timestamps.

## Tech Stack

| Layer          | Technologies                                          |
|---------------|-------------------------------------------------------|
| **Frontend**   | Streamlit ≥ 1.36, Plotly, Pandas                     |
| **Backend**    | FastAPI ≥ 0.115, Uvicorn, SQLAlchemy ≥ 2.0, Pydantic ≥ 2.4 |
| **Auth**       | JWT (python-jose) + bcrypt (passlib)                  |
| **Database**   | SQLite (local, auto-created)                          |
| **AI/LLM**     | Ollama (Llama 3.2) via async httpx                    |
| **File Parsing**| PyPDF2 ≥ 3.0, python-docx ≥ 1.1                     |
| **Config**     | pydantic-settings, python-dotenv                      |


