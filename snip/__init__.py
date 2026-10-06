"""Snip: a URL shortener with click analytics."""

from __future__ import annotations

import os

from flask import Flask

from snip import db, routes


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "snip.sqlite3"),
        # Links created per IP address per minute
        RATE_LIMIT=10,
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if config:
        app.config.update(config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(routes.bp)
    return app
