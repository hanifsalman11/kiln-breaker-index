import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/kiln-breaker-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4").strip()
CUSTOM_KILN = os.environ.get("CUSTOM_KILN", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_kilns.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Kiln Model / Scenario, Watts, Voltage, Nameplate Amps, Required Breaker Amps, Chamber Cu Ft, Max Cone / Temp)
SEED_KILNS = [
    ("Skutt KM-1027 (11,520W 240V 48A) 7.0 Cu Ft Pottery Kiln", 11520, 240, 48.0, 60, 7.0, "Cone 10 (2,350°F)"),
    ("Skutt KM-1027-3 (9,980W 240V 41.6A) 3\" Brick Pottery Kiln", 9980, 240, 41.6, 60, 6.4, "Cone 10 (2,350°F)"),
    ("Skutt KM-818 (6,480W 240V 27.0A) 3.2 Cu Ft Pottery Kiln", 6480, 240, 27.0, 40, 3.2, "Cone 10 (2,350°F)"),
    ("Skutt KM-822 (8,640W 240V 36.0A) 4.2 Cu Ft Pottery Kiln", 8640, 240, 36.0, 50, 4.2, "Cone 10 (2,350°F)"),
    ("Skutt KM-1227-3PK (14,300W 240V 59.6A) 9.9 Cu Ft Studio Kiln", 14300, 240, 59.6, 80, 9.9, "Cone 10 (2,350°F)"),
    ("Skutt FireBox 8x6 & 14 (1,800W 120V 15A) Glass & Test Kiln", 1800, 120, 15.0, 20, 0.4, "Cone 6 (2,200°F)"),
    ("L&L e23S-3 (9,460W 240V 39.4A) Easy-Fire Ceramic Kiln", 9460, 240, 39.4, 50, 4.7, "Cone 10 (2,350°F)"),
    ("L&L e23T-3 (11,520W 240V 48.0A) 7.0 Cu Ft Easy-Fire Kiln", 11520, 240, 48.0, 60, 7.0, "Cone 10 (2,350°F)"),
    ("L&L e18S-3 (5,520W 240V 23.0A) Compact Ceramic Kiln", 5520, 240, 23.0, 30, 2.6, "Cone 10 (2,350°F)"),
    ("L&L e28T-3 (11,520W 240V 48.0A) 10.2 Cu Ft Pottery Kiln", 11520, 240, 48.0, 60, 10.2, "Cone 8 / Cone 10"),
    ("Olympic 2327HE (11,520W 240V 48.0A) Electric Pottery Kiln", 11520, 240, 48.0, 60, 7.0, "Cone 10 (2,350°F)"),
    ("Olympic 1823HE (7,920W 240V 33.0A) Home Studio Kiln", 7920, 240, 33.0, 50, 3.7, "Cone 10 (2,350°F)"),
    ("Olympic Doll E / 1214HE (3,360W 240V 14A / 120V 28A) Kiln", 3360, 240, 14.0, 20, 1.1, "Cone 10 (2,350°F)"),
    ("Cone Art BX2327D (11,000W 240V 45.8A) Double-Insulated Kiln", 11000, 240, 45.8, 60, 7.0, "Cone 10 (2,350°F)"),
    ("Evenheat KH418 & KF22.5 (3,120W 240V 13A) Knife Heat-Treat Oven", 3120, 240, 13.0, 20, 0.9, "2,200°F Blade Hardening"),
    ("Evenheat LB18 & LB27 (3,600W 240V 15A) Knife Heat-Treat Kiln", 3600, 240, 15.0, 20, 1.1, "2,200°F Blade Hardening"),
    ("Evenheat RM II 2322 (9,600W 240V 40.0A) Pottery Kiln", 9600, 240, 40.0, 50, 5.3, "Cone 10 (2,350°F)"),
    ("Paragon KM-24D & KM-36D (240V 13A–20A) Knife Making Furnace", 4200, 240, 17.5, 25, 1.0, "2,350°F Blade Heat-Treat"),
    ("Paragon Caldera & SC-2 (1,680W 120V 14A) Jewelry/Enamel Kiln", 1680, 120, 14.0, 20, 0.3, "2,000°F Silver Clay/Glass"),
    ("Paragon TNF-82 & Viking-28 (11,500W 240V 48.0A) Ceramic Kiln", 11500, 240, 48.0, 60, 8.8, "Cone 10 (2,350°F)"),
    ("Cress E2327 & FX27P (11,040W 240V 46.0A) Electronic Kiln", 11040, 240, 46.0, 60, 7.0, "Cone 10 (2,350°F)"),
    ("Amaco Excel EX-270 & EX-365 (240V / 208V) School Pottery Kiln", 11520, 240, 48.0, 60, 7.0, "Cone 10 (2,350°F)"),
    ("48-Amp Kiln on 60-Amp Breaker vs 50-Amp NEMA 6-50R Code Rule", 11520, 240, 48.0, 60, 7.0, "NEC 424.3(B) 125% Rule"),
    ("40-Amp Kiln on 50-Amp Breaker & 6 AWG NEMA 6-50 Plug Setup", 9600, 240, 40.0, 50, 5.5, "NEC 424.3(B) 125% Rule"),
    ("240V Kiln Running on 208V Commercial Power (25% Wattage Loss)", 11520, 208, 41.6, 60, 7.0, "8,653W Actual Output!"),
    ("Cone 04 Bisque vs Cone 6 Glaze vs Cone 10 Firing kWh Cost", 11520, 240, 48.0, 60, 7.0, "$0.16/kWh Cost Breakdown"),
    ("Orton EnviroVent 2 vs Overhead Hood Kiln Fume & Heat CFM", 11520, 240, 48.0, 60, 7.0, "Downdraft + Room Exhaust"),
    ("Kanthal A-1 Kiln Element Ohm Resistance (Ω) Multimeter Test", 11520, 240, 48.0, 60, 7.0, "10% Ohm Drift Replacement"),
    ("120V 15-Amp vs 20-Amp Plug-In Test Kiln Breaker & Cord Sizing", 1800, 120, 15.0, 20, 0.5, "NEMA 5-15R vs 5-20R"),
    ("Garage Heat Gain (BTU/hr) & Mini-Split Sizing for Pottery Kiln", 11520, 240, 48.0, 60, 7.0, "13,700 BTU/hr Peak Heat")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=11520.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Model Free Tier Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_kiln_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Kiln Amps × Voltage × Cone Permutator.
    """
    discovered = []
    seeds = [
        "what size breaker for kiln ",
        "skutt kiln ",
        "pottery kiln electricity cost ",
        "evenheat kiln "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        discovered.append((cleaned.title(), 11520, 240, 48.0, 60, 7.0, "Cone 10 (2,350°F)"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    kiln_power_tiers = [
        (3600, 240, 15.0, 20, 1.1, "15A (3,600W) Knife / Test Kiln"),
        (5760, 240, 24.0, 30, 2.8, "24A (5,760W) Small Studio Kiln"),
        (7200, 240, 30.0, 40, 3.5, "30A (7,200W) Medium Ceramic Kiln"),
        (8640, 240, 36.0, 50, 4.5, "36A (8,640W) Mid-Size Pottery Kiln"),
        (9600, 240, 40.0, 50, 5.5, "40A (9,600W) NEMA 6-50 Pottery Kiln"),
        (11520, 240, 48.0, 60, 7.0, "48A (11,520W) Full-Size Studio Kiln")
    ]
    firing_schedules = [
        ("Cone 04 Bisque Firing (1,945°F)"),
        ("Cone 6 Mid-Fire Glaze (2,232°F)"),
        ("Cone 10 High-Fire Reduction/Oxidation (2,345°F)"),
        ("208V vs 240V Element Derating")
    ]
    for w_val, v_val, a_val, brk_val, cu_v, k_desc in kiln_power_tiers:
        for f_sched in firing_schedules:
            combo_title = f"{k_desc} — {f_sched}"
            test_slug = slugify(f"{combo_title}-breaker-wire-cost-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, w_val, v_val, a_val, brk_val, cu_v, f_sched))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_kiln_data(kiln_tuple):
    """
    LAPIS 3: Mesin Fisika NEC 424.3(B), Hukum Ohm Elemen Kanthal & Biaya kWh Cone Firing (100% Bebas Gagal).
    """
    model_name, watts, volts, nameplate_amps, breaker_amps, chamber_cuft, cone_spec = kiln_tuple

    # 1. NEC Article 424.3(B) Continuous Load Rule (125% dari Nameplate Amps):
    nec_125_amps = round(nameplate_amps * 1.25, 1)
    if breaker_amps <= 20:
        wire_awg = "12/2 AWG Copper (90°C THHN/NM-B)"
        plug_spec = "NEMA 6-20R (240V) or 5-20R (120V)"
    elif breaker_amps <= 30:
        wire_awg = "10/2 AWG Copper (90°C THHN/NM-B)"
        plug_spec = "NEMA 6-30R or L6-30R (240V 30A)"
    elif breaker_amps <= 40:
        wire_awg = "8/2 AWG Stranded Copper (90°C THHN)"
        plug_spec = "NEMA 6-50R (Hubbell Industrial)"
    elif breaker_amps <= 50:
        wire_awg = "6 AWG THHN Copper in Conduit (or 6/2 NM-B)"
        plug_spec = "NEMA 6-50R (40A Max Continuous!)"
    elif breaker_amps <= 60:
        wire_awg = "6 AWG THHN Copper in Conduit (75°C Column — NO 6/2 Romex!)"
        plug_spec = "Hardwired 60A Disconnect (or NEMA 6-50R per Mfr Listing)"
    else:
        wire_awg = "4 AWG THHN Copper in Conduit"
        plug_spec = "Hardwired 80A Non-Fused Disconnect"

    # 2. Hukum Ohm Total Resistansi Elemen Pemanas Kanthal A-1 (R_total = V^2 / P):
    total_ohms_new = round((volts ** 2) / max(500.0, float(watts)), 2)
    # Jika kiln 6-bagian (3 zona / 6 elemen paralel), resistansi per elemen = R_total * 6 (atau per loop seri = R_total * 3):
    ohms_replace_threshold = round(total_ohms_new * 1.10, 2)

    # 3. Penurunan Daya jika Kiln 240V Dipasang pada Listrik Komersial 208V (P_208 = P_240 * (208/240)^2 = 0.751x):
    watts_on_208v = int(round(watts * ((208.0 / 240.0) ** 2))) if volts == 240 else watts

    # 4. Konsumsi Energi (kWh) & Biaya Listrik per Pembakaran (@ $0.16/kWh):
    # Rata-rata Cone 6 medium speed membutuhkan ~8.5 jam dengan duty cycle rata-rata 58% (karena awal firing relay nyala 20% dan akhir firing 100%)
    kw_rating = round(watts / 1000.0, 2)
    cone6_kwh = round(kw_rating * 8.5 * 0.58, 1)
    cone6_cost_usd = round(cone6_kwh * 0.16, 2)
    peak_room_btu_hr = int(round(watts * 3.412 * 0.35, -2))

    return {
        "kiln_name": model_name,
        "cone_spec": cone_spec,
        "seo_title": f"{model_name} Breaker, Wire Size (AWG), Ohm & Firing Cost Calculator (2026)",
        "meta_description": f"Calculate exact NEC 424 breaker & wire gauge ({breaker_amps}A / {wire_awg} for {nameplate_amps}A load), Cone 6 firing cost (${cone6_cost_usd} / {cone6_kwh} kWh), Kanthal element resistance ({total_ohms_new} Ω), and 208V derating for {model_name}.",
        "specs": {
            "rated_watts": watts,
            "rated_kw": kw_rating,
            "rated_voltage": volts,
            "nameplate_amps": nameplate_amps,
            "nec_125_continuous_amps": nec_125_amps,
            "required_breaker_amps": breaker_amps,
            "recommended_wire_awg": wire_awg,
            "receptacle_or_disconnect": plug_spec,
            "chamber_volume_cuft": chamber_cuft,
            "total_element_ohms_new": total_ohms_new,
            "replace_element_ohms_10pct": ohms_replace_threshold,
            "watts_if_run_on_208v": watts_on_208v,
            "cone6_firing_kwh": cone6_kwh,
            "cone6_firing_cost_usd": cone6_cost_usd,
            "peak_room_heat_btu_hr": peak_room_btu_hr,
            "cone_spec": cone_spec
        },
        "nec_verdict": f"Drawing {nameplate_amps} Amps ({watts:,}W / {kw_rating} kW at {volts}V) across a {chamber_cuft} cu. ft. chamber ({cone_spec}), {model_name} is classified as a continuous electrical load under NEC Article 424.3(B)—requiring a circuit sized at 125% ({nec_125_amps}A minimum = {breaker_amps}-Amp 2-pole breaker) wired with {wire_awg} ({plug_spec}). A standard Cone 6 glaze firing consumes ~{cone6_kwh} kWh (~${cone6_cost_usd} at $0.16/kWh) while radiating ~{peak_room_btu_hr:,} BTU/hr of peak heat into your studio. New Kanthal A-1 elements measure {total_ohms_new} $\\Omega$ total circuit resistance (replace elements when multimeter readings climb +10% to {ohms_replace_threshold} $\\Omega$).",
        "hardware_bundle": [
            {
                "badge": "Downdraft Kiln Vent Kit",
                "title": "Orton EnviroVent 2 / Downdraft Kiln Fume Extractor Vent System + High-Temp 4\" Aluminum Duct",
                "price_range": "$289 - $529",
                "amazon_query": "Orton EnviroVent Downdraft Kiln Vent System High Temp Duct",
                "kln_note": "Pulls toxic sulfur, carbon monoxide, and wax-burnout fumes downward through the kiln floor and vents them outdoors."
            },
            {
                "badge": f"{breaker_amps}A Breaker & Hubbell 6-50R",
                "title": f"Industrial Hubbell HBL9367 NEMA 6-50R Receptacle + {breaker_amps}A 2-Pole Breaker & 6 AWG Copper Whip",
                "price_range": "$84 - $219",
                "amazon_query": f"Hubbell NEMA 6-50R Industrial Outlet {breaker_amps}A 2 Pole Breaker 6 AWG Copper Wire",
                "kln_note": f"Prevents melted outlets during 10-hour {nameplate_amps}A Cone 6/10 firings; cheap $12 hardware-store outlets burn up under kiln loads."
            },
            {
                "badge": f"{chamber_cuft} ft³ Shelf & Post Kit",
                "title": "Cordierite / Mullite Kiln Shelf & Post Furniture Kit + High-Alumina Kiln Wash & Orton Pyrometric Cones",
                "price_range": "$94 - $269",
                "amazon_query": "Cordierite Kiln Shelf Post Furniture Kit Orton Self Supporting Cones Cone 6 04",
                "kln_note": "Thermal-shock-resistant cordierite shelves won't warp at 2,350°F, and witness cones verify true heat-work on every shelf."
            },
            {
                "badge": "Type-K Pyrometer & Ohm Meter",
                "title": "Digital High-Temp 2,500°F 8-Gauge Ceramic Type-K Kiln Thermocouple + True-RMS Ohm/Amp Clamp Meter",
                "price_range": "$49 - $139",
                "amazon_query": "Kiln Type K Thermocouple 8 Gauge Ceramic Block Digital Clamp Multimeter",
                "kln_note": f"Lets you measure element aging ({total_ohms_new} Ω new vs. {ohms_replace_threshold} Ω worn) and verify firing accuracy."
            }
        ],
        "potter_checklist": [
            f"Respect the NEC 125% Continuous Kiln Rule AND the 6/2 Romex Trap: a {nameplate_amps}A kiln requires {nec_125_amps}A minimum circuit ampacity ({breaker_amps}A breaker). If using a 60A breaker, NEC 334.80 prohibits 6/2 NM-B Romex (capped at 55A in the 60°C column)—you MUST run individual 6 AWG THHN copper wires inside conduit (rated 65A @ 75°C) or step up to 4 AWG.",
            f"Never run a 240V-element kiln on 208V commercial/school power without swapping to 208V elements: on 208V, a {watts:,}W (240V) kiln drops by $(208 \\div 240)^2 = 25\\%$ down to just {watts_on_208v:,}W, causing Cone 6/10 firings to stall out and fail.",
            f"Check Kanthal A-1 Element Resistance ($\Omega$) every 25 firings with a digital multimeter: your total circuit resistance is {total_ohms_new} $\\Omega$ when new—once oxidation thins the wire and resistance rises +10% to {ohms_replace_threshold} $\\Omega$, replace the elements before firing times stall.",
            "Maintain 18 inches of clear air space between the stainless steel kiln jacket and any studio wall, never place a kiln on carpet or vinyl flooring, and install a 60–150 CFM room exhaust fan to remove the ~{:,} BTU/hr of ambient heat.".format(peak_room_btu_hr)
        ],
        "faqs": [
            {
                "q": f"What size breaker and wire gauge do I need for {model_name} ({nameplate_amps}A)?",
                "a": f"Per NEC Article 424.3(B), electric kilns are continuous loads requiring a circuit breaker rated at 125% of nameplate amperage ({nameplate_amps}A × 1.25 = {nec_125_amps}A). Install a dedicated {breaker_amps}-Amp 2-pole breaker wired with {wire_awg} ({plug_spec})."
            },
            {
                "q": f"How much electricity does {model_name} cost per Cone 04 or Cone 6 firing?",
                "a": f"Because kiln relays cycle on and off during the ramp-up (averaging ~58% duty cycle over an 8.5-hour firing), a {kw_rating} kW kiln uses approximately {cone6_kwh} kWh per Cone 6 glaze firing. At the US average of $0.16/kWh, one full firing costs just ~${cone6_cost_usd}."
            },
            {
                "q": f"What happens if I plug a 240V {model_name} into a 208V commercial outlet?",
                "a": f"Because heating element wattage varies with the square of voltage ($P = V^2 \\div R$), dropping voltage by 13.3% (from 240V to 208V) cuts heating power by 24.9%—dropping your {watts:,}W kiln to {watts_on_208v:,}W. It will still reach Cone 04 bisque, but will struggle or fail to reach Cone 6/10 without 208V-specific elements."
            }
        ]
    }


def generate_kiln_data(kiln_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_kiln_data(kiln_tuple)

    model_name, watts, volts, nameplate_amps, breaker_amps, chamber_cuft, cone_spec = kiln_tuple
    det_fallback = build_deterministic_kiln_data(kiln_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Master Ceramic Studio Electrical Engineer (NEC Article 424 Specialist) & Kiln Thermodynamics Technician. Create an accurate 2026 electric pottery/knife kiln breaker and wire gauge (NEC 125% rule), 240V vs 208V wattage derating, Kanthal A-1 element Ohm resistance, and Cone firing kWh cost guide for: "{model_name}".
Baseline specs: Power={watts}W ({sp['rated_kw']} kW) @ {volts}V, Nameplate={nameplate_amps}A (125% NEC={sp['nec_125_continuous_amps']}A -> {breaker_amps}A Breaker, {sp['recommended_wire_awg']}, {sp['receptacle_or_disconnect']}), Chamber={chamber_cuft} cu ft ({cone_spec}), Element Ohms={sp['total_element_ohms_new']} Ohms new (Replace @ {sp['replace_element_ohms_10pct']} Ohms), Power on 208V={sp['watts_if_run_on_208v']}W, Cone 6 Firing={sp['cone6_firing_kwh']} kWh (${sp['cone6_firing_cost_usd']}).
Return ONLY a valid JSON object matching this exact schema:
{{
  "kiln_name": "{model_name}",
  "cone_spec": "{cone_spec}",
  "seo_title": "{model_name} Breaker, Wire Size (AWG), Ohm & Firing Cost Calculator (2026)",
  "meta_description": "Calculate exact NEC 424 kiln breaker and wire size, Cone 6/10 firing electricity cost, Kanthal element Ohm resistance, and 208V wattage loss for {model_name}.",
  "specs": {{
    "rated_watts": {watts},
    "rated_kw": {sp['rated_kw']},
    "rated_voltage": {volts},
    "nameplate_amps": {nameplate_amps},
    "nec_125_continuous_amps": {sp['nec_125_continuous_amps']},
    "required_breaker_amps": {breaker_amps},
    "recommended_wire_awg": "{sp['recommended_wire_awg']}",
    "receptacle_or_disconnect": "{sp['receptacle_or_disconnect']}",
    "chamber_volume_cuft": {chamber_cuft},
    "total_element_ohms_new": {sp['total_element_ohms_new']},
    "replace_element_ohms_10pct": {sp['replace_element_ohms_10pct']},
    "watts_if_run_on_208v": {sp['watts_if_run_on_208v']},
    "cone6_firing_kwh": {sp['cone6_firing_kwh']},
    "cone6_firing_cost_usd": {sp['cone6_firing_cost_usd']},
    "peak_room_heat_btu_hr": {sp['peak_room_heat_btu_hr']},
    "cone_spec": "{cone_spec}"
  }},
  "nec_verdict": "3-sentence technical summary stating nameplate amps, 125% NEC 424 breaker and copper wire gauge, Cone 6 kWh firing cost, and Kanthal element Ohm resistance.",
  "hardware_bundle": [
    {{
      "badge": "Downdraft Kiln Vent Kit",
      "title": "Orton EnviroVent 2 / Downdraft Kiln Fume Extractor Vent System + Duct",
      "price_range": "$289 - $529",
      "amazon_query": "Orton EnviroVent Downdraft Kiln Vent System",
      "kln_note": "1-sentence fume removal and glaze color consistency note"
    }},
    {{
      "badge": "{breaker_amps}A Breaker & Hubbell 6-50R",
      "title": "Industrial Hubbell NEMA 6-50R Receptacle + {breaker_amps}A 2-Pole Breaker & 6 AWG Wire",
      "price_range": "$84 - $219",
      "amazon_query": "Hubbell NEMA 6-50R Industrial Outlet {breaker_amps}A 2 Pole Breaker 6 AWG",
      "kln_note": "1-sentence anti-melting industrial brass contact note"
    }},
    {{
      "badge": "{chamber_cuft} ft³ Shelf & Post Kit",
      "title": "Cordierite Kiln Shelf & Post Furniture Kit + Kiln Wash & Pyrometric Cones",
      "price_range": "$94 - $269",
      "amazon_query": "Cordierite Kiln Shelf Post Furniture Kit Orton Pyrometric Cones",
      "kln_note": "1-sentence thermal shock resistance and witness cone note"
    }},
    {{
      "badge": "Type-K Pyrometer & Ohm Meter",
      "title": "8-Gauge Ceramic Type-K Kiln Thermocouple + Digital True-RMS Ohm/Amp Multimeter",
      "price_range": "$49 - $139",
      "amazon_query": "Kiln Type K Thermocouple 8 Gauge Digital Clamp Multimeter",
      "kln_note": "1-sentence element Ohm aging test and thermocouple calibration note"
    }}
  ],
  "potter_checklist": [
    "Step 1 regarding NEC 424.3(B) 125% breaker sizing and 6 AWG THHN vs 6/2 Romex",
    "Step 2 regarding 25% wattage loss when running a 240V kiln on 208V power",
    "Step 3 regarding testing Kanthal A-1 element Ohms ({sp['total_element_ohms_new']} Ohms new vs +10% worn)",
    "Step 4 regarding 18-inch wall clearance and removing {sp['peak_room_heat_btu_hr']} BTU/hr studio heat"
  ],
  "faqs": [
    {{"q": "What size breaker and wire do I need for {model_name}?", "a": "Exact nameplate amps, 125% NEC multiplier, breaker size, and copper AWG."}},
    {{"q": "How much does it cost to fire {model_name} to Cone 6 or Cone 10?", "a": "Exact kW, hours, 58% duty cycle, kWh used, and dollar cost."}},
    {{"q": "How do I test if the heating elements on {model_name} need replacing?", "a": "Exact Ohm's Law resistance when new ({sp['total_element_ohms_new']} Ohms) vs +10% replacement threshold ({sp['replace_element_ohms_10pct']} Ohms)."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_kiln_html_page(data, slug, mon_cfg):
    kiln_name = data.get("kiln_name", "Electric Pottery & Knife Kiln")
    sp = data.get("specs", {})
    watts = int(safe_float(sp.get("rated_watts", 11520), 11520))
    kw = round(safe_float(sp.get("rated_kw", 11.52), 11.52), 2)
    volts = int(safe_float(sp.get("rated_voltage", 240), 240))
    amps = round(safe_float(sp.get("nameplate_amps", 48.0), 48.0), 1)
    brk_a = int(safe_float(sp.get("required_breaker_amps", 60), 60))
    wire_s = sp.get("recommended_wire_awg", "6 AWG THHN Copper")
    ohms_new = round(safe_float(sp.get("total_element_ohms_new", 5.0), 5.0), 2)
    w_208 = int(safe_float(sp.get("watts_if_run_on_208v", 8653), 8653))
    c6_kwh = round(safe_float(sp.get("cone6_firing_kwh", 56.8), 56.8), 1)
    c6_usd = round(safe_float(sp.get("cone6_firing_cost_usd", 9.09), 9.09), 2)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Pottery+Kiln+Shelf+Kit+NEMA+6-50+Orton+Vent"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{kiln_name} Breaker, Wire Size & Firing Cost Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Pottery Kiln Kit")), mon_cfg)
        bundle_html += f"""
        <div class="bg-stone-900 border border-stone-800 rounded-xl p-5 flex flex-col justify-between hover:border-orange-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Kiln Studio Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$79+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-stone-400 mt-2 leading-relaxed">🏺 {item.get('kln_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-orange-500 hover:bg-orange-400 text-stone-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Kiln Amperage vs NEC 125% Breaker, Copper Wire Gauge, Receptacle & Cone 6 Cost Matrix Table
    kiln_tiers = [
        ("15A @ 120V (1,800W Test Kiln)", "20A 1-Pole Breaker", "12/2 AWG Copper", "NEMA 5-20R Outlet", "~$1.45 / Firing"),
        ("15A @ 240V (3,600W Knife Kiln)", "20A 2-Pole Breaker", "12/2 AWG Copper", "NEMA 6-20R Outlet", "~$2.85 / Firing"),
        ("27A @ 240V (6,480W KM-818)", "35A / 40A 2-Pole Brk", "8/2 AWG Copper", "NEMA 6-50R (Hubbell)", "~$5.10 / Firing"),
        ("36A–40A @ 240V (8.6–9.6 kW)", "50A 2-Pole Breaker", "6/2 Romex or 6 THHN", "NEMA 6-50R (Hubbell)", "~$7.50 / Firing"),
        ("48A @ 240V (11,520W KM-1027)", "60A 2-Pole Breaker", "6 AWG THHN (Conduit!)", "Hardwired / Listed 6-50R", "~$9.10 / Firing"),
        ("60A @ 240V (14,300W KM-1227)", "80A 2-Pole Breaker", "4 AWG THHN Copper", "Hardwired Disconnect", "~$11.30 / Firing")
    ]
    matrix_rows_html = ""
    for k_lbl, b_lbl, w_lbl, p_lbl, c_lbl in kiln_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-stone-800 hover:bg-stone-800/40">
          <td class="py-3 px-4 font-bold text-white">{k_lbl}</td>
          <td class="py-3 px-4 font-bold text-orange-400">{b_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{w_lbl}</td>
          <td class="py-3 px-4 text-stone-300">{p_lbl}</td>
          <td class="py-3 px-4 text-xs text-stone-300">{c_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("potter_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-stone-900 border border-stone-800 rounded-xl p-4 cursor-pointer hover:border-stone-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-orange-500 rounded cursor-pointer kln-check">
          <span class="text-sm text-stone-200 leading-relaxed"><strong>NEC 424 Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-stone-900 border border-stone-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-stone-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', kiln_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', kiln_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-stone-950 text-stone-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-stone-800 bg-stone-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-orange-500 text-stone-950 px-2 py-0.5 rounded font-black">KILN</span>BreakerIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-stone-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Kilns, Vents & Wiring Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-orange-500 text-stone-950 px-3 py-1 rounded-full">{amps}A ({watts:,}W @ {volts}V) → {brk_a}A Breaker</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Cone 6 Cost: ~${c6_usd} ({c6_kwh} kWh)</span>
        <span class="text-xs font-semibold bg-stone-800 text-stone-300 px-3 py-1 rounded-full">Elements: {ohms_new} Ω | On 208V: {w_208:,}W</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', kiln_name)}</h1>
      <div class="mt-4 bg-stone-900 border-l-4 border-orange-500 p-4 rounded-r-xl text-sm text-stone-200 leading-relaxed">
        <strong>NEC Article 424.3(B) & Kanthal Element Verdict:</strong> {data.get('nec_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE KILN BREAKER/WIRE, CONE FIRING COST & ELEMENT OHM CALCULATOR -->
    <section class="bg-stone-900 border border-stone-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {kiln_name} Breaker, Firing Cost & Ohm Calculator</h2>
      <p class="text-xs text-stone-400 mb-6">Adjust your kiln nameplate amperage, supply voltage (240V vs. 208V), cone firing schedule, and local electricity rate to compute exact NEC 125% breaker/wire gauge, firing cost, and Kanthal element Ohms.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="ampSlider" class="text-stone-300">Kiln Nameplate Current Draw (Amps)</label>
              <span class="text-orange-400 font-bold"><span id="ampVal">{amps:g}</span> Amps</span>
            </div>
            <input id="ampSlider" type="range" min="12" max="60" step="1" value="{int(amps)}" class="w-full accent-orange-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="voltSelect" class="block text-xs font-medium text-stone-400 mb-1">Supply Voltage</label>
              <select id="voltSelect" class="w-full bg-stone-950 border border-stone-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="240" {"selected" if volts == 240 else ""}>240V Single-Phase (Residential)</option>
                <option value="208" {"selected" if volts == 208 else ""}>208V Single-Phase (Commercial/School)</option>
                <option value="120" {"selected" if volts == 120 else ""}>120V Household (Test/Knife Kiln)</option>
              </select>
            </div>
            <div>
              <label for="coneSelect" class="block text-xs font-medium text-stone-400 mb-1">Cone Firing Schedule</label>
              <select id="coneSelect" class="w-full bg-stone-950 border border-stone-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="7.5|0.50">Cone 04 Bisque (1,945°F — ~7.5 hrs)</option>
                <option value="8.5|0.58" selected>Cone 6 Glaze (2,232°F — ~8.5 hrs)</option>
                <option value="10.5|0.65">Cone 10 High-Fire (2,345°F — ~10.5 hrs)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="rateSlider" class="text-stone-300">Local Electricity Rate ($ per kWh)</label>
              <span class="text-orange-400 font-bold">$<span id="rateVal">0.16</span> / kWh</span>
            </div>
            <input id="rateSlider" type="range" min="0.08" max="0.45" step="0.01" value="0.16" class="w-full accent-orange-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-stone-950 border border-orange-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-orange-400 font-bold">NEC 424 Breaker & Wire</span>
            <div id="brkWireOut" class="text-xl sm:text-2xl font-black text-white mt-1">{brk_a}A (6 AWG THHN)</div>
            <p id="wattsOhmOut" class="text-xs text-orange-400 font-semibold mt-1">{watts:,}W | {ohms_new} Ω Elements</p>
          </div>

          <div class="bg-stone-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Cost Per Firing</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1">$<span id="costOut">{c6_usd:.2f}</span></div>
            <p id="kwhHeatOut" class="text-xs text-stone-300 font-semibold mt-1">{c6_kwh} kWh Used</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-orange-950/40 border border-orange-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="klnAdviceBanner" class="text-sm text-orange-100 font-medium"></div>
        <a id="dynamicKlnBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-orange-500 hover:bg-orange-400 text-stone-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Kiln Vent, Outlet & Shelves on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {kiln_name} Vent, Hubbell 6-50R & Shelf Bundle</h2>
        <span class="text-xs text-stone-400">NEC Article 424.3(B) & UL-499 Compliant</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Electric Kiln Amperage, NEC 125% Breaker, Copper Wire Gauge & Firing Cost Chart</h2>
      <div class="overflow-x-auto bg-stone-900 border border-stone-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-stone-800 bg-stone-950/60 text-stone-400 uppercase text-xs">
              <th class="py-3.5 px-4">Kiln Amps & Wattage</th>
              <th class="py-3.5 px-4 text-orange-400">NEC 125% Breaker</th>
              <th class="py-3.5 px-4 text-emerald-400">Copper Wire Gauge</th>
              <th class="py-3.5 px-4">Receptacle / Connection</th>
              <th class="py-3.5 px-4">Cone 6 Cost (@$0.16)</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">NEC 424 Kiln Wiring, 208V Derating & Kanthal Element Ohm Checklist</h2>
        <span id="klnBadge" class="text-xs font-bold bg-stone-800 text-orange-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({kiln_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-stone-800 py-8 text-center text-xs text-stone-500 px-4">
    <p>© {datetime.now(timezone.utc).year} KilnBreakerIndex. Independent Electric Kiln NEC 424 Wiring & Cone Firing Cost Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const ampSlider = document.getElementById('ampSlider');
    const voltSelect = document.getElementById('voltSelect');
    const coneSelect = document.getElementById('coneSelect');
    const rateSlider = document.getElementById('rateSlider');
    const ampVal = document.getElementById('ampVal');
    const rateVal = document.getElementById('rateVal');
    const brkWireOut = document.getElementById('brkWireOut');
    const wattsOhmOut = document.getElementById('wattsOhmOut');
    const costOut = document.getElementById('costOut');
    const kwhHeatOut = document.getElementById('kwhHeatOut');
    const klnAdviceBanner = document.getElementById('klnAdviceBanner');
    const dynamicKlnBtn = document.getElementById('dynamicKlnBtn');

    function recalculateKiln() {{
      const amps = parseInt(ampSlider.value, 10);
      const volts = parseInt(voltSelect.value, 10);
      const coneParts = coneSelect.value.split('|');
      const fireHrs = parseFloat(coneParts[0]);
      const dutyCycle = parseFloat(coneParts[1]);
      const kwhRate = parseFloat(rateSlider.value);

      ampVal.textContent = amps;
      rateVal.textContent = kwhRate.toFixed(2);

      const watts = amps * volts;
      const kw = watts / 1000.0;
      const ohms = (volts / amps).toFixed(2);

      const minBrkRaw = amps * 1.25;
      let brkSpec = "60A (6 AWG THHN)";
      if (minBrkRaw <= 20) brkSpec = "20A (12 AWG)";
      else if (minBrkRaw <= 30) brkSpec = "30A (10 AWG)";
      else if (minBrkRaw <= 40) brkSpec = "40A (8 AWG)";
      else if (minBrkRaw <= 50) brkSpec = "50A (6 AWG)";
      else if (minBrkRaw <= 60) brkSpec = "60A (6 AWG THHN)";
      else brkSpec = "80A (4 AWG THHN)";

      const kwhUsed = (kw * fireHrs * dutyCycle).toFixed(1);
      const costUsd = (parseFloat(kwhUsed) * kwhRate).toFixed(2);
      const btuHr = Math.round((watts * 3.412 * 0.35) / 100) * 100;

      brkWireOut.textContent = brkSpec;
      wattsOhmOut.textContent = `${{watts.toLocaleString()}}W | ${{ohms}} Ω Elements`;
      costOut.textContent = costUsd;
      kwhHeatOut.textContent = `${{kwhUsed}} kWh (~${{btuHr.toLocaleString()}} BTU/hr)`;

      klnAdviceBanner.innerHTML = `🏺 <strong>NEC 424.3(B) Studio Spec:</strong> A <strong>${{amps}}A (${{watts.toLocaleString()}}W @ ${{volts}}V)</strong> kiln requires a dedicated <strong>${{brkSpec}} circuit</strong> + <strong>Industrial Hubbell NEMA 6-50R / Hardwired Disconnect</strong> + <strong>Downdraft Kiln Vent</strong>. Each firing uses <strong>${{kwhUsed}} kWh ($${{costUsd}})</strong>.`;
      dynamicKlnBtn.href = `https://${{amzDomain}}/s?k=Hubbell+NEMA+6-50R+Outlet+Orton+Kiln+Vent+Cordierite+Kiln+Shelf+Kit&tag=${{amzTag}}`;
    }}

    ampSlider.addEventListener('input', recalculateKiln);
    voltSelect.addEventListener('change', recalculateKiln);
    coneSelect.addEventListener('change', recalculateKiln);
    rateSlider.addEventListener('input', recalculateKiln);
    recalculateKiln();

    const checks = document.querySelectorAll('.kln-check');
    const badge = document.getElementById('klnBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Pottery+Kiln+Shelf+Kit+NEMA+6-50+Orton+Vent"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-stone-900 border border-stone-800 hover:border-orange-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-orange-500 text-stone-950 px-2.5 py-0.5 rounded">{item.get('amps', 48.0):g}A → {item.get('brk_a', 60)}A Brk</span>
            <span class="text-xs text-stone-400">~${item.get('cost', 9.09):.2f}/Firing | {item.get('ohms', 5.0)} Ω</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-orange-400 transition">{item['kiln_name']}</h2>
          <p class="text-xs text-stone-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-orange-400">Calculate Breaker, Wire & Firing Cost →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KilnBreakerIndex — Electric Pottery & Knife Kiln Breaker, Wire Size & Firing Cost Calculator (2026)</title>
  <meta name="description" content="Calculate exact NEC 424.3(B) 125% electric pottery and knife kiln breaker and wire gauge, Cone 04/6/10 firing electricity cost, 240V vs 208V wattage derating, and Kanthal element Ohm resistance for Skutt, L&L, Olympic, Evenheat, and Paragon kilns.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="KilnBreakerIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-950 text-stone-100 min-h-screen flex flex-col">
  <header class="border-b border-stone-800 bg-stone-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-orange-500 text-stone-950 px-2 py-0.5 rounded font-black">KILN</span>BreakerIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-stone-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Kilns, Vents & Wiring Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Electric Kiln Breaker, Wire Gauge, Ohm & Cone Firing Cost Database</h1>
      <p class="text-stone-400 mt-3 text-base sm:text-lg">Select your pottery, glass, or knife heat-treating kiln model below to calculate NEC 424.3(B) 125% continuous breaker sizing, 6 AWG THHN vs. Romex rules, Cone 6/10 kWh firing costs, and Kanthal element Ohms.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search kiln model or amps (e.g. Skutt KM-1027, KM-818, L&L e23T, Evenheat, Paragon, 48A Kiln, 208V vs 240V...)" class="w-full bg-stone-900 border border-stone-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-orange-500">
      </div>
    </div>

    <div id="klnGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-stone-800 py-8 text-center text-xs text-stone-500">
    <p>© {datetime.now(timezone.utc).year} KilnBreakerIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('klnGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>KilnBreakerIndex Electric Pottery & Knife Kiln Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Electric Kiln NEC 424 Breaker, Wire Gauge, Ohm Resistance & Cone Firing Cost Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_KILN:
        candidates.append((CUSTOM_KILN.strip(), 11520, 240, 48.0, 60, 7.0, "Cone 10 (2,350°F)"))
    candidates.extend(SEED_KILNS)
    candidates.extend(discover_google_kiln_queries(published_slugs))

    new_urls = []
    count = 0

    for kiln_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        k_name = kiln_tuple[0]
        slug = slugify(f"{k_name}-breaker-wire-cost-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating electric kiln breaker & firing cost calculator for: {k_name}...")
        try:
            data = generate_kiln_data(kiln_tuple)
            build_kiln_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "kiln_name": data.get("kiln_name", k_name),
                "slug": slug,
                "title": data.get("seo_title", f"{k_name} Kiln Calculator"),
                "description": data.get("meta_description", ""),
                "amps": round(safe_float(sp.get("nameplate_amps", kiln_tuple[3]), kiln_tuple[3]), 1),
                "brk_a": int(safe_float(sp.get("required_breaker_amps", kiln_tuple[4]), kiln_tuple[4])),
                "cost": round(safe_float(sp.get("cone6_firing_cost_usd", 9.09), 9.09), 2),
                "ohms": round(safe_float(sp.get("total_element_ohms_new", 5.0), 5.0), 2),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {k_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new electric kiln breaker & firing cost calculator pages.")


if __name__ == "__main__":
    main()
