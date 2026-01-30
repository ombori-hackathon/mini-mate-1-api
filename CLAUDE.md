# Hackathon API - FastAPI Backend

Python FastAPI backend with PostgreSQL database.

## Commands
- Run dev server: `uv run fastapi dev`
- Run tests: `uv run pytest`
- Sync dependencies: `uv sync`
- Add dependency: `uv add <package>`

## Project Structure
```
app/
├── main.py          # FastAPI app entry point
├── config.py        # Pydantic settings
├── db.py            # SQLAlchemy database setup
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
└── routers/         # API route handlers
```

## Database
- PostgreSQL via Docker Compose
- SQLAlchemy 2.0 ORM
- Connection: postgresql://postgres:postgres@localhost:5432/hackathon

## API Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Adding Features
1. Create model in app/models/
2. Create schemas in app/schemas/
3. Create router in app/routers/
4. Register router in app/main.py

## Services Pattern
For complex business logic, create services in `app/services/`:
```
app/services/
├── __init__.py
├── ai_service.py      # External AI integrations
└── hint_generator.py  # Business logic
```

## Learnings & Gotchas

### Ollama Integration
- Use `httpx.AsyncClient` for async AI calls
- Always force JSON output: "RESPOND WITH JSON ONLY. NO OTHER TEXT."
- Extract JSON with `response.find('{')` and `response.rfind('}')`
- Set reasonable timeouts (25s for AI generation)

### Background Tasks
- Use FastAPI `BackgroundTasks` for non-blocking hint generation
- Database sessions in background tasks need careful handling
- Rate limiting should happen before AI calls to save resources

### Enums in Models
- SQLAlchemy enums must match exactly (case-sensitive)
- Create category mappings when AI returns different values:
```python
category_map = {
    'debugging': 'workflow_tip',
    'coding': 'app_suggestion',
}
```

### Activity Tracking
- Always include `app_switch_count` in struggle_data for distraction detection
- Window titles from clients may be empty - handle gracefully
- Recent windows list helps with context even when current title is empty
