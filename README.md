# MiniMate API

FastAPI backend for the MiniMate desktop companion.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL (via Docker)
- Ollama (for AI hint generation)

## Quick Start

```bash
# Start database (from workspace root)
docker compose up -d

# Install dependencies
uv sync

# Run development server
uv run fastapi dev

# Run tests
uv run pytest
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/
├── main.py          # FastAPI app entry point
├── config.py        # Pydantic settings
├── db.py            # SQLAlchemy database setup
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
├── routers/         # API route handlers
└── services/        # Business logic (AI, hint generation)
```

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/activities/report` | Report user activity batch |
| GET | `/hints/{device_id}/pending` | Get pending hints for device |
| PATCH | `/hints/{hint_id}/status` | Update hint status |
| GET | `/preferences/{device_id}` | Get user preferences |
| PATCH | `/preferences/{device_id}` | Update preferences |
| POST | `/events/reminder` | Send scheduled event reminder |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/hackathon` | Database connection |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Model for hint generation |

Copy `.env.example` to `.env` and adjust as needed.

## AI Hint Generation

The API uses Ollama to generate contextual hints based on user activity. Install Ollama and pull a model:

```bash
# Install Ollama (macOS)
brew install ollama

# Pull model
ollama pull llama3.2

# Start Ollama server
ollama serve
```

## Testing

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=app

# Specific test file
uv run pytest tests/test_activities.py
```
