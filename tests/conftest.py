import pytest

from snip import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(
        {"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3"), "RATE_LIMIT": 100}
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_link(client):
    def _make(url="https://example.com/page", **extra):
        response = client.post("/api/links", json={"url": url, **extra})
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make
