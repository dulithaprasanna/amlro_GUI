# amlro_gui

A web interface for [AMLRO](https://github.com/RxnRover/amlro) (Active Machine
Learning Reaction Optimizer) that lets a bench chemist run a full
active-learning reaction-optimization campaign — define a reaction scope,
collect initial training data, then iteratively review AI-suggested reaction
conditions, record results, and let the model retrain each cycle — without
writing any Python.

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Related projects](#related-projects)
- [Citation](#citation)
- [License](#license)

## Overview

A reaction-optimization campaign has three phases, each with its own screen:

1. **Reaction scope** — define continuous features (bounds, resolution) and
   categorical features (allowed values) and objectives (with min/max
   direction), or upload an existing dataset instead of starting fresh.
2. **Training** — run the initial sampling plan AMLRO generates, recording an
   objective value for each condition.
3. **Prediction** — each cycle, AMLRO trains a regression model on the data
   collected so far and suggests the next batch of conditions to try; record
   results and repeat until the campaign is stopped.

Every experiment's state is file-backed (not stored in a session cookie), so
closing the browser or restarting the app never loses progress, and past
experiments can be resumed, listed, or removed from a landing page.

## Architecture

- **Backend** (`backend/`) — Flask, as a pure JSON API (no server-rendered
  templates) behind a thin routing layer, a Pydantic-validated schema layer,
  and a service layer that calls into AMLRO. State for each experiment is a
  `state.json` file in that experiment's own directory.
- **Frontend** (`frontend/`) — React + TypeScript, built with Vite, using
  Mantine for UI components, TanStack Query for API state, and Nivo for
  charts.
- Served as one origin in production (the built frontend as static files
  behind the Flask app).

## Getting started

### Backend

```
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m flask --app amlro_gui.app run --debug
.venv\Scripts\python -m pytest
```

Runs on `http://127.0.0.1:5000`.

### Frontend

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

## Related projects

- **[AMLRO](https://github.com/RxnRover/amlro)** — the active-learning
  reaction-optimization engine this GUI wraps. An open-source framework that
  accelerates chemical reaction optimization using active learning with
  classical machine learning regression models, combining space-filling
  sampling strategies (Sobol, Latin Hypercube) with iterative model training,
  prediction, and experiment selection — supporting multiple regression
  models, multi-objective definitions, and user-defined parameter bounds for
  data-efficient optimization from small initial datasets. This repo has no
  optimization logic of its own; every reaction-scope, training, and
  prediction computation is delegated to AMLRO.

## Citation

If you use AMLRO (the optimization engine this GUI wraps) in your work,
please cite:

> Kulathunga, D. P. et al. *RxnRover/amlro*. Computer Software. USDOE Office
> of Energy Efficiency and Renewable Energy (EERE), Advanced Materials &
> Manufacturing Technologies Office (AMMTO), 2026.
> DOI: [10.11578/dc.20260205.1](https://doi.org/10.11578/dc.20260205.1)

```bibtex
@misc{doecode_174798,
  title        = {RxnRover/amlro},
  author       = {Kulathunga, Dulitha Prasanna and Crandall, Zachery},
  doi          = {10.11578/dc.20260205.1},
  url          = {https://doi.org/10.11578/dc.20260205.1},
  howpublished = {[Computer Software] \url{https://doi.org/10.11578/dc.20260205.1}},
  year         = {2026},
  month        = {feb}
}
```

## License

_Not yet set for this repo — see the note below._
