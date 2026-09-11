import json
import os
from pathlib import Path

import pandas as pd
from amlro.generate_reaction_conditions import get_reaction_scope
from amlro.optimizer import categorical_feature_decoding, categorical_feature_encoding

from amlro_gui.schemas.config import ExperimentConfig
from amlro_gui.schemas.experiment import ExperimentState
from amlro_gui.services import experiment_service


def _validate_existing_data_matches_config(
    exp_dir: Path, config: ExperimentConfig
) -> None:
    """For "old" mode (existing data), the uploaded file's columns must
    match the configured features/objectives, in the same order.

    Order matters, not just presence: AMLRO's own pandas calls
    (train[objectives], train.drop(objectives)) select by column name and
    would still separate features from objectives correctly even if the
    file's column order didn't match — but the resulting feature-column
    order would still reflect the file's original order, not necessarily
    matching full_combo.csv's generation order (continuous names, then
    categorical names). Since the sklearn models underneath fit/predict
    positionally rather than by column name, a silent order mismatch there
    would misalign which numbers mean which feature, with no error raised.
    """
    data_path = exp_dir / config.file_name
    if not data_path.exists():
        raise ValueError(
            f"No uploaded data found at '{config.file_name}'. Upload your "
            "existing reaction data before generating the reaction space."
        )

    expected_columns = (
        config.continuous.feature_names
        + config.categorical.feature_names
        + config.objectives
    )
    actual_columns = pd.read_csv(data_path, nrows=0).columns.tolist()

    if actual_columns != expected_columns:
        raise ValueError(
            "Uploaded data columns don't match this configuration. "
            f"Expected (in order): {expected_columns}. "
            f"Found: {actual_columns}. Fix the feature/objective names "
            "above, or re-upload a file with matching column headers in "
            "that exact order."
        )


def _is_valid_encoded_index(value: str, category_count: int) -> bool:
    try:
        index = int(float(value))
    except ValueError:
        return False
    return 0 <= index < category_count


def _detect_categorical_mode(df: pd.DataFrame, config: ExperimentConfig) -> str:
    """Classifies each categorical column as holding either the real
    category names ("decoded") or their numeric index into
    config.categorical.values ("encoded"), then requires every categorical
    column to agree — a file can't have one column with real names and
    another with numeric codes.

    Returns "decoded" if there are no categorical features at all (nothing
    to classify, nothing to transform).
    """
    column_modes: dict[str, str] = {}

    for feature_name, allowed_values in zip(
        config.categorical.feature_names, config.categorical.values, strict=True
    ):
        allowed = {str(value) for value in allowed_values}
        actual_values = set(df[feature_name].astype(str))

        if actual_values <= allowed:
            column_modes[feature_name] = "decoded"
            continue

        if all(
            _is_valid_encoded_index(value, len(allowed_values))
            for value in actual_values
        ):
            column_modes[feature_name] = "encoded"
            continue

        raise ValueError(
            f"Column '{feature_name}' in the uploaded data has values that "
            "are neither recognized category names nor valid encoded "
            f"indices (0-{len(allowed_values) - 1}): {sorted(actual_values)}. "
            f"Configured values for '{feature_name}': {allowed_values}. Fix "
            "the uploaded data or the configured categories above."
        )

    modes = set(column_modes.values())
    if len(modes) > 1:
        breakdown = ", ".join(
            f"'{name}' looks {mode}" for name, mode in column_modes.items()
        )
        raise ValueError(
            "Uploaded data mixes encoded and decoded categorical columns "
            f"({breakdown}). All categorical columns must consistently be "
            "either real category names or encoded indices, not a mix."
        )

    return modes.pop() if modes else "decoded"


def _write_encoded_and_decoded_files(exp_dir: Path, config: ExperimentConfig) -> None:
    """Ensures both the encoded (numeric categorical values, what AMLRO's
    own training/prediction code reads directly and feeds to sklearn) and
    decoded (real category names, for human reference) files exist,
    whichever direction the uploaded file was in.

    Uses AMLRO's own categorical_feature_encoding/categorical_feature_decoding
    so these files can never disagree with AMLRO about what "encoded" means.
    """
    data_path = exp_dir / config.file_name
    name, extension = os.path.splitext(config.file_name)
    decoded_path = exp_dir / f"{name}_decoded{extension}"

    df = pd.read_csv(data_path)

    if not config.categorical.feature_names:
        df.to_csv(decoded_path, index=False)
        return

    mode = _detect_categorical_mode(df, config)
    config_dict = config.to_amlro_dict()
    feature_columns = config.continuous.feature_names + config.categorical.feature_names
    objective_columns = config.objectives

    if mode == "decoded":
        df.to_csv(decoded_path, index=False)
        transform, target_path = categorical_feature_encoding, data_path
    else:
        transform, target_path = categorical_feature_decoding, decoded_path

    transformed_rows = [
        list(transform(config_dict, row[feature_columns].tolist()))
        + row[objective_columns].tolist()
        for _, row in df.iterrows()
    ]
    pd.DataFrame(transformed_rows, columns=feature_columns + objective_columns).to_csv(
        target_path, index=False
    )


def create_reaction_scope(
    workspace_root: Path, experiment_id: str, config: ExperimentConfig
) -> ExperimentState:
    state = experiment_service.load_state(workspace_root, experiment_id)
    exp_dir = experiment_service.experiment_dir_for(workspace_root, experiment_id)

    if state.mode == "old":
        _validate_existing_data_matches_config(exp_dir, config)
        _write_encoded_and_decoded_files(exp_dir, config)

    config_dict = config.to_amlro_dict()

    (exp_dir / "config.json").write_text(json.dumps(config_dict, indent=2))

    get_reaction_scope(
        config=config_dict,
        sampling=config.sampling,
        write_files=True,
        exp_dir=str(exp_dir),
    )

    state.config = config
    state.batch_size = config.batch_size
    state.progress.reaction_scope = True
    experiment_service.save_state(workspace_root, state)

    return state
