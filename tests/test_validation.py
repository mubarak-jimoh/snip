import pytest

from snip.validation import MAX_URL_LENGTH, url_problem


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com/path?query=1#part",
        "https://sub.example.co.uk:8443/a",
        "http://localhost:3000/dev",
    ],
)
def test_normal_web_links_are_accepted(url):
    assert url_problem(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com/file",
        "https://",
        "https://nodots",
        "https://example.com/a b",
        "https://example.com/\nSet-Cookie: x=1",
    ],
)
def test_unsafe_or_broken_links_are_rejected(url):
    assert url_problem(url) is not None


def test_very_long_url_is_rejected():
    assert url_problem("https://example.com/" + "a" * MAX_URL_LENGTH) is not None


def test_link_to_this_site_is_rejected():
    assert url_problem("http://snip.test/abc123", own_host="snip.test") is not None
    assert url_problem("http://other.test/abc123", own_host="snip.test") is None
