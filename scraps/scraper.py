"""
netastats_scraper/scraper.py
────────────────────────────
Scrapes myneta.info for a given election (default: LokSabha2024) and writes:
  - mps.json            → { members: [...], parties: {...} }
  - criminal_records.json → { records: [...] }

Both files are shaped to match the dossier.html JS template exactly.

Usage:
  python scraper.py                          # full Lok Sabha 2024 scrape
  python scraper.py --election LokSabha2019  # different election
  python scraper.py --limit 10               # test run, first 10 candidates only
  python scraper.py --candidate-id 8414      # single candidate debug

Output files land in ./output/
"""

import asyncio
import json
import re
import sys
import time
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

import httpx
from bs4 import BeautifulSoup

# ── CONFIG ────────────────────────────────────────────────────────────────────

BASE_URL        = "https://myneta.info"
CONCURRENCY     = 4          # simultaneous requests (be polite to ADR's server)
DELAY_BETWEEN   = 1.5        # seconds between batches
REQUEST_TIMEOUT = 30
HEADERS = {
    "User-Agent": "NetaStats/1.0 (civic research; contact: your@email.com)",
    "Accept-Language": "en-US,en;q=0.9",
}
OUTPUT_DIR = Path("output")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")


# ── PARTY METADATA (static — update as needed) ───────────────────────────────
# color = brand hex, coalition = NDA | INDIA | Other

PARTY_META = {
    "BJP":  {"name": "Bharatiya Janata Party",    "color": "#FF6B35", "coalition": "NDA"},
    "INC":  {"name": "Indian National Congress",   "color": "#19AAED", "coalition": "INDIA"},
    "SP":   {"name": "Samajwadi Party",             "color": "#E63946", "coalition": "INDIA"},
    "BSP":  {"name": "Bahujan Samaj Party",         "color": "#1565C0", "coalition": "Other"},
    "TMC":  {"name": "All India Trinamool Congress","color": "#20B2AA", "coalition": "INDIA"},
    "DMK":  {"name": "Dravida Munnetra Kazhagam",  "color": "#D32F2F", "coalition": "INDIA"},
    "AAP":  {"name": "Aam Aadmi Party",             "color": "#00BCD4", "coalition": "INDIA"},
    "NCP":  {"name": "Nationalist Congress Party",  "color": "#4CAF50", "coalition": "INDIA"},
    "SS":   {"name": "Shiv Sena",                   "color": "#FF8F00", "coalition": "NDA"},
    "SS(UBT)":{"name":"Shiv Sena (UBT)",            "color": "#E65100", "coalition": "INDIA"},
    "JDU":  {"name": "Janata Dal (United)",          "color": "#66BB6A", "coalition": "NDA"},
    "TDP":  {"name": "Telugu Desam Party",           "color": "#FFD600", "coalition": "NDA"},
    "YSRCP":{"name": "YSR Congress Party",           "color": "#6A1B9A", "coalition": "Other"},
    "CPI(M)":{"name":"Communist Party of India (M)", "color": "#C62828", "coalition": "INDIA"},
    "CPI":  {"name": "Communist Party of India",     "color": "#B71C1C", "coalition": "INDIA"},
    "RJD":  {"name": "Rashtriya Janata Dal",         "color": "#00796B", "coalition": "INDIA"},
    "SHS":  {"name": "Shiv Sena",                    "color": "#FF8F00", "coalition": "NDA"},
    "LJPRV":{"name": "LJP (Ram Vilas)",              "color": "#90A4AE", "coalition": "NDA"},
    "IND":  {"name": "Independent",                  "color": "#9E9E9E", "coalition": "Other"},
}

def party_meta(abbr: str) -> dict:
    abbr = abbr.strip()
    base = PARTY_META.get(abbr, {
        "name": abbr,
        "color": "#888888",
        "coalition": "Other",
    })
    return {"abbr": abbr, **base}


# ── DATA CLASSES ──────────────────────────────────────────────────────────────

@dataclass
class ItrEntry:
    year: str
    income: int  # in rupees

@dataclass
class ItrRecord:
    relation: str   # self | spouse | huf | dependent1 ...
    pan: bool
    itr: list[ItrEntry] = field(default_factory=list)

@dataclass
class PriorElection:
    election: str
    assets: int    # in rupees
    cases: int

@dataclass
class CriminalCase:
    num: str       # e.g. "IPC 302"
    text: str

@dataclass
class AssetBreakdown:
    cash: int = 0
    bank_deposits: int = 0
    shares_bonds: int = 0
    insurance: int = 0
    loans_given: int = 0
    vehicles: int = 0
    jewellery: int = 0
    other_movable: int = 0
    agricultural_land: int = 0
    non_agri_land: int = 0
    commercial_buildings: int = 0
    residential_buildings: int = 0
    other_immovable: int = 0

@dataclass
class Candidate:
    # Identity
    candidate_id: int
    name: str
    constituency: str
    state: str
    party: str
    election: str
    is_winner: bool

    # Personal
    age: Optional[int]
    parentage: str
    photo_url: Optional[str]
    self_profession: str
    spouse_profession: str

    # Financials
    total_assets: int         # in rupees
    total_liabilities: int    # in rupees
    assets_cr: float          # total_assets / 1e7, rounded 2dp
    movable_total: int
    immovable_total: int
    asset_breakdown: AssetBreakdown = field(default_factory=AssetBreakdown)

    # Criminal
    total_cases: int = 0
    serious_cases: int = 0
    cases: list[CriminalCase] = field(default_factory=list)
    convicted: bool = False
    conviction_detail: str = ""

    # Income & Tax
    income_sources: dict = field(default_factory=dict)   # {self, spouse, dependent}
    itr_records: list[ItrRecord] = field(default_factory=list)
    has_govt_contracts: bool = False

    # History
    prior_elections: list[PriorElection] = field(default_factory=list)

    # Source
    source_url: str = ""


# ── PARSING HELPERS ───────────────────────────────────────────────────────────

def clean_int(text: str) -> int:
    """Extract first integer from a messy string like 'Rs 1,23,456'."""
    digits = re.sub(r'[^\d]', '', text)
    return int(digits) if digits else 0

def safe_int(s) -> int:
    try: return int(str(s).strip())
    except: return 0

def to_cr(rupees: int) -> float:
    return round(rupees / 1e7, 2)

def first_bold_int(tag) -> int:
    """Given a <td>, return the integer inside its first <b>."""
    if not tag: return 0
    b = tag.find_next('b')
    return clean_int(b.get_text()) if b else 0

def parse_money_cell(td) -> int:
    """Parse a table cell that may contain multiple amounts and descriptions.
    Returns the row-total (last bold element is usually the grand total per row)."""
    if not td: return 0
    # The last <b> in the last <td> of a movable/immovable row is the row total
    bolds = td.find_all('b')
    if not bolds: return 0
    return clean_int(bolds[-1].get_text())


# ── CANDIDATE PAGE PARSER ─────────────────────────────────────────────────────

def parse_candidate_page(html: str, candidate_id: int, election: str) -> Optional[Candidate]:
    soup = BeautifulSoup(html, 'html.parser')

    # ── Name + Winner ──
    h2 = soup.find('h2')
    if not h2:
        return None
    name_raw   = h2.get_text(strip=True)
    is_winner  = '(Winner)' in name_raw
    name       = re.sub(r'\(Winner\)|\(Loser\)', '', name_raw).strip()

    # ── Constituency / State ──
    h5 = soup.find('h5')
    cs_text = h5.get_text(strip=True) if h5 else ''
    state_m = re.search(r'\(([^)]+)\)\s*$', cs_text)
    if state_m:
        state        = state_m.group(1).strip()
        constituency = cs_text[:state_m.start()].strip()
    else:
        state, constituency = '', cs_text

    # ── Party ──
    party_b = soup.find('b', string=re.compile(r'^Party:$'))
    party   = party_b.next_sibling.strip() if party_b else 'IND'

    # ── Age ──
    age_b   = soup.find('b', string=re.compile(r'^Age:$'))
    age_raw = age_b.next_sibling.strip() if age_b else ''
    age_m   = re.search(r'\d+', age_raw)
    age     = int(age_m.group()) if age_m else None

    # ── Parentage ──
    par_b = soup.find('b', string=re.compile(r'S/o|D/o|W/o'))
    parentage = par_b.next_sibling.strip() if par_b else ''

    # ── Photo ──
    img = soup.find('img', src=re.compile(r'/images_candidate/'))
    photo_url = img['src'] if img else None
    if photo_url and not photo_url.startswith('http'):
        photo_url = BASE_URL + photo_url

    # ── Profession ──
    self_prof   = ''
    spouse_prof = ''
    for p_tag in soup.find_all('p'):
        txt = p_tag.get_text()
        if 'Self Profession:' in txt:
            m = re.search(r'Self Profession:\s*(.+?)(?:\n|Spouse|$)', txt, re.S)
            if m: self_prof = m.group(1).strip()
            m2 = re.search(r'Spouse Profession:\s*(.+?)$', txt, re.S)
            if m2: spouse_prof = m2.group(1).strip()
            break

    # ── Assets / Liabilities summary ──
    def find_summary_val(label_re):
        td = soup.find('td', string=re.compile(label_re))
        return first_bold_int(td) if td else 0

    total_assets      = find_summary_val(r'Assets:')
    total_liabilities = find_summary_val(r'Liabilities:')
    assets_cr         = to_cr(total_assets)

    # ── Movable assets breakdown ──
    ab = AssetBreakdown()
    mov_table = soup.find('table', id='movable_assets')
    movable_total = 0
    if mov_table:
        rows = mov_table.find_all('tr')
        for tr in rows:
            tds = tr.find_all('td')
            if len(tds) < 2: continue
            desc = tds[1].get_text(strip=True).lower()
            # The last td in each data row = row total (before the grand total rows)
            if 'gross total' in tds[0].get_text(strip=True).lower():
                green = tr.find('span', style=re.compile(r'color:green'))
                if green:
                    movable_total = clean_int(green.get_text())
                continue
            if 'totals' in tds[0].get_text(strip=True).lower():
                continue
            amt_td = tds[-1]
            amt    = parse_money_cell(amt_td)
            if   'cash'          in desc:  ab.cash += amt
            elif 'deposit'       in desc:  ab.bank_deposits += amt
            elif 'bond' in desc or 'share' in desc or 'debenture' in desc: ab.shares_bonds += amt
            elif 'insurance' in desc or 'lic' in desc: ab.insurance += amt
            elif 'loan' in desc or 'advance' in desc:  ab.loans_given += amt
            elif 'motor' in desc or 'vehicle' in desc: ab.vehicles += amt
            elif 'jewel' in desc:           ab.jewellery += amt
            else:                           ab.other_movable += amt

    # ── Immovable assets breakdown ──
    imm_table = soup.find('table', id='immovable_assets')
    immovable_total = 0
    if imm_table:
        for tr in imm_table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 2: continue
            first_text = tds[0].get_text(strip=True).lower()
            if 'total current market' in tds[0].get_text(strip=True).lower() if tds else '':
                green = tr.find('span', style=re.compile(r'color:green'))
                if green: immovable_total = clean_int(green.get_text())
                continue
            if 'totals' in first_text: continue
            desc = tds[1].get_text(strip=True).lower() if len(tds) > 1 else ''
            amt  = parse_money_cell(tds[-1])
            if   'agricultural' in desc:    ab.agricultural_land += amt
            elif 'non agricultural' in desc or 'non-agri' in desc: ab.non_agri_land += amt
            elif 'commercial' in desc:      ab.commercial_buildings += amt
            elif 'residential' in desc:     ab.residential_buildings += amt
            else:                           ab.other_immovable += amt

    # ── Criminal cases ──
    total_cases   = 0
    serious_cases = 0
    cases         = []
    convicted     = False
    conviction_detail = ''

    no_crime_tag = soup.find(string=re.compile(r'No criminal cases', re.I))

    if not no_crime_tag:
        # Look for the criminal details section
        # Cases are listed in a structured way — each case as a block
        # Find all case blocks between "Details of Criminal Cases" and next section
        crime_section = None
        for div in soup.find_all(['div', 'h3']):
            if 'Criminal Cases' in div.get_text():
                crime_section = div
                break

        # Count IPC/section references
        all_text = soup.get_text()
        # Pattern: "Section 302" or "IPC" markers
        ipc_matches = re.findall(
            r'(?:Section|Sec\.?|IPC|CrPC|NDPS|PC|IT Act|Arms Act)\s+[\w,/\(\)\s]+',
            all_text, re.I
        )
        # More reliable: look at the crime-o-meter gauge value in the script
        gauge_m = re.search(r"\['Cases\s*',\s*(\d+)\]", html)
        if gauge_m:
            total_cases = int(gauge_m.group(1))

        # Serious cases — look for "serious" keyword near numbers
        serious_m = re.search(
            r'serious criminal cases.*?(\d+)', all_text, re.I | re.S
        )
        if serious_m:
            serious_cases = int(serious_m.group(1))

        # Conviction
        if re.search(r'convicted|conviction', all_text, re.I):
            convicted = True
            conv_m = re.search(r'convicted[^.]*\.', all_text, re.I)
            if conv_m:
                conviction_detail = conv_m.group().strip()

        # Extract individual case entries: look for tables with IPC/section info
        for tbl in soup.find_all('table'):
            tbl_text = tbl.get_text()
            if re.search(r'IPC|Section|CrPC|NDPS', tbl_text, re.I):
                for tr in tbl.find_all('tr')[1:]:
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        case_txt = tr.get_text(separator=' ', strip=True)
                        # Extract section number from first meaningful td
                        sec_m = re.search(
                            r'(?:Section|Sec|IPC|CrPC)\s*([\w/]+)', case_txt, re.I
                        )
                        num = sec_m.group(0) if sec_m else f"Case {len(cases)+1}"
                        cases.append(CriminalCase(num=num, text=case_txt[:200]))

    # ── ITR ──
    itr_records = []
    itr_tbl = soup.find('table', id='income_tax')
    if itr_tbl:
        for tr in itr_tbl.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if len(tds) < 4: continue
            rel = tds[0].get_text(strip=True)
            pan = tds[1].get_text(strip=True) == 'Y'
            # Parse "YYYY - YYYY  **  Rs NNN" patterns from the raw HTML
            raw_html = str(tds[3])
            pairs = re.findall(
                r'(\d{4}\s*-\s*\d{4})\s*\*\*\s*<b>Rs(?:&nbsp;|&#xa0;|\s)*([\d,]+)',
                raw_html
            )
            entries = [
                ItrEntry(year=y.replace(' ', ''), income=int(a.replace(',', '')))
                for y, a in pairs
                if int(a.replace(',', '')) > 0
            ]
            if entries or pan:
                itr_records.append(ItrRecord(relation=rel, pan=pan, itr=entries))

    # ── Income Sources ──
    income_sources = {}
    inc_tbl = soup.find('table', id='incomesource')
    if inc_tbl:
        for tr in inc_tbl.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) == 2:
                k = tds[0].get_text(strip=True).lower().rstrip(':')
                v = tds[1].get_text(strip=True)
                if v and v.lower() not in ('no source', 'nil', ''):
                    income_sources[k] = v

    # ── Govt Contracts ──
    has_govt_contracts = False
    con_tbl = soup.find('table', id='contractdetails')
    if con_tbl:
        for tr in con_tbl.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) == 2:
                label = tds[0].get_text(strip=True).lower()
                val   = tds[1].get_text(strip=True).lower()
                if 'candidate' in label and val == 'yes':
                    has_govt_contracts = True
                    break

    # ── Prior Elections ──
    prior_elections = []
    for tbl in soup.find_all('table'):
        ths = [th.get_text(strip=True) for th in tbl.find_all('th')]
        if 'Declaration in' in ths:
            for tr in tbl.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 3:
                    el    = tds[0].get_text(strip=True)
                    ab_el = tds[1].find('b')
                    cas   = tds[2].get_text(strip=True)
                    if ab_el and el:
                        raw = re.sub(r'[^\d]', '', ab_el.get_text())
                        prior_elections.append(PriorElection(
                            election=el,
                            assets=int(raw) if raw else 0,
                            cases=safe_int(cas),
                        ))

    source_url = f"myneta.info/{election}/candidate.php?candidate_id={candidate_id}"

    return Candidate(
        candidate_id      = candidate_id,
        name              = name,
        constituency      = constituency,
        state             = state,
        party             = party,
        election          = election,
        is_winner         = is_winner,
        age               = age,
        parentage         = parentage,
        photo_url         = photo_url,
        self_profession   = self_prof,
        spouse_profession = spouse_prof,
        total_assets      = total_assets,
        total_liabilities = total_liabilities,
        assets_cr         = assets_cr,
        movable_total     = movable_total,
        immovable_total   = immovable_total,
        asset_breakdown   = ab,
        total_cases       = total_cases,
        serious_cases     = serious_cases,
        cases             = cases,
        convicted         = convicted,
        conviction_detail = conviction_detail,
        income_sources    = income_sources,
        itr_records       = itr_records,
        has_govt_contracts= has_govt_contracts,
        prior_elections   = prior_elections,
        source_url        = source_url,
    )


# ── CONSTITUENCY LIST PARSER ──────────────────────────────────────────────────

def parse_constituency_list(html: str, election: str) -> list[dict]:
    """Returns list of {constituency_id, name, state_name}."""
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        m = re.search(
            rf'{re.escape(election)}/index\.php\?action=show_candidates&constituency_id=(\d+)',
            href
        )
        if m:
            results.append({
                'constituency_id': int(m.group(1)),
                'name': a.get_text(strip=True),
            })
    # Deduplicate
    seen = set()
    unique = []
    for r in results:
        if r['constituency_id'] not in seen:
            seen.add(r['constituency_id'])
            unique.append(r)
    return unique


def parse_candidates_in_constituency(html: str) -> list[int]:
    """Returns list of candidate_ids from a constituency page."""
    soup = BeautifulSoup(html, 'html.parser')
    ids = []
    for a in soup.find_all('a', href=re.compile(r'candidate\.php\?candidate_id=\d+')):
        m = re.search(r'candidate_id=(\d+)', a['href'])
        if m:
            ids.append(int(m.group(1)))
    seen = set()
    return [x for x in ids if not (x in seen or seen.add(x))]


# ── ASYNC FETCHER ─────────────────────────────────────────────────────────────

async def fetch(client: httpx.AsyncClient, url: str, retries=3) -> Optional[str]:
    for attempt in range(retries):
        try:
            r = await client.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.text
            log.warning(f"HTTP {r.status_code} for {url}")
        except Exception as e:
            log.warning(f"Attempt {attempt+1} failed for {url}: {e}")
            await asyncio.sleep(2 ** attempt)
    return None


async def fetch_all(client, urls: list[str]) -> list[Optional[str]]:
    """Fetch in batches with rate limiting."""
    results = []
    sem = asyncio.Semaphore(CONCURRENCY)

    async def bounded_fetch(url):
        async with sem:
            result = await fetch(client, url)
            await asyncio.sleep(DELAY_BETWEEN / CONCURRENCY)
            return result

    tasks = [bounded_fetch(u) for u in urls]
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        result = await coro
        results.append(result)
        if i % 20 == 0:
            log.info(f"  fetched {i}/{len(urls)}")
    return results


# ── SERIALISATION ─────────────────────────────────────────────────────────────

def candidate_to_mp_record(c: Candidate) -> dict:
    """Shape for mps.json members array — matches dossier.html expectations."""
    return {
        "id":             c.candidate_id,
        "name":           c.name,
        "constituency":   c.constituency,
        "state":          c.state,
        "party":          c.party,
        "election":       c.election,
        "is_winner":      c.is_winner,
        "age":            c.age,
        "parentage":      c.parentage,
        "photo_url":      c.photo_url,
        "self_profession":c.self_profession,
        "spouse_profession": c.spouse_profession,
        "total_assets":   c.total_assets,
        "total_liabilities": c.total_liabilities,
        "assets_cr":      c.assets_cr,
        "movable_total":  c.movable_total,
        "immovable_total":c.immovable_total,
        "has_govt_contracts": c.has_govt_contracts,
        "income_sources": c.income_sources,
    }

def candidate_to_criminal_record(c: Candidate) -> dict:
    """Shape for criminal_records.json — matches dossier.html crimRec."""
    return {
        "candidate_id":      c.candidate_id,
        "mp_id":             c.candidate_id,
        "name":              c.name,
        "total_cases":       c.total_cases,
        "serious_cases":     c.serious_cases,
        "cases":             [{"num": x.num, "text": x.text} for x in c.cases],
        "convicted":         c.convicted,
        "conviction_detail": c.conviction_detail,
        "assets_cr":         c.assets_cr,
        "total_assets":      c.total_assets,
        "total_liabilities": c.total_liabilities,
        "movable_total":     c.movable_total,
        "immovable_total":   c.immovable_total,
        "asset_breakdown":   asdict(c.asset_breakdown),
        "itr_records": [
            {
                "relation": r.relation,
                "pan": r.pan,
                "itr": [asdict(e) for e in r.itr],
            }
            for r in c.itr_records
        ],
        "prior_elections": [asdict(p) for p in c.prior_elections],
        "source_url": c.source_url,
    }


# ── MAIN SCRAPE FLOW ──────────────────────────────────────────────────────────

async def scrape_election(election: str, limit: Optional[int] = None,
                          single_candidate_id: Optional[int] = None):
    OUTPUT_DIR.mkdir(exist_ok=True)
    checkpoint_file = OUTPUT_DIR / f"{election}_checkpoint.json"

    # Load checkpoint (resume interrupted runs)
    done_ids: set[int] = set()
    all_candidates: list[Candidate] = []
    if checkpoint_file.exists():
        saved = json.loads(checkpoint_file.read_text())
        done_ids = set(saved.get("done_ids", []))
        log.info(f"Resuming from checkpoint: {len(done_ids)} candidates already done")

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:

        # ── Single candidate debug mode ──
        if single_candidate_id:
            url = f"{BASE_URL}/{election}/candidate.php?candidate_id={single_candidate_id}"
            html = await fetch(client, url)
            if not html:
                log.error("Failed to fetch candidate page")
                return
            c = parse_candidate_page(html, single_candidate_id, election)
            if c:
                print(json.dumps(candidate_to_criminal_record(c), indent=2, ensure_ascii=False))
            else:
                log.error("Failed to parse candidate page")
            return

        # ── Step 1: get all constituencies ──
        log.info(f"Fetching constituency list for {election}...")
        index_html = await fetch(client, f"{BASE_URL}/{election}/")
        if not index_html:
            log.error("Could not fetch election index page")
            return
        constituencies = parse_constituency_list(index_html, election)
        log.info(f"Found {len(constituencies)} constituencies")

        # ── Step 2: get candidate IDs per constituency ──
        log.info("Fetching candidate lists per constituency...")
        cons_urls = [
            f"{BASE_URL}/{election}/index.php?action=show_candidates&constituency_id={c['constituency_id']}"
            for c in constituencies
        ]
        cons_htmls = await fetch_all(client, cons_urls)

        candidate_ids: list[int] = []
        for html in cons_htmls:
            if html:
                candidate_ids.extend(parse_candidates_in_constituency(html))

        # Deduplicate
        seen = set()
        candidate_ids = [x for x in candidate_ids if not (x in seen or seen.add(x))]
        log.info(f"Found {len(candidate_ids)} unique candidates")

        if limit:
            candidate_ids = candidate_ids[:limit]
            log.info(f"Limiting to {limit} candidates")

        # Filter already done
        todo = [cid for cid in candidate_ids if cid not in done_ids]
        log.info(f"Fetching {len(todo)} candidate pages (skipping {len(done_ids)} cached)")

        # ── Step 3: fetch + parse candidate pages in batches ──
        BATCH = 20
        for batch_start in range(0, len(todo), BATCH):
            batch = todo[batch_start: batch_start + BATCH]
            urls  = [
                f"{BASE_URL}/{election}/candidate.php?candidate_id={cid}"
                for cid in batch
            ]
            htmls = await fetch_all(client, urls)

            for cid, html in zip(batch, htmls):
                if not html:
                    log.warning(f"  No HTML for candidate_id={cid}")
                    continue
                c = parse_candidate_page(html, cid, election)
                if c:
                    all_candidates.append(c)
                    done_ids.add(cid)
                else:
                    log.warning(f"  Parse failed for candidate_id={cid}")

            # Checkpoint after each batch
            checkpoint_file.write_text(json.dumps({
                "election": election,
                "done_ids": list(done_ids),
            }))
            log.info(f"  Batch done. Total parsed so far: {len(all_candidates)}")
            await asyncio.sleep(DELAY_BETWEEN)

    # ── Step 4: Build and write output JSON ──
    log.info("Writing output files...")

    winners    = [c for c in all_candidates if c.is_winner]
    all_mps    = winners if winners else all_candidates  # fallback if winners not flagged

    parties_dict = {}
    for c in all_candidates:
        if c.party not in parties_dict:
            parties_dict[c.party] = party_meta(c.party)

    mps_json = {
        "election": election,
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_candidates": len(all_candidates),
        "total_winners": len(winners),
        "members": [candidate_to_mp_record(c) for c in all_candidates],
        "parties": parties_dict,
    }

    criminal_json = {
        "election": election,
        "scraped_at": mps_json["scraped_at"],
        "records": [candidate_to_criminal_record(c) for c in all_candidates],
    }

    mps_out  = OUTPUT_DIR / "mps.json"
    crim_out = OUTPUT_DIR / "criminal_records.json"

    mps_out.write_text(json.dumps(mps_json, indent=2, ensure_ascii=False))
    crim_out.write_text(json.dumps(criminal_json, indent=2, ensure_ascii=False))

    log.info(f"✅  Wrote {mps_out}  ({len(all_candidates)} candidates)")
    log.info(f"✅  Wrote {crim_out}")

    # Summary stats
    with_crimes  = sum(1 for c in all_candidates if c.total_cases > 0)
    crorepatis   = sum(1 for c in all_candidates if c.total_assets >= 1e7)
    log.info(f"\n── Summary ────────────────────────────────")
    log.info(f"Total candidates parsed : {len(all_candidates)}")
    log.info(f"Winners                 : {len(winners)}")
    log.info(f"With criminal cases     : {with_crimes}")
    log.info(f"Crorepatis              : {crorepatis}")
    log.info(f"───────────────────────────────────────────")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NetaStats myneta.info scraper")
    parser.add_argument('--election',      default='LokSabha2024',
                        help='Election slug, e.g. LokSabha2024, Karnataka2023')
    parser.add_argument('--limit',         type=int, default=None,
                        help='Max candidates to scrape (for testing)')
    parser.add_argument('--candidate-id',  type=int, default=None,
                        help='Scrape a single candidate and print JSON (debug)')
    args = parser.parse_args()

    asyncio.run(scrape_election(
        election             = args.election,
        limit                = args.limit,
        single_candidate_id  = args.candidate_id,
    ))


if __name__ == '__main__':
    main()
