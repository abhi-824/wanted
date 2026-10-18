# Neta Check — Know Your Parliament

A transparency tool for India's 18th Lok Sabha. It maps all 543 constituencies, surfaces each MP's self-declared criminal cases and assets (from ECI/ADR affidavits), and renders an interactive parliament chamber and constituency map.

This README covers the **runtime system**: the SQLite database, the FastAPI server, and the static frontend pages. It intentionally skips the scraping pipeline (`scripts/`, `data/`, `scraps/`) and focuses on how MP, constituency, and criminal case data flow from storage to screen.

---

## 1. Data model

The system is backed by a single SQLite database (`server/netacheck.db`), opened **read-only** by the API (`?mode=ro` URI). The server never writes — it's a pure read layer over a dataset produced offline by the scraper.

### Table: `mps`

One row per elected Member of Parliament (winner of their constituency, 2024 General Election).

| Column | Type | Notes |
|---|---|---|
| `myneta_id` | INTEGER (PK) | Candidate ID from myneta.info — the stable identifier used everywhere (URLs, dossier lookups, joins) |
| `constituency_id` | INTEGER | Myneta's internal constituency ID |
| `constituency` | TEXT | Display name, e.g. "Varanasi" |
| `state` | TEXT | e.g. "Uttar Pradesh" |
| `name` | TEXT | MP's full name |
| `party` | TEXT | Party abbreviation, e.g. "BJP" |
| `coalition` | TEXT | "NDA" / "INDIA" / "Others" — derived at scrape time via static party→coalition mapping |
| `age` | INTEGER | |
| `education` | TEXT | Free text from affidavit |
| `photo_url` | TEXT | Absolute URL to myneta.info profile photo |
| `total_cases` | INTEGER | Count of pending criminal cases (Crime-O-Meter, falls back to `len(criminal_cases)` if unparsed) |
| `serious_cases` | INTEGER | Subset of `total_cases` matching a curated list of "serious" IPC/BNS sections (murder, rape, kidnapping, extortion, etc.) |
| `assets_inr` | INTEGER | Declared assets in raw rupees (not crores) |
| `liabilities_inr` | INTEGER | Declared liabilities in raw rupees |
| `self_profession` | TEXT | |
| `spouse_profession` | TEXT | |
| `voter_constituency` | TEXT | Raw "Home → Lok Sabha → State → Constituency" breadcrumb text from the source page |
| `seat_id` | TEXT | Reserved — currently unused/empty |
| `election` | TEXT | e.g. "LokSabha2024" |
| `scraped_at` | TEXT | ISO timestamp of when this row was scraped |

Indexes: `constituency_id`, `party`, `coalition`.

### Table: `criminal_cases`

One row per pending criminal case declared in an MP's affidavit. Many-to-one with `mps`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK, autoincrement) | |
| `mp_myneta_id` | INTEGER (FK → `mps.myneta_id`) | |
| `serial_no` | TEXT | Serial number as listed on the affidavit |
| `fir_no` | TEXT | FIR number |
| `case_no` | TEXT | Court case number |
| `court` | TEXT | Court name/jurisdiction |
| `ipc_sections` | TEXT | Raw comma/space-separated IPC or BNS section string, e.g. "188, 171A" |
| `other_acts` | TEXT | Charges under acts other than IPC/BNS |
| `charges_framed` | INTEGER (bool) | Whether charges have formally been framed |
| `charge_date` | TEXT | |
| `is_serious` | INTEGER (bool) | Computed at scrape time from `ipc_sections` against a static "serious offences" set |

Indexes: `mp_myneta_id`.

---

## 2. Server (`server/`)

FastAPI app, single shared `aiosqlite` connection opened at startup and closed at shutdown (see `db.py` lifespan hooks in `main.py`).

```
server/
├── main.py          # app factory, CORS, rate limiting, security headers, lifespan
├── config.py        # pydantic-settings: DB path, allowed origins, env
├── db.py            # Database wrapper + MpRepository + CaseRepository
├── models/
│   ├── mp.py        # MPSummary, MPDetail, MpFilters, StatsResponse
│   └── cases.py     # CriminalCase (int→bool coercion for SQLite booleans)
├── middleware/
│   └── rate_limit.py # slowapi limiter + per-endpoint limit strings
└── netacheck.db     # the SQLite file (not committed — see .gitignore)
```

### Endpoints

| Method | Path | Rate limit | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/mps` | 60/min | Bulk list — filterable by `state`, `party`, `q`; paginated. **No assets/cases** in the response (kept lean, non-scrapeable). |
| `GET` | `/api/v1/mps/constituencies` | 60/min | Flat sorted list of constituency names — powers the search dropdown in `india-map.html`. |
| `GET` | `/api/v1/mps/{myneta_id}` | 30/min | Full profile: assets, liabilities, education, profession, and nested `criminal_cases[]`. The only place assets are exposed. |
| `GET` | `/api/v1/stats` | 20/min | Aggregate counts: total MPs, MPs with cases, MPs with serious cases, average assets, top 10 states by case count. |
| `GET` | `/health` | unlimited | Liveness check, excluded from OpenAPI schema. |

Design choices worth noting:
- **Bulk vs. detail separation**: `MPSummary` (list endpoint) deliberately omits `assets_inr` and `criminal_cases` — anyone wanting that data has to fetch one MP at a time, which is rate-limited more tightly (30/min vs 60/min).
- **Read-only DB connection**: the SQLite file is opened with `?mode=ro`, so even a bug in query-building can't mutate data through the API.
- **CORS**: `GET`-only, no credentials, origins restricted via `.env`.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, and a default 5-minute `Cache-Control` applied to every response.

---

## 3. Frontend lifecycle

The UI is a **React + TypeScript SPA** in `frontend/` (Vite). Production builds are emitted to `server/static/` and served by FastAPI. **Do not edit `server/static/` by hand** — change `frontend/src` and run `npm run build`.

### Routes

| Path | Page | Data |
|---|---|---|
| `/` | Home | static |
| `/map` | Constituency map + finder | `/stats`, `/mps/constituencies`, `/mps?limit=543`, SVG asset |
| `/dossier`, `/dossier/:id` | MP dossier card | `/mps/{id}` |
| `/parliament`, `/parliament/:id` | Hemicycle seating chart | `/stats`, `/mps/constituencies`, `/mps?limit=600` |

Legacy URLs (`/index.html`, `/india-map.html`, `/dossier.html?id=…`, `/parliament.html?id=…`) redirect to the routes above.

### Source layout (`frontend/src/`)

```
pages/
  home/           landing
  map/            SVG map, finder panel, shared TopBar + StatusBar
  dossier/        dossier card components
  parliament/     chamber layout (canvas), coalition tally, seat card
  MapPage.tsx     route shell → map/
  DossierPage.tsx route shell → dossier/
  ParliamentPage.tsx / ParliamentDetailPage.tsx → parliament/
api/              fetch client + TypeScript types
lib/              formatting, party colors, coalition helpers
components/       shared UI (tabs, stat chips, grid background)
```

### Dev vs prod

**Development** — API on port 8000, Vite dev server on 5173 (proxies `/api` to the backend):

```bash
cd server && uvicorn main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`.

**Production** — build the SPA, then serve everything from FastAPI:

```bash
cd frontend && npm run build    # writes to server/static/
cd server && uvicorn main:app --port 8000
```

Open `http://localhost:8000/`.

---

## 4. Local development

See **§3 Dev vs prod** for the recommended Vite + FastAPI workflow. Minimal API-only setup:

```bash
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DB_PATH, ALLOWED_ORIGINS as needed
uvicorn main:app --reload --port 8000
```

---

## 5. Data provenance & disclaimer

All data originates from candidates' **self-declared ECI affidavits** for the 2024 General Election, sourced via [myneta.info](https://www.myneta.info) (an ADR project). Criminal cases reflect *pending* charges at the time of filing — they are not convictions unless explicitly marked. This tool does not independently verify affidavit contents and makes no legal claims about guilt or wrongdoing.