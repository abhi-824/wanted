"""
Myneta Lok Sabha 2024 Winner Scraper
=====================================
Stage 1: Scrapes all 543 constituency listing pages to get winner candidate_ids.
Stage 2: Scrapes each winner's candidate page for full dossier data.
Outputs:  data/winners.json, data/mps.json, data/cases.json, data/mps.db

Rate limit: 1 request per 10–20 seconds (random jitter).
Resumable: already-scraped IDs are skipped on restart.
"""

import requests
import time
import random
import json
import sqlite3
import re
import os
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://www.myneta.info"
ELECTION = "LokSabha2024"
TOTAL_CONSTITUENCIES = 543
RATE_MIN = 10   # seconds
RATE_MAX = 20   # seconds

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

WINNERS_FILE  = DATA_DIR / "winners.json"
MPS_FILE      = DATA_DIR / "mps.json"
CASES_FILE    = DATA_DIR / "cases.json"
DB_FILE       = DATA_DIR / "mps.db"
LOG_FILE      = DATA_DIR / "scraper.log"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.myneta.info/",
}

# IPC sections classified as "serious" (ADR definition + common serious offences)
SERIOUS_IPC_SECTIONS = {
    "120B",  # criminal conspiracy
    "121", "121A", "122", "123", "124", "124A",  # offences against state
    "153A", "153B",  # promoting enmity
    "161", "162", "163", "164", "165",  # bribery
    "171E", "171F",  # electoral offences (bribery/undue influence)
    "186",  # obstructing public servant
    "201",  # causing disappearance of evidence
    "269", "270",  # negligent act likely to spread disease
    "295A",  # deliberate acts outraging religious feelings
    "302", "304", "304A", "304B",  # culpable homicide / murder
    "306", "307", "308",  # attempt to murder / abetment of suicide
    "323", "324", "325", "326", "326A", "326B",  # hurt / grievous hurt
    "354", "354A", "354B", "354C", "354D",  # assault on woman
    "363", "364", "364A", "365", "366", "366A", "366B",  # kidnapping
    "376", "376A", "376B", "376C", "376D", "376E",  # rape
    "377",  # unnatural offences
    "379", "380", "381", "382",  # theft
    "384", "385", "386", "387", "388", "389",  # extortion
    "392", "393", "394", "395", "396", "397", "398",  # robbery / dacoity
    "406", "407", "408", "409",  # criminal breach of trust
    "411", "412", "413", "414",  # receiving stolen property
    "419", "420",  # cheating / impersonation
    "436", "437", "438",  # mischief by fire
    "447", "448", "449", "450",  # criminal trespass / house breaking
    "457", "458", "459", "460",  # lurking house trespass
    "465", "466", "467", "468", "469", "470", "471",  # forgery
    "489A", "489B", "489C", "489D",  # counterfeiting currency
    "498A",  # cruelty by husband
    "500", "501", "502",  # defamation (serious if public servant)
    "505",  # statements causing public mischief
    # BNS equivalents (2023 code)
    "103", "109", "110", "111",  # homicide
    "118", "119", "123",  # attempt to murder
    "130", "131",  # culpable homicide
    "74", "75", "76", "77", "78",  # sexual offences
    "316", "317", "318",  # cheating
}

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def sleep_politely():
    delay = random.uniform(RATE_MIN, RATE_MAX)
    log.info(f"  ↳ sleeping {delay:.1f}s")
    time.sleep(delay)


def fetch(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            log.warning(f"  Attempt {attempt}/{retries} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(random.uniform(15, 30))
    log.error(f"  Giving up on {url}")
    return None


def clean_rs(text: str) -> int | None:
    """Convert 'Rs 10,77,18,589' or '10,77,18,589' to int."""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse_ipc_sections(raw: str) -> list[str]:
    """Extract IPC section numbers from a comma/space separated string like '188, 171A'."""
    if not raw:
        return []
    parts = re.split(r"[,\s/]+", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def is_serious(sections: list[str]) -> bool:
    return any(s.upper() in SERIOUS_IPC_SECTIONS for s in sections)


def load_json(path: Path) -> dict | list:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Stage 1: Collect winner candidate_ids ────────────────────────────────────

def scrape_winners() -> dict[int, dict]:
    """
    Returns {constituency_id: {candidate_id, name, constituency, state}}
    Saves to winners.json and resumes if partially done.
    """
    winners: dict = load_json(WINNERS_FILE)
    # keys are stored as strings in JSON
    done_ids = {int(k) for k in winners.keys()}

    log.info(f"Stage 1: collecting winners. Already have {len(done_ids)}/543.")

    for c_id in range(1, TOTAL_CONSTITUENCIES + 1):
        if c_id in done_ids:
            continue

        url = f"{BASE_URL}/{ELECTION}/index.php?action=show_candidates&constituency_id={c_id}"
        log.info(f"[{c_id}/543] Fetching constituency listing: {url}")
        soup = fetch(url)

        if soup is None:
            log.warning(f"  Skipping constituency {c_id} (fetch failed)")
            sleep_politely()
            continue

        winner = _parse_winner_from_listing(soup, c_id)
        if winner:
            winners[str(c_id)] = winner
            log.info(f"  ✓ Winner: {winner['name']} (id={winner['candidate_id']})")
        else:
            log.warning(f"  No winner found for constituency {c_id}")
            # Store a sentinel so we don't retry endlessly
            winners[str(c_id)] = {"candidate_id": None, "error": "no_winner_found"}

        save_json(WINNERS_FILE, winners)
        sleep_politely()

    log.info(f"Stage 1 complete. {sum(1 for v in winners.values() if v.get('candidate_id'))} winners found.")
    return winners


def _parse_winner_from_listing(soup: BeautifulSoup, c_id: int) -> dict | None:
    """Find the row marked (W) = winner in the candidates table."""
    # The table has rows with a green (W) cell or 'Winner' text
    # Also check breadcrumb for constituency + state names
    breadcrumb = soup.find("div", class_="w3-leftbar")
    constituency_name = ""
    state_name = ""
    if breadcrumb:
        links = breadcrumb.find_all("a")
        # Pattern: Home → LokSabha2024 → STATE → CONSTITUENCY
        if len(links) >= 4:
            state_name = links[-2].get_text(strip=True)
            constituency_name = links[-1].get_text(strip=True)

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            row_text = row.get_text()
            # Winner rows have a (W) cell or green winner marker
            if "(W)" in row_text or "Winner" in row_text:
                # Find the candidate detail link
                link = row.find("a", href=re.compile(r"candidate\.php\?candidate_id=\d+"))
                if link:
                    href = link["href"]
                    m = re.search(r"candidate_id=(\d+)", href)
                    if m:
                        return {
                            "candidate_id": int(m.group(1)),
                            "name": link.get_text(strip=True),
                            "constituency": constituency_name,
                            "constituency_id": c_id,
                            "state": state_name,
                        }
    return None

# ── Stage 2: Scrape individual candidate pages ────────────────────────────────

def scrape_candidates(winners: dict) -> tuple[list, list]:
    """
    Returns (mps_list, cases_list).
    Resumes from mps.json — skips already scraped candidate_ids.
    """
    existing_mps: list = load_json(MPS_FILE) if MPS_FILE.exists() else []
    existing_cases: list = load_json(CASES_FILE) if CASES_FILE.exists() else []

    done_cids = {mp["myneta_id"] for mp in existing_mps}

    valid_winners = [
        v for v in winners.values()
        if v.get("candidate_id") and v["candidate_id"] not in done_cids
    ]

    log.info(f"Stage 2: scraping {len(valid_winners)} candidate pages. {len(done_cids)} already done.")

    mps = list(existing_mps)
    cases = list(existing_cases)

    for i, winner in enumerate(valid_winners, 1):
        cid = winner["candidate_id"]
        url = f"{BASE_URL}/{ELECTION}/candidate.php?candidate_id={cid}"
        log.info(f"[{i}/{len(valid_winners)}] candidate_id={cid} — {winner.get('name', '?')}")

        soup = fetch(url)
        if soup is None:
            log.warning(f"  Skipping candidate {cid}")
            sleep_politely()
            continue

        mp_data, case_rows = parse_candidate_page(soup, winner)
        mps.append(mp_data)
        cases.extend(case_rows)

        save_json(MPS_FILE, mps)
        save_json(CASES_FILE, cases)

        log.info(
            f"  ✓ {mp_data['name']} | {mp_data['party']} | "
            f"cases={mp_data['total_cases']} | assets=₹{mp_data['assets_inr']}"
        )
        sleep_politely()

    log.info(f"Stage 2 complete. {len(mps)} MPs scraped.")
    return mps, cases


def parse_candidate_page(soup: BeautifulSoup, winner: dict) -> tuple[dict, list]:
    """Parse a single candidate.php page into structured data."""
    mp = {
        "myneta_id": winner["candidate_id"],
        "constituency_id": winner.get("constituency_id"),
        "constituency": winner.get("constituency", ""),
        "state": winner.get("state", ""),
        "scraped_at": datetime.utcnow().isoformat(),
        # filled below
        "name": "",
        "party": "",
        "coalition": "",
        "age": None,
        "education": "",
        "photo_url": "",
        "total_cases": 0,
        "serious_cases": 0,
        "assets_inr": None,
        "liabilities_inr": None,
        "self_profession": "",
        "spouse_profession": "",
        "voter_constituency": "",
        "election": ELECTION,
    }

    # ── Name ──────────────────────────────────────────────────────────────────
    h2 = soup.find("h2")
    if h2:
        raw = h2.get_text(" ", strip=True)
        # Remove "(Winner)" suffix
        mp["name"] = re.sub(r"\s*\(Winner\)\s*", "", raw, flags=re.IGNORECASE).strip()

    # ── Photo ─────────────────────────────────────────────────────────────────
    img = soup.find("img", alt="profile image")
    if img:
        src = img.get("src", "")
        mp["photo_url"] = src if src.startswith("http") else BASE_URL + src

    # ── Party ─────────────────────────────────────────────────────────────────
    for div in soup.find_all("div"):
        txt = div.get_text()
        if "Party:" in txt and len(txt) < 80:
            m = re.search(r"Party:\s*(.+)", txt)
            if m:
                mp["party"] = m.group(1).strip()
                break

    # ── Age ───────────────────────────────────────────────────────────────────
    for div in soup.find_all("div"):
        txt = div.get_text()
        if "Age:" in txt and len(txt) < 40:
            m = re.search(r"Age:\s*(\d+)", txt)
            if m:
                mp["age"] = int(m.group(1))
                break

    # ── Voter constituency ────────────────────────────────────────────────────
    for div in soup.find_all("div"):
        txt = div.get_text()
        if "Name Enrolled as Voter in:" in txt:
            mp["voter_constituency"] = txt.replace("Name Enrolled as Voter in:", "").strip()[:200]
            break

    # ── Profession ────────────────────────────────────────────────────────────
    for p_tag in soup.find_all("p"):
        txt = p_tag.get_text(" ", strip=True)
        if "Self Profession:" in txt:
            m = re.search(r"Self Profession:\s*(.+?)(?:\s+Spouse Profession:|$)", txt, re.DOTALL)
            if m:
                mp["self_profession"] = m.group(1).strip()
            m2 = re.search(r"Spouse Profession:\s*(.+)", txt, re.DOTALL)
            if m2:
                mp["spouse_profession"] = m2.group(1).strip()[:200]
            break

    # ── Education ─────────────────────────────────────────────────────────────
    for div in soup.find_all("div", class_="w3-panel"):
        if "Educational Details" in div.get_text():
            # Text after the <hr>
            raw = div.get_text(" ", strip=True)
            raw = re.sub(r"Educational Details\s*", "", raw).strip()
            mp["education"] = raw[:300]
            break

    # ── Crime-O-Meter: total cases ────────────────────────────────────────────
    red_panel = soup.find("div", class_="w3-red")
    if red_panel:
        m = re.search(r"Number of Criminal Cases:\s*(\d+)", red_panel.get_text())
        if m:
            mp["total_cases"] = int(m.group(1))

    # ── Assets & Liabilities ──────────────────────────────────────────────────
    asset_rows = soup.find_all("tr")
    for row in asset_rows:
        cells = row.find_all("td")
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            if label == "Assets:":
                b = cells[1].find("b")
                if b:
                    mp["assets_inr"] = clean_rs(b.get_text())
            elif label == "Liabilities:":
                b = cells[1].find("b")
                if b:
                    mp["liabilities_inr"] = clean_rs(b.get_text())

    # ── Criminal cases table ──────────────────────────────────────────────────
    cases_table = soup.find("table", id="cases")
    case_rows = []
    serious_count = 0

    if cases_table:
        rows = cases_table.find_all("tr")
        for row in rows[1:]:  # skip header
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            try:
                serial = cells[0].get_text(strip=True)
                fir_no = cells[1].get_text(strip=True)
                case_no = cells[2].get_text(strip=True)
                court = cells[3].get_text(strip=True)
                ipc_raw = cells[4].get_text(strip=True)
                other_acts = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                charges_framed_raw = cells[6].get_text(strip=True) if len(cells) > 6 else ""
                charge_date = cells[7].get_text(strip=True) if len(cells) > 7 else ""

                sections = parse_ipc_sections(ipc_raw)
                serious = is_serious(sections)
                if serious:
                    serious_count += 1

                case_rows.append({
                    "mp_myneta_id": winner["candidate_id"],
                    "serial_no": serial,
                    "fir_no": fir_no,
                    "case_no": case_no,
                    "court": court,
                    "ipc_sections": ipc_raw,
                    "ipc_sections_list": sections,
                    "other_acts": other_acts,
                    "charges_framed": charges_framed_raw.lower() == "yes",
                    "charge_date": charge_date,
                    "is_serious": serious,
                })
            except (IndexError, AttributeError):
                continue

    mp["serious_cases"] = serious_count

    # Fallback: if Crime-O-Meter didn't parse, use len(case_rows)
    if mp["total_cases"] == 0 and case_rows:
        mp["total_cases"] = len(case_rows)

    # ── Coalition mapping (party → coalition) ─────────────────────────────────
    mp["coalition"] = map_coalition(mp["party"])

    return mp, case_rows


# ── Coalition map ─────────────────────────────────────────────────────────────

NDA_PARTIES = {
    "BJP", "Bharatiya Janata Party",
    "JDU", "Janata Dal (United)",
    "TDP", "Telugu Desam Party",
    "SS(UBT)", "Shiv Sena (Shinde)",  # Shinde faction = NDA
    "Shiv Sena",
    "LJP", "Lok Jan Shakti Party",
    "LJP(RV)", "Lok Jan Shakti Party (Ram Vilas)",
    "AJSU", "All Jharkhand Students Union",
    "NPP", "Nationalist People's Party",
    "NPF",
    "SKM", "Sikkim Krantikari Morcha",
    "AGP", "Asom Gana Parishad",
    "UPPL",
    "JNP",
    "RSP",  # Republican Sena Party
    "NCP",  # Ajit Pawar faction
    "PMK", "Pattali Makkal Katchi",
    "RLD", "Rashtriya Lok Dal",
    "RLSP",
    "HMP",
    "MGP",
    "GFP",
    "NDPP",
    "MNF", "Mizo National Front",
}

INDIA_PARTIES = {
    "INC", "Indian National Congress",
    "SP", "Samajwadi Party",
    "TMC", "All India Trinamool Congress",
    "DMK", "Dravida Munnetra Kazhagam",
    "RJD", "Rashtriya Janata Dal",
    "JMM", "Jharkhand Mukti Morcha",
    "AAP", "Aam Aadmi Party",
    "SS(UBT)", "Shiv Sena (UBT)",
    "NCP(SP)", "Nationalist Congress Party (Sharad Pawar)",
    "CPI(M)", "Communist Party of India (Marxist)",
    "CPI", "Communist Party of India",
    "IUML", "Indian Union Muslim League",
    "VCK", "Viduthalai Chiruthaigal Katchi",
    "RSP",  # Revolutionary Socialist Party
    "KECPF",
    "MDMK",
    "AIFB", "All India Forward Bloc",
    "KC(M)",
    "JKND",
}


def map_coalition(party: str) -> str:
    p = party.strip().upper()
    for nda in NDA_PARTIES:
        if p == nda.upper() or p in nda.upper():
            return "NDA"
    for india in INDIA_PARTIES:
        if p == india.upper() or p in india.upper():
            return "INDIA"
    return "Others"

# ── Stage 3: Write to SQLite ──────────────────────────────────────────────────

def write_db(mps: list, cases: list):
    log.info(f"Writing {len(mps)} MPs and {len(cases)} cases to {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS mps (
            myneta_id         INTEGER PRIMARY KEY,
            constituency_id   INTEGER,
            constituency      TEXT,
            state             TEXT,
            name              TEXT,
            party             TEXT,
            coalition         TEXT,
            age               INTEGER,
            education         TEXT,
            photo_url         TEXT,
            total_cases       INTEGER DEFAULT 0,
            serious_cases     INTEGER DEFAULT 0,
            assets_inr        INTEGER,
            liabilities_inr   INTEGER,
            self_profession   TEXT,
            spouse_profession TEXT,
            voter_constituency TEXT,
            seat_id           TEXT,
            election          TEXT,
            scraped_at        TEXT
        );

        CREATE TABLE IF NOT EXISTS criminal_cases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            mp_myneta_id    INTEGER REFERENCES mps(myneta_id),
            serial_no       TEXT,
            fir_no          TEXT,
            case_no         TEXT,
            court           TEXT,
            ipc_sections    TEXT,
            other_acts      TEXT,
            charges_framed  INTEGER,
            charge_date     TEXT,
            is_serious      INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_cases_mp ON criminal_cases(mp_myneta_id);
        CREATE INDEX IF NOT EXISTS idx_mps_constituency ON mps(constituency_id);
        CREATE INDEX IF NOT EXISTS idx_mps_party ON mps(party);
        CREATE INDEX IF NOT EXISTS idx_mps_coalition ON mps(coalition);
    """)

    for mp in mps:
        c.execute("""
            INSERT OR REPLACE INTO mps (
                myneta_id, constituency_id, constituency, state, name, party,
                coalition, age, education, photo_url, total_cases, serious_cases,
                assets_inr, liabilities_inr, self_profession, spouse_profession,
                voter_constituency, seat_id, election, scraped_at
            ) VALUES (
                :myneta_id, :constituency_id, :constituency, :state, :name, :party,
                :coalition, :age, :education, :photo_url, :total_cases, :serious_cases,
                :assets_inr, :liabilities_inr, :self_profession, :spouse_profession,
                :voter_constituency, '', :election, :scraped_at
            )
        """, mp)

    for case in cases:
        c.execute("""
            INSERT OR IGNORE INTO criminal_cases (
                mp_myneta_id, serial_no, fir_no, case_no, court,
                ipc_sections, other_acts, charges_framed, charge_date, is_serious
            ) VALUES (
                :mp_myneta_id, :serial_no, :fir_no, :case_no, :court,
                :ipc_sections, :other_acts, :charges_framed, :charge_date, :is_serious
            )
        """, case)

    conn.commit()
    conn.close()
    log.info("DB write complete.")


def print_summary(mps: list):
    if not mps:
        return
    total = len(mps)
    with_cases = sum(1 for m in mps if m["total_cases"] > 0)
    crorepatis = sum(1 for m in mps if m["assets_inr"] and m["assets_inr"] >= 1_00_00_000)
    avg_assets = sum(m["assets_inr"] for m in mps if m["assets_inr"]) // max(1, total)

    print("\n" + "="*50)
    print(f"  MPs scraped    : {total}")
    print(f"  With cases     : {with_cases} ({100*with_cases//total}%)")
    print(f"  Crorepatis     : {crorepatis} ({100*crorepatis//total}%)")
    print(f"  Avg assets     : ₹{avg_assets:,}")
    print("="*50 + "\n")

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Myneta Lok Sabha 2024 scraper")
    parser.add_argument(
        "--stage", choices=["1", "2", "all", "db"], default="all",
        help="Stage to run: 1=collect winners, 2=scrape candidates, db=write DB only, all=1+2+db"
    )
    args = parser.parse_args()

    if args.stage in ("1", "all"):
        winners = scrape_winners()
    else:
        winners = load_json(WINNERS_FILE)

    if args.stage in ("2", "all"):
        mps, cases = scrape_candidates(winners)
    else:
        mps = load_json(MPS_FILE) if MPS_FILE.exists() else []
        cases = load_json(CASES_FILE) if CASES_FILE.exists() else []

    if args.stage in ("db", "all") and mps:
        write_db(mps, cases)
        print_summary(mps)

    log.info("Done.")