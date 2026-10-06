"""HTTP routes: the web pages, the JSON API and the redirect itself."""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
)

from snip import links, ratelimit

bp = Blueprint("snip", __name__)


def short_url(code: str) -> str:
    return request.host_url + code


def link_json(link) -> dict:
    return {
        "code": link["code"],
        "url": link["url"],
        "short_url": short_url(link["code"]),
        "stats_url": request.host_url + "stats/" + link["code"],
        "expires_at": link["expires_at"],
    }


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.post("/api/links")
def create():
    if not ratelimit.allow(request.remote_addr or "unknown", current_app.config["RATE_LIMIT"]):
        response = jsonify(error="Too many links created. Wait a minute and try again.")
        response.headers["Retry-After"] = "60"
        return response, 429

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Send JSON with a url field."), 400

    expires = data.get("expires_in_days")
    if expires is not None and (isinstance(expires, bool) or not isinstance(expires, int)):
        return jsonify(error="expires_in_days must be a whole number."), 400

    try:
        link = links.create_link(
            url=str(data.get("url") or ""),
            alias=str(data.get("alias") or ""),
            expires_in_days=expires,
            own_host=request.host,
        )
    except links.LinkError as error:
        return jsonify(error=str(error)), error.status

    return jsonify(link_json(link)), 201


@bp.get("/api/links/<code>")
def stats_api(code: str):
    link = links.get_link(code)
    if link is None:
        return jsonify(error="No link with that code."), 404
    return jsonify(links.get_stats(link))


@bp.get("/stats/<code>")
def stats_page(code: str):
    link = links.get_link(code)
    if link is None:
        abort(404)
    stats = links.get_stats(link)
    busiest = max((day["clicks"] for day in stats["daily"]), default=0)
    return render_template("stats.html", stats=stats, short_url=short_url(code), busiest=busiest)


@bp.get("/<code>")
def follow(code: str):
    link = links.get_link(code)
    if link is None:
        abort(404)
    if links.is_expired(link):
        return render_template("message.html", title="This link has expired", code=410), 410

    links.record_click(link, request.headers.get("Referer", ""))
    # 302, not 301: browsers cache a 301 forever and would stop asking this
    # server, so later clicks would never be counted.
    return redirect(link["url"], code=302)


@bp.app_errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify(error="Not found."), 404
    return render_template("message.html", title="Link not found", code=404), 404


@bp.after_app_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
    return response
