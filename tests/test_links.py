import pytest

from snip import links
from snip.links import SECONDS_PER_DAY, LinkError

DAY = SECONDS_PER_DAY
NOON = 20_000 * DAY + DAY / 2


def test_create_link_stores_the_url(app):
    with app.app_context():
        link = links.create_link("https://example.com/a")
        assert links.get_link(link["code"])["url"] == "https://example.com/a"


def test_custom_alias_is_used_as_the_code(app):
    with app.app_context():
        assert links.create_link("https://example.com", alias="docs")["code"] == "docs"


def test_taken_alias_is_a_conflict(app):
    with app.app_context():
        links.create_link("https://example.com", alias="docs")
        with pytest.raises(LinkError) as error:
            links.create_link("https://example.org", alias="docs")
        assert error.value.status == 409


def test_random_code_collision_is_retried(app, monkeypatch):
    codes = iter(["same01", "same01", "fresh2"])
    monkeypatch.setattr(links, "random_code", lambda: next(codes))
    with app.app_context():
        first = links.create_link("https://example.com/1")
        second = links.create_link("https://example.com/2")
        assert (first["code"], second["code"]) == ("same01", "fresh2")


def test_expiry_outside_the_allowed_range_is_rejected(app):
    with app.app_context():
        for days in (0, -1, 366):
            with pytest.raises(LinkError):
                links.create_link("https://example.com", expires_in_days=days)


def test_link_expires_at_the_right_moment(app):
    with app.app_context():
        link = links.create_link("https://example.com", expires_in_days=1, now=NOON)
        assert not links.is_expired(link, now=NOON + DAY - 1)
        assert links.is_expired(link, now=NOON + DAY)


def test_link_without_expiry_never_expires(app):
    with app.app_context():
        link = links.create_link("https://example.com", now=NOON)
        assert not links.is_expired(link, now=NOON + 1000 * DAY)


def test_stats_count_clicks_and_group_referrers(app):
    with app.app_context():
        link = links.create_link("https://example.com", now=NOON)
        links.record_click(link, "https://news.example/story?id=5", now=NOON)
        links.record_click(link, "https://news.example/other", now=NOON)
        links.record_click(link, "", now=NOON)

        stats = links.get_stats(link, now=NOON)
        assert stats["clicks"] == 3
        assert stats["referrers"] == [
            {"source": "news.example", "clicks": 2},
            {"source": "Direct", "clicks": 1},
        ]


def test_only_the_referrer_domain_is_stored(app):
    with app.app_context():
        link = links.create_link("https://example.com")
        links.record_click(link, "https://mail.example/inbox/private-message-123?token=abc")
        from snip.db import get_db

        stored = get_db().execute("SELECT referrer FROM clicks").fetchone()["referrer"]
        assert stored == "mail.example"


def test_daily_stats_cover_seven_days_including_empty_ones(app):
    with app.app_context():
        link = links.create_link("https://example.com", now=NOON - 10 * DAY)
        links.record_click(link, now=NOON)
        links.record_click(link, now=NOON - 2 * DAY)
        links.record_click(link, now=NOON - 2 * DAY)
        links.record_click(link, now=NOON - 9 * DAY)  # too old for the chart

        stats = links.get_stats(link, now=NOON)
        assert [day["clicks"] for day in stats["daily"]] == [0, 0, 0, 0, 2, 0, 1]
        assert stats["clicks"] == 4
