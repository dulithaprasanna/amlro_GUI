# Contributing

## Setup

Follow [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) for backend and
frontend setup.

**Known issue:** `backend/pyproject.toml` depends on AMLRO's `main` branch,
unpinned. `main` is temporarily ahead of what this backend is built against,
until the `mo_update` branch merges upstream. If a fresh
`pip install -e ".[dev]"` gives you errors like `"Cannot sample N out of
arrays with dim M when replace is False"` when generating a reaction scope,
reinstall AMLRO from `mo_update` instead:

```
pip install --force-reinstall "git+https://github.com/RxnRover/amlro.git@mo_update"
```

## Before opening a pull request

```
cd backend
pytest
ruff check src tests
```

```
cd frontend
npm run lint
npm run build
```

All four must pass. CI (`.github/workflows/ci.yml`) runs the same checks on
every push and pull request against `main`.

## Where things live

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): code layout and the
  request-flow pattern (route, schema, service, AMLRO, `state.json`). New
  backend/frontend resources should follow it rather than improvise a new
  shape.
- Backend tests live in `backend/tests/`, one file per resource, using the
  Flask test client against a `tmp_path` workspace.
- There's no frontend test suite yet; `tsc` (via `npm run build`) and
  `oxlint` are the current safety net.

## Style

- Backend: `ruff` (see `backend/pyproject.toml` for enabled rules).
- Frontend: `oxlint` and `prettier` (`npm run format`).
- Comments explain *why*, not *what* — skip comments that just restate what
  well-named code already shows.
