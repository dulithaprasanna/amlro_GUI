import os
from pathlib import Path

import pandas as pd
from amlro.const import TRAINING_COMBO_FILENAME
from amlro.generate_training_data import (
    generate_training_data,
    load_training_conditions,
)

from amlro_gui.services import experiment_service


def get_training_table(workspace_root: Path, experiment_id: str) -> dict:
    """Full training plan (every condition to be run) with objective values
    filled in for whichever rows have already been completed.

    Completed rows are read back from the decoded reaction-data file AMLRO
    already maintains, rather than tracked separately here, so this can
    never drift from what AMLRO actually wrote to disk.
    """
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)
    config = state.config

    conditions = load_training_conditions(str(exp_dir / TRAINING_COMBO_FILENAME))

    objective_names = config.objectives
    name, extension = os.path.splitext(config.file_name)
    decoded_path = exp_dir / f"{name}_decoded{extension}"

    completed_objectives: list[list] = []
    if decoded_path.exists():
        decoded_df = pd.read_csv(decoded_path)
        if not decoded_df.empty:
            completed_objectives = decoded_df[objective_names].values.tolist()

    rows = []
    for i, condition in enumerate(conditions):
        completed = i < len(completed_objectives)
        rows.append(
            {
                "iteration": i,
                "parameters": condition,
                "objectives": completed_objectives[i] if completed else None,
                "status": "completed" if completed else "pending",
            }
        )

    return {
        "feature_names": (
            config.continuous.feature_names + config.categorical.feature_names
        ),
        "objective_names": objective_names,
        "training_size": len(conditions),
        "current_iteration": state.training_progress.current_iteration,
        "rows": rows,
    }


def next_training_batch(
    workspace_root: Path,
    experiment_id: str,
    obj_values: list | None = None,
) -> dict:
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)
    config_dict = state.config.to_amlro_dict()
    training_progress = state.training_progress

    training_size = len(pd.read_csv(exp_dir / TRAINING_COMBO_FILENAME))

    if obj_values:
        training_progress.objectives = obj_values
        training_progress.current_iteration += 1

        if training_progress.current_iteration == training_size:
            generate_training_data(
                exp_dir=str(exp_dir),
                config=config_dict,
                parameters=training_progress.parameters,
                obj_values=training_progress.objectives,
                termination=True,
            )
            state.progress.training_set = True
            experiment_service.save_state(workspace_root, state)
            return {"complete": True}

    parameters = generate_training_data(
        exp_dir=str(exp_dir),
        config=config_dict,
        parameters=training_progress.parameters,
        obj_values=training_progress.objectives,
    )
    training_progress.parameters = parameters
    experiment_service.save_state(workspace_root, state)

    return {
        "complete": False,
        "parameters": parameters,
        "current_iteration": training_progress.current_iteration,
        "training_size": training_size,
    }
