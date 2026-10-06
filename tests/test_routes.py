from snip import create_app


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Shorten a link" in response.data


def test_health_check(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_create_returns_the_short_link(client):
    response = client.post("/api/links", json={"url": "https://example.com/page"})
    data = response.get_json()
    assert response.status_code == 201
    assert data["short_url"] == "http://localhost/" + data["code"]
    assert data["stats_url"] == "http://localhost/stats/" + data["code"]


def test_short_link_redirects_with_302(client, make_link):
    link = make_link("https://example.com/page")
    response = client.get("/" + link["code"])
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/page"


def test_each_visit_is_counted(client, make_link):
    link = make_link()
    for _ in range(3):
        client.get("/" + link["code"], headers={"Referer": "https://news.example/story"})
    stats = client.get("/api/links/" + link["code"]).get_json()
    assert stats["clicks"] == 3
    assert stats["referrers"] == [{"source": "news.example", "clicks": 3}]


def test_unknown_code_is_404(client):
    assert client.get("/nope99").status_code == 404
    assert client.get("/api/links/nope99").get_json() == {"error": "No link with that code."}


def test_invalid_url_is_rejected_with_a_message(client):
    response = client.post("/api/links", json={"url": "javascript:alert(1)"})
    assert response.status_code == 400
    assert "http" in response.get_json()["error"]


def test_body_that_is_not_json_is_rejected(client):
    assert client.post("/api/links", data="url=https://example.com").status_code == 400
    assert client.post("/api/links", json=["https://example.com"]).status_code == 400


def test_expiry_must_be_a_whole_number(client):
    for bad in ("7", 1.5, True):
        response = client.post(
            "/api/links", json={"url": "https://example.com", "expires_in_days": bad}
        )
        assert response.status_code == 400


def test_duplicate_alias_is_409(client, make_link):
    make_link(alias="docs")
    response = client.post("/api/links", json={"url": "https://example.org", "alias": "docs"})
    assert response.status_code == 409


def test_link_to_this_site_is_rejected(client, make_link):
    link = make_link()
    response = client.post("/api/links", json={"url": link["short_url"]})
    assert response.status_code == 400


def test_expired_link_returns_410_and_is_not_counted(client, make_link, app):
    link = make_link(expires_in_days=1)
    with app.app_context():
        from snip.db import get_db

        get_db().execute("UPDATE links SET expires_at = 1")
        get_db().commit()

    assert client.get("/" + link["code"]).status_code == 410
    assert client.get("/api/links/" + link["code"]).get_json()["clicks"] == 0


def test_stats_page_shows_the_click_count(client, make_link):
    link = make_link()
    client.get("/" + link["code"])
    response = client.get("/stats/" + link["code"])
    assert response.status_code == 200
    assert b"Total clicks" in response.data


def test_stats_page_escapes_the_stored_url(client, make_link):
    link = make_link("https://example.com/<script>alert(1)</script>")
    page = client.get("/stats/" + link["code"]).data
    assert b"<script>alert(1)</script>" not in page
    assert b"&lt;script&gt;" in page


def test_rate_limit_returns_429(tmp_path):
    app = create_app(
        {"TESTING": True, "DATABASE": str(tmp_path / "limit.sqlite3"), "RATE_LIMIT": 2}
    )
    client = app.test_client()
    for _ in range(2):
        assert client.post("/api/links", json={"url": "https://example.com"}).status_code == 201
    response = client.post("/api/links", json={"url": "https://example.com"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


def test_security_headers_are_set(client):
    headers = client.get("/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Content-Security-Policy"] == "default-src 'self'"
