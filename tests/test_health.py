def test_root_identifies_service(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>Nutrition Tracker Service</title>" in r.text
    assert 'href="/favicon.svg"' in r.text
    assert 'href="/docs"' in r.text


def test_favicon(client):
    r = client.get("/favicon.svg")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/svg+xml"
    assert "<svg" in r.text


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
