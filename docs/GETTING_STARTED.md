# Getting started

Full setup and run instructions for developing or trying out `amlro_gui`
locally. For the short version, see the README's Quick install section.

## Prerequisites

- **Python 3.10+**
  - Windows: [python.org installer](https://www.python.org/downloads/) — on
    the first install screen, check **"Add python.exe to PATH."**
  - macOS: [python.org installer](https://www.python.org/downloads/macos/),
    or `brew install python` if you use [Homebrew](https://brew.sh/).
  - Linux: usually already installed; if not, use your package manager, e.g.
    `sudo apt install python3 python3-venv` (Debian/Ubuntu).
  - Verify: `python --version` (Windows) or `python3 --version` (macOS/Linux)
    in a terminal.
- **Node.js 18+** (any OS): [nodejs.org](https://nodejs.org/) — download the
  **LTS** version, default installer options are fine. Verify: `node --version`.

Two terminals — backend and frontend run at the same time.

## Backend

**Windows (PowerShell):**

```
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m flask --app amlro_gui.app run --debug
.venv\Scripts\python -m pytest
```

**macOS / Linux:**

```
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m flask --app amlro_gui.app run --debug
.venv/bin/python -m pytest
```

Runs on `http://127.0.0.1:5000`.

## Frontend

**Any OS:**

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
