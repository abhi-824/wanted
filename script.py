"""
extract_constituencies.py
Run: python3 extract_constituencies.py Wahlkreise_in_Indien.svg
Output: india_constituencies.svg — 543 tagged polygons, ready to embed.
No third-party libraries needed.
"""
import sys, re
from xml.etree import ElementTree as ET

INPUT_FILE  = sys.argv[1] if len(sys.argv) > 1 else "Wahlkreise_in_Indien.svg"
OUTPUT_FILE = "india_constituencies.svg"
VIEWBOX     = "0 0 1449.064 1534.05"

def xe(s):
    """Escape string for XML attribute."""
    return s.replace("&","&amp;").replace('"',"&quot;").replace("<","&lt;").replace(">","&gt;")

NAMES = [
    "Baramulla","Srinagar","Anantnag-Rajouri","Udhampur","Jammu",
    "Ladakh",
    "Kangra","Mandi","Hamirpur","Shimla",
    "Gurdaspur","Amritsar","Khadoor Sahib","Jalandhar","Hoshiarpur",
    "Anandpur Sahib","Ludhiana","Fatehgarh Sahib","Faridkot","Firozpur",
    "Bathinda","Sangrur","Patiala",
    "Chandigarh",
    "Tehri Garhwal","Garhwal","Almora","Nainital-Udham Singh Nagar","Haridwar",
    "Ambala","Kurukshetra","Sirsa","Hisar","Karnal","Sonipat",
    "Rohtak","Bhiwani-Mahendragarh","Gurgaon","Faridabad",
    "Chandni Chowk","North East Delhi","East Delhi","New Delhi",
    "North West Delhi","West Delhi","South Delhi",
    "Ganganagar","Bikaner","Churu","Jhunjhunu","Sikar","Jaipur Rural",
    "Jaipur","Alwar","Bharatpur","Karauli-Dholpur","Dausa",
    "Tonk-Sawai Madhopur","Ajmer","Nagaur","Barmer","Jalore",
    "Udaipur","Banswara","Chittorgarh","Rajsamand","Bhilwara",
    "Kota","Jhalawar-Baran","Dungarpur","Pali",
    "Saharanpur","Kairana","Muzaffarnagar","Bijnor","Nagina",
    "Moradabad","Rampur","Sambhal","Amroha","Meerut",
    "Baghpat","Ghaziabad","Gautam Buddha Nagar","Bulandshahr","Aligarh",
    "Hathras","Mathura","Agra","Fatehpur Sikri","Firozabad",
    "Mainpuri","Etah","Badaun","Aonla","Bareilly",
    "Pilibhit","Shahjahanpur","Kheri","Dhaurahra","Sitapur",
    "Hardoi","Misrikh","Unnao","Mohanlalganj","Lucknow",
    "Rae Bareli","Amethi","Sultanpur","Pratapgarh","Farrukhabad",
    "Etawah","Kannauj","Kanpur","Akbarpur","Jhansi",
    "Hamirpur HP","Banda","Fatehpur UP","Kaushambi","Allahabad",
    "Phulpur","Ambedkar Nagar","Shrawasti","Gonda","Kaiserganj",
    "Bahraich","Sitapur 2","Dhaurahra 2","Hardoi 2","Barabanki",
    "Faizabad","Bahraich 2","Gonda 2","Domariyaganj","Basti",
    "Sant Kabir Nagar","Lalganj","Azamgarh","Ghosi","Salempur",
    "Ballia","Jaunpur","Machhlishahr","Ghazipur","Chandauli",
    "Varanasi","Bhadohi","Mirzapur","Robertsganj",
    "Valmiki Nagar","Sitamarhi","Jhanjharpur","Supaul","Araria",
    "Kishanganj","Katihar","Purnia","Bhagalpur","Banka",
    "Munger","Nalanda","Patna Sahib","Pataliputra","Arrah",
    "Buxar","Sasaram","Karakat","Jahanabad","Aurangabad",
    "Gaya","Nawada","Jamui","Darbhanga","Muzaffarpur",
    "Vaishali","Gopalganj","Siwan","Maharajganj","Saran",
    "Hajipur","Ujiarpur","Samastipur","Begusarai","Khagaria",
    "Madhubani","Sheohar","Sitamarhi 2","Champaran East","Champaran West",
    "Sikkim",
    "Arunachal West","Arunachal East",
    "Nagaland",
    "Inner Manipur","Outer Manipur",
    "Mizoram",
    "Tripura East","Tripura West",
    "Shillong","Tura",
    "Karimganj","Silchar","Autonomous District","Dhubri","Kokrajhar",
    "Barpeta","Gauhati","Mangaldoi","Nowgong","Kaliabor",
    "Jorhat","Dibrugarh","Lakhimpur","Tezpur",
    "Cooch Behar","Alipurduars","Jalpaiguri","Darjeeling","Raiganj",
    "Balurghat","Maldaha Uttar","Maldaha Dakshin","Jangipur","Baharampur",
    "Murshidabad","Krishnanagar","Ranaghat","Bangaon","Barrackpore",
    "Dum Dum","Barasat","Basirhat","Joynagar","Mathurapur",
    "Diamond Harbour","Jadavpur","Kolkata Dakshin","Kolkata Uttar","Howrah",
    "Uluberia","Srerampur","Hooghly","Arambag","Tamluk",
    "Kanthi","Ghatal","Jhargram","Medinipur","Purulia",
    "Bankura","Bishnupur","Bardhaman Purba","Bardhaman-Durgapur","Asansol",
    "Bolpur","Birbhum",
    "Rajmahal","Dumka","Godda","Chatra","Koderma",
    "Giridih","Dhanbad","Ranchi","Jamshedpur","Singhbhum",
    "Khunti","Lohardaga","Palamu","Hazaribagh",
    "Bargarh","Sundargarh","Sambalpur","Keonjhar","Mayurbhanj",
    "Balasore","Bhadrak","Jajpur","Dhenkanal","Bolangir",
    "Kandhamal","Cuttack","Kendrapara","Jagatsinghpur","Puri",
    "Bhubaneswar","Aska","Berhampur","Koraput","Nabarangpur","Kalahandi",
    "Sarguja","Raigarh","Janjgir-Champa","Korba","Bilaspur",
    "Rajnandgaon","Durg","Raipur","Mahasamund","Bastar","Kanker",
    "Morena","Bhind","Gwalior","Guna","Sagar",
    "Tikamgarh","Damoh","Khajuraho","Satna","Rewa",
    "Sidhi","Shahdol","Jabalpur","Mandla","Balaghat",
    "Chhindwara","Hoshangabad","Vidisha","Bhopal","Rajgarh",
    "Dewas","Ujjain","Mandsour","Ratlam","Dhar",
    "Indore","Khargone","Khandwa","Betul",
    "Kutch","Banaskantha","Patan","Mahesana","Sabarkantha",
    "Gandhinagar","Ahmedabad East","Ahmedabad West","Surendranagar","Rajkot",
    "Porbandar","Jamnagar","Junagadh","Amreli","Bhavnagar",
    "Anand","Kheda","Panchmahal","Dahod","Vadodara",
    "Chhota Udaipur","Bharuch","Bardoli","Surat","Navsari","Valsad",
    "Daman and Diu","Dadra and Nagar Haveli",
    "Nandurbar","Dhule","Jalgaon","Raver","Buldhana",
    "Akola","Amravati","Wardha","Ramtek","Nagpur",
    "Bhandara-Gondiya","Gadchiroli-Chimur","Chandrapur","Yavatmal-Washim","Hingoli",
    "Nanded","Latur","Osmanabad","Solapur","Madha",
    "Sangli","Satara","Ratnagiri-Sindhudurg","Kolhapur","Hatkanangle",
    "Shirur","Baramati","Pune","Shirdi","Nashik",
    "Dindori","Palghar","Bhiwandi","Kalyan","Thane",
    "Mumbai North","Mumbai North West","Mumbai North East","Mumbai North Central",
    "Mumbai South Central","Mumbai South","Raigad","Maval","Ahmadnagar",
    "Aurangabad MH","Jalna","Parbhani","Beed",
    "North Goa","South Goa",
    "Chikkodi","Belgaum","Bagalkot","Bijapur KA","Gulbarga",
    "Raichur","Bidar","Koppal","Bellary","Haveri",
    "Dharwad","Uttara Kannada","Davangere","Shimoga","Udupi-Chikmagalur",
    "Hassan","Dakshina Kannada","Chitradurga","Tumkur","Mandya",
    "Mysore","Chamarajanagar","Bangalore Rural","Bangalore North","Bangalore Central",
    "Bangalore South","Chikkaballapur","Kolar",
    "Adilabad","Peddapalle","Karimnagar","Nizamabad","Zahirabad",
    "Medak","Malkajgiri","Secunderabad","Hyderabad","Chevella",
    "Mahbubnagar","Nagarkurnool","Nalgonda","Bhongir","Warangal",
    "Mahabubabad","Khammam",
    "Aruku","Srikakulam","Vizianagaram","Visakhapatnam","Anakapalli",
    "Kakinada","Amalapuram","Rajampet AP","Narsapuram","Eluru",
    "Machilipatnam","Vijayawada","Guntur","Narasaraopet","Bapatla",
    "Ongole","Nandyal","Kurnool","Anantapur","Hindupur",
    "Kadapa","Nellore","Tirupati","Rajampet 2","Chittoor",
    "Kasaragod","Kannur","Vatakara","Wayanad","Kozhikode",
    "Malappuram","Ponnani","Palakkad","Alathur","Thrissur",
    "Chalakudy","Ernakulam","Idukki","Kottayam","Alappuzha",
    "Mavelikkara","Pathanamthitta","Kollam","Attingal","Thiruvananthapuram",
    "Lakshadweep",
    "Thiruvallur","Chennai North","Chennai South","Chennai Central","Sriperumbudur",
    "Kancheepuram","Arakkonam","Vellore","Krishnagiri","Dharmapuri",
    "Tiruvannamalai","Arani","Viluppuram","Kallakurichi","Salem",
    "Namakkal","Erode","Tiruppur","Nilgiris","Coimbatore",
    "Pollachi","Dindigul","Karur","Tiruchirappalli","Perambalur",
    "Cuddalore","Chidambaram","Mayiladuthurai","Nagapattinam","Thanjavur",
    "Sivaganga","Madurai","Theni","Virudhunagar","Ramanathapuram",
    "Thoothukudi","Tirunelveli","Kanniyakumari","Vellore 2",
    "Puducherry",
    "Andaman and Nicobar Islands",
]

PARTY_DATA = {
    "Varanasi":           {"state":"Uttar Pradesh","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Narendra Modi"},
    "Rae Bareli":         {"state":"Uttar Pradesh","party":"INC","color":"#1a7fe0","coalition":"INDIA","mp":"Rahul Gandhi"},
    "Wayanad":            {"state":"Kerala","party":"INC","color":"#1a7fe0","coalition":"INDIA","mp":"Priyanka Gandhi Vadra"},
    "Purnia":             {"state":"Bihar","party":"INC","color":"#1a7fe0","coalition":"INDIA","mp":"Rajesh Ranjan"},
    "New Delhi":          {"state":"Delhi","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Bansuri Swaraj"},
    "Hyderabad":          {"state":"Telangana","party":"AIMIM","color":"#10b981","coalition":"Other","mp":"Asaduddin Owaisi"},
    "Mumbai North":       {"state":"Maharashtra","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Piyush Goyal"},
    "Bangalore South":    {"state":"Karnataka","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Tejasvi Surya"},
    "Thiruvananthapuram": {"state":"Kerala","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Rajeev Chandrasekhar"},
    "Gandhinagar":        {"state":"Gujarat","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Amit Shah"},
    "Lucknow":            {"state":"Uttar Pradesh","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Rajnath Singh"},
    "Patna Sahib":        {"state":"Bihar","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Ravi Shankar Prasad"},
    "Amethi":             {"state":"Uttar Pradesh","party":"INC","color":"#1a7fe0","coalition":"INDIA","mp":"Kishori Lal Sharma"},
    "Jadavpur":           {"state":"West Bengal","party":"TMC","color":"#8b5cf6","coalition":"Other","mp":"Saayoni Ghosh"},
    "Kolkata Uttar":      {"state":"West Bengal","party":"TMC","color":"#8b5cf6","coalition":"Other","mp":"Sudip Bandyopadhyay"},
    "Bhopal":             {"state":"Madhya Pradesh","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Alok Sharma"},
    "Indore":             {"state":"Madhya Pradesh","party":"BJP","color":"#e8630a","coalition":"NDA","mp":"Shankar Lalwani"},
}

PALETTE = [
    "#1a4878","#0d2640","#16304e","#1e4870","#1a5c78","#235e40",
    "#1a5c38","#3a1a6e","#7a3000","#0a3d62","#1a3a5c","#2a5c1a",
    "#5c1a1a","#1a5c5c","#3a1a5c","#1a3a1a","#3a3a1a","#1a3a3a",
    "#2a3a1a","#3a2a1a","#1a2a3a","#4a2a00","#3a1a00","#5c2a00",
    "#005858","#5a0000","#006070","#3a0060","#604000","#005a40",
    "#5a0050","#004a50","#004a6a","#005c3a","#003a5a",
]

def get_fill(name, i):
    return PARTY_DATA[name]["color"] if name in PARTY_DATA else PALETTE[i % len(PALETTE)]

def parse_svg(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    # Fix bare & not part of a valid entity reference
    raw = re.sub(r'&(?!(?:#\d+|#x[\da-fA-F]+|[a-zA-Z]\w*);)', '&amp;', raw)
    root = ET.fromstring(raw)
    ns = {"svg": "http://www.w3.org/2000/svg"}
    polys = root.findall(".//svg:polygon", ns)
    paths = root.findall(".//svg:path", ns)

    # Some constituencies in source art are encoded as filled paths (not polygons).
    # Keep only filled paths with geometry and append enough to cover the names list.
    filled_paths = [
        p for p in paths
        if (p.get("d") or "").strip() and (p.get("fill") or "").strip().lower() not in ("", "none")
    ]

    needed = max(0, len(NAMES) - len(polys))
    selected_paths = filled_paths[:needed]

    shapes = [("polygon", p) for p in polys] + [("path", p) for p in selected_paths]
    print(
        f"Found {len(polys)} polygons, {len(filled_paths)} filled paths; "
        f"using {len(selected_paths)} paths (total shapes: {len(shapes)})"
    )
    return shapes

def build(shapes):
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" id="india-constituencies"',
        f'     viewBox="{VIEWBOX}" style="width:100%;height:100%;display:block">',
        f'  <desc>India Lok Sabha Constituencies — 543 seats</desc>',
        f'  <g id="constituencies">',
    ]
    for i, (shape_type, p) in enumerate(shapes):
        name = NAMES[i] if i < len(NAMES) else f"Constituency {i+1}"
        d    = PARTY_DATA.get(name, {})
        fill = get_fill(name, i)
        common = (
            f'class="constituency" id="c{i+1}"'
            f' data-index="{i+1}" data-name="{xe(name)}"'
            f' data-state="{xe(d.get("state",""))}"'
            f' data-party="{xe(d.get("party",""))}"'
            f' data-color="{fill}"'
            f' data-coalition="{xe(d.get("coalition",""))}"'
            f' data-mp="{xe(d.get("mp",""))}"'
            f' fill="{fill}"'
        )

        if shape_type == "polygon":
            pts = re.sub(r'\s+', ' ', (p.get('points') or '').strip())
            lines.append(f'    <polygon {common} points="{pts}"/>')
        else:
            path_d = re.sub(r'\s+', ' ', (p.get('d') or '').strip())
            lines.append(f'    <path {common} d="{path_d}"/>')
    lines += ['  </g>', '</svg>']
    return '\n'.join(lines)

def main():
    print(f"Reading: {INPUT_FILE}")
    try:
        shapes = parse_svg(INPUT_FILE)
    except FileNotFoundError:
        print(f"ERROR: '{INPUT_FILE}' not found.")
        print("Usage: python3 extract_constituencies.py <path/to/Wahlkreise_in_Indien.svg>")
        return
    except ET.ParseError as e:
        print(f"XML parse error after & fix: {e}")
        print("Try opening the SVG in a text editor and manually search for stray & characters.")
        return

    if not shapes:
        print("No map shapes found — check SVG structure.")
        return

    svg = build(shapes)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written: {OUTPUT_FILE}  ({len(svg)//1024} KB, {len(shapes)} constituencies)")
    print()
    print("Integration steps:")
    print("  1. In landing.html, replace <svg id='india-map'>...</svg>")
    print("     with the full contents of india_constituencies.svg")
    print("  2. In JS: change '.state-shape' to '.constituency'")
    print("  3. In JS tooltip: use el.dataset.name instead of el.dataset.state")

if __name__ == "__main__":
    main()