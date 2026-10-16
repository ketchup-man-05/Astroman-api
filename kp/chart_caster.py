import swisseph as swe
from datetime import datetime, timezone, timedelta
import re
from kp import kp_math
from kp import location_engine
from kp import ephemeris_utils
from kp import kp_logger
from kp import timing_engine
from kp import transit_engine

# --- CORE SETTINGS ---
swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)

ZODIAC_SIGNS = kp_math.ZODIAC_SIGNS
SIGN_LORDS = kp_math.SIGN_LORDS
NAKSHATRA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"] * 3

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAY_LORDS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
TITHIS = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima"] * 2
TITHIS[-1] = "Amavasya"

NODES = ["Rahu", "Ketu"]

def get_sign_lord(degree):
    return kp_math.get_sign_lord(degree)

def get_star_lord(degree):
    return kp_math.get_star_lord(degree)

def get_node_agent_info(node, planets_dict):
    """
    Which planet Rahu/Ketu act through. Priority order (KP Reader VI cascade):
      1. a planet conjunct the node within 3deg20' (the closest one wins; other node excluded)
      2. the node's own Star Lord, if that is a classical planet (not the other node / itself)
      3. a classical planet aspecting the node within 3deg20' (Vedic aspects: all planets
         aspect the 7th; Mars also 4th/8th; Jupiter 5th/9th; Saturn 3rd/10th; nodes do not
         aspect; closest one wins)
      4. the Sign Lord of the node's position (last resort)
    Returns (agent, rule_name, human-readable explanation).
    """
    node_lon = planets_dict.get(node, 0)
    nearest, nearest_dist = None, None
    for p_name, p_lon in planets_dict.items():
        if p_name not in NODES:
            dist = abs(node_lon - p_lon)
            if dist > 180: dist = 360 - dist
            if dist <= 3.33 and (nearest_dist is None or dist < nearest_dist):
                nearest, nearest_dist = p_name, dist
    if nearest is not None:
        return nearest, "conjunction", f"{nearest} is conjunct {node} within 3.33 degrees ({nearest_dist:.2f} deg)"
    star = get_star_lord(node_lon)
    if star not in NODES:
        return star, "star lord", f"no planet conjunct {node}; {node} sits in the star of {star}"
    _ASPECTS = {"Sun": (180,), "Moon": (180,), "Mars": (180, 90, 240),
                "Mercury": (180,), "Jupiter": (180, 120, 240),
                "Venus": (180,), "Saturn": (180, 60, 270)}
    asp_nearest, asp_dist = None, None
    for p_name, p_lon in planets_dict.items():
        if p_name in NODES:
            continue
        d = (node_lon - p_lon) % 360
        for a in _ASPECTS.get(p_name, (180,)):
            off = abs(d - a)
            if off <= 3.33 and (asp_dist is None or off < asp_dist):
                asp_nearest, asp_dist = p_name, off
    if asp_nearest is not None:
        return asp_nearest, "aspect", (f"no planet conjunct {node} and its star lord {star} is a node; "
                                       f"{asp_nearest} aspects {node} (orb {asp_dist:.2f} deg)")
    sign_lord = get_sign_lord(node_lon)
    return sign_lord, "sign lord", (f"no planet conjunct or aspecting {node}; its Star Lord {star} is a node, "
                                    f"so the Sign Lord {sign_lord} is used as last resort")
def get_true_agent(planet, planets_dict):
    if planet not in NODES: return planet
    return get_node_agent_info(planet, planets_dict)[0]

def get_sign_index(degree):
    return int((degree % 360) // 30)

def get_houses_owned_by_planet(planet, ownership, planets_dict):
    """
    House ownership = the houses whose CUSP falls in a sign ruled by the planet.
    `ownership` is the {planet: [houses]} map from kp_math.build_house_ownership().
    Rahu/Ketu are resolved to their true agent first.
    """
    agent = get_true_agent(planet, planets_dict)
    return list(ownership.get(agent, []))

def _asc_diff(jd, lat, lon, target):
    """Signed difference (-180..180) between the Ascendant at jd and the target. Positive = Asc is ahead."""
    _, ascmc = swe.houses_ex(jd, lat, lon, b'P', swe.FLG_SIDEREAL)
    return (ascmc[0] - target + 180) % 360 - 180

def find_horary_moment(target_ascendant, lat, lon, ref_jd, half_window_days=0.5, step_minutes=7.5):
    """
    Finds the moment whose Ascendant equals target_ascendant, searching +-12h around ref_jd
    (the moment of the query) and returning the crossing NEAREST to ref_jd.

    The old version searched 'today's UTC calendar day', so the moment could land many hours
    from the real query time. A +-12h window always contains the nearest crossing (the Ascendant
    passes any degree about once per 23h56m). Raises ValueError if none is found instead of
    silently returning a meaningless time.
    """
    n = int((2 * half_window_days * 24 * 60) / step_minutes)
    step = (2 * half_window_days) / n
    t0 = ref_jd - half_window_days

    brackets = []
    prev_jd = t0
    prev_d = _asc_diff(prev_jd, lat, lon, target_ascendant)
    for i in range(1, n + 1):
        jd = t0 + i * step
        d = _asc_diff(jd, lat, lon, target_ascendant)
        # Ascendant moves forward, so we look for negative -> positive; ignore the 360->0 wrap jump
        if prev_d <= 0 <= d and abs(d - prev_d) < 180:
            brackets.append((prev_jd, jd))
        prev_jd, prev_d = jd, d

    if not brackets:
        raise ValueError(f"No moment found with Ascendant {target_ascendant:.4f} within +-{half_window_days*24:.0f}h of the query")

    best = None
    for lo, hi in brackets:
        lo_d = _asc_diff(lo, lat, lon, target_ascendant)
        for _ in range(80):
            mid = (lo + hi) / 2.0
            d = _asc_diff(mid, lat, lon, target_ascendant)
            if (d > 0) == (lo_d > 0):
                lo, lo_d = mid, d
            else:
                hi = mid
            if (hi - lo) < (0.01 / 86400.0):   # 0.01 second
                break
        moment = (lo + hi) / 2.0
        if best is None or abs(moment - ref_jd) < abs(best - ref_jd):
            best = moment
    return best

def calculate_horary_cusps(target_ascendant, lat, lon, ref_jd):
    """Returns (12 Placidus cusps, JD of the moment that Ascendant rises)."""
    jd = find_horary_moment(target_ascendant, lat, lon, ref_jd)
    cusps, _ = swe.houses_ex(jd, lat, lon, b'P', swe.FLG_SIDEREAL)
    return list(cusps)[-12:], jd

def calculate_placidus_cusps(target_ascendant, lat, lon, ref_jd=None):
    """Backward-compatible wrapper: returns only the cusps."""
    if ref_jd is None:
        ref_jd = ephemeris_utils.to_jd(datetime.now(timezone.utc))
    return calculate_horary_cusps(target_ascendant, lat, lon, ref_jd)[0]

def get_panchang_tithi(sun_lon, moon_lon):
    diff = (moon_lon - sun_lon) % 360
    tithi_index = int(diff / 12)
    paksha = "Shukla (Waxing)" if tithi_index < 15 else "Krishna (Waning)"
    return f"{paksha} {TITHIS[tithi_index]}"

def get_current_day_lord(lon, as_of=None):
    offset_hours = lon / 15.0
    local_time = (as_of or datetime.now(timezone.utc)) + timedelta(hours=offset_hours)
    sun_index = (local_time.weekday() + 1) % 7
    if local_time.hour < 6: sun_index = (sun_index - 1) % 7
    return DAYS[sun_index], DAY_LORDS[sun_index]

def get_live_ascendant(lat, lon, as_of=None):
    jd_ut = ephemeris_utils.to_jd(as_of or datetime.now(timezone.utc))
    cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'P', swe.FLG_SIDEREAL)
    return ascmc[0]

# --- PRE-CALCULATED FACT BUILDERS (all math lives here, never in the LLM) ---

def build_planet_facts(planets, retrogrades, cusps, ownership):
    """Explicit per-planet fact records + a ready-to-read summary string."""
    facts = []
    for name, lon_val in planets.items():
        d = kp_math.get_kp_dignities(lon_val)
        house = kp_math.get_house_from_cusps(lon_val, cusps)
        retro = bool(retrogrades.get(name, False))

        if name in NODES:
            agent = get_true_agent(name, planets)
            owned = list(ownership.get(agent, []))
            owns_text = (
                f"no cusps of its own; acts as agent of {agent}, "
                f"which owns {kp_math.format_house_list(owned)}"
            )
        else:
            agent = name
            owned = list(ownership.get(name, []))
            owns_text = kp_math.format_house_list(owned)

        facts.append({
            "planet": name,
            "sign": d["sign"],
            "degree_in_sign": kp_math.format_degree_in_sign(lon_val),
            "sign_lord": d["sign_lord"],
            "star_lord": get_true_agent(d["star_lord"], planets),
            "sub_lord": d["sub_lord"],
            "house_occupied": house,
            "acts_as_agent_of": agent,
            "owns_houses": owned,
            "is_retrograde": retro,
            "summary": (
                f"Planet: {name}, Sign: {d['sign']} ({kp_math.format_degree_in_sign(lon_val)}), "
                f"Occupies: {kp_math.ordinal(house)} House, Owns: {owns_text}"
                f"{', Retrograde: Yes' if retro else ''}"
            ),
        })
    return facts

def _classify(house, positive_set, negative_set):
    if house in positive_set: return "positive"
    if house in negative_set: return "negative"
    return "neutral"

def compute_step_breakdown(star_lord, sub_lord, planet_houses, ownership, planets, positive_set, negative_set):
    """
    KP signification of the DECIDING planet = the sub lord of the key house's cusp
    (`sub_lord`), read through the star it sits in (`star_lord`). Steps follow the classical
    KP order of strength, and the weights are +-4 / +-3 / +-2 / +-1:

      1. houses occupied by its Star Lord        (weight 4)
      2. house occupied by the planet itself     (weight 3)
      3. houses owned by its Star Lord           (weight 2)
      4. houses owned by the planet itself       (weight 1)

    Ownership steps (3 and 4) are CAPPED: the weight counts once for "any owned house is
    positive" and once for "any owned house is negative", never once per house. If both are
    present the step is flagged mixed/volatile instead of looking neutral.
    If the planet sits in its own star (star_lord == sub_lord), steps 2 and 4 would only repeat
    steps 1 and 3, so they are not counted a second time.
    """
    weights = {"positive": 1, "negative": -1, "neutral": 0}

    def occupation_step(step_no, label, planet, weight):
        house = planet_houses.get(planet, 0)
        cls = _classify(house, positive_set, negative_set)
        pts = weights[cls] * weight
        return {
            "step": step_no, "name": label, "planet": planet,
            "houses": [house], "weight": weight,
            "house_results": [{"house": house, "classification": cls, "points": pts}],
            "mixed": False, "skipped": False,
            "step_points": pts,
            "text": f"Step {step_no} ({label}): {planet} occupies the {kp_math.ordinal(house)} House -> {cls} -> {pts:+d}",
        }

    def ownership_step(step_no, label, planet, weight):
        owned = get_houses_owned_by_planet(planet, ownership, planets)
        results = [{"house": h, "classification": _classify(h, positive_set, negative_set)} for h in owned]
        has_pos = any(r["classification"] == "positive" for r in results)
        has_neg = any(r["classification"] == "negative" for r in results)
        mixed = has_pos and has_neg
        total = (weight if has_pos else 0) - (weight if has_neg else 0)
        if owned:
            detail = "; ".join(f"{kp_math.ordinal(r['house'])} House -> {r['classification']}" for r in results)
            if mixed:
                outcome = f"MIXED/VOLATILE (positive {weight:+d} and negative {-weight:+d}) = {total:+d}"
            elif has_pos:
                outcome = f"positive, counted once (not stacked) = {total:+d}"
            elif has_neg:
                outcome = f"negative, counted once (not stacked) = {total:+d}"
            else:
                outcome = "neutral = +0"
            text = f"Step {step_no} ({label}): {planet} owns {kp_math.format_house_list(owned)}: {detail} => {outcome}"
        else:
            text = f"Step {step_no} ({label}): {planet} owns no house cusps = 0"
        return {
            "step": step_no, "name": label, "planet": planet,
            "houses": owned, "weight": weight,
            "house_results": results, "mixed": mixed, "skipped": False,
            "step_points": total, "text": text,
        }

    def repeated_step(step_no, label, planet, weight, same_as):
        return {
            "step": step_no, "name": label, "planet": planet,
            "houses": [], "weight": weight,
            "house_results": [], "mixed": False, "skipped": True,
            "step_points": 0,
            "text": f"Step {step_no} ({label}): {planet} sits in its own star, so this repeats Step {same_as} and is not counted again = 0",
        }

    own_star = (star_lord == sub_lord)
    steps = [
        occupation_step(1, "Star Lord Occupation", star_lord, 4),
        repeated_step(2, "Cusp Sub Lord Occupation", sub_lord, 3, 1) if own_star
            else occupation_step(2, "Cusp Sub Lord Occupation", sub_lord, 3),
        ownership_step(3, "Star Lord Ownership", star_lord, 2),
        repeated_step(4, "Cusp Sub Lord Ownership", sub_lord, 1, 3) if own_star
            else ownership_step(4, "Cusp Sub Lord Ownership", sub_lord, 1),
    ]
    return steps, sum(s["step_points"] for s in steps)

def decide_verdict(score, steps, is_retrograde, deciding_planet, retro_who=""):
    """
    Turns the score into a verdict.
      * Definitive thresholds are +-6.
      * With the step weights (4/3/2/1) a score of +-6 or more can only happen when the two
        occupation steps (the strongest KP levels) agree with it, so no extra guard is needed.
      * Retrogression is treated as a DELAY indicator, never as a denial (this is a deliberate
        project choice: classical sources are split on whether retrograde denies or only delays
        an event - see decision.retrograde_rule_note - so this bot always reads it as delay).
      * is_retrograde is true if the deciding planet OR its Star Lord is retrograde; retro_who
        names which one(s), for the text below.
    """
    classes = [r["classification"] for st in steps for r in st["house_results"]]
    has_pos, has_neg = "positive" in classes, "negative" in classes
    who = retro_who or deciding_planet
    retro_note = f" {who} is retrograde, so expect delay or obstruction." if is_retrograde else ""

    if score >= 6:
        if is_retrograde:
            return (f"YES WITH DELAYS. Positives dominate (Score: +{score}) but {who} is retrograde, "
                    f"so the result cannot be called definitive. Expect success only after delay or obstacles.")
        return f"DEFINITIVE YES. Strong positive dominance (Score: +{score}). Success is likely, but no chart is infallible."
    if 1 <= score <= 5:
        return (f"YES WITH DELAYS. Positives slightly outweigh negatives (Score: +{score}). "
                f"Expect success but with obstacles." + retro_note)
    if score == 0:
        if has_pos and has_neg:
            return ("MIXED / CONFLICTING. Supporting and opposing influences cancel out (Score: 0). "
                    "The outcome is uncertain and may swing either way." + retro_note)
        return ("MIXED / UNCLEAR. The chart shows no strong link to the houses of this question (Score: 0). "
                "The outcome cannot be judged from this chart." + retro_note)
    # score < 0: negative dominance
    if is_retrograde:
        return (f"DELAYED, NOT DENIED. The chart leans negative (Score: {score}), and {who} is retrograde. "
                f"This project reads retrograde as delay rather than outright denial, so the matter is read as "
                f"delayed, not refused - expect it to move only once {who} turns direct, or recheck with a "
                f"fresh chart closer to the expected time.")
    if -5 <= score <= -1:
        return f"UNFAVORABLE / NO. Negatives overpower positives or lack strong support (Score: {score})."
    return (f"DEFINITIVE NO. Strong negative dominance (Score: {score}). The chart leans heavily "
            f"against the event. Note: strongly negative charts have historically been the hardest to call, "
            f"so read this as a strong lean, not a certainty.")

def _verdict_class(verdict):
    v = verdict.upper()
    if v.startswith("DELAYED"): return "DELAYED"
    if v.startswith("MIXED"): return "MIXED"
    if v.startswith("UNFAVORABLE") or v.startswith("DEFINITIVE NO") or v.startswith("NO"): return "NO"
    return "YES"

# --- THE MASTER PIPELINE ---
def transit_confirmation(cusps, positive_set, key_house, deciding_planet, deciding_star,
                         ruling_planets, planets_now, retrogrades_now=None):
    """Gochar (transit) cross-check, read against the HORARY chart's own houses.

    For the moment `planets_now` describes, finds where the chart's key significators are
    transiting and whether that supports the question:
      1. Transit Moon: its horary house, and whether its star/sub lord is one of the chart's
         fruitful significators (deciding planet, deciding star lord, ruling planets).
      2. Transit deciding planet: whether it transits a positive house.
      3. Transit deciding star lord: whether it transits a positive house.
      4. Ruling planets currently transiting the key house.
    REPORT-ONLY: the classification never changes the verdict. Transits are read against the
    horary chart's houses because this bot has no natal chart to read them against.
    """
    pos = set(positive_set)
    rp = set(ruling_planets or [])
    retro = retrogrades_now or {}
    fruitful = {deciding_planet, deciding_star} | rp
    checks = []  # (supportive: bool, text: str)

    def house_of(p):
        lon = planets_now.get(p)
        if lon is None:
            return None
        try:
            return kp_math.get_house_from_cusps(lon, cusps)
        except Exception:
            return None

    def retro_note(p):
        return " (retrograde in transit: delay indicated, not denial)" if retro.get(p) else ""

    # 1. Transit Moon
    m_lon = planets_now.get("Moon")
    if m_lon is None:
        checks.append((False, "Transit Moon position unavailable."))
    else:
        m_house = house_of("Moon")
        m_star = kp_math.get_star_lord(m_lon)
        m_sub = kp_math.get_sub_lord(m_lon)
        links = [x for x in (m_star, m_sub) if x in fruitful]
        ok = (m_house in pos) or bool(links)
        why = ("transits a positive house" if m_house in pos else
               "its star/sub lord is a fruitful significator (" + "/".join(links) + ")" if links else
               "no link to the question houses")
        checks.append((ok, f"Transit Moon in horary house {m_house} (star {m_star}, sub {m_sub}): "
                           f"{'supportive' if ok else 'not supportive'} - {why}."))

    # 2 & 3. Transit deciding planet and its star lord (distinct planets only).
    seen = set()
    for p, label in ((deciding_planet, "the deciding planet"), (deciding_star, "its Star Lord")):
        if p in seen:
            continue
        seen.add(p)
        h = house_of(p)
        ok = h in pos
        checks.append((ok, f"Transit {p} ({label}) in horary house {h}{retro_note(p)}: "
                           f"{'supportive - transits a positive house' if ok else 'not in a positive house'}."))

    # 4. Ruling planets transiting the key house.
    key_transits = sorted(p for p in rp if p in planets_now and house_of(p) == key_house)
    ok = bool(key_transits)
    checks.append((ok, f"Ruling planets transiting the key {kp_math.ordinal(key_house)} house: "
                       + (", ".join(key_transits) + " - supportive." if ok else "none - not supportive.")))

    score = sum(1 for ok, _ in checks if ok)
    total = len(checks)
    ratio = score / total if total else 0
    classification = "supportive" if ratio >= 0.75 else "mixed" if ratio >= 0.25 else "not supportive"
    summary = (f"Transit check {score}/{total} supportive: the current gochar is {classification} of the "
               f"question. This is a cross-check only and does not change the verdict.")
    return {
        "classification": classification, "score": f"{score}/{total}",
        "findings": [t for _, t in checks], "text": " ".join(t for _, t in checks) + " " + summary,
        "note": ("Transits are read against the horary chart's own houses (no natal chart is available). "
                 "A retrograde transit indicates delay, never denial, per this project's convention."),
    }


def execute_kp_reading(city, horary_number, positive_houses, negative_houses, key_house=None,
                       as_of=None, coords=None, chart_time_mode="query", log=True, include_timing=True):
    """
    as_of            : aware UTC datetime of the question (default: now). Lets you replay old charts.
    coords           : (lat, lon) to skip the geocoder (used by tests/backtests).
    chart_time_mode  : "query"  -> planets at the query moment, cusps from the number (KP convention, old behaviour)
                       "horary" -> planets at the moment the number's Ascendant rises (cusps and planets share one moment)
    log              : write one JSON file per reading to ./logs
    include_timing   : add Vimshottari dasha/bhukti timing (timing_engine.py). False = skip it entirely.
    """
    if chart_time_mode not in ("query", "horary"):
        return {"error": "chart_time_mode must be 'query' or 'horary'"}
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    query_jd = ephemeris_utils.to_jd(as_of)

    def _parse_houses(h_input):
        if not h_input: return set()
        if isinstance(h_input, list): return set(int(str(x).strip()) for x in h_input if str(x).strip().isdigit())
        if isinstance(h_input, str): return set(int(x) for x in re.findall(r'\d+', h_input))
        if isinstance(h_input, dict):
            vals = []
            for v in h_input.values():
                if isinstance(v, list): vals.extend(v)
                elif isinstance(v, str): vals.extend(re.findall(r'\d+', v))
            return set(int(x) for x in vals if str(x).isdigit())
        return set()

    positive_set = _parse_houses(positive_houses)
    negative_set = _parse_houses(negative_houses)

    # The "key house": the cusp whose SUB LORD decides this kind of question (default 11 = fulfilment of desire)
    try:
        key_house = int(key_house)
    except (TypeError, ValueError):
        key_house = 11
    if not 1 <= key_house <= 12:
        key_house = 11

    lat, lon = coords if coords else location_engine.get_coordinates(city)
    if lat is None or lon is None: return {"error": "Location not found or GPS block active."}
    
    asc_data = kp_math.get_horary_chart(horary_number)
    if "error" in asc_data: return asc_data
    target_asc = asc_data["ascendant_longitude"]
    horary_asc_lord = asc_data["sign_lord"]
    horary_sign = asc_data["sign"]
    horary_sub_lord = asc_data["sub_lord"]
    horary_star_lord = asc_data["star_lord"]  # the fixed Nakshatra lord from the 1-249 table
    
    # --- 1. Cusps, and the sign on every cusp ---
    try:
        cusps, horary_jd = calculate_horary_cusps(target_asc, lat, lon, query_jd)
    except ValueError as e:
        return {"error": str(e)}
    cusp_facts = kp_math.build_cusp_facts(cusps)

    # --- 2. House ownership: cusp sign -> ruling planet ---
    ownership = kp_math.build_house_ownership(cusp_facts)

    # --- 3. Planets: sign (degree // 30), house from cusp boundaries ---
    planet_jd = query_jd if chart_time_mode == "query" else horary_jd
    planets, retrogrades = ephemeris_utils.planets_at(planet_jd)
    planet_houses = {p: kp_math.get_house_from_cusps(lon_val, cusps) for p, lon_val in planets.items()}
    planet_facts = build_planet_facts(planets, retrogrades, cusps, ownership)

    # --- 4. The deciding planet: SUB LORD of the key house's cusp, read through the star it sits in ---
    key_cusp = cusp_facts[key_house - 1]
    cusp_sub_lord = key_cusp["sub_lord"]
    deciding_planet = get_true_agent(cusp_sub_lord, planets)              # Rahu/Ketu act through their agent
    deciding_star_raw = kp_math.get_star_lord(planets[deciding_planet])   # the star the PLANET sits in (not the cusp's star)
    deciding_star = get_true_agent(deciding_star_raw, planets)
    planet_retro = bool(retrogrades.get(deciding_planet, False))
    star_retro = bool(retrogrades.get(deciding_star, False))
    is_retrograde = planet_retro or star_retro
    if planet_retro and star_retro:
        retro_who = f"the deciding planet ({deciding_planet}) and its Star Lord ({deciding_star})"
    elif planet_retro:
        retro_who = f"the deciding planet ({deciding_planet})"
    elif star_retro:
        retro_who = f"the deciding planet's Star Lord ({deciding_star})"
    else:
        retro_who = ""

    live_asc = get_live_ascendant(lat, lon, as_of)
    rp_asc_sign_lord = get_sign_lord(live_asc)
    rp_asc_star_lord = get_star_lord(live_asc)
    rp_asc_sub_lord = kp_math.get_sub_lord(live_asc)

    moon_lon = planets["Moon"]
    # Ruling planets belong to the moment of the question, so the RP Moon always comes from query time
    rp_moon_lon = moon_lon if chart_time_mode == "query" else ephemeris_utils.planets_at(query_jd)[0]["Moon"]
    rp_moon_sign_lord = get_sign_lord(rp_moon_lon)
    rp_moon_star_lord = get_star_lord(rp_moon_lon)
    rp_moon_sub_lord = kp_math.get_sub_lord(rp_moon_lon)
    day_name, day_lord = get_current_day_lord(lon, as_of)
    current_tithi = get_panchang_tithi(planets["Sun"], moon_lon)
    
    saturn_lon = planets["Saturn"]
    dist = abs(moon_lon - saturn_lon)
    if dist > 180: dist = 360 - dist
    punarphoo_active = dist <= 3.33 

    # Ruling-planet confirmation (informational only - it does not change the score)
    rp_names = {rp_asc_sign_lord, rp_asc_star_lord, rp_asc_sub_lord,
                rp_moon_sign_lord, rp_moon_star_lord, rp_moon_sub_lord, day_lord}
    rp_support = (deciding_planet in rp_names) or (deciding_star in rp_names)
    sub_in_rp = cusp_sub_lord in rp_names or deciding_planet in rp_names
    star_in_rp = deciding_star_raw in rp_names or deciding_star in rp_names
    rp_text = (f"Ruling planets (Ascendant sign/star/sub lord, Moon sign/star/sub lord, day lord): {', '.join(sorted(rp_names))}. "
               f"Ruling planet check (confirmation only, not scored): Cusp Sub Lord {deciding_planet} is "
               f"{'' if sub_in_rp else 'not '}among the ruling planets; its Star Lord {deciding_star} is "
               f"{'' if star_in_rp else 'not '}among the ruling planets.")

    # --- 5. Scoring and verdict, fully in Python ---
    step_breakdown, score = compute_step_breakdown(
        deciding_star, deciding_planet, planet_houses, ownership, planets, positive_set, negative_set
    )
    verdict = decide_verdict(score, step_breakdown, is_retrograde, deciding_planet, retro_who)
    if _verdict_class(verdict) == "YES" and not rp_support:
        verdict += (f" (Ruling Planets do not confirm this: neither the deciding planet ({deciding_planet}) "
                    f"nor its Star Lord ({deciding_star}) is a Ruling Planet. Per KP, an event is unlikely to "
                    f"materialize without Ruling Planet support, so treat this YES as unconfirmed.)")
    # --- 5b. Secondary KP checks: 11th-CSL fulfillment + Moon genuineness ---
    # Both are REPORTED SIGNALS ONLY: appended as cautions/confirmations, logged for
    # backtesting, and never change the verdict class.
    # Sources: KP Reader VI - "The 11th house shows fulfilment of desire" (11th-CSL
    # passages); the Moon-reflects-the-querent\'s-mind genuineness check.
    verdict_class = _verdict_class(verdict)

    # (a) 11th cusp Sub Lord fulfillment check. Skipped as redundant when the key
    # house itself is 11 (then the 11th CSL IS the deciding planet).
    eleventh = {"applicable": key_house != 11}
    if key_house != 11:
        csl11_raw = cusp_facts[10]["sub_lord"]
        csl11 = get_true_agent(csl11_raw, planets)
        csl11_star_raw = kp_math.get_star_lord(planets[csl11])
        csl11_star = get_true_agent(csl11_star_raw, planets)
        _, score11 = compute_step_breakdown(
            csl11_star, csl11, planet_houses, ownership, planets, positive_set, negative_set
        )
        csl11_retro = bool(retrogrades.get(csl11, False)) or bool(retrogrades.get(csl11_star, False))
        cls11 = "confirms" if score11 >= 6 else ("contradicts" if score11 <= -6 else "neutral")
        eleventh.update({
            "cusp_sub_lord": csl11_raw, "deciding_planet": csl11,
            "deciding_planet_star_lord": csl11_star, "score": score11,
            "classification": cls11, "is_retrograde": csl11_retro,
            "source": "KP Reader VI: 'The 11th house shows fulfilment of desire'",
        })
        if verdict_class == "YES" and cls11 == "contradicts":
            verdict += (f" (Fulfillment check: the Sub Lord of the 11th cusp ({csl11}, score {score11:+d}) "
                        f"signifies the unfavourable houses, so fulfillment of the desire is doubtful - "
                        f"treat this YES as unconfirmed.)")
        elif verdict_class == "YES" and cls11 == "confirms":
            verdict += (f" (Fulfillment check: the Sub Lord of the 11th cusp ({csl11}, score {score11:+d}) "
                        f"also signifies the favourable houses, confirming fulfillment of the desire.)")
        elif verdict_class in ("NO", "DELAYED") and cls11 == "confirms":
            verdict += (f" (Note: the Sub Lord of the 11th cusp of fulfillment ({csl11}) does signify the "
                        f"favourable houses, but the key-house significations rule against the matter, "
                        f"so the verdict stands.)")
        if csl11_retro:
            verdict += (f" (The 11th-cusp Sub Lord ({csl11}) or its Star Lord is retrograde, indicating "
                        f"delay or obstruction in fulfillment - read as delay, not denial.)")

    # (b) Moon genuineness check: the Moon reflects the querent\'s mind and should
    # connect with the houses of the question. Reported only - never refuses judgment.
    moon_star_raw = kp_math.get_star_lord(planets["Moon"])
    moon_star = get_true_agent(moon_star_raw, planets)
    _, moon_score = compute_step_breakdown(
        moon_star, "Moon", planet_houses, ownership, planets, positive_set, negative_set
    )
    moon_reflected = moon_score >= 1
    genuineness = {
        "moon_star_lord": moon_star_raw, "moon_star_lord_agent": moon_star,
        "moon_house": planet_houses.get("Moon"), "score": moon_score,
        "reflected": moon_reflected,
        "source": "KP Reader VI: verify the Moon reflects the querent\'s mind/question before judging",
    }
    if moon_score <= -1:
        verdict += (" (Genuineness check: the Moon does not connect with the houses of this question, "
                    "so the question may not be genuinely rooted - the judgment above stands, but treat "
                    "it with reserve.)")

    step_1_house = planet_houses.get(deciding_star, 0)
    step_2_house = planet_houses.get(deciding_planet, 0)
    step_3_houses = get_houses_owned_by_planet(deciding_star, ownership, planets)
    step_4_houses = get_houses_owned_by_planet(deciding_planet, ownership, planets)
    all_signified_houses = [step_1_house, step_2_house] + step_3_houses + step_4_houses

    house_ownership_text = {
        p: f"{p} owns {kp_math.format_house_list(hs)}" for p, hs in ownership.items()
    }

    node_rule, node_rule_text, star_rule_text = None, "", ""
    if cusp_sub_lord != deciding_planet:
        _, node_rule, node_rule_text = get_node_agent_info(cusp_sub_lord, planets)
    if deciding_star_raw != deciding_star:
        star_rule_text = get_node_agent_info(deciding_star_raw, planets)[2]

    ruling_planets = {
        "asc_sign_lord": rp_asc_sign_lord, "asc_star_lord": rp_asc_star_lord, "asc_sub_lord": rp_asc_sub_lord,
        "moon_sign_lord": rp_moon_sign_lord, "moon_star_lord": rp_moon_star_lord, "moon_sub_lord": rp_moon_sub_lord,
        "day_lord": day_lord,
    }

    # --- Optional timing (Vimshottari at the chart moment). Never allowed to break a reading. ---
    timing = None
    if include_timing:
        try:
            timing = timing_engine.compute_timing(
                planets, planet_houses, ownership, positive_set, negative_set,
                chart_time=ephemeris_utils.from_jd(planet_jd), agent_fn=get_true_agent,
                verdict_class=_verdict_class(verdict), ruling_planets=rp_names)
        except Exception as e:
            timing = {"error": f"Timing could not be computed: {type(e).__name__}: {e}"}

    # --- Optional transit confirmation (gochar cross-check). Never allowed to break a reading. ---
    # Transit is read at the QUERY moment (as_of), not wall-clock now, so a reading is fully
    # reproducible from its inputs (same inputs + same as_of -> identical output).
    transit = None
    try:
        planets_now, retro_now = transit_engine.get_planets_at(as_of)
        transit = transit_confirmation(cusps, positive_set, key_house, deciding_planet, deciding_star,
                                       rp_names, planets_now, retro_now)
        transit["as_of_utc"] = as_of.isoformat()
        nxt = (timing or {}).get("next_supportive_antara") or {}
        if nxt.get("start"):
            when = datetime.fromisoformat(nxt["start"])
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            planets_fut, retro_fut = transit_engine.get_planets_at(when)
            transit["at_next_antara"] = transit_confirmation(
                cusps, positive_set, key_house, deciding_planet, deciding_star,
                rp_names, planets_fut, retro_fut)
            transit["at_next_antara"]["window"] = f"{nxt.get('start')} to {nxt.get('end')}"
    except Exception as e:
        transit = {"error": f"Transit check could not be computed: {type(e).__name__}: {e}"}

    decision = {
        "key_house": key_house,
        "key_house_cusp": key_cusp["summary"],
        "cusp_sub_lord": cusp_sub_lord,
        "deciding_planet": deciding_planet,
        "deciding_planet_star_lord": deciding_star,
        "deciding_planet_is_retrograde": is_retrograde,
        "retrograde_who": retro_who,
        "retrograde_rule_note": ("Retrograde is treated as a delay indicator only in this project, never as an "
                                  "automatic denial - classical KP sources disagree on whether it denies or "
                                  "merely delays, so a negative score with a retrograde deciding planet or Star "
                                  "Lord is reported as DELAYED, NOT DENIED rather than as NO."),
        "ruling_planet_support": rp_support,
        "node_agent_rule": node_rule,
        "note": (f"{cusp_sub_lord} is a node and acts through its agent {deciding_planet} ({node_rule_text}). " if cusp_sub_lord != deciding_planet else "")
                + (f"{deciding_star_raw} (the Star Lord) is a node and acts through {deciding_star} ({star_rule_text}). " if deciding_star_raw != deciding_star else "")
                + (f"{deciding_planet} sits in its own star, so its occupation and ownership are counted once."
                   if deciding_star == deciding_planet else ""),
        "eleventh_csl_check": eleventh,
        "moon_genuineness": genuineness,
        "transit_confirmation": transit,
    }

    # Text-only payload for the LLM: no raw longitudes, nothing left to calculate.
    ai_facts = {
        "verdict": verdict,
        "kp_score": score,
        "is_retrograde": is_retrograde,
        "punarphoo": punarphoo_active,
        "horary": {
            "number": horary_number,
            "ascendant_sign": horary_sign,
            "ascendant_sign_lord": horary_asc_lord,
            "ascendant_star_lord": horary_star_lord,
            "ascendant_sub_lord": horary_sub_lord,
        },
        "decision": decision,
        "ruling_planet_check": {
            "cusp_sub_lord_in_ruling_planets": sub_in_rp,
            "star_lord_in_ruling_planets": star_in_rp,
            "text": rp_text,
        },
        "secondary_signals": {
            "eleventh_csl_fulfillment": (
                "Not applicable: the key house is the 11th, so the 11th CSL is the deciding planet itself."
                if not eleventh["applicable"] else
                f"11th CSL {eleventh['deciding_planet']} (cusp sub lord {eleventh['cusp_sub_lord']}, star lord "
                f"{eleventh['deciding_planet_star_lord']}) scores {eleventh['score']:+d} against the question houses: "
                f"{eleventh['classification']}. Retrograde: {eleventh['is_retrograde']}."
            ),
            "moon_genuineness": (
                f"Moon sits in house {genuineness['moon_house']}, star lord {genuineness['moon_star_lord']}: "
                f"signification score {genuineness['score']:+d} against the question houses - "
                + ("reflected: the question reads as genuine." if genuineness["reflected"]
                   else "not reflected: treat the question\'s genuineness with reserve (judgment still given)." if genuineness["score"] <= -1
                   else "neutral: no clear connection either way.")
            )
        },
        "target_positive_houses": sorted(positive_set),
        "target_negative_houses": sorted(negative_set),
        "step_breakdown": step_breakdown,
        "house_cusps": [f["summary"] for f in cusp_facts],
        "house_ownership": house_ownership_text,
        "planets": [f["summary"] for f in planet_facts],
        "panchang": {"day_name": day_name, "tithi": current_tithi},
        "ruling_planets": ruling_planets,
    }
    if timing is not None:
        ai_facts["timing"] = timing
    if transit is not None:
        ai_facts["transit_confirmation"] = transit
        
    chart_time = {
        "mode": chart_time_mode,
        "query_utc": as_of.isoformat(),
        "cusp_moment_utc": ephemeris_utils.from_jd(horary_jd).isoformat(),
        "gap_minutes": round((horary_jd - query_jd) * 1440.0, 1),
        "lat": lat, "lon": lon,
    }

    result = {
        "chart_time": chart_time,
        "verdict": verdict, "kp_score": score, "horary_number": horary_number, "horary_sign": horary_sign,
        "horary_ascendant_longitude": target_asc, "horary_asc_lord": horary_asc_lord,
        "sub_lord": horary_sub_lord, "star_lord": horary_star_lord, "is_retrograde": is_retrograde,
        "all_houses": list(set(all_signified_houses)), "moon_star_lord": get_star_lord(moon_lon),
        "punarphoo": punarphoo_active,
        "key_house": key_house, "cusp_sub_lord": cusp_sub_lord, "deciding_planet": deciding_planet,
        "horary_chart": {
            "number": horary_number,
            "sign": horary_sign,
            "ascendant_longitude": target_asc,
            "sign_lord": horary_asc_lord,
            "star_lord": horary_star_lord,
            "sub_lord": horary_sub_lord
        },
        "significators": {
            "true_star_lord": deciding_star,
            "true_sub_lord": deciding_planet,
            "step_1_house": step_1_house,
            "step_2_house": step_2_house,
            "step_3_houses": step_3_houses,
            "step_4_houses": step_4_houses
        },
        "step_breakdown": step_breakdown,
        "cusp_facts": cusp_facts,
        "planet_facts": planet_facts,
        "house_ownership": ownership,
        "panchang": {"day_name": day_name, "tithi": current_tithi},
        "ruling_planets": ruling_planets, "timing": timing,
        "chart_data": {"cusps": list(cusps), "planets": planets, "planet_houses": planet_houses},
        "ai_facts": ai_facts,
    }

    if log:
        kp_logger.log_reading({
            "inputs": {"city": city, "horary_number": horary_number, "positive": sorted(positive_set),
                       "negative": sorted(negative_set), "key_house": key_house,
                       "mode": chart_time_mode},
            "chart_time": chart_time,
            "verdict": verdict, "score": score,
            "decision": decision, "ai_facts": ai_facts,
        })
    return result