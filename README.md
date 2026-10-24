# IOC Watchlist

A small app to keep a list of IOCs (indicators of compromise) like IPs, domains, URLs and file hashes (md5, sha1, sha256).

You paste a value, it figures out the type by itself, rejects bad values, and won't let you save the same IOC twice. Even if it's written differently (like `hxxps://evil[.]com` and `https://evil.com`), it counts as the same one.

## Tech used

- Frontend: React + TypeScript (Vite)
- Backend: Python, FastAPI, SQLAlchemy
- Database: SQLite
- Tests: pytest

## Folder layout

```
frontend/          react app (form, list, filters, delete)
backend/
  app/normalize.py   detects type and cleans the value
  app/models.py      db tables (ioc, tag, and the join table)
  app/schemas.py     request/response validation
  app/main.py        the api endpoints
  tests/             tests for normalize and the api
```

## How duplicates are handled

Every value is cleaned up first (lowercase, remove defang stuff, trailing slashes etc). The cleaned value is saved in `iocs.value` which is UNIQUE. The original text you typed is saved in `raw_value`.

The api checks if it already exists and returns a 409 with the existing entry. The unique constraint in the db is the backup in case two requests come at the same time.

## What gets cleaned

- **hashes**: only hex, 32/40/64 chars, lowercased
- **ipv4**: must be a proper ip. Leading zeros are rejected (`010` can be read as octal)
- **domain**: lowercased, trailing `.` and `/` removed, needs at least 2 parts and a TLD with letters
- **url**: http, https, ftp only. Host is lowercased, default port removed, `#fragment` dropped, trailing slash removed. Path and query keep their case because servers care about it

Defang stuff that is reversed: `hxxp`, `hxxps`, `fxp`, `[.]`, `(.)`, `{.}`, `[dot]`, `[:]`, `[://]`.

These all count as the same IOC:
`hxxps://Evil[.]example[.]com/login/`, `https://evil.example.com/login#top`, `https://evil.example.com:443/login`

## Tags

An IOC can have many tags and a tag can be on many IOCs (join table `ioc_tags`). Tags are lowercased and duplicates are removed. When the last IOC using a tag is deleted, the tag is deleted too so the filter doesn't show dead tags.

## Assumptions

- `http://x.com` and `https://x.com` are different IOCs. Same for `evil.com` and `http://evil.com`.
- `www.evil.com` and `evil.com` are different domains.
- Query param order is not changed.
- `evil.com/path` without a scheme is rejected, it doesn't guess.
- No IPv6.
- Defanged input is saved in the normal (refanged) form, so be careful with it. The UI never makes it a clickable link.
- No login/auth.

## Run locally

Needs Python 3.12+ and Node 20+.

```bash
# terminal 1 - backend (http://localhost:8000, docs at /docs)
cd backend
python -m venv venv
venv\Scripts\activate          # on mac/linux: source venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# terminal 2 - frontend (http://localhost:5173)
cd frontend
npm install
npm run dev
```

The `backend/iocs.db` file and tables get created automatically on first start. No migration needed.

## Run tests

```bash
cd backend
pytest -q
```

To check the frontend build: `cd frontend && npm run build`

## Deploy (no docker)

```bash
# build frontend once
cd frontend
npm ci
npm run build

# start backend, it serves the api and the built ui on one port
cd ../backend
python -m venv venv
venv\Scripts\activate          # on mac/linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

Optional env variables:
- `DATABASE_URL` - default is `sqlite:///./iocs.db`
- `STATIC_DIR` - where the built frontend is, default is `frontend/dist`

To reset the data, stop the server and delete the `.db` file. No seed data needed, but you can add one with:

```bash
curl -XPOST localhost:8000/api/iocs -H 'content-type: application/json' \
  -d '{"value":"hxxps://evil[.]example[.]com/login","tags":["phishing"]}'
```

For real use, run it behind something like systemd and nginx, and back up the sqlite file.

## API

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/api/iocs` | add one. Body: `{"value": "...", "note": "...", "tags": ["..."]}`. 201 ok, 422 invalid, 409 duplicate |
| GET | `/api/iocs?tag=&type=` | list, newest first. Both filters optional |
| DELETE | `/api/iocs/{id}` | delete. 204 or 404 |
| GET | `/api/tags` | all tag names |
| GET | `/api/health` | health check |

Docs page: `http://localhost:8000/docs`

Duplicate (409) looks like this:
```json
{"detail": {"code": "duplicate",
            "message": "This indicator already exists as entry #1 (url: https://evil.example.com/login).",
            "existing": {"id": 1, "type": "url", "value": "https://evil.example.com/login"}}}
```

## Known limitations

- No pagination, list returns everything
- No edit, only add / list / delete
- No frontend tests
- `created_at` loses its timezone when read back from sqlite (it is stored in UTC)
- Tables made with `create_all`, no real migrations
- Not tested with lots of data

## Would do with more time

- Alembic migrations and Postgres
- Pagination, search, sorting
- Bulk import (paste list or csv)
- Edit tags and notes
- IPv6, CIDR, emails, CVE ids
- Frontend tests and CI
