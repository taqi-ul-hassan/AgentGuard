# Agent Guard

Agent Guard is a real-time safety checkpoint for clinical AI agents. It generates or accepts a clinical recommendation, verifies it with an independent Agent Guard verifier, makes a deterministic `PASS` or `FLAG` decision, explains the decision, and stores an audit trail.

The application is intentionally compact for hackathon delivery: one FastAPI backend, one Streamlit frontend, SQLite persistence, Docker Compose deployment, and Fireworks AI through an OpenAI-compatible API.

## Architecture

```text
Clinician
  -> Streamlit Dashboard
  -> FastAPI Backend
  -> Clinical Agent Service
  -> Fireworks AI
  -> Agent Guard Verification Orchestrator
  -> Decision Engine
  -> Explainability Engine
  -> SQLite Audit Store
  -> Streamlit Results
```

The verifier uses one structured LLM call per recommendation. Context validation, safety verification, policy verification, and confidence/risk assessment modules parse that shared verifier report rather than making independent model calls.

## Services

- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite
- Frontend: Streamlit
- LLM provider: Fireworks AI through its OpenAI-compatible chat completions endpoint
- Optional hardware path: AMD ROCm-compatible local OpenAI-style model endpoint

## Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `FIREWORKS_API_KEY` | Fireworks API key for live model calls | empty |
| `FIREWORKS_CLINICAL_MODEL` | Model used by the clinical agent | `accounts/fireworks/models/llama-v3p1-8b-instruct` |
| `FIREWORKS_VERIFIER_MODEL` | Model used by Agent Guard verifier | `accounts/fireworks/models/llama-v3p1-8b-instruct` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./agent_guard.db` |
| `POLICY_PATH` | YAML policy file path | `app/policies/default_clinical_policies.yaml` |
| `AGENT_GUARD_API_BASE_URL` | Frontend-to-backend URL | `http://localhost:8000` |
| `ENABLE_LOCAL_ROCM` | Enables ROCm deployment profile metadata | `false` |
| `LOCAL_ROCM_BASE_URL` | Local ROCm OpenAI-compatible endpoint | `http://localhost:8001/v1` |

Without `FIREWORKS_API_KEY`, the API fails closed and returns a `FLAG` response instead of crashing. This keeps the demo stable even before live credentials are configured.

## Run With Docker

```bash
docker compose up --build
```

Open:

- Streamlit: http://localhost:8501
- FastAPI docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The backend stores SQLite data in the `audit_data` Docker volume.

## Run Locally

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Demo Instructions

1. Open Streamlit.
2. Select a synthetic demo case.
3. Click `Load Case`.
4. Choose either `Generate and verify` or `Verify existing recommendation`.
5. Click `Run Agent Guard`.
6. Review decision, risk level, confidence, explanation, module findings, policy findings, and audit history.

Included synthetic cases:

- Safe recommendation
- Unsafe recommendation
- Medication allergy conflict
- High-risk patient
- Missing context

All demo data is fictional.

## API Endpoints

- `GET /health`
- `POST /v1/recommendations/generate-and-verify`
- `POST /v1/recommendations/verify`
- `GET /v1/audits`
- `GET /v1/audits/{audit_id}`
- `GET /v1/policies`
- `POST /v1/policies/reload`

OpenAPI documentation is available at `/docs`.

## Project Structure

```text
backend/
  app/
    api/              FastAPI routes and schemas
    core/             settings, logging, errors, prompt loading
    decision/         deterministic PASS/FLAG logic
    explainability/   clinician-facing explanation generation
    llm/              Fireworks and local ROCm client adapters
    policies/         configurable YAML governance policies
    prompts/          prompt templates
    services/         application workflow services
    storage/          SQLAlchemy models and repositories
    verification/     verifier models, orchestrator, module parsers
  tests/
frontend/
  pages/              Streamlit secondary pages
  streamlit_app.py    Recommendation Review page
  ui_helpers.py       shared UI/API/demo helpers
```

## ROCm Support

`docker-compose.rocm.yml` exposes AMD GPU devices for ROCm-compatible deployments. The backend also includes a local OpenAI-compatible ROCm client adapter for future on-prem verifier or clinical model serving.

Example:

```bash
docker compose -f docker-compose.yml -f docker-compose.rocm.yml up --build
```

## Testing

```bash
pip install -r requirements.txt
pytest
python -m compileall -q backend frontend
```

The test suite covers:

- API startup and validation behavior
- Decision engine rules
- Policy loading and parsing
- Verifier JSON parsing
- Repository persistence
- Recommendation-to-audit workflow

## Security Notes

- No API keys are hardcoded.
- Request validation errors do not echo submitted clinical content.
- Structured logs avoid logging raw patient payloads.
- YAML policies are loaded with `safe_load`.
- This project is for clinical review support only and does not make autonomous medical decisions.

## Limitations

- SQLite is suitable for the demo and single-node usage, not high-concurrency production.
- Confidence scores are verifier estimates, not calibrated clinical probabilities.
- Streamlit is optimized for demo speed, not production EHR embedding.
- Live clinical quality depends on model selection, prompt quality, and configured policies.

## Future Work

- PostgreSQL migration path
- Authentication and role-based access
- FHIR/EHR adapters
- Guideline retrieval and citation support
- Human override workflow
- Continuous evaluation dashboard

## Troubleshooting

- If every request returns `FLAG HIGH`, check `FIREWORKS_API_KEY`.
- If Streamlit cannot reach the backend in Docker, verify `AGENT_GUARD_API_BASE_URL=http://backend:8000`.
- If audit history is empty, run a recommendation review first and confirm the backend can write to the SQLite volume.
- If policies fail to load, verify `POLICY_PATH` points to a valid YAML file with a `version` and `policies` list.
