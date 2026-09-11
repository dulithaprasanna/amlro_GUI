import json
from pathlib import Path

import pandas as pd
from amlro.optimizer import get_optimized_parameters

from amlro_gui.schemas.config import ExperimentConfig
from amlro_gui.schemas.experiment import ExperimentState
from amlro_gui.services import experiment_service

NEXT_BATCH_FILENAME = "next_batch.csv"


def _validate_parameters_in_scope(config: ExperimentConfig, parameters: list) -> None:
    """Rows a user typed in by hand (added/edited in the prediction batch
    table, rather than left as AMLRO's own suggestion) aren't constrained by
    a UI widget the way the reaction-scope upload is — so check them here
    against the same reaction scope AMLRO was configured with, rather than
    silently accepting values AMLRO was never asked to consider.
    """
    continuous_names = config.continuous.feature_names
    bounds = config.continuous.bounds
    categorical_names = config.categorical.feature_names
    categorical_values = config.categorical.values
    n_continuous = len(continuous_names)

    for row_index, row in enumerate(parameters):
        for i, name in enumerate(continuous_names):
            value = float(row[i])
            low, high = bounds[i]
            if not (low <= value <= high):
                raise ValueError(
                    f"Row {row_index + 1}: '{name}' = {row[i]} is outside "
                    f"the configured bounds [{low}, {high}]."
                )
        for i, name in enumerate(categorical_names):
            value = row[n_continuous + i]
            allowed = categorical_values[i]
            if str(value) not in allowed:
                raise ValueError(
                    f"Row {row_index + 1}: '{name}' = '{value}' is not one "
                    f"of the configured categories {allowed}."
                )


def _write_next_batch_csv(exp_dir: Path, config_dict: dict, parameters: list) -> None:
    feature_names = (
        config_dict["continuous"]["feature_names"]
        + config_dict["categorical"]["feature_names"]
    )
    pd.DataFrame(parameters, columns=feature_names).to_csv(
        exp_dir / NEXT_BATCH_FILENAME, index=False
    )


def _apply_batch_size(exp_dir: Path, state: ExperimentState, batch_size: int) -> None:
    """Updates batch size everywhere it's recorded: the in-memory state used
    for the next AMLRO call, and config.json on disk (kept in sync purely
    for the user's own reference — AMLRO itself is always called with the
    batch_size passed explicitly, not read back out of the config dict)."""
    state.batch_size = batch_size
    state.config.batch_size = batch_size
    (exp_dir / "config.json").write_text(
        json.dumps(state.config.to_amlro_dict(), indent=2)
    )


def update_batch_size(
    workspace_root: Path, experiment_id: str, batch_size: int
) -> ExperimentState:
    """Persists a batch size change immediately, independent of submitting a
    batch's results — mirrors the old app's separate "Update Batch Size"
    action. Without this, changing the batch size in the UI but not
    submitting yet (e.g. before navigating away) would be silently lost:
    the server would still hand back a batch sized to the old value on
    resume, since nothing had actually told it to change.
    """
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)
    _apply_batch_size(exp_dir, state, batch_size)
    experiment_service.save_state(workspace_root, state)
    return state


def resume_optimization(
    workspace_root: Path, experiment_id: str
) -> ExperimentState:
    """Reopens a stopped/completed experiment for further optimization.

    Nothing about the recorded data changes — the next call to
    get_current_batch will simply retrain on whatever's already in the
    reaction-data file (including everything recorded before stopping) and
    predict the next batch from there, exactly like resuming mid-cycle.
    """
    state = experiment_service.load_state(workspace_root, experiment_id)
    state.progress.optimization = False
    experiment_service.save_state(workspace_root, state)
    return state


def get_current_batch(workspace_root: Path, experiment_id: str) -> dict:
    """The batch AMLRO currently recommends trying, without submitting or
    writing anything new.

    Retrains on whatever is already in the reaction-data file and predicts
    from there — safe to call any number of times (e.g. after reloading the
    page mid-cycle) since AMLRO's models use a fixed random seed and are
    reproducible for a given training set. Submitting results is a separate
    call (submit_batch) that's the only place allowed to write new rows.
    """
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)
    config_dict = state.config.to_amlro_dict()

    parameters = get_optimized_parameters(
        exp_dir=str(exp_dir),
        config=config_dict,
        parameters_list=[],
        objectives_list=[],
        model=state.config.regresor_model,
        batch_size=state.batch_size,
    )
    _write_next_batch_csv(exp_dir, config_dict, parameters)

    return {
        "parameters": parameters,
        "current_iteration": state.prediction_progress.current_iteration,
        "batch_size": state.batch_size,
    }


def submit_batch(
    workspace_root: Path,
    experiment_id: str,
    parameters: list,
    objectives: list,
    stop: bool = False,
    batch_size: int | None = None,
) -> dict:
    """Records a completed batch's results, then either finalizes the
    experiment (stop=True) or returns the next batch to try."""
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)
    prediction_progress = state.prediction_progress

    if parameters:
        _validate_parameters_in_scope(state.config, parameters)

    prediction_progress.parameters = parameters
    prediction_progress.objectives = objectives
    prediction_progress.current_iteration += 1

    if batch_size is not None:
        _apply_batch_size(exp_dir, state, batch_size)

    config_dict = state.config.to_amlro_dict()

    if stop:
        get_optimized_parameters(
            exp_dir=str(exp_dir),
            config=config_dict,
            parameters_list=parameters,
            objectives_list=objectives,
            model=state.config.regresor_model,
            termination=True,
        )
        state.progress.optimization = True
        experiment_service.save_state(workspace_root, state)
        return {"complete": True}

    next_parameters = get_optimized_parameters(
        exp_dir=str(exp_dir),
        config=config_dict,
        parameters_list=parameters,
        objectives_list=objectives,
        model=state.config.regresor_model,
        batch_size=state.batch_size,
    )
    _write_next_batch_csv(exp_dir, config_dict, next_parameters)
    experiment_service.save_state(workspace_root, state)

    return {
        "complete": False,
        "parameters": next_parameters,
        "current_iteration": prediction_progress.current_iteration,
        "batch_size": state.batch_size,
    }
