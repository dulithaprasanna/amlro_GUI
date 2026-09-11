from amlro_gui.app import create_app


def test_health_check():
    client = create_app().test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}
