import os
from pathlib import Path

import pandas as pd

from amlro_gui.services import experiment_service


def get_full_dataset(workspace_root: Path, experiment_id: str) -> dict:
    """The full accumulated reaction dataset recorded so far — training rows
    then every submitted prediction batch, in the order AMLRO wrote them.

    Read back from the decoded reaction-data file (the same one
    training_service reads completed rows from) rather than tracked
    separately, so it can never drift from what AMLRO actually wrote to disk.
    """
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)
    config = state.config

    if config is None:
        return {"feature_names": [], "objective_names": [], "columns": [], "rows": []}

    feature_names = config.continuous.feature_names + config.categorical.feature_names
    objective_names = config.objectives

    name, extension = os.path.splitext(config.file_name)
    decoded_path = exp_dir / f"{name}_decoded{extension}"

    rows: list[list] = []
    if decoded_path.exists():
        df = pd.read_csv(decoded_path)
        if not df.empty:
            rows = df[feature_names + objective_names].values.tolist()

    return {
        "feature_names": feature_names,
        "objective_names": objective_names,
        "columns": feature_names + objective_names,
        "rows": rows,
    }
