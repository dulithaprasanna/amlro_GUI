# amlro_gui

The graphical interface for [AMLRO](https://github.com/RxnRover/amlro) (Active
Machine Learning Reaction Optimizer) — lets a bench chemist run a full
active-learning reaction-optimization campaign (define a reaction scope,
collect initial training data, then iteratively predict and record new
conditions) without writing Python.

This is a ground-up rewrite of the original AMLRO GUI (kept at
`amlro_interface` for reference), moving from Flask-session state and
server-rendered templates to a file-backed experiment store behind a JSON
API, with a React/TypeScript frontend.

Architecture: Flask JSON API (`backend/`) + React/TypeScript SPA (`frontend/`),
served as one origin in production. See `docs/MIGRATION_NOTES.md` for the
full old-route → new-endpoint mapping and behavioral differences from
`amlro_interface`.

## Backend

```
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m flask --app amlro_gui.app run --debug
.venv\Scripts\python -m pytest
```

Runs on `http://127.0.0.1:5000`.

## Frontend

```
cd frontend
npm install
npm run dev
```

Runs on `http://127.0.0.1:5173` and proxies `/api/*` to the backend on port
5000 (see `vite.config.ts`) — run both at once during development.

- `npm run lint` — oxlint
- `npm run format` — Prettier
- `npm run build` — type-checks (`tsc -b`) then builds to `dist/`
