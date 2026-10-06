"""Entry point: `flask run` or `gunicorn app:app`."""

from snip import create_app

app = create_app()
