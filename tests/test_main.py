from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_shorten_requires_api_key():
    response = client.post("/shorten", params={"long_url": "https://example.com"})
    assert response.status_code == 401


def test_shorten_and_redirect():
    response = client.post(
        "/shorten",
        params={"long_url": "https://example.com"},
        headers={"api-key": "CWe3_2ilKs-mA8ewLKTOfG7wID8kBe3g"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data

    short_code = data["short_code"]
    redirect_response = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 302


def test_invalid_code_returns_404():
    response = client.get("/thiscodedoesnotexist123", follow_redirects=False)
    assert response.status_code == 404

def test_rate_limit_blocks_after_threshold():
    headers = {"api-key": "CWe3_2ilKs-mA8ewLKTOfG7wID8kBe3g"}
    responses = []
    for _ in range(10):
        r = client.post("/shorten", params={"long_url": "https://example.com"}, headers=headers)
        responses.append(r.status_code)

    assert 429 in responses


def test_idempotency_returns_same_result():
    headers = {
        "api-key": "3D0V0fdd09N_3miBb3Mrl6429OG5p_OJ",
        "idempotency-key": "test-fixed-key-999"
    }
    first = client.post("/shorten", params={"long_url": "https://example.com"}, headers=headers)
    second = client.post("/shorten", params={"long_url": "https://example.com"}, headers=headers)

    assert first.json()["short_code"] == second.json()["short_code"]