import json

import pandas as pd

import amlro_gui.services.prediction_service as prediction_service_module
from tests.conftest import TINY_CONFIG


def test_get_current_batch_is_safe_to_call_repeatedly(client, monkeypatch, tmp_path):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-pred"})
    client.post("/api/experiments/exp-pred/reaction-scope", json=TINY_CONFIG)

    calls = []

    def fake_get_optimized_parameters(**kwargs):
        calls.append(kwargs)
        return [[15, "A"]]

    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        fake_get_optimized_parameters,
    )

    first = client.get("/api/experiments/exp-pred/prediction")
    second = client.get("/api/experiments/exp-pred/prediction")

    assert first.status_code == 200
    assert first.json == {
        "parameters": [[15, "A"]],
        "current_iteration": 0,
        "batch_size": TINY_CONFIG["batch_size"],
    }
    assert second.json == first.json

    # Simulates reloading mid-cycle: calling this any number of times must
    # never write to the training data (only re-predicting from what's
    # already there), unlike resubmitting a batch would.
    for call in calls:
        assert call["parameters_list"] == []
        assert call["objectives_list"] == []

    next_batch_csv = tmp_path / "exp-pred" / "next_batch.csv"
    next_batch_df = pd.read_csv(next_batch_csv)
    assert next_batch_df.values.tolist() == [[15, "A"]]


def test_submit_batch_requires_parameters_and_objectives(client, monkeypatch):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-missing"})
    client.post("/api/experiments/exp-missing/reaction-scope", json=TINY_CONFIG)
    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        lambda **kwargs: [[15, "A"]],
    )

    resp = client.post("/api/experiments/exp-missing/prediction/next", json={})

    assert resp.status_code == 400
    assert "error" in resp.json


def test_submit_batch_then_stop(client, monkeypatch, tmp_path):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-submit"})
    client.post("/api/experiments/exp-submit/reaction-scope", json=TINY_CONFIG)

    calls = []

    def fake_get_optimized_parameters(**kwargs):
        calls.append(kwargs)
        return None if kwargs.get("termination") else [[20, "B"]]

    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        fake_get_optimized_parameters,
    )

    submit = client.post(
        "/api/experiments/exp-submit/prediction/next",
        json={"parameters": [[15, "A"]], "objectives": [[50]], "stop": False},
    )
    assert submit.status_code == 200
    assert submit.json["parameters"] == [[20, "B"]]
    assert submit.json["current_iteration"] == 1
    assert calls[0]["parameters_list"] == [[15, "A"]]
    assert calls[0]["objectives_list"] == [[50]]

    stop = client.post(
        "/api/experiments/exp-submit/prediction/next",
        json={"parameters": [[20, "B"]], "objectives": [[55]], "stop": True},
    )
    assert stop.json == {"complete": True}
    assert calls[1]["termination"] is True

    state = client.get("/api/experiments/exp-submit").json
    assert state["progress"]["optimization"] is True


def test_submit_batch_can_stop_with_empty_batch(client, monkeypatch):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-stop-empty"})
    client.post("/api/experiments/exp-stop-empty/reaction-scope", json=TINY_CONFIG)
    monkeypatch.setattr(
        prediction_service_module, "get_optimized_parameters", lambda **kwargs: None
    )

    resp = client.post(
        "/api/experiments/exp-stop-empty/prediction/next",
        json={"parameters": [], "objectives": [], "stop": True},
    )

    assert resp.json == {"complete": True}


def test_submit_batch_passes_selected_regressor_model(client, monkeypatch):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-model"})
    config = dict(TINY_CONFIG, regresor_model="knn")
    client.post("/api/experiments/exp-model/reaction-scope", json=config)

    calls = []
    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        lambda **kwargs: calls.append(kwargs) or [[15, "A"]],
    )

    client.post(
        "/api/experiments/exp-model/prediction/next",
        json={"parameters": [[15, "A"]], "objectives": [[50]]},
    )

    assert calls[0]["model"] == "knn"


def test_get_current_batch_passes_selected_regressor_model(client, monkeypatch):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-model-get"})
    config = dict(TINY_CONFIG, regresor_model="knn")
    client.post("/api/experiments/exp-model-get/reaction-scope", json=config)

    calls = []
    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        lambda **kwargs: calls.append(kwargs) or [[15, "A"]],
    )

    client.get("/api/experiments/exp-model-get/prediction")

    assert calls[0]["model"] == "knn"


def test_submit_batch_can_override_batch_size_and_syncs_config_json(
    client, monkeypatch, tmp_path
):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-batch"})
    client.post("/api/experiments/exp-batch/reaction-scope", json=TINY_CONFIG)

    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        lambda **kwargs: [[15, "A"], [20, "B"]],
    )

    resp = client.post(
        "/api/experiments/exp-batch/prediction/next",
        json={"parameters": [], "objectives": [], "batch_size": 2},
    )

    assert resp.json["batch_size"] == 2

    state = client.get("/api/experiments/exp-batch").json
    assert state["batch_size"] == 2
    assert state["config"]["batch_size"] == 2

    config_json = json.loads((tmp_path / "exp-batch" / "config.json").read_text())
    assert config_json["batch_size"] == 2


def test_update_batch_size_persists_independently_of_submitting(
    client, monkeypatch, tmp_path
):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-batch-only"})
    client.post("/api/experiments/exp-batch-only/reaction-scope", json=TINY_CONFIG)

    resp = client.post(
        "/api/experiments/exp-batch-only/prediction/batch-size",
        json={"batch_size": 2},
    )
    assert resp.status_code == 200
    assert resp.json["batch_size"] == 2
    assert resp.json["config"]["batch_size"] == 2

    # Simulates navigating away and back without ever submitting a batch —
    # the size change must already be visible to a fresh GET.
    state = client.get("/api/experiments/exp-batch-only").json
    assert state["batch_size"] == 2

    config_json = json.loads(
        (tmp_path / "exp-batch-only" / "config.json").read_text()
    )
    assert config_json["batch_size"] == 2

    calls = []
    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        lambda **kwargs: calls.append(kwargs) or [[15, "A"], [20, "B"]],
    )
    current = client.get("/api/experiments/exp-batch-only/prediction")
    assert current.json["batch_size"] == 2
    assert calls[0]["batch_size"] == 2


def test_update_batch_size_rejects_invalid_values(client):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-batch-bad"})
    client.post("/api/experiments/exp-batch-bad/reaction-scope", json=TINY_CONFIG)

    resp = client.post(
        "/api/experiments/exp-batch-bad/prediction/batch-size",
        json={"batch_size": 0},
    )

    assert resp.status_code == 400


def test_submit_batch_rejects_continuous_value_outside_bounds(client, monkeypatch):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-oob"})
    client.post("/api/experiments/exp-oob/reaction-scope", json=TINY_CONFIG)
    monkeypatch.setattr(
        prediction_service_module, "get_optimized_parameters", lambda **kwargs: []
    )

    # T's configured bounds are [10, 20] — 99 is a hand-edited/added row
    # that AMLRO was never asked to consider.
    resp = client.post(
        "/api/experiments/exp-oob/prediction/next",
        json={"parameters": [[99, "A"]], "objectives": [[50]]},
    )

    assert resp.status_code == 400
    assert "'T' = 99" in resp.json["error"]
    assert "outside the configured bounds" in resp.json["error"]


def test_submit_batch_rejects_unknown_categorical_value(client, monkeypatch):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-badcat"})
    client.post("/api/experiments/exp-badcat/reaction-scope", json=TINY_CONFIG)
    monkeypatch.setattr(
        prediction_service_module, "get_optimized_parameters", lambda **kwargs: []
    )

    # "C" isn't one of TINY_CONFIG's configured solvent values (["A", "B"]).
    resp = client.post(
        "/api/experiments/exp-badcat/prediction/next",
        json={"parameters": [[15, "C"]], "objectives": [[50]]},
    )

    assert resp.status_code == 400
    assert "'solvent' = 'C'" in resp.json["error"]
    assert "not one of the configured categories" in resp.json["error"]


def test_resume_optimization_reopens_a_completed_experiment(client, monkeypatch):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-resume"})
    client.post("/api/experiments/exp-resume/reaction-scope", json=TINY_CONFIG)
    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        lambda **kwargs: None if kwargs.get("termination") else [[15, "A"]],
    )

    client.post(
        "/api/experiments/exp-resume/prediction/next",
        json={"parameters": [], "objectives": [], "stop": True},
    )
    stopped_state = client.get("/api/experiments/exp-resume").json
    assert stopped_state["progress"]["optimization"] is True

    resp = client.post("/api/experiments/exp-resume/prediction/resume")

    assert resp.status_code == 200
    assert resp.json["progress"]["optimization"] is False

    state = client.get("/api/experiments/exp-resume").json
    assert state["progress"]["optimization"] is False

    # A resumed experiment can fetch a fresh batch off the existing data,
    # same as any other in-progress cycle.
    monkeypatch.setattr(
        prediction_service_module,
        "get_optimized_parameters",
        lambda **kwargs: [[20, "B"]],
    )
    next_batch = client.get("/api/experiments/exp-resume/prediction")
    assert next_batch.status_code == 200
    assert next_batch.json["parameters"] == [[20, "B"]]
