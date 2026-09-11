from pathlib import Path

import pandas as pd
from werkzeug.datastructures import FileStorage

from amlro_gui.services import experiment_service


def upload_reaction_data(
    workspace_root: Path,
    experiment_id: str,
    file: FileStorage,
    file_name: str,
    preview_rows: int = 10,
) -> dict:
    """Read an uploaded reaction-data CSV, save it into the experiment
    directory, and return a preview for the frontend to display.

    Writing the file directly from the parsed DataFrame (rather than
    round-tripping through a session dict, as the old app did) preserves
    column order for free and needs no separate "verify" step.
    """
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)

    df = pd.read_csv(file)
    df.to_csv(exp_dir / file_name, index=False)

    state.mode = "old"
    state.progress.reaction_scope = False
    state.progress.training_set = False
    state.progress.optimization = False
    experiment_service.save_state(workspace_root, state)

    return {
        "columns": df.columns.tolist(),
        "row_count": len(df),
        "preview": df.head(preview_rows).to_dict(orient="records"),
    }
