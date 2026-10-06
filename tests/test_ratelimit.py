from snip import ratelimit


def test_requests_under_the_limit_are_allowed(app):
    with app.app_context():
        assert all(ratelimit.allow("1.1.1.1", limit=3, now=100 + i) for i in range(3))


def test_request_over_the_limit_is_refused(app):
    with app.app_context():
        for i in range(3):
            ratelimit.allow("1.1.1.1", limit=3, now=100 + i)
        assert not ratelimit.allow("1.1.1.1", limit=3, now=110)


def test_limit_is_counted_per_ip_address(app):
    with app.app_context():
        for i in range(3):
            ratelimit.allow("1.1.1.1", limit=3, now=100 + i)
        assert ratelimit.allow("2.2.2.2", limit=3, now=110)


def test_limit_resets_after_the_window(app):
    with app.app_context():
        for _ in range(3):
            ratelimit.allow("1.1.1.1", limit=3, now=100)
        assert not ratelimit.allow("1.1.1.1", limit=3, now=159)
        assert ratelimit.allow("1.1.1.1", limit=3, now=160)


def test_refused_requests_do_not_extend_the_block(app):
    with app.app_context():
        for _ in range(3):
            ratelimit.allow("1.1.1.1", limit=3, now=100)
        for second in range(101, 160):
            ratelimit.allow("1.1.1.1", limit=3, now=second)
        assert ratelimit.allow("1.1.1.1", limit=3, now=160)
