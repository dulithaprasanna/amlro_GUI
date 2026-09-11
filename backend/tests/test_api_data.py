import io


def test_upload_data_returns_preview_and_sets_mode(client):
    client.post("/api/experiments", json={"mode": "new", "id": "exp-data"})

    csv_bytes = b"T,solvent,Yield\n10,A,55\n20,B,60\n"
    data = {
        "file": (io.BytesIO(csv_bytes), "reactions_data.csv"),
        "file_name": "reactions_data.csv",
    }

    resp = client.post(
        "/api/experiments/exp-data/data",
        data=data,
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    assert resp.json["columns"] == ["T", "solvent", "Yield"]
    assert resp.json["row_count"] == 2
    assert resp.json["preview"][0] == {"T": 10, "solvent": "A", "Yield": 55}

    state_resp = client.get("/api/experiments/exp-data")
    assert state_resp.json["mode"] == "old"
