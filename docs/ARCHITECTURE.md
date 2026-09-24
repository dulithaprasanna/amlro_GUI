# Architecture

How this codebase is organized and how a request flows through it. For *why*
specific behaviors work the way they do, see `DESIGN_NOTES.md` on the
`design-notes` branch. For how to use the app itself, see the tutorial/user
guide.

## The shape of it

Two independent halves in one repo, talking over HTTP:

```
amlro_gui/
├── backend/    Flask JSON API — owns all state and every AMLRO call
└── frontend/   React/TypeScript SPA — the wizard UI, talks only to the API
```

Nothing in `frontend/` imports Python, and nothing in `backend/` renders
HTML — the boundary is strictly a JSON API, proxied together in dev
(`vite.config.ts`) and served from one Flask origin in production.

## Backend (`backend/src/amlro_gui/`)

```
api/         Flask blueprints — one file per resource (experiments, reaction_scope,
             training, prediction, data, dataset). Routes are thin: parse the
             request, call a service, jsonify the result.
schemas/     Pydantic models — the request/response contract. config.py mirrors
             AMLRO's own config shape (continuous/categorical features, objectives,
             sampling); experiment.py is the file-backed state shape.
services/    One file per resource, same split as api/. All the actual logic
             lives here: validation beyond what Pydantic covers, calls into the
             amlro package, reading/writing each experiment's files.
app.py       create_app() — wires blueprints + error handlers together.
errors.py    Central exception → JSON error-response mapping.
config.py    Runtime config (WORKSPACE_ROOT and friends).
```

**A typical request** (e.g. `POST /api/experiments/<id>/reaction-scope`):

1. **`api/reaction_scope.py`** — the route function. Parses the JSON body
   into a `schemas.config.ExperimentConfig` (Pydantic validates shape,
   bounds, and cross-field constraints here; a bad request never reaches the
   service layer).
2. **`services/reaction_scope_service.py`** — `create_reaction_scope()`.
   Loads the experiment's current `ExperimentState`, does any
   validation that needs the filesystem (e.g. checking uploaded data against
   the configured features), calls into `amlro.generate_reaction_conditions`,
   and writes the results back to the experiment's directory.
3. **State**: every experiment is one directory containing a `state.json`
   (`schemas.experiment.ExperimentState` — progress flags, config, training/
   prediction progress) plus whatever CSVs AMLRO itself writes there
   (`config.json`, `reactions_data*.csv`, `training_combo.csv`, ...).
   `services/experiment_service.py` is the only place that reads/writes
   `state.json`; every other service goes through it (`load_state`/
   `save_state`) rather than touching the file directly.
4. Any raised exception (a custom one in `exceptions.py`, a Pydantic
   `ValidationError`, or a bare `ValueError`) is caught centrally in
   `errors.py` and turned into `{"error": "<human-readable message>"}` —
   routes and services never format error responses themselves.

This same route → schema → service → `state.json` shape repeats for every
resource; reading one blueprint/service pair (e.g. `training.py` +
`training_service.py`) tells you the pattern for all of them.

## Frontend (`frontend/src/`)

```
api/         One file per backend resource, mirroring backend/src/amlro_gui/api/.
             Each exports a typed fetch wrapper + TanStack Query hooks
             (useXxx for reads, useXxxMutation-style for writes). types.ts holds
             the TypeScript shapes matching the backend's Pydantic schemas.
pages/       LandingPage.tsx (create/resume/manage experiments) and
             ExperimentPage.tsx (the app shell + stepper for one experiment).
pages/steps/ One component per wizard step (ReactionScopeStep, TrainingStep,
             PredictionStep, CompletedStep) — ExperimentPage renders whichever
             step matches the experiment's current progress.
components/  Shared pieces used by more than one page (e.g.
             ObjectiveTrajectoryChart.tsx).
```

**Data flow**: a step component calls a hook from `api/` (e.g.
`usePredictionNext`), which POSTs/GETs through `api/client.ts` (the one place
that knows about error-response shape and base fetch config) and is cached/
invalidated by TanStack Query — no component reaches for `fetch` directly,
and no component holds server state in local `useState` beyond what it's
actively editing before submit.

## Adding a new resource

Follow the existing pattern rather than improvising a new one:

1. Backend: a Pydantic schema (if it needs one beyond primitives) → a
   `services/<name>_service.py` function → a thin route in
   `api/<name>.py` → register the blueprint in `api/__init__.py`.
2. Frontend: add the type to `api/types.ts` → a fetch function + hook in
   `api/<name>.ts` → use the hook from whichever page/step needs it.
3. Backend tests live in `backend/tests/`, one file per resource, using the
   Flask test client against a `tmp_path` workspace (see `conftest.py`).
