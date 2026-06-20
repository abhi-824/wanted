"""
Build india_constituencies.svg from Wahlkreise source art + GeoJSON boundaries.

Run: python3 scripts/script.py [path/to/Wahlkreise_in_Indien.svg]
Output: india_constituencies.svg

Names are assigned by matching each SVG polygon centroid to the nearest
parliamentary constituency in DataMeet's india_pc_2019_simplified.geojson —
not by polygon order in the source file.
"""
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scraps" / "ind.svg"
OUTPUT_FILE = ROOT / "india_constituencies.svg"
GEOJSON_FILE = ROOT / "scraps" / "india_pc_2019_simplified.geojson"
MPS_FILE = ROOT / "data" / "mps.json"
VIEWBOX = "0 0 1449.064 1534.05"

# GeoJSON pc_name (+ state) → app/API constituency name
NAME_ALIASES = {
    ("Firozepur", "Punjab"): "Firozpur",
    ("Nainital-Udhamsingh Nagar", "Uttarakhand"): "Nainital-Udham Singh Nagar",
    ("Fatehpur", "Uttar Pradesh"): "Fatehpur UP",
    ("Hamirpur", "Uttar Pradesh"): "Hamirpur HP",
    ("Kushi Nagar", "Uttar Pradesh"): "Kushinagar",
    ("Paschim Champaran", "Bihar"): "Champaran West",
    ("Purvi Champaran", "Bihar"): "Champaran East",
    ("Jaynagar", "West Bengal"): "Joynagar",
    ("Sreerampur", "West Bengal"): "Srerampur",
    ("Arambagh", "West Bengal"): "Arambag",
    ("Surguja", "Chhattisgarh"): "Sarguja",
    ("Janjgir", "Chhattisgarh"): "Janjgir-Champa",
    ("Mandsaur", "Madhya Pradesh"): "Mandsour",
    ("Kachchh", "Gujarat"): "Kutch",
    ("Peddapalli", "Telangana"): "Peddapalle",
    ("Ahmednagar", "Maharashtra"): "Ahmadnagar",
    ("Mahabubnagar", "Telangana"): "Mahbubnagar",
    ("Bhuvanagiri", "Telangana"): "Bhongir",
    ("Araku", "Andhra Pradesh"): "Aruku",
    ("Rajahmundry", "Andhra Pradesh"): "Rajahmundry",
    ("Anantapuramu", "Andhra Pradesh"): "Anantapur",
    ("Rajampet", "Andhra Pradesh"): "Rajampet",
    ("Bijapur", "Karnataka"): "Bijapur KA",
    ("Udupi Chikmagalur", "Karnataka"): "Udupi-Chikmagalur",
    ("Haasan", "Karnataka"): "Hassan",
    ("Vadakara", "Kerala"): "Vatakara",
    ("Mavelikara", "Kerala"): "Mavelikkara",
    ("Mayiladuturai", "Tamil Nadu"): "Mayiladuthurai",
    ("Tenkasi", "Tamil Nadu"): "Tenkasi",
    ("Kanyakumari", "Tamil Nadu"): "Kanniyakumari",
    ("Chikodi", "Karnataka"): "Chikkodi",
    ("Belagavi", "Karnataka"): "Belgaum",
    ("Chikballapur", "Karnataka"): "Chikkaballapur",
    ("Kodarma", "Jharkhand"): "Koderma",
    ("Anantnag", "Jammu & Kashmir"): "Anantnag-Rajouri",
    ("Faizabad", "Uttar Pradesh"): "Ayodhya",
    ("Allahabad", "Uttar Pradesh"): "Prayagraj",
}

PARTY_DATA = {
    "Varanasi":           {"state": "Uttar Pradesh", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Narendra Modi"},
    "Rae Bareli":         {"state": "Uttar Pradesh", "party": "INC", "color": "#1a7fe0", "coalition": "INDIA", "mp": "Rahul Gandhi"},
    "Wayanad":            {"state": "Kerala", "party": "INC", "color": "#1a7fe0", "coalition": "INDIA", "mp": "Priyanka Gandhi Vadra"},
    "Purnia":             {"state": "Bihar", "party": "INC", "color": "#1a7fe0", "coalition": "INDIA", "mp": "Rajesh Ranjan"},
    "New Delhi":          {"state": "Delhi", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Bansuri Swaraj"},
    "Hyderabad":          {"state": "Telangana", "party": "AIMIM", "color": "#10b981", "coalition": "Other", "mp": "Asaduddin Owaisi"},
    "Mumbai North":       {"state": "Maharashtra", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Piyush Goyal"},
    "Bangalore South":    {"state": "Karnataka", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Tejasvi Surya"},
    "Thiruvananthapuram": {"state": "Kerala", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Rajeev Chandrasekhar"},
    "Gandhinagar":        {"state": "Gujarat", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Amit Shah"},
    "Lucknow":            {"state": "Uttar Pradesh", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Rajnath Singh"},
    "Patna Sahib":        {"state": "Bihar", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Ravi Shankar Prasad"},
    "Amethi":             {"state": "Uttar Pradesh", "party": "INC", "color": "#1a7fe0", "coalition": "INDIA", "mp": "Kishori Lal Sharma"},
    "Jadavpur":           {"state": "West Bengal", "party": "TMC", "color": "#8b5cf6", "coalition": "Other", "mp": "Saayoni Ghosh"},
    "Kolkata Uttar":      {"state": "West Bengal", "party": "TMC", "color": "#8b5cf6", "coalition": "Other", "mp": "Sudip Bandyopadhyay"},
    "Bhopal":             {"state": "Madhya Pradesh", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Alok Sharma"},
    "Indore":             {"state": "Madhya Pradesh", "party": "BJP", "color": "#e8630a", "coalition": "NDA", "mp": "Shankar Lalwani"},
}

PALETTE = [
    "#1a4878", "#0d2640", "#16304e", "#1e4870", "#1a5c78", "#235e40",
    "#1a5c38", "#3a1a6e", "#7a3000", "#0a3d62", "#1a3a5c", "#2a5c1a",
    "#5c1a1a", "#1a5c5c", "#3a1a5c", "#1a3a1a", "#3a3a1a", "#1a3a3a",
    "#2a3a1a", "#3a2a1a", "#1a2a3a", "#4a2a00", "#3a1a00", "#5c2a00",
    "#005858", "#5a0000", "#006070", "#3a0060", "#604000", "#005a40",
    "#5a0050", "#004a50", "#004a6a", "#005c3a", "#003a5a",
]


def xe(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def norm_key(s):
    return re.sub(r"\s+", " ", s.lower().replace("(st)", "").replace("(sc)", "").replace("&", "and").strip())


def title_name(s):
    """Title-case while preserving parenthetical reservation tags."""
    s = re.sub(r"\s+", " ", s.strip())
    if not s:
        return s
    parts = re.split(r"(\([^)]*\))", s)
    out = []
    for part in parts:
        if part.startswith("("):
            out.append(part.upper())
        else:
            out.append(part.title())
    return "".join(out)


def load_mps_lookup():
    """state_norm + pc_norm → display constituency name from scraped MP data."""
    lookup = {}
    if not MPS_FILE.exists():
        return lookup
    with MPS_FILE.open(encoding="utf-8") as f:
        mps = json.load(f)
    for row in mps:
        text = row.get("voter_constituency") or ""
        match = re.search(r"Home\s*→\s*Lok Sabha \d+\s*→\s*(.+?)\s*→\s*(.+?)\s*→", text)
        if not match:
            continue
        state = match.group(1).strip()
        const = title_name(match.group(2).strip())
        lookup[(norm_key(state), norm_key(const))] = const
        lookup[(norm_key(state), norm_key(match.group(2).strip()))] = const
    return lookup


def resolve_name(pc_name, st_name, mps_lookup):
    alias = NAME_ALIASES.get((pc_name, st_name))
    if alias:
        return alias

    mps_hit = mps_lookup.get((norm_key(st_name), norm_key(pc_name)))
    if mps_hit:
        return mps_hit

    return title_name(pc_name)


def geo_centroid(geom):
    coords = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            coords.append(c)
        else:
            for item in c:
                walk(item)

    walk(geom["coordinates"])
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def svg_centroid(shape_type, el):
    if shape_type == "polygon":
        nums = [float(x) for x in re.split(r"[\s,]+", (el.get("points") or "").strip()) if x]
    else:
        nums = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", el.get("d") or "")]
    xs = nums[0::2]
    ys = nums[1::2]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def load_geo_features():
    with GEOJSON_FILE.open(encoding="utf-8") as f:
        geo = json.load(f)
    feats = []
    for feat in geo["features"]:
        props = feat["properties"]
        lon, lat = geo_centroid(feat["geometry"])
        feats.append({
            "lon": lon,
            "lat": lat,
            "pc_name": props.get("pc_name", ""),
            "st_name": props.get("st_name", ""),
        })
    return feats


def rough_project(lon, lat):
    lon0, lon1 = 68.0, 98.0
    lat0, lat1 = 6.0, 37.0
    x = (lon - lon0) / (lon1 - lon0) * 1449.064
    y = (lat1 - lat) / (lat1 - lat0) * 1534.05
    return x, y


def match_shapes_to_geo(svg_centroids, geo_feats):
    """Greedy nearest-neighbour assignment in projected lon/lat space."""
    used = set()
    matches = []
    for i, (sx, sy) in enumerate(svg_centroids):
        best_j = None
        best_d = 1e18
        for j, g in enumerate(geo_feats):
            if j in used:
                continue
            px, py = rough_project(g["lon"], g["lat"])
            d = (px - sx) ** 2 + (py - sy) ** 2
            if d < best_d:
                best_d = d
                best_j = j
        used.add(best_j)
        matches.append((i, geo_feats[best_j], best_d ** 0.5))
    return matches


def parse_svg(filepath):
    with filepath.open("r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    raw = re.sub(r"&(?!(?:#\d+|#x[\da-fA-F]+|[a-zA-Z]\w*);)", "&amp;", raw)
    root = ET.fromstring(raw)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    polys = root.findall(".//svg:polygon", ns)
    paths = root.findall(".//svg:path", ns)
    filled_paths = [
        p for p in paths
        if (p.get("d") or "").strip() and (p.get("fill") or "").strip().lower() not in ("", "none")
    ]
    # Source art has 481 polygons + 61 filled paths = 542 seats
    needed = max(0, 542 - len(polys))
    selected_paths = filled_paths[:needed]
    shapes = [("polygon", p) for p in polys] + [("path", p) for p in selected_paths]
    print(
        f"Found {len(polys)} polygons, {len(filled_paths)} filled paths; "
        f"using {len(selected_paths)} paths (total shapes: {len(shapes)})"
    )
    return shapes


def get_fill(name, i):
    return PARTY_DATA[name]["color"] if name in PARTY_DATA else PALETTE[i % len(PALETTE)]


def build(shapes, names, states):
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" id="india-constituencies"',
        f'     viewBox="{VIEWBOX}" style="width:100%;height:100%;display:block">',
        "  <desc>India Lok Sabha Constituencies — 543 seats</desc>",
        '  <g id="constituencies">',
    ]
    for i, (shape_type, p) in enumerate(shapes):
        name = names[i]
        state = states[i]
        meta = PARTY_DATA.get(name, {})
        if not meta.get("state") and state:
            meta = {**meta, "state": state}
        fill = get_fill(name, i)
        common = (
            f'class="constituency" id="c{i + 1}"'
            f' data-index="{i + 1}" data-name="{xe(name)}"'
            f' data-state="{xe(meta.get("state", state))}"'
            f' data-party="{xe(meta.get("party", ""))}"'
            f' data-color="{fill}"'
            f' data-coalition="{xe(meta.get("coalition", ""))}"'
            f' data-mp="{xe(meta.get("mp", ""))}"'
            f' fill="{fill}"'
        )
        if shape_type == "polygon":
            pts = re.sub(r"\s+", " ", (p.get("points") or "").strip())
            lines.append(f'    <polygon {common} points="{pts}"/>')
        else:
            path_d = re.sub(r"\s+", " ", (p.get("d") or "").strip())
            lines.append(f'    <path {common} d="{path_d}"/>')
    lines += ["  </g>", "</svg>"]
    return "\n".join(lines)


def main():
    print(f"Reading: {INPUT_FILE}")
    if not GEOJSON_FILE.exists():
        print(f"ERROR: GeoJSON not found at {GEOJSON_FILE}")
        print("Download india_pc_2019_simplified.geojson from DataMeet maps repo.")
        return 1

    try:
        shapes = parse_svg(INPUT_FILE)
    except FileNotFoundError:
        print(f"ERROR: '{INPUT_FILE}' not found.")
        return 1
    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        return 1

    if not shapes:
        print("No map shapes found — check SVG structure.")
        return 1

    svg_centroids = [svg_centroid(st, el) for st, el in shapes]
    geo_feats = load_geo_features()
    mps_lookup = load_mps_lookup()
    matches = match_shapes_to_geo(svg_centroids, geo_feats)

    names = []
    states = []
    for i, geo, dist in matches:
        name = resolve_name(geo["pc_name"], geo["st_name"], mps_lookup)
        names.append(name)
        states.append(geo["st_name"])

    avg_dist = sum(m[2] for m in matches) / len(matches)
    print(f"Matched {len(matches)} shapes to GeoJSON (mean centroid error: {avg_dist:.0f}px)")

    bihar = sum(
        1 for (_, g, _), (sx, sy) in zip(matches, svg_centroids)
        if g["st_name"] == "Bihar" and 650 <= sx <= 950 and 500 <= sy <= 750
    )
    print(f"Bihar seats placed in Bihar region: {bihar}/40")

    svg = build(shapes, names, states)
    OUTPUT_FILE.write_text(svg, encoding="utf-8")
    print(f"Written: {OUTPUT_FILE}  ({len(svg) // 1024} KB, {len(shapes)} constituencies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
