import os
from pathlib import Path


class Config:
    WORKSPACE_ROOT = Path(
        os.environ.get("AMLRO_GUI_WORKSPACE_ROOT", Path.cwd() / "workspace")
    ).resolve()
