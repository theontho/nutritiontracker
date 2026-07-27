def test_root_identifies_service(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>Nutrition Service</title>" in r.text
    assert 'href="/docs"' in r.text


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
