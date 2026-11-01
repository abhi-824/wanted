# Neta Check — Know Your Parliament

A transparency tool for India's 18th Lok Sabha. It maps all 543 constituencies, surfaces each MP's self-declared criminal cases and assets (from ECI/ADR affidavits), and renders an interactive parliament chamber, constituency map, and per-MP dossier with PRS participation data.

This README covers the **runtime system**: the SQLite database, the data loader, the FastAPI server, and the React frontend. It intentionally skips the scraping pipeline (`scripts/scraper_myneta.py`, `data/`, `scraps/`) and focuses on how MP, constituency, criminal case, and participation data flow from storage to screen.

---

## 1. Data model

The system is backed by a single SQLite database (`server/netacheck.db`), opened **read-only** by the API (`?mode=ro` URI). The server never writes through that connection — it's a pure read layer over a dataset produced offline by the scraper and the loaders. The one exception is the severity recompute endpoint, which opens a separate short-lived writable connection.

Current dataset: **510 MPs**, **1,198 criminal cases**, **574 IPC/BNS section descriptions**, and **544 PRS MPTrack rows** (510 linked to an MP).

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
| `severity_raw_score` | REAL | Written by `POST /api/v1/severity/recompute` |
| `severity_percentile` | INTEGER | 0–100 rank of the raw score |
| `severity_computed_at` | TEXT | ISO timestamp of the last recompute |

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

### Table: `ipc_sections`

Pure lookup table for IPC/BNS section descriptions (loaded by `scripts/load_ipc_sections.py` from `scripts/ipc.json`). Not related to `criminal_cases` at the DB level — the frontend splits a case's free-text section string and fetches descriptions by code.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK, autoincrement) | |
| `section` | TEXT (unique) | Section code, e.g. "171F", "302" |
| `chapter` | INTEGER | IPC chapter number |
| `chapter_title` | TEXT | Chapter heading |
| `section_title` | TEXT | Short title |
| `section_desc` | TEXT | Plain-language description |

### Table: `mp_track_record`

One row per PRS Legislative Research MPTrack CSV row (rebuilt by `scripts/load_mp_track.py`). Linked to `mps` by `mp_myneta_id`; **at most one row per MP** (enforced by a partial unique index).

| Column | Type | Notes |
|---|---|---|
| `prs_id` | INTEGER (PK) | PRS election index (`mp_election_index` in the CSV) |
| `mp_myneta_id` | INTEGER (FK → `mps.myneta_id`) | NULL when the row could not be linked |
| `name`, `constituency`, `state` | TEXT | Display values from PRS (not normalized) |
| `party`, `gender`, `age`, `house` | — | Profile fields from PRS |
| `membership_type` | TEXT | e.g. "Elected" |
| `term_label`, `term_number` | TEXT / INTEGER | e.g. "Third Term" / `3` |
| `term_start`, `term_end` | TEXT | ISO dates (`YYYY-MM-DD`) |
| `in_office` | INTEGER (bool) | `1` while the term is current |
| `education_level`, `education_details` | TEXT | |
| `attendance` | REAL | 0–1 fraction |
| `debates`, `questions`, `private_member_bills` | INTEGER | Counts for the data period |
| `national_avg_*`, `state_avg_*` | REAL | Comparison benchmarks for the same period |
| `note` | TEXT | PRS note (includes the data period for ministers/Speaker/LoP) |
| `data_period_start`, `data_period_end` | TEXT | Parsed from `note` |
| `source`, `loaded_at` | TEXT | Provenance of the row |

Indexes: unique partial index on `mp_myneta_id` where it is not NULL.

---

## 2. Loading PRS MPTrack data

`scripts/load_mp_track.py` rebuilds `mp_track_record` from the PRS CSV:

```bash
server/venv/bin/python scripts/load_mp_track.py --csv MPTrackData.csv
```

> The script **drops and recreates** `mp_track_record` on every run. It builds every row (and every link) in memory before touching the schema, so a parse failure cannot leave a half-populated table.

### Linking rules

PRS and myneta spell seats and states differently, so rows are linked to `mps` on a normalized `(constituency, state)` key:

1. **Normalize** both sides: lowercase → drop `(SC)` / `(ST)` / `(NCT)` suffixes → replace `&` with `and` → keep letters only.
2. **Apply aliases** (normalized → canonical) to absorb remaining spelling differences:
   - Constituency: `palasur`/`palamau` → `palamu`, `devangare`/`davangere` → `davanagere`, `hatkanangle` → `hatkanangale`, `baharaich` → `bahraich`, `kurnool`/`kurnoolu` → `kurnool`, `darangudguri` → `derrangadulguri`, `darangudalguri` → `darrangudalguri`, `bangaon` → `bongaon`, `srerampur` → `sreerampur`, `thirupati` → `thirupathi`, `patliputra` → `pataliputra`, `dadraandnagarhaveli`/`dadarandnagarhaveli` → `dadradandnagarhaveli`, `damananddiu` → `damanddiu`.
   - State: `dadraandnagarhaveli`, `damanddiu`, and `dadraandnagarhavelianddamananddiu` → `dadraandnagarhavelianddamanddiu`.
3. **General election only**: a row links only if its `term_start` is the earliest `term_start` for that seat. By-election rows are kept but left unlinked.
4. **One MP per row**: a given `myneta_id` is linked at most once, matching the unique partial index.
5. **Missing values**: `""`, `NA`, and `N/A` are stored as SQL `NULL` (text fields and numeric/date parsers).

The script prints the loaded count, the linked count, and every unlinked row with its normalized key and reason (`by-election` or `no matching MP`). Current result: **544 rows loaded, 510 linked, 34 unlinked** — 32 West Bengal seats and the Andaman & Nicobar seat are absent from `mps`, plus one Nanded by-election.

---

## 3. Server (`server/`)

FastAPI app with a single shared `aiosqlite` read-only connection opened at startup and closed at shutdown (see `db.py` lifespan hooks in `main.py`).

```
server/
├── main.py              # app factory, CORS, rate limiting, security headers, SPA fallback
├── config.py            # pydantic-settings: DB path, allowed origins, cron secret, env
├── db.py                # Database wrapper + Mp/Case/TrackRecord/Ipc/Severity repositories
├── severity_weights.py  # static weight table for severity scoring
├── models/              # Pydantic response models (mp, cases, ipc, track, severity)
├── routers/             # mps, stats, ipc, severity
├── services/severity.py # scoring + percentile pipeline
├── middleware/          # slowapi limiter + rate-limit handler
├── static/              # GENERATED frontend build (do not edit by hand)
└── netacheck.db         # the SQLite file (not committed — see .gitignore)
```

### Endpoints

| Method | Path | Rate limit | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/mps` | 60/min | Bulk list — filterable by `state`, `party`, `q`; paginated. Includes gender and attendance, but **no assets/cases** (kept lean, non-scrapeable). |
| `GET` | `/api/v1/mps/constituencies` | 60/min | Flat sorted list of constituency names — powers the search dropdowns. |
| `GET` | `/api/v1/mps/{myneta_id}` | 30/min | Full profile: assets, liabilities, education, profession, nested `criminal_cases[]`, and `parliament_record` (attendance, debates, questions, PMBs). The only place assets are exposed. |
| `GET` | `/api/v1/stats` | 20/min | Aggregate counts: total MPs, MPs with cases, MPs with serious cases, average assets, top 10 states by case count. |
| `GET` | `/api/v1/ipc/{section}` | — | Single IPC/BNS section description. |
| `GET` | `/api/v1/ipc?sections=188,171A` | — | Batch section lookup keyed by code, plus `not_found[]`. |
| `POST` | `/api/v1/severity/recompute` | — | Recomputes `severity_raw_score` / `severity_percentile` for every MP. Requires the `X-Cron-Secret` header. Opens a separate writable connection. |
| `GET` | `/health` | unlimited | Liveness check, excluded from OpenAPI schema. |

Design choices worth noting:
- **Bulk vs. detail separation**: `MPSummary` (list endpoint) deliberately omits `assets_inr` and `criminal_cases` — anyone wanting that data has to fetch one MP at a time, which is rate-limited more tightly (30/min vs 60/min).
- **Read-only DB connection**: the SQLite file is opened with `?mode=ro`, so even a bug in query-building can't mutate data through the API. The severity writer is the only writable path.
- **CORS**: `GET`-only, no credentials, origins restricted via `.env`. Server-to-server cron POSTs bypass CORS, so the severity endpoint is gated by the cron secret instead.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, and a default 5-minute `Cache-Control` applied to every response.

### Static serving and SPA fallback

`main.py` mounts `server/static/assets` and adds a catch-all route that:

- returns a **JSON 404** for `/api` and any `/api/...` path that no router matched;
- serves an existing file from `server/static` (with a path-traversal guard);
- returns **503** if `server/static/index.html` is missing (frontend not built);
- otherwise returns `index.html` so client-side routes (`/map`, `/dossier/123`, …) work on a hard refresh.

---

## 4. Frontend (`frontend/`)

A **React 19 + TypeScript SPA** built with Vite (React Router 8). Production builds are emitted to `server/static/`.

> **`server/static/` is build output.** Never edit it by hand — change `frontend/src` and run `npm run build`. Vite empties the directory on every build (`emptyOutDir: true`), so manual edits are lost.

### Routes

| Path | Page | Data |
|---|---|---|
| `/` | Home | static |
| `/map` | Constituency map + finder | `/stats`, `/mps/constituencies`, `/mps?limit=543`, `/india_constituencies.svg` |
| `/parliament` | Hemicycle seating chart | `/stats`, `/mps/constituencies`, `/mps?limit=600` |
| `/parliament/:id` | Same chart with one seat selected | same as above |
| `/dossier` | Dossier shell — shows "NO MP ID PROVIDED" | none |
| `/dossier/:id` | MP dossier (cases, assets, attendance bars) | `/mps/{id}`, `/ipc?sections=…` |

Legacy URLs redirect client-side to the routes above:

| Legacy URL | Redirects to |
|---|---|
| `/index.html` | `/` |
| `/india-map.html` | `/map` |
| `/dossier.html?id=…` | `/dossier/:id` (or `/dossier` when no `id`) |
| `/parliament.html?id=…` | `/parliament/:id` (or `/parliament` when no `id`) |

Unknown paths redirect to `/`.

The three feature pages (`map/MapPage`, `parliament/ParliamentPage`, `dossier/DossierPage`) are lazy-loaded behind a single `<Suspense fallback={null}>`; the home page is eager.

### Source layout (`frontend/src/`)

```
pages/
  home/           landing page sections
  map/            MapPage + SVG map, finder, tooltip, shared TopBar/StatusBar
  parliament/     ParliamentPage + canvas chamber, coalition tally, seat card
  dossier/        DossierPage + dossier card, cases, education, performance bars
api/              fetch client + TypeScript types
lib/              name normalization, formatting, party colors, coalition helpers
components/       shared UI (tabs, stat chips, grid background)
```

### Dev flow

Two processes: the FastAPI API on **8000** and the Vite dev server on **5173**. Vite proxies `/api` and `/health` to the backend, so the browser only talks to `localhost:5173`.

```bash
# terminal 1 — API
cd server && source venv/bin/activate
uvicorn main:app --reload --port 8000

# terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

`npm run build` runs `tsc -b && vite build`; `npm run lint` runs `oxlint`.

### Production flow

FastAPI serves the built SPA and the API from a single origin:

```bash
cd frontend
npm install
npm run build        # writes to ../server/static (index.html + hashed assets)

cd ../server
source venv/bin/activate
uvicorn main:app --port 8000
```

Open **http://localhost:8000**. Deep links such as `/map`, `/parliament/1`, and `/dossier/123` are handled by the SPA fallback in `main.py`; no separate web server or rewrite rule is needed.

---

## 5. Local development

See **§4 Dev flow** for the recommended Vite + FastAPI workflow. Minimal API-only setup:

```bash
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DB_PATH, ALLOWED_ORIGINS, CRON_SECRET as needed
uvicorn main:app --reload --port 8000
```

Rebuild the PRS participation table with the loader in §2. Rebuild the frontend with `cd frontend && npm install && npm run build`.

---

## 6. Data provenance & disclaimer

MP, constituency, and criminal case data originates from candidates' **self-declared ECI affidavits** for the 2024 General Election, sourced via [myneta.info](https://www.myneta.info) (an ADR project). Participation data (attendance, debates, questions, private member bills) comes from **PRS Legislative Research MPTrack**. Criminal cases reflect *pending* charges at the time of filing — they are not convictions unless explicitly marked. This tool does not independently verify affidavit contents and makes no legal claims about guilt or wrongdoing.
