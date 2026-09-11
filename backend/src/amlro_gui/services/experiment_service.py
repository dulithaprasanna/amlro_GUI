import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from amlro_gui.exceptions import (
    ExperimentAlreadyExistsError,
    ExperimentNotFoundError,
    InvalidExperimentIdError,
)
from amlro_gui.schemas.experiment import (
    ExperimentMode,
    ExperimentState,
    ExperimentSummary,
)

STATE_FILENAME = "state.json"
REGISTRY_FILENAME = "registry.json"

# The id is used in URLs and (for auto-assigned experiment folders) as a
# directory name, so it only allows a safe charset — this alone rules out
# path separators and ".." traversal for the id itself. The exp_dir an
# experiment actually stores its files in may be any path the user chooses
# (see create_experiment) since this is a single-user local app operating on
# the user's own filesystem, not a shared/multi-tenant server.
_VALID_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_id(experiment_id: str) -> None:
    if not _VALID_ID.match(experiment_id):
        raise InvalidExperimentIdError(
            f"Experiment id '{experiment_id}' may only contain letters, "
            "digits, '-', and '_'."
        )


def _load_registry(workspace_root: Path) -> dict[str, str]:
    registry_path = workspace_root / REGISTRY_FILENAME
    if not registry_path.exists():
        return {}
    return json.loads(registry_path.read_text())


def _save_registry(workspace_root: Path, registry: dict[str, str]) -> None:
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / REGISTRY_FILENAME).write_text(json.dumps(registry, indent=2))


def experiment_dir_for(workspace_root: Path, experiment_id: str) -> Path:
    """Filesystem directory AMLRO should read/write its data files in."""
    _validate_id(experiment_id)
    registry = _load_registry(workspace_root)
    if experiment_id not in registry:
        raise ExperimentNotFoundError(f"Experiment '{experiment_id}' not found.")
    return Path(registry[experiment_id])


def create_experiment(
    workspace_root: Path,
    mode: ExperimentMode,
    experiment_id: str | None = None,
    exp_dir: str | None = None,
) -> ExperimentState:
    if experiment_id is None:
        experiment_id = uuid.uuid4().hex[:8]
    _validate_id(experiment_id)

    registry = _load_registry(workspace_root)
    if experiment_id in registry:
        raise ExperimentAlreadyExistsError(
            f"Experiment '{experiment_id}' already exists."
        )

    experiment_dir = (
        Path(exp_dir).expanduser().resolve()
        if exp_dir
        else (workspace_root.resolve() / experiment_id)
    )

    if (experiment_dir / STATE_FILENAME).exists():
        raise ExperimentAlreadyExistsError(
            f"'{experiment_dir}' is already an AMLRO GUI experiment folder."
        )

    try:
        experiment_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise InvalidExperimentIdError(
            f"Could not create experiment folder '{experiment_dir}': {error}"
        ) from error

    state = ExperimentState(id=experiment_id, mode=mode, exp_dir=str(experiment_dir))
    (experiment_dir / STATE_FILENAME).write_text(state.model_dump_json(indent=2))

    registry[experiment_id] = str(experiment_dir)
    _save_registry(workspace_root, registry)

    return state


def load_state(workspace_root: Path, experiment_id: str) -> ExperimentState:
    experiment_dir = experiment_dir_for(workspace_root, experiment_id)
    state_path = experiment_dir / STATE_FILENAME

    if not state_path.exists():
        raise ExperimentNotFoundError(f"Experiment '{experiment_id}' not found.")

    return ExperimentState.model_validate_json(state_path.read_text())


def save_state(workspace_root: Path, state: ExperimentState) -> None:
    # workspace_root is unused here (state.exp_dir is authoritative) but kept
    # in the signature so callers don't need to special-case save vs. load.
    del workspace_root
    state.updated_at = datetime.now(timezone.utc)
    state_path = Path(state.exp_dir) / STATE_FILENAME
    state_path.write_text(state.model_dump_json(indent=2))


def list_experiments(workspace_root: Path) -> list[ExperimentSummary]:
    registry = _load_registry(workspace_root)

    summaries = []
    for exp_dir in registry.values():
        state_path = Path(exp_dir) / STATE_FILENAME
        if not state_path.exists():
            continue
        state = ExperimentState.model_validate_json(state_path.read_text())
        summaries.append(
            ExperimentSummary(
                id=state.id,
                mode=state.mode,
                created_at=state.created_at,
                updated_at=state.updated_at,
                progress=state.progress,
                exp_dir=state.exp_dir,
            )
        )
    # Most recently worked-on first — what a user resuming a campaign wants
    # to see at the top, not just whichever was created first.
    summaries.sort(key=lambda summary: summary.updated_at, reverse=True)
    return summaries


def remove_experiment(
    workspace_root: Path, experiment_id: str, delete_files: bool = False
) -> None:
    """Unregisters an experiment from the landing page (registry.json only,
    the default) and optionally also deletes its folder from disk.

    Unregistering alone is non-destructive and reversible via
    scan_for_experiments — the safer default for a "remove from list"
    action. Deleting files is a separate, explicit opt-in since it can't be
    undone.
    """
    registry = _load_registry(workspace_root)
    if experiment_id not in registry:
        raise ExperimentNotFoundError(f"Experiment '{experiment_id}' not found.")

    exp_dir = Path(registry[experiment_id])
    del registry[experiment_id]
    _save_registry(workspace_root, registry)

    if delete_files and (exp_dir / STATE_FILENAME).exists():
        shutil.rmtree(exp_dir)


def scan_for_experiments(workspace_root: Path, root_dir: str) -> dict:
    """Looks one level into root_dir's subfolders for experiment folders
    (containing state.json) not already in the registry, and registers any
    it finds — for experiments that exist on disk but aren't showing up on
    the landing page (e.g. copied in from elsewhere, or a fresh workspace).

    Only descends one level, not arbitrarily deep, to keep a scan of e.g. a
    whole drive from silently walking into unrelated folders.
    """
    root = Path(root_dir).expanduser()
    if not root.is_dir():
        raise InvalidExperimentIdError(f"'{root_dir}' is not a folder that exists.")

    registry = _load_registry(workspace_root)
    registered_dirs = {str(Path(p).resolve()) for p in registry.values()}

    added: list[ExperimentSummary] = []
    skipped: list[dict] = []

    candidates = [root, *(p for p in root.iterdir() if p.is_dir())]
    for candidate in candidates:
        state_path = candidate / STATE_FILENAME
        if not state_path.exists():
            continue

        resolved = str(candidate.resolve())
        if resolved in registered_dirs:
            continue

        try:
            state = ExperimentState.model_validate_json(state_path.read_text())
        except Exception:
            skipped.append(
                {"exp_dir": str(candidate), "reason": "Unreadable state.json"}
            )
            continue

        if state.id in registry:
            skipped.append(
                {
                    "exp_dir": str(candidate),
                    "reason": f"Id '{state.id}' is already used by a different "
                    "registered experiment.",
                }
            )
            continue

        registry[state.id] = str(candidate)
        registered_dirs.add(resolved)
        added.append(
            ExperimentSummary(
                id=state.id,
                mode=state.mode,
                created_at=state.created_at,
                updated_at=state.updated_at,
                progress=state.progress,
                exp_dir=state.exp_dir,
            )
        )

    if added:
        _save_registry(workspace_root, registry)

    return {"added": added, "skipped": skipped}
