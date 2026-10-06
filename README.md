# Snip

[![CI](https://github.com/mubarak-jimoh/snip/actions/workflows/ci.yml/badge.svg)](https://github.com/mubarak-jimoh/snip/actions/workflows/ci.yml)

A URL shortener with click statistics. Paste a long link, get a short one, and see how many people clicked it, on which days and from which sites.

Built with Python, Flask and SQLite. 53 automated tests.

## What it does

- Shortens any `http` or `https` link to a six-character code, or to a custom alias you choose.
- Counts every click and shows a seven-day chart and the top referring sites.
- Lets a link expire after 1 to 365 days.
- Limits each IP address to 10 new links per minute.
- Works as a web page and as a JSON API.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app run
```

Open http://127.0.0.1:5000.

Or with Docker:

```bash
docker build -t snip .
docker run -p 8000:8000 snip
```

## API

| Method | Path | What it does |
| --- | --- | --- |
| `POST` | `/api/links` | Create a short link |
| `GET` | `/api/links/<code>` | Get a link's statistics |
| `GET` | `/<code>` | Follow the short link |
| `GET` | `/health` | Health check |

Create a link:

```bash
curl -X POST http://127.0.0.1:5000/api/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/a/long/address", "alias": "docs", "expires_in_days": 7}'
```

```json
{
  "code": "docs",
  "url": "https://example.com/a/long/address",
  "short_url": "http://127.0.0.1:5000/docs",
  "stats_url": "http://127.0.0.1:5000/stats/docs",
  "expires_at": 1791917704.66
}
```

`alias` and `expires_in_days` are optional. Errors come back as `{"error": "..."}` with one of these status codes:

| Status | Meaning |
| --- | --- |
| 400 | The URL, alias or expiry is not valid |
| 404 | No link with that code |
| 409 | The alias is already taken |
| 410 | The link has expired |
| 429 | Too many links created in the last minute |

## How it works

**Short codes.** A code is six random characters from `0-9`, `a-z` and `A-Z`, which gives about 56 billion combinations. The codes are random, not counted up from 1, so nobody can find other people's links by trying the next number. They come from Python's `secrets` module, whose output cannot be predicted.

**Collisions.** Two links could be given the same random code. The `code` column is `UNIQUE`, so the database refuses the second one and the app tries again with a new code. Checking first and then inserting would leave a gap where two requests could both pass the check.

**Validation.** Only `http` and `https` links are accepted. This blocks `javascript:`, `data:` and `file:` links, which could run code or read local files when someone clicks. Links that point back at Snip itself are refused, so a link cannot loop.

**Redirects.** A short link answers with status 302, not 301. Browsers remember a 301 forever and stop asking the server, so later clicks would never be counted.

**Privacy.** A click stores the time and the referring site's domain. It does not store the visitor's IP address or the full referring address.

**Rate limiting.** Each new link is logged with the IP address and time. Before creating one, the app counts that address's links in the last 60 seconds. Because it counts back from now, a burst cannot slip through at the boundary between two minutes.

**Security.** Every SQL query uses `?` placeholders, so user input is never part of the SQL text. Templates escape everything they print. Responses carry a Content Security Policy that only allows scripts and styles from the site itself.

## Project layout

```
app.py              Entry point
snip/
  __init__.py       App factory
  db.py             SQLite connection and schema
  codes.py          Random codes and alias rules
  validation.py     URL checks
  links.py          Create, follow and statistics
  ratelimit.py      Sliding-window rate limit
  routes.py         Pages, API and redirect
  templates/        HTML pages
  static/           CSS and JavaScript
tests/              53 tests
```

## Tests

```bash
pytest
ruff check .
```

Both run on every push through GitHub Actions.

## What I would add next

- User accounts, so only the person who made a link can see its statistics or delete it.
- A shared store such as Redis for the rate limit, so it works across several servers.
- PostgreSQL in place of SQLite for heavier traffic.
