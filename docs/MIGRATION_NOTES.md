# Migration notes: `amlro_interface` (original) → `amlro_gui` (this rewrite)

Living table mapping the old Flask routes to their new API/frontend
equivalents. Filled in as each phase lands — see the refactor plan for phase
definitions.

| Old route (`amlro_gui/app.py`) | New backend endpoint | New frontend step | Phase | Status |
|---|---|---|---|---|
| `GET /` (`main.html`) | — | Mode-select step (landing page create form) | 3 | **Done** |
| `GET /set_mode/<mode>` | `POST /api/experiments` | Mode-select step | 1, 2, 4 | **Done** |
| `GET /amlro_dashboard` | `GET /api/experiments/<id>` | App shell + Stepper | 1, 2, 3 | **Done** |
| `GET/POST /upload_old_data` | `POST /api/experiments/<id>/data` | Data upload + preview step | 2, 4 | **Done** |
| `POST /verify_data` | *(folded into the above)* | Data upload + preview step | 2, 4 | **Done** |
| `GET/POST /reaction_scope` | `POST /api/experiments/<id>/reaction-scope` | Reaction scope config step | 2, 4 | **Done** |
| `GET /config_result` | *(dropped — response returned inline)* | — | 2 | **Done** |
| `GET /start_training`, `GET/POST /training` | `GET /api/experiments/<id>/training` (full plan table) + `POST /api/experiments/<id>/training/next` (advance one iteration) | Training loop step | 2, 4 | **Done** |
| `POST /update_batch_size` | folded into training/prediction request body | Training/prediction step | 2, 4 | **Done** |
| `GET /start_prediction`, `GET/POST /prediction` | `GET /api/experiments/<id>/prediction` (current batch, side-effect-free) + `POST /api/experiments/<id>/prediction/next` (submit results) | Prediction loop step | 2, 4 | **Done** |
| *(new — no old equivalent)* | `GET /api/experiments/<id>/analysis` | Data analysis dashboard | 5 | Not started |
| *(new — no old equivalent)* | `GET /api/experiments/<id>/sensitivity` | Feature sensitivity (SHAP) dashboard | 6 | Blocked on AMLRO-side `get_feature_sensitivity` (see `AMLRO_SENSITIVITY_CONTRACT.md`, to be written in Phase 6) |
| *(new — no old equivalent)* | `GET /api/experiments` | Landing page (resume experiment) | 1, 3 | **Done** |

All rows above are now backed by both a working API endpoint *and* a
frontend screen that calls it (Phase 4 wizard steps: mode-select on the
landing page, reaction scope config, training loop, prediction loop,
completed screen) — feature parity with the old app's core flow is reached.
Not yet built: the two new dashboards (Phases 5-6) and packaging (Phase 8).

## Behavioral changes from the old app (intentional)

- All experiment progress/config moves from the Flask session cookie to a
  file-backed `state.json` in the experiment directory (Phase 1) — surviving
  browser/cookie resets and CSVs of any size.
- Two-step upload/verify (`upload_old_data` → `verify_data`) becomes one
  upload-with-preview call.
- GET/POST-overloaded routes (`/training`, `/prediction`) become one explicit
  "get next batch" action each.
- New: `GET /api/experiments/<id>/training` returns the *entire* training
  plan up front (every condition to be run, via AMLRO's own
  `load_training_conditions`), with objective columns filled in for whichever
  rows are already completed (read back from AMLRO's decoded reaction-data
  file — no separate tracking to drift out of sync). Lets the frontend show
  a persistent table instead of one popup with no sense of overall progress.
- New: every prediction cycle writes the suggested batch to
  `next_batch.csv` in the experiment directory (replaced each cycle), so the
  next reactions to run are readable/printable outside the browser too.
- New: an experiment's data no longer has to live under one fixed
  server-managed folder — creating an experiment accepts an optional
  `exp_dir` (any absolute path the user chooses), matching the old app's
  free-form `exp_dir`/`New Experiment Directory` fields, but resolved through
  a small `registry.json` (id → exp_dir) in the workspace root so listing and
  resuming experiments still works regardless of where each one's files live.
  A folder already containing a `state.json` is refused rather than silently
  adopted/overwritten.
- Fixed: the old app (and this app's first pass) always trained with the
  default "gb" regressor, silently ignoring the model the user picked in the
  reaction-scope config. `regresor_model` is now actually passed through to
  `get_optimized_parameters`.
- Fixed: `/prediction/next` originally doubled as both "give me the current
  batch" (empty body) and "submit these results" (with a body) — reusing the
  *last submitted* batch's parameters/objectives whenever an empty body call
  landed after the first cycle. Reloading mid-cycle would silently
  re-submit (and duplicate in `reactions_data.csv`) the previous cycle's row.
  Split into `GET /prediction` (always side-effect-free — retrains on
  whatever's already recorded and returns the batch, reproducible since
  AMLRO's models are seeded) and `POST /prediction/next` (always requires
  `parameters`/`objectives`, only ever appends once, on explicit submission).
- Changing batch size mid-prediction now also updates `state.config` and
  rewrites `config.json`, instead of only the in-memory batch size used for
  that one call.
- New: `POST /api/experiments/<id>/prediction/batch-size` persists a batch
  size change immediately (mirrors the old app's separate "Update Batch
  Size" button) — previously batch size was only bundled into a full
  submit, so changing it without submitting and navigating away silently
  lost the change; resuming would retrain at the *old* size.
- New (old/existing-data mode): uploaded categorical data may be either the
  real category names (e.g. "A"/"THF") or their already-encoded 0/1/2...
  index — auto-detected per column at reaction-scope submission. Whichever
  direction it's in, both `config.file_name` (encoded, what AMLRO's own
  training/prediction code reads straight into sklearn) and
  `{name}_decoded{ext}` (human-readable) end up correct, via AMLRO's own
  `categorical_feature_encoding`/`categorical_feature_decoding` — never
  guessed at independently of AMLRO's own logic. The old app never did this
  conversion at all — an existing-data experiment with categorical features
  would have silently fed strings to the regressor. Submission is blocked
  (with a clear error) if: no data was uploaded, uploaded columns don't
  match the configured feature/objective names and order, a categorical
  column mixes encoded and decoded-looking values across different
  features in the same file, or a value doesn't fit either interpretation.
- Fixed: the "old" mode upload card had its own independent "save as" field,
  completely disconnected from the reaction-scope form's "File name" field
  — the two could silently drift apart, so the uploaded file wouldn't be
  found under the name the backend actually checked at submission. The
  upload now always uses the form's `file_name` value directly.
- New: the landing page's "Resume an experiment" list is now paginated
  (5 or 10 per page, toggle in the card header) and sorted by most
  recently worked-on first (`updated_at`, bumped on every `state.json`
  save) rather than creation order — the old app had no listing at all.
  Each entry has a "Remove" (×) button that unregisters it from the list
  (`DELETE /api/experiments/<id>`) without touching its files by default;
  an explicit, separately-confirmed checkbox in the removal dialog is
  required to also delete the experiment's folder from disk, since that's
  irreversible. A "Find experiments already on disk" scan
  (`POST /api/experiments/scan`) looks one level into a given folder for
  experiment subfolders (containing `state.json`) not already registered
  and adds them — for experiments copied in from elsewhere or left behind
  after an unregister.
- New: reaction conditions a user hand-adds or edits in the prediction
  batch table (as opposed to AMLRO's own suggestions, which aren't
  editable) are validated against the configured reaction scope — continuous
  values must fall within their configured bounds, categorical values must
  be one of the configured categories — both in the UI (immediate feedback,
  `Select` limited to configured categories, `NumberInput` bounded) and
  again on the backend at submission (`POST /prediction/next`), since the
  backend is the actual source of truth and can be called directly. The old
  app never validated hand-entered training/prediction values against the
  configured scope at all.
