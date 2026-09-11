import io

import pandas as pd

from tests.conftest import TINY_CONFIG


def test_reaction_scope_then_training_loop(client):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-rs"})

    scope_resp = client.post(
        "/api/experiments/exp-rs/reaction-scope", json=TINY_CONFIG
    )
    assert scope_resp.status_code == 200
    assert scope_resp.json["progress"]["reaction_scope"] is True

    table = client.get("/api/experiments/exp-rs/training").json
    assert table["training_size"] == 2
    assert len(table["rows"]) == 2
    assert all(row["status"] == "pending" for row in table["rows"])

    first = client.post("/api/experiments/exp-rs/training/next", json={})
    assert first.status_code == 200
    assert first.json["complete"] is False
    assert first.json["current_iteration"] == 0
    assert len(first.json["parameters"]) == 2  # [T, solvent]

    second = client.post(
        "/api/experiments/exp-rs/training/next", json={"obj_values": [42]}
    )
    assert second.json["complete"] is False
    assert second.json["current_iteration"] == 1

    table_mid = client.get("/api/experiments/exp-rs/training").json
    assert table_mid["rows"][0]["status"] == "completed"
    assert table_mid["rows"][0]["objectives"] == [42]
    assert table_mid["rows"][1]["status"] == "pending"

    third = client.post(
        "/api/experiments/exp-rs/training/next", json={"obj_values": [77]}
    )
    assert third.json == {"complete": True}

    final_state = client.get("/api/experiments/exp-rs").json
    assert final_state["progress"]["training_set"] is True


def test_reaction_scope_with_invalid_config_returns_422(client):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-bad"})

    bad_config = dict(TINY_CONFIG)
    bad_config["directions"] = ["max", "min"]  # mismatched length vs objectives

    resp = client.post("/api/experiments/exp-bad/reaction-scope", json=bad_config)

    assert resp.status_code == 422
    assert "error" in resp.json


def test_old_mode_reaction_scope_requires_uploaded_data(client):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-nodata"})

    resp = client.post(
        "/api/experiments/exp-old-nodata/reaction-scope", json=TINY_CONFIG
    )

    assert resp.status_code == 400
    assert "Upload your existing reaction data" in resp.json["error"]


def test_old_mode_reaction_scope_rejects_mismatched_columns(client):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-mismatch"})

    # Columns present but in the wrong order (solvent/T swapped) — a silent
    # correctness hazard, not just a missing-column problem.
    csv_bytes = b"solvent,T,Yield\nA,10,55\nB,20,60\n"
    client.post(
        "/api/experiments/exp-old-mismatch/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )

    resp = client.post(
        "/api/experiments/exp-old-mismatch/reaction-scope", json=TINY_CONFIG
    )

    assert resp.status_code == 400
    assert "don't match this configuration" in resp.json["error"]


def test_old_mode_reaction_scope_accepts_matching_columns(client):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-match"})

    csv_bytes = b"T,solvent,Yield\n10,A,55\n20,B,60\n"
    client.post(
        "/api/experiments/exp-old-match/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )

    resp = client.post(
        "/api/experiments/exp-old-match/reaction-scope", json=TINY_CONFIG
    )

    assert resp.status_code == 200
    assert resp.json["progress"]["reaction_scope"] is True


def test_old_mode_upload_produces_encoded_and_decoded_files(client, tmp_path):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-files"})

    # Uploaded data is human-readable (real category names) — the natural
    # thing for someone to have in their own spreadsheet.
    csv_bytes = b"T,solvent,Yield\n10,A,55\n20,B,60\n"
    client.post(
        "/api/experiments/exp-old-files/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )
    client.post("/api/experiments/exp-old-files/reaction-scope", json=TINY_CONFIG)

    exp_dir = tmp_path / "exp-old-files"

    # config.categorical.values == [["A", "B"]], so A -> 0, B -> 1.
    encoded = pd.read_csv(exp_dir / "reactions_data.csv")
    assert encoded["solvent"].tolist() == [0, 1]
    assert encoded["T"].tolist() == [10, 20]

    decoded = pd.read_csv(exp_dir / "reactions_data_decoded.csv")
    assert decoded["solvent"].tolist() == ["A", "B"]
    assert decoded["T"].tolist() == [10, 20]


def test_old_mode_upload_with_encoded_categorical_values(client, tmp_path):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-encoded"})

    # Uploaded data already holds the numeric index (0/1) rather than the
    # real category names — should be detected and handled the other way
    # around: preserved as-is at reactions_data.csv, decoded companion
    # generated from it.
    csv_bytes = b"T,solvent,Yield\n10,0,55\n20,1,60\n"
    client.post(
        "/api/experiments/exp-old-encoded/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )
    resp = client.post(
        "/api/experiments/exp-old-encoded/reaction-scope", json=TINY_CONFIG
    )
    assert resp.status_code == 200

    exp_dir = tmp_path / "exp-old-encoded"
    encoded = pd.read_csv(exp_dir / "reactions_data.csv")
    assert encoded["solvent"].tolist() == [0, 1]

    decoded = pd.read_csv(exp_dir / "reactions_data_decoded.csv")
    assert decoded["solvent"].tolist() == ["A", "B"]


def test_old_mode_upload_rejects_mixed_encoded_and_decoded_columns(client):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-mixed"})

    config = {
        "continuous": {"feature_names": [], "bounds": [], "resolutions": []},
        "categorical": {
            "feature_names": ["solvent", "ligand"],
            "values": [["A", "B"], ["X", "Y"]],
        },
        "objectives": ["Yield"],
        "directions": ["max"],
        "sampling": "random",
        "training_size": 2,
        "batch_size": 1,
        "file_name": "reactions_data.csv",
    }

    # solvent looks decoded ("A"/"B"), ligand looks encoded (0/1) — an
    # inconsistent file that shouldn't be silently guessed at either way.
    csv_bytes = b"solvent,ligand,Yield\nA,0,55\nB,1,60\n"
    client.post(
        "/api/experiments/exp-old-mixed/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )

    resp = client.post("/api/experiments/exp-old-mixed/reaction-scope", json=config)

    assert resp.status_code == 400
    assert "mixes encoded and decoded categorical columns" in resp.json["error"]


def test_old_mode_reaction_scope_rejects_unknown_categorical_value(client):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-unknown-cat"})

    # "C" isn't in TINY_CONFIG's configured solvent values (["A", "B"]).
    csv_bytes = b"T,solvent,Yield\n10,A,55\n20,C,60\n"
    client.post(
        "/api/experiments/exp-old-unknown-cat/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )

    resp = client.post(
        "/api/experiments/exp-old-unknown-cat/reaction-scope", json=TINY_CONFIG
    )

    assert resp.status_code == 400
    assert (
        "neither recognized category names nor valid encoded indices"
        in resp.json["error"]
    )
    assert "'C'" in resp.json["error"]


def test_old_mode_upload_with_no_categorical_features_is_unchanged(client, tmp_path):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-old-nocat"})

    config = dict(TINY_CONFIG)
    config["categorical"] = {"feature_names": [], "values": []}

    csv_bytes = b"T,Yield\n10,55\n20,60\n"
    client.post(
        "/api/experiments/exp-old-nocat/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )

    resp = client.post("/api/experiments/exp-old-nocat/reaction-scope", json=config)
    assert resp.status_code == 200

    exp_dir = tmp_path / "exp-old-nocat"
    original = pd.read_csv(exp_dir / "reactions_data.csv")
    decoded = pd.read_csv(exp_dir / "reactions_data_decoded.csv")
    assert original["T"].tolist() == [10, 20]
    assert decoded["T"].tolist() == [10, 20]
