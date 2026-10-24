# IOC Watchlist Manager

A small full-stack app for analysts to maintain a watchlist of Indicators of Compromise (IOCs): IPv4 addresses, domains, URLs and file hashes (MD5 / SHA-1 / SHA-256).

The type is detected automatically, invalid values are rejected, and **the same indicator can never be stored twice**, even when it is written differently (defanged vs. normal, different case, surrounding whitespace, trailing dots or slashes, URL fragments).

## Tech stack

| Layer    | Choice                                  |
|----------|-----------------------------------------|
| Frontend | React 18 + TypeScript (Vite)            |
| Backend  | Python 3.12, FastAPI, SQLAlchemy 2      |
| Database | SQLite (relational, many-to-many tags)  |
| Tests    | pytest (56 tests)                       |

## Architecture and design decisions

```
frontend/   React + TS UI (form, list, filters, delete)
backend/
  app/normalize.py   type detection + canonicalisation (pure functions, no I/O)
  app/models.py      IOC, Tag, ioc_tags (many-to-many join table)
  app/schemas.py     request/response validation (Pydantic)
  app/main.py        REST endpoints
  tests/             unit tests for normalisation, API tests for everything else
```

- **Canonical value + UNIQUE constraint.** Every value is normalised to a canonical form which is stored in `iocs.value` (UNIQUE). The original input is kept in `raw_value`. The API checks for an existing entry first (to return a helpful 409), and the DB constraint is the real guarantee: if two concurrent requests race, the loser hits `IntegrityError` and still gets the same clean 409.
- **Normalisation is a pure module** (`normalize.py`), so the tricky logic is unit-tested in isolation from HTTP and the DB.
- **Many-to-many tags** via `ioc_tags` join table with `ON DELETE CASCADE` (SQLite foreign keys are switched on explicitly, as they are off by default). Tags are lowercased and de-duplicated. Orphaned tags are removed when the last IOC using them is deleted, so the tag filter never offers dead options.
- **One deployable.** After `npm run build`, FastAPI serves the built React app from `frontend/dist`, so production is one process on one port with no CORS. In development Vite proxies `/api` to FastAPI.
- **Structured errors.** All errors return `{"detail": {"code", "message", ...}}`; a duplicate also returns the `existing` entry.

### Domain rules (canonical form)

| Type | Rules |
|------|-------|
| md5 / sha1 / sha256 | Hex only, 32 / 40 / 64 chars, lowercased |
| ipv4 | Valid dotted quad; leading zeros rejected (ambiguous: some tools read `010` as octal) |
| domain | Lowercased; IDN converted to punycode; trailing `.` and `/` removed; >= 2 labels; alphabetic TLD (so `1.2.3` and `evil.123` are rejected) |
| url | Schemes `http`, `https`, `ftp`; host lowercased, trailing dot removed; default port removed (`:443` on https); **fragment dropped**; trailing slashes on the path removed; **path and query keep their case** because servers treat them as case-sensitive |

Defang patterns reversed before validation: `hxxp(s)`, `fxp`, `[.]`, `(.)`, `{.}`, `[dot]`, `[:]`, `[://]`.

Examples that are treated as the same indicator:
`hxxps://Evil[.]example[.]com/login/`, `https://evil.example.com/login#top`, `https://evil.example.com:443/login`.

### Assumptions and trade-offs

- `http://x.com` and `https://x.com` are **different** indicators (different scheme can mean different infrastructure). Same for `evil.com` (domain) vs `http://evil.com` (url).
- `www.evil.com` and `evil.com` are different domains; no subdomain collapsing.
- Query parameter order is not normalised, since order can matter to a server.
- A bare `evil.com/path` (no scheme) is rejected rather than guessed.
- IPv6 is out of scope (not in the supported type list). `http://[::1]/` is rejected.
- Defanged input is accepted but the stored/displayed value is the **refanged** form. Analysts should treat it as live; the UI never renders it as a link. React escapes all values.
- No authentication (per the brief).

## Run locally (development)

Requires Python 3.12+ and Node 20+.

```bash
# Terminal 1: backend  (http://localhost:8000, docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Terminal 2: frontend (http://localhost:5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

The SQLite file `backend/iocs.db` and its tables are created automatically on first start. No migration step is needed for this schema.

## Run tests

```bash
cd backend && source .venv/bin/activate
pytest -q
```

Frontend type-check and production build: `cd frontend && npm run build`.

## Deployment (no Docker)

Requires Python 3.12+ and Node 20+ on the target machine.

```bash
# 1. Build the frontend once
cd frontend
npm ci
npm run build            # outputs frontend/dist

# 2. Install backend deps and start the server (serves API + built UI on one port)
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

- **Environment variables** (both optional)
  - `DATABASE_URL`: SQLAlchemy URL. Default `sqlite:///./iocs.db` (file created in the directory you start the server from). For an absolute path use `sqlite:////var/data/iocs.db`.
  - `STATIC_DIR`: folder containing the built frontend. Default `frontend/dist` relative to the repo.
- **Database setup / migration:** tables are created automatically at startup (`create_all`), so there is no separate migration step. To reset, stop the server and delete the `.db` file.
- **Seeding:** none required. To add sample data:
  ```bash
  curl -XPOST localhost:8000/api/iocs -H 'content-type: application/json' \
    -d '{"value":"hxxps://evil[.]example[.]com/login","tags":["phishing"]}'
  ```
- **Production notes:** run behind a process manager (systemd, supervisor) and a reverse proxy such as nginx for TLS. Back up the SQLite file. Switching to Postgres only needs a different `DATABASE_URL` plus the `psycopg[binary]` package.
- Health check: `GET /api/health`.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/iocs` | Create. Body: `{"value": str, "note"?: str, "tags"?: [str]}`. `201` with the IOC; `422` invalid value; `409` duplicate |
| GET | `/api/iocs?tag=&type=` | List, newest first. Both filters optional and combinable. `422` for an unknown type |
| DELETE | `/api/iocs/{id}` | `204`, or `404` |
| GET | `/api/tags` | All tag names (used by the UI filter) |
| GET | `/api/health` | Liveness |

Interactive docs: `http://localhost:8000/docs`.

Duplicate response (`409`):
```json
{"detail": {"code": "duplicate",
            "message": "This indicator already exists as entry #1 (url: https://evil.example.com/login).",
            "existing": {"id": 1, "type": "url", "value": "https://evil.example.com/login", "...": "..."}}}
```

## Known limitations

- No pagination: the list endpoint returns everything.
- No edit/update endpoint, only create / list / delete.
- No frontend tests (the logic that matters is on the backend and tested there).
- `created_at` loses its timezone marker when read back from SQLite (stored as UTC).
- Schema is created with `create_all`, not versioned migrations.
- Not tested at scale; SQLite is single-writer.

## What I would improve with more time

- Alembic migrations and a Postgres option in compose.
- Pagination, search, and sorting; bulk import (paste a list or CSV) with a per-line report.
- Edit tags and note on existing IOCs.
- IPv6 and CIDR support, email addresses, and CVE IDs.
- Use a public-suffix list for stricter domain validation.
- Frontend tests (Vitest + Testing Library) and a CI pipeline (lint, tests, build).
