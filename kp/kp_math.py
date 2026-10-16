from decimal import Decimal, ROUND_FLOOR

# Vimshottari dasha definitions
DASHA_SEQUENCE = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
    ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17)
]
TOTAL_DASHA_YEARS = 120
NAKSHATRA_LENGTH = 13.333333333333334
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"
]
OWNER_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

SIGN_SPAN_ARCSECONDS = 30 * 3600
NAKSHATRA_SPAN_ARCSECONDS = 13 * 3600 + 20 * 60
SUB_SPANS_ARCSECONDS = {
    name: (years * NAKSHATRA_SPAN_ARCSECONDS) // TOTAL_DASHA_YEARS
    for name, years in DASHA_SEQUENCE
}

def _normalize_longitude(longitude):
    return longitude % 360.0

def _degree_to_arcseconds(longitude):
    normalized = Decimal(str(_normalize_longitude(longitude)))
    total_arcseconds = normalized * Decimal("3600")
    # tiny epsilon absorbs float error (e.g. 13199.9999999 -> 13200) at exact boundaries
    return int((total_arcseconds + Decimal("0.000001")).to_integral_value(rounding=ROUND_FLOOR))

def _arcseconds_to_degree(arcseconds):
    return arcseconds / 3600.0

def _get_sign_index(longitude):
    # Strict boundary: equivalent to floor(longitude / 30), done in integer arcseconds
    return _degree_to_arcseconds(longitude) // SIGN_SPAN_ARCSECONDS

def get_sign_name(longitude):
    return ZODIAC_SIGNS[_get_sign_index(longitude)]

def get_sign_lord(longitude):
    return SIGN_LORDS[_get_sign_index(longitude)]

def get_star_lord(longitude):
    normalized_arcseconds = _degree_to_arcseconds(longitude)
    nakshatra_index = normalized_arcseconds // NAKSHATRA_SPAN_ARCSECONDS
    return DASHA_SEQUENCE[nakshatra_index % 9][0]

def get_sub_lord(longitude):
    normalized_arcseconds = _degree_to_arcseconds(longitude)
    nakshatra_index = normalized_arcseconds // NAKSHATRA_SPAN_ARCSECONDS
    degree_in_nakshatra = normalized_arcseconds % NAKSHATRA_SPAN_ARCSECONDS
    start_idx = nakshatra_index % 9
    accumulated_span = 0

    for i in range(9):
        idx = (start_idx + i) % 9
        planet_name, _ = DASHA_SEQUENCE[idx]
        accumulated_span += SUB_SPANS_ARCSECONDS[planet_name]
        if degree_in_nakshatra < accumulated_span:
            return planet_name

    return DASHA_SEQUENCE[(start_idx + 8) % 9][0]

def get_kp_dignities(longitude):
    """Takes any 360-degree longitude and returns Sign, Star, and Sub-Lord."""
    return {
        "longitude": round(_normalize_longitude(longitude), 4),
        "sign": get_sign_name(longitude),
        "sign_lord": get_sign_lord(longitude),
        "star_lord": get_star_lord(longitude),
        "sub_lord": get_sub_lord(longitude)
    }

# ---------------------------------------------------------------------------
# Pre-computed facts for the AI narrator (all math happens here, never in the LLM)
# ---------------------------------------------------------------------------

def ordinal(n):
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', ..."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def format_house_list(houses):
    """[4, 10] -> '4th, 10th Houses'; [4] -> '4th House'; [] -> 'no houses'."""
    if not houses:
        return "no houses"
    label = "House" if len(houses) == 1 else "Houses"
    return f"{', '.join(ordinal(h) for h in sorted(houses))} {label}"

def format_degree_in_sign(longitude):
    """Returns degrees within the sign as D°M'S\" (strict: longitude % 30)."""
    deg_in_sign = _normalize_longitude(longitude) % 30
    d = int(deg_in_sign)
    m = int((deg_in_sign - d) * 60)
    s = int(round(((deg_in_sign - d) * 60 - m) * 60))
    if s == 60:
        s, m = 0, m + 1
    if m == 60:
        m, d = 0, d + 1
    return f"{d}°{m:02d}'{s:02d}\""

def get_house_from_cusps(longitude, cusps):
    """
    Which house (1-12) a longitude falls in, using the actual cusp boundaries.
    House n spans from cusp n up to (not including) cusp n+1, wrapping at 360.
    """
    lon = _normalize_longitude(longitude)
    for i in range(12):
        start = _normalize_longitude(cusps[i])
        end = _normalize_longitude(cusps[(i + 1) % 12])
        span = (end - start) % 360.0
        offset = (lon - start) % 360.0
        if offset < span:
            return i + 1
    return 1  # unreachable for valid cusps

def build_cusp_facts(cusps):
    """One explicit fact record per house cusp (sign, sign lord, star/sub lord)."""
    facts = []
    for i, cusp_lon in enumerate(cusps[:12]):
        house = i + 1
        d = get_kp_dignities(cusp_lon)
        facts.append({
            "house": house,
            "sign": d["sign"],
            "degree_in_sign": format_degree_in_sign(cusp_lon),
            "sign_lord": d["sign_lord"],
            "star_lord": d["star_lord"],
            "sub_lord": d["sub_lord"],
            "summary": (
                f"{ordinal(house)} House Cusp: Sign: {d['sign']} ({format_degree_in_sign(cusp_lon)}), "
                f"Ruled by: {d['sign_lord']}"
            ),
        })
    return facts

def build_house_ownership(cusp_facts):
    """
    House ownership from the sign on each cusp -> that sign's ruling planet.
    Returns {planet: [houses]} for the 7 classical planets (nodes are handled
    by the caller through their true agent).
    """
    ownership = {p: [] for p in OWNER_PLANETS}
    for fact in cusp_facts:
        ownership[fact["sign_lord"]].append(fact["house"])
    return ownership

# ---------------------------------------------------------------------------

def generate_kp_249_table():
    """Generates the official 249 KP Horary sub-lord boundaries."""
    table = []
    current_arcseconds = 0
    
    for nak_idx in range(27):
        star_lord = DASHA_SEQUENCE[nak_idx % 9][0]
        start_sub_idx = nak_idx % 9
        
        for i in range(9):
            sub_idx = (start_sub_idx + i) % 9
            sub_lord, _ = DASHA_SEQUENCE[sub_idx]
            span_arcseconds = SUB_SPANS_ARCSECONDS[sub_lord]
            end_arcseconds = current_arcseconds + span_arcseconds

            current_sign_idx = current_arcseconds // SIGN_SPAN_ARCSECONDS
            end_sign_idx = (end_arcseconds - 1) // SIGN_SPAN_ARCSECONDS
            
            if current_sign_idx != end_sign_idx and end_sign_idx < 12:
                split_arcseconds = end_sign_idx * SIGN_SPAN_ARCSECONDS
                table.append({
                    "start_arcseconds": current_arcseconds,
                    "end_arcseconds": split_arcseconds,
                    "start_deg": _arcseconds_to_degree(current_arcseconds),
                    "end_deg": _arcseconds_to_degree(split_arcseconds),
                    "sign": ZODIAC_SIGNS[current_sign_idx],
                    "star_lord": star_lord,
                    "sub_lord": sub_lord
                })
                table.append({
                    "start_arcseconds": split_arcseconds,
                    "end_arcseconds": end_arcseconds,
                    "start_deg": _arcseconds_to_degree(split_arcseconds),
                    "end_deg": _arcseconds_to_degree(end_arcseconds),
                    "sign": ZODIAC_SIGNS[end_sign_idx],
                    "star_lord": star_lord,
                    "sub_lord": sub_lord
                })
            else:
                table.append({
                    "start_arcseconds": current_arcseconds,
                    "end_arcseconds": end_arcseconds,
                    "start_deg": _arcseconds_to_degree(current_arcseconds),
                    "end_deg": _arcseconds_to_degree(end_arcseconds),
                    "sign": ZODIAC_SIGNS[current_sign_idx],
                    "star_lord": star_lord,
                    "sub_lord": sub_lord
                })
            current_arcseconds = end_arcseconds
            
    return table

kp_table = generate_kp_249_table()

def get_horary_chart(number):
    """Takes a Horary Number (1-249) and returns its exact Ascendant details.

    Ascendant = START of the number's sub-division (book convention).
    """
    if not (1 <= number <= 249):
        return {"error": "Horary number must be between 1 and 249"}
    
    entry = kp_table[number - 1]
    # 2026-10-02 (X4): book-standard ascendant = START of the number's sub
    # (Reader III: No.37 -> Taurus 22°40' = sub start exactly). The old
    # sub-midpoint convention shifted every chart up to ~1.1° and flipped
    # cusp sub-lords near boundaries (Dutta A1: 6th CSL Rahu vs Mars).
    start = _arcseconds_to_degree(entry["start_arcseconds"])

    return {
        "horary_number": number,
        "ascendant_longitude": round(start, 6),
        "start_deg": round(entry["start_deg"], 6),
        "end_deg": round(entry["end_deg"], 6),
        "sign": entry["sign"],
        "sign_lord": get_sign_lord(start),
        "star_lord": entry["star_lord"],
        "sub_lord": entry["sub_lord"]
    }