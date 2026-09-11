import io

from tests.conftest import TINY_CONFIG


def test_dataset_before_reaction_scope_is_empty(client):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-empty"})

    resp = client.get("/api/experiments/exp-empty/dataset")

    assert resp.status_code == 200
    assert resp.json == {
        "feature_names": [],
        "objective_names": [],
        "columns": [],
        "rows": [],
    }


def test_dataset_reflects_completed_training_rows(client):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-ds"})
    client.post("/api/experiments/exp-ds/reaction-scope", json=TINY_CONFIG)

    client.post("/api/experiments/exp-ds/training/next", json={})
    client.post("/api/experiments/exp-ds/training/next", json={"obj_values": [42]})
    client.post("/api/experiments/exp-ds/training/next", json={"obj_values": [77]})

    resp = client.get("/api/experiments/exp-ds/dataset")

    assert resp.status_code == 200
    body = resp.json
    assert body["feature_names"] == ["T", "solvent"]
    assert body["objective_names"] == ["Yield"]
    assert body["columns"] == ["T", "solvent", "Yield"]
    assert len(body["rows"]) == 2
    # Yield is the last column — matches what was submitted, in order.
    assert [row[-1] for row in body["rows"]] == [42, 77]


def test_dataset_for_old_mode_reflects_uploaded_data(client):
    client.post("/api/experiments", json={"mode": "old", "id": "exp-ds-old"})

    csv_bytes = b"T,solvent,Yield\n10,A,55\n20,B,60\n"
    client.post(
        "/api/experiments/exp-ds-old/data",
        data={"file": (io.BytesIO(csv_bytes), "reactions_data.csv")},
        content_type="multipart/form-data",
    )
    client.post("/api/experiments/exp-ds-old/reaction-scope", json=TINY_CONFIG)

    resp = client.get("/api/experiments/exp-ds-old/dataset")

    assert resp.status_code == 200
    body = resp.json
    assert body["rows"] == [[10, "A", 55], [20, "B", 60]]
