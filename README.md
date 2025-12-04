# Vacation Planner LLM PoC

Proof-of-concept vacation planner with a FastAPI backend, mock tools (calendar, booking, search), and pluggable LLM layer. Focused on showing planning flow, structured outputs, and simulated bookings.

## Run locally
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Streamlit UI (optional)
```bash
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
BACKEND_URL=http://localhost:8000 streamlit run app.py
```

## API quickstart
- Health: `GET http://localhost:8000/health`
- Plan: `POST http://localhost:8000/plan` with JSON:
```json
{
  "destination_preferences": ["Lisbon", "Bali"],
  "min_duration_days": 3,
  "max_duration_days": 5,
  "budget_max": 1500,
  "travel_style": "relaxing"
}
```
- Get plan: `GET http://localhost:8000/plan/{trip_id}`
- Book (simulate): `POST http://localhost:8000/plan/{trip_id}/book`

## Tests
```bash
cd backend
pytest
```

## Architecture (high level)
- `app/llm`: Planner abstraction (`LLMClient`) with mock backend; prompts stored separately.
- `app/llm/tools`: Mock integrations for calendar, search catalog, preferences merge, booking simulation.
- `app/services`: Orchestrates planning and booking, persists to `InMemoryRepository`.
- `app/models`: Domain entities and Pydantic schemas for API.
- `app/api`: FastAPI routes for planning, booking, and health checks.
- `frontend/`: Streamlit PoC UI to submit preferences, view plan, and trigger simulated bookings.
- Calendar ICS: set `CALENDAR_ICS_URL` in `.env` (e.g., public/secret Google Calendar ICS) and backend will ingest busy slots on startup. Keep secret ICS URLs out of logs and never expose to clients.
- RAG (optional): place `.txt` files under path in `RAG_DOCS_PATH` (default `/extracted`) to index lightweight context (FAISS if available, fallback otherwise). Planner will sprinkle top snippet into activity descriptions.

Authentication/authorization is not implemented (single demo user). Do not store real payment data; bookings are simulated.
