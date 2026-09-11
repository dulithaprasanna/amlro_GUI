class ExperimentError(Exception):
    """Base class for experiment-related errors."""


class InvalidExperimentIdError(ExperimentError):
    pass


class ExperimentNotFoundError(ExperimentError):
    pass


class ExperimentAlreadyExistsError(ExperimentError):
    pass
