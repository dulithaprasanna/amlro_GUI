import pytest

from amlro_gui.app import create_app

TINY_CONFIG = {
    "continuous": {
        "feature_names": ["T"],
        "bounds": [[10, 20]],
        "resolutions": [5],
    },
    "categorical": {
        "feature_names": ["solvent"],
        "values": [["A", "B"]],
    },
    "objectives": ["Yield"],
    "directions": ["max"],
    "sampling": "random",
    "training_size": 2,
    "batch_size": 1,
    "file_name": "reactions_data.csv",
}


@pytest.fixture
def app(tmp_path):
    return create_app({"WORKSPACE_ROOT": tmp_path})


@pytest.fixture
def client(app):
    return app.test_client()
