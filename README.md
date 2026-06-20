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

> **Note on `parliament.html`:** the chamber visualization currently reads from a flat `criminal_records.json` + `mps.json` pair rather than hitting the API. This is a legacy/static path — `index.html`, `india-map.html`, and `dossier.html` are the ones wired to the live SQLite-backed API. Migrating `parliament.html` onto the same `/api/v1` endpoints is a natural next step.

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

Four static HTML pages, each independently fetching from `API_BASE = http://localhost:8000/api/v1`.

```
index.html        →  landing page, static content + parliament seating legend (no API calls)
india-map.html    →  SVG constituency map + search → resolves to a myneta_id → links to dossier.html
dossier.html       →  single-MP "GTA wanted poster" style card, driven entirely by /mps/{id}
parliament.html    →  canvas-rendered seating chart (currently reads local mps.json/criminal_records.json)
```

### Flow A — Find your MP (`india-map.html` → `dossier.html`)

1. On load, `india-map.html` fetches three things in parallel:
   - `india_constituencies.svg` — the map geometry, where each `<path>`/`<polygon>` carries `data-name`, `data-state`, `data-party`, `data-mp`, `data-coalition` baked in at SVG-build time (see `scripts/script.py`, out of scope here).
   - `GET /api/v1/mps/constituencies` — names for the search dropdown.
   - `GET /api/v1/mps?limit=543` — full MP list, used purely to build a `constituency name → myneta_id` lookup map client-side.
   - `GET /api/v1/stats` — populates the header stat chips.
2. The user either clicks a constituency on the map or selects one from the dropdown. Both paths converge on a normalized constituency name (`normConstName()` strips casing/punctuation/`(SC)`/`(ST)` suffixes so SVG names and API names line up).
3. Clicking "View MP Dossier" resolves the normalized name to a `myneta_id` and navigates to `dossier.html?id=<myneta_id>`.

### Flow B — Dossier (`dossier.html`)

1. Reads `id` from the query string.
2. Single call: `GET /api/v1/mps/{id}` — returns the full `MPDetail` payload including nested `criminal_cases[]`.
3. Client-side only logic (no extra fetches):
   - Wanted-level stars (1–5) derived from `serious_cases`/`total_cases`.
   - Tags (role, case count, coalition, state) — role/minister lookup is a small static table in the page's JS, not in the DB.
   - "Performance" bars (attendance, questions raised, party loyalty) are **seeded pseudo-random placeholders** based on the MP's name — explicitly labeled "(est.)" in the UI. Only "Criminal severity" is computed from real data.
   - Renders one `case-item` per entry in `criminal_cases[]`, or a clean-record message if empty.

### Flow C — Parliament chamber (`parliament.html`)

Currently a self-contained static visualization: it fetches `mps.json` and `criminal_records.json` directly (flat files alongside the HTML) rather than the API, and positions 543 seats on a canvas based on party/coalition. This predates the FastAPI migration and is the one piece still decoupled from SQLite — flagged above as a future migration target.

---

## 4. Local development

```bash
# 1. Set up the API
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DB_PATH, ALLOWED_ORIGINS as needed
uvicorn main:app --reload --port 8000

# 2. Serve the frontend (any static server, must match ALLOWED_ORIGINS)
cd ..
python3 -m http.server 5500
```

Open `http://localhost:5500/index.html`.

---

## 5. Data provenance & disclaimer

All data originates from candidates' **self-declared ECI affidavits** for the 2024 General Election, sourced via [myneta.info](https://www.myneta.info) (an ADR project). Criminal cases reflect *pending* charges at the time of filing — they are not convictions unless explicitly marked. This tool does not independently verify affidavit contents and makes no legal claims about guilt or wrongdoing.