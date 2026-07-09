# chaincheck-backend

The ChainCheck API service. Sierra chain controls, closures, and incidents
(via the shared `ca_roads` feed layer), NWS pass forecasts, Open-Meteo snow
accumulation, and the tier-change watcher, behind one client-agnostic JSON
API.

Run locally:

```
uv venv .venv
uv pip install -e ".[dev]"
uv run uvicorn chaincheck.api.app:app --reload
```

Tests and lint:

```
uv run pytest -q
uv run ruff check .
```
