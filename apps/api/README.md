# Vigil API (`apps/api`)

FastAPI REST services for the Vigil oncology surveillance platform.

## Architecture
Structured according to Clean Architecture / Hexagonal Architecture:
- `vigil_api/models/`: SQLAlchemy 2.0 relational persistence models.
- `vigil_api/schemas/`: Pydantic v2 validation contracts.
- `vigil_api/api/`: Endpoint routers and HTTP controllers.
- `vigil_api/ml/`: Inference engine interfaces and wrappers.

## Local Execution
```bash
uv run uvicorn vigil_api.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation: `http://localhost:8000/docs`.

## Testing
```bash
uv run pytest tests/
```
