from typing import Literal

from pydantic import BaseModel, Field, model_validator

Direction = Literal["min", "max"]
SamplingMethod = Literal["random", "lhs", "sobol"]


class ContinuousFeatures(BaseModel):
    feature_names: list[str] = Field(default_factory=list)
    bounds: list[tuple[float, float]] = Field(default_factory=list)
    resolutions: list[float] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_lengths_match(self) -> "ContinuousFeatures":
        lengths = {len(self.feature_names), len(self.bounds), len(self.resolutions)}
        if len(lengths) > 1:
            raise ValueError(
                "continuous.feature_names, bounds, and resolutions must all have "
                "the same length"
            )
        return self

    @model_validator(mode="after")
    def check_bounds_and_resolutions(self) -> "ContinuousFeatures":
        for name, (low, high) in zip(self.feature_names, self.bounds, strict=True):
            if low > high:
                raise ValueError(f"'{name}': min bound must be <= max bound")
        for name, resolution in zip(
            self.feature_names, self.resolutions, strict=True
        ):
            if resolution <= 0:
                raise ValueError(f"'{name}': resolution must be a positive number")
        return self


class CategoricalFeatures(BaseModel):
    feature_names: list[str] = Field(default_factory=list)
    values: list[list[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_lengths_match(self) -> "CategoricalFeatures":
        if len(self.feature_names) != len(self.values):
            raise ValueError(
                "categorical.feature_names and categorical.values must have "
                "the same length"
            )
        return self


class ExperimentConfig(BaseModel):
    continuous: ContinuousFeatures = Field(default_factory=ContinuousFeatures)
    categorical: CategoricalFeatures = Field(default_factory=CategoricalFeatures)
    objectives: list[str]
    directions: list[Direction]
    sampling: SamplingMethod = "random"
    training_size: int = 15
    batch_size: int = 1
    file_name: str = "reactions_data.csv"
    regresor_model: str = "gb"

    @model_validator(mode="after")
    def check_objectives_and_directions(self) -> "ExperimentConfig":
        if len(self.objectives) != len(self.directions):
            raise ValueError(
                "objectives and directions must have the same length"
            )
        return self

    def to_amlro_dict(self) -> dict:
        """Plain-dict shape expected by amlro.* functions (config param)."""
        return self.model_dump()
