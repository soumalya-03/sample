# Enterprise Document Chatbot

A production-minded RAG application for local and cloud document QA, with FastAPI backend, React + Vite frontend, Chroma vector storage, LangChain/LangGraph orchestration, and SQLite persistence.

## Architecture

- Frontend: React + TypeScript + Vite + Tailwind
- Backend: FastAPI + SQLAlchemy + Pydantic + LangChain + LangGraph
- Storage: SQLite + local file storage + ChromaDB persistent collections
- Models: local Ollama default, optional Groq or provider adapters

## Local setup

1. Create and activate a Python environment:
   - `py -m venv .venv`
   - `.venv\Scripts\Activate.ps1`
2. Install backend dependencies:
   - `py -m pip install -r backend/requirements.txt`
3. Copy environment file:
   - `Copy-Item .env.example .env`
4. Update `.env` for your local model configuration.
5. Initialize the database:
   - `py -m backend.app.main` or call the app bootstrap in the backend service.
6. Install Node.js LTS and build the frontend:
   - `Set-Location frontend`
   - `npm install`
   - `npm run build`
   - `Set-Location ..`
7. Start the app:
   - `py -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000`

## Required local models

For the default local mode, install Ollama and pull models such as:

- `ollama pull llama3.1`
- `ollama pull nomic-embed-text`

The app will fail gracefully when these are unavailable and will show startup health warnings.

## Deployment

See Docker Compose and Dockerfiles in the repository root and backend/frontend folders.

## Environment variables

The main settings are in `.env.example`.

## Smoke tests

- Upload a supported document.
- Confirm the document enters `processed` state.
- Ask a question grounded in a document.
- Confirm citations include filename and excerpt.
- Verify cross-user isolation in multi-user mode.

## Notes

This project defaults to a safe local-first mode. Paid providers are optional and never activated automatically.

## KPI dashboard status

For a complete architecture, data, login, dashboard, and manager Q&A walkthrough, see [DASHBOARD_EXPLANATION_GUIDE.md](DASHBOARD_EXPLANATION_GUIDE.md).

The existing FastAPI + React application now reads its individual demo scorecards and process history from `data/demo_process_kpi_data.xlsx`. KPI names and formulas are extracted from the role-specific sheets in `storage/Medical_Device_Business_Services_Inc_Mentor_08_09_2026.xlsx`; process executions, weekly measurements, and SLA alerts are synthetic examples. They are explicitly labeled `DEMO / SYNTHETIC DATA` and are not approved business results.

The dashboard includes account-scoped role KPIs, weekly trends, a searchable process execution ledger, in-progress elapsed time, a separate retry attempt, and traceable SLA alerts. Incomplete executions have no actual duration. Control limits are not populated because the workbook does not provide enough validated historical observations. Role 14 demo targets are explicitly synthetic examples, not source-supplied or approved business thresholds.

Customer Metrics KPI cards open an authenticated KPI detail view at `/kpis/{kpi_id}`. The source workbook defines KPI tabs for Roles 01–16. `KPI_Observations` contains 150 clearly synthetic account observations per source-defined KPI, and `KPI_Measurements` provides weekly aggregates for each demo login. `GET /api/kpis` and `GET /api/kpis/{kpi_id}/details` calculate each selected KPI and period from workbook rows. Daily, Weekly, Monthly, Quarterly, and Yearly selections aggregate matching dated observations. The compact detail page shows current value, the explicitly illustrative Role 14 target (where configured), a synthetic role-wide average, period trend, source formula, and update time; it does not download or display the full observation ledger.

Role 01–16 responsibilities and formulas are extracted from the source workbook's `Role_Responsibilities` sheet. `Responsibilities` and `Responsibility_Work` in the generated workbook link those source responsibilities to illustrative status records and synthetic customer requests. The dashboard offers authenticated `GET /api/dashboard/responsibilities`, `GET /api/dashboard/responsibilities/{responsibility_id}`, and paginated `GET /api/dashboard/process-executions` endpoints. Status and text filters are applied by the API before returning work/execution rows. Dashboard summaries load without the full process execution ledger.

Regenerate the demo data after changing the source workbook with:

```powershell
py backend/scripts/generate_demo_process_kpi_data.py
```

The generated workbook separates customer requests, process master/workflow definitions, activities/tasks, 19 demo persona/resource assignments, process executions, source KPI definitions, weekly KPI measurements, 150 account-level observations per KPI for source Roles 01–16, source responsibilities for Roles 01–16, illustrative responsibility work/status records, alert rules/history, business outcomes, and a field-level data dictionary. Role 17 – Manager has a demo login and process dashboard but no role-specific KPI or responsibility tab in the supplied source workbook; its KPI view contains only the shared process-execution metrics.

The 17 role demo accounts below are assigned and enforced by the backend. On the login form, selecting any of the 17 personas fills in that role's matching demo email and password; the fields can be edited if needed. Select any of the three categories, as category is a demo-form selection and does not affect dashboard authorization. Two existing convenience accounts are also retained: `admin@local.dev` / `local-dev` (Role 09) and `sales@local.dev` / `local-sales` (Role 14). Selecting a different persona for an account is rejected. These fixed demo passwords are for local demonstration only; do not use them outside this development app. Google/Microsoft OAuth and email OTP are not configured.

| Role | Demo email | Password |
|---|---|---|
| 01 | `role01@local.dev` | `role01-demo` |
| 02 | `role02@local.dev` | `role02-demo` |
| 03 | `role03@local.dev` | `role03-demo` |
| 04 | `role04@local.dev` | `role04-demo` |
| 05 | `role05@local.dev` | `role05-demo` |
| 06 | `role06@local.dev` | `role06-demo` |
| 07 | `role07@local.dev` | `role07-demo` |
| 08 | `role08@local.dev` | `role08-demo` |
| 09 | `role09@local.dev` | `role09-demo` |
| 10 | `role10@local.dev` | `role10-demo` |
| 11 | `role11@local.dev` | `role11-demo` |
| 12 | `role12@local.dev` | `role12-demo` |
| 13 | `role13@local.dev` | `role13-demo` |
| 14 | `role14@local.dev` | `role14-demo` |
| 15 – CSR | `role15@local.dev` | `role15-demo` |
| 16 | `role16@local.dev` | `role16-demo` |
| 17 – Manager | `role17@local.dev` | `role17-demo` |

## Login personas

- Role 01 – CC Customer
- Role 02 – CC Inventory
- Role 03 – CC Warranty
- Role 04 – BO Customer
- Role 05 – BO Inventory
- Role 06 – BO Warranty
- Role 07 – CC Manager
- Role 08 – BO Manager
- Role 09 – Operations Manager
- Role 10 – Quality Analyst
- Role 11 – Admin Executive
- Role 12 – Surgeon
- Role 13 – Office Manager
- Role 14 – Sales Rep
- Role 15 – CSR
- Role 16 – Patient
- Role 17 – Manager

The supplied KPI workbook contains 16 role tabs and no Role 17 tab. Role 15 is named CSR in the source workbook and dashboard; the previous frontend "CEO" label was corrected to match the source. Role 17 is preserved as a login persona but is not assigned fabricated role-specific KPI definitions or responsibilities.

## Run the dashboard

Install frontend dependencies, build the React app, and start FastAPI:

```powershell
Set-Location frontend
npm install
npm run build
Set-Location ..
py -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000/`. For live frontend development, use `npm run dev` from `frontend` in one terminal and start FastAPI in another; open `http://localhost:5173/`. If no build exists in development, FastAPI redirects `/` to Vite.

Demo credentials: `admin@local.dev` / `local-dev` and `sales@local.dev` / `local-sales`.

All observations in the generated workbook are synthetic. Production process tracking, persistent assignment history, validated SLA targets/control-limit rules, category authorization, remaining persona assignments, and OAuth/email OTP require separate integration work.
