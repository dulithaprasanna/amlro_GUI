from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from amlro_gui.schemas.config import ExperimentConfig

ExperimentMode = Literal["new", "old"]


class Progress(BaseModel):
    reaction_scope: bool = False
    training_set: bool = False
    optimization: bool = False


class TrainingProgress(BaseModel):
    """Training runs one reaction condition at a time, so parameters/
    objectives here are a single flat row, not a batch."""

    current_iteration: int = 0
    parameters: list[Any] = Field(default_factory=list)
    objectives: list[Any] = Field(default_factory=list)


class PredictionProgress(BaseModel):
    """Prediction works in batches (batch_size may be >1), so parameters/
    objectives here are each a list of rows."""

    current_iteration: int = 0
    parameters: list[list] = Field(default_factory=list)
    objectives: list[list] = Field(default_factory=list)


class ExperimentState(BaseModel):
    id: str
    mode: ExperimentMode
    exp_dir: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    progress: Progress = Field(default_factory=Progress)
    config: ExperimentConfig | None = None
    batch_size: int = 1
    training_progress: TrainingProgress = Field(default_factory=TrainingProgress)
    prediction_progress: PredictionProgress = Field(
        default_factory=PredictionProgress
    )


class ExperimentSummary(BaseModel):
    """Lightweight listing entry so /api/experiments doesn't parse every config."""

    id: str
    mode: ExperimentMode
    exp_dir: str
    created_at: datetime
    updated_at: datetime
    progress: Progress
