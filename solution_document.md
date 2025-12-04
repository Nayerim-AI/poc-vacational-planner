# Solution Document

## Problem understanding
A PoC vacation planner that collects user preferences, checks calendar availability, proposes an itinerary within budget, and simulates bookings (flights, hotels, activities). Uses an LLM-style planner abstraction but ships with a deterministic mock backend for offline/demo use.

## Use cases & journey
- User submits preferences (destinations, budget, timing constraints).
- System checks calendar availability, selects dates, and suggests an itinerary with budget breakdown.
- User retrieves saved plan and triggers simulated bookings.

## High-level architecture
- **FastAPI backend** (`backend/main.py`) exposes planning, booking, and health endpoints.
- **LLM layer** (`app/llm`) with `LLMClient` abstraction and `MockPlannerBackend` for deterministic planning; prompts are stored separately for future real-model swaps.
- **Tools** (`app/llm/tools`): calendar (availability), search (destinations catalog), preferences (merge defaults), booking (simulate reservations).
- **RAG** (`app/llm/tools/rag_store.py`): optional FAISS-backed store that loads `.txt` docs from `RAG_DOCS_PATH` (default `/extracted`) and surfaces top snippets to the planner.
- **Services** (`app/services`): orchestrate planner and booking flows, interact with storage.
- **Storage** (`app/storage`): in-memory repository for plans and booking records.
- **Models** (`app/models`): domain dataclasses and Pydantic schemas for requests/responses.
- **Tests** (`backend/tests`): cover planner budget behavior and booking simulation.
- **Frontend** (`frontend/app.py`): Streamlit form to submit preferences, view plan, and trigger simulated bookings against the backend.

## Tech stack choices
- Python 3.10+, FastAPI for lightweight API.
- Pydantic for typed schemas/settings.
- Mock LLM backend to avoid external dependencies; `LLMClient` enables swapping to open-source (Ollama/HF) or hosted APIs later.
- In-memory storage keeps the PoC simple; swap to SQLite/JSON by replacing `InMemoryRepository`.

## Planner logic
1. Merge preferences with defaults (duration, budgets).
2. Calendar tool finds available date ranges; selects requested dates if free or first available slot within 90 days.
3. Select destination from preferences (falls back to catalog default).
4. Assemble daily activities from catalog, respecting duration.
5. Build budget summary (flight + hotel + activities) capped at user budget.
6. Persist plan and return structured JSON (`TripPlanSchema`).

Error handling: if requested dates unavailable or no free ranges, raise HTTP 400/500 via service layer; planner logs failures.

## Data models
- `TripPlan`: trip_id, user_id, destination, start/end dates, day-by-day activities, budget summary.
- `BookingRecord`: booking_id, type (flight/hotel/activity), status, provider, price, payment_status, reference.
- API schemas mirror domain models for FastAPI responses.

## Key design decisions & trade-offs
- Mock planner backend to keep demo offline and deterministic; real LLM can plug into `PlannerBackend.generate_plan`.
- In-memory storage over DB for speed; trade-off is volatility and lack of concurrency safety.
- Minimal catalog and calendar data keep logic transparent; not suitable for real inventory or pricing.
- Single demo user assumption simplifies auth but is not production-ready.

## Assumptions
- Demo user id from config (`DEFAULT_USER_ID`).
- Calendar access is mocked; busy ranges seeded on startup.
- Payment is simulated; `payment_allowed` flag toggles success/failure.
- Destinations limited to small catalog for PoC; extend via `SearchTool`.

## Limitations
- No authentication/authorization.
- No persistence beyond process lifetime.
- Planner uses deterministic logic instead of true LLM reasoning.
- Pricing and inventory are static; no real-time data or availability checks.
- No frontend included yet (API-first).
