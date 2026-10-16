import pytest

from app import app, limiter


@pytest.fixture
def client():
    app.config["TESTING"] = True
    limiter.reset()
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"<html" in response.data.lower()


def test_api_services_and_testimonials(client):
    services = client.get("/api/services").get_json()["services"]
    testimonials = client.get("/api/testimonials").get_json()["testimonials"]
    assert services and all({"title", "description"} <= set(s) for s in services)
    assert testimonials and all({"quote", "author"} <= set(t) for t in testimonials)


def test_version(client):
    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.get_json()["version"]


def test_contact_requires_message(client):
    response = client.post("/contact", json={"name": "Ada"})
    assert response.status_code == 400


def test_contact_accepts_message(client):
    response = client.post("/contact", json={"name": "Ada", "message": "Hello"})
    assert response.status_code == 200


def test_contact_is_rate_limited(client):
    statuses = [client.post("/contact", json={"message": "Hi"}).status_code for _ in range(6)]
    assert statuses == [200] * 5 + [429]


def test_unknown_path_returns_404_page(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert b"<html" in response.data.lower()


def test_metrics_count_requests(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.content_type.startswith("text/plain")
    assert b'endpoint="health"' in response.data


def test_security_headers(client):
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
