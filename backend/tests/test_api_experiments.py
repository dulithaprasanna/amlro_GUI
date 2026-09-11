def test_create_list_and_get_experiment(client):
    create_resp = client.post(
        "/api/experiments", json={"mode": "new", "id": "exp-1"}
    )
    assert create_resp.status_code == 201
    assert create_resp.json["id"] == "exp-1"
    assert create_resp.json["mode"] == "new"

    list_resp = client.get("/api/experiments")
    assert list_resp.status_code == 200
    assert [e["id"] for e in list_resp.json] == ["exp-1"]

    get_resp = client.get("/api/experiments/exp-1")
    assert get_resp.status_code == 200
    assert get_resp.json["id"] == "exp-1"


def test_get_missing_experiment_returns_404(client):
    resp = client.get("/api/experiments/does-not-exist")

    assert resp.status_code == 404
    assert "error" in resp.json


def test_create_duplicate_experiment_returns_400(client):
    client.post("/api/experiments", json={"mode": "new", "id": "dup"})

    resp = client.post("/api/experiments", json={"mode": "new", "id": "dup"})

    assert resp.status_code == 400
    assert "error" in resp.json


def test_create_experiment_with_invalid_id_returns_400(client):
    resp = client.post("/api/experiments", json={"mode": "new", "id": "../evil"})

    assert resp.status_code == 400


def test_remove_experiment_unregisters_by_default(client, tmp_path):
    client.post("/api/experiments", json={"mode": "new", "id": "to-remove"})

    resp = client.delete("/api/experiments/to-remove")

    assert resp.status_code == 204
    assert client.get("/api/experiments").json == []
    assert (tmp_path / "to-remove" / "state.json").exists()


def test_remove_experiment_with_delete_files_removes_folder(client, tmp_path):
    client.post("/api/experiments", json={"mode": "new", "id": "to-delete"})

    resp = client.delete("/api/experiments/to-delete?delete_files=true")

    assert resp.status_code == 204
    assert not (tmp_path / "to-delete").exists()


def test_remove_missing_experiment_returns_404(client):
    resp = client.delete("/api/experiments/does-not-exist")

    assert resp.status_code == 404


def test_scan_finds_and_registers_unregistered_folder(client, tmp_path):
    other_root = tmp_path / "other"
    other_workspace = other_root / "_unused_registry"
    from amlro_gui.services import experiment_service

    experiment_service.create_experiment(
        other_workspace,
        mode="old",
        experiment_id="found-elsewhere",
        exp_dir=str(other_root / "found-elsewhere"),
    )

    resp = client.post("/api/experiments/scan", json={"root_dir": str(other_root)})

    assert resp.status_code == 200
    assert [e["id"] for e in resp.json["added"]] == ["found-elsewhere"]
    assert resp.json["skipped"] == []

    list_resp = client.get("/api/experiments")
    assert [e["id"] for e in list_resp.json] == ["found-elsewhere"]


def test_scan_requires_root_dir(client):
    resp = client.post("/api/experiments/scan", json={})

    assert resp.status_code == 400
