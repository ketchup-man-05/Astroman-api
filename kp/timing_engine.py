"""
timing_engine.py - Vimshottari dasha/bhukti timing for a KP horary chart.

Convention (as chosen by the project owner):
  * The Moon's position in the chart sets the Vimshottari dasha at the chart moment.
  * A dasha/bhukti "supports" the question when BOTH its Mahadasha lord and its Bhukti lord
    signify at least one POSITIVE house of the question.
  * Each supportive bhukti is subdivided into its 9 antaras (in Vimshottari order, starting
    with the bhukti lord). An antara "supports" when ALL THREE lords (Mahadasha, Bhukti,
    Antara) signify at least one POSITIVE house. Ruling-Planet confirmation works the same
    way: a period is fruitful when at least one of its lords is a Ruling Planet.
  * A planet signifies: the house it occupies, the houses it owns, and the same two things for
    its Star Lord (the KP signification chain, same as the 4 scoring steps).
    Rahu/Ketu own no signs: their ownership is read through their agent (agent_fn).

Pure Python: no swisseph needed. Optional: chart_caster.execute_kp_reading(include_timing=False)
skips this module completely.
"""
from datetime import timedelta
from kp import kp_math

YEAR_DAYS = 365.25                      # length of a dasha year
DASHA_SEQUENCE = kp_math.DASHA_SEQUENCE
TOTAL_YEARS = kp_math.TOTAL_DASHA_YEARS


def _fmt_span(days):
    years = int(days // YEAR_DAYS)
    rem = days - years * YEAR_DAYS
    month_len = YEAR_DAYS / 12.0
    months = int(rem // month_len)
    d = int(rem - months * month_len)
    return f"{years}y {months}m {d}d"


def moon_dasha_state(moon_lon):
    """(index into DASHA_SEQUENCE of the running Mahadasha, fraction of the nakshatra already elapsed)."""
    arc = kp_math._degree_to_arcseconds(moon_lon)
    span = kp_math.NAKSHATRA_SPAN_ARCSECONDS
    return (arc // span) % 9, (arc % span) / span


def build_periods(moon_lon, chart_time, horizon_years=40):
    """
    Yields every dasha/bhukti in time order, starting with the Mahadasha that is running at
    chart_time (its earlier bhuktis are included; callers skip those that already ended).
    """
    md_idx, frac = moon_dasha_state(moon_lon)
    first_years = DASHA_SEQUENCE[md_idx][1]
    md_start = chart_time - timedelta(days=frac * first_years * YEAR_DAYS)
    limit = chart_time + timedelta(days=horizon_years * YEAR_DAYS)
    k = 0
    while md_start <= limit:
        idx = (md_idx + k) % 9
        md_lord, md_years = DASHA_SEQUENCE[idx]
        md_end = md_start + timedelta(days=md_years * YEAR_DAYS)
        b_start = md_start
        for j in range(9):
            b_lord, b_years = DASHA_SEQUENCE[(idx + j) % 9]
            b_end = md_end if j == 8 else b_start + timedelta(days=md_years * b_years / TOTAL_YEARS * YEAR_DAYS)
            yield {"md": md_lord, "bd": b_lord, "start": b_start, "end": b_end,
                   "md_start": md_start, "md_end": md_end}
            b_start = b_end
        md_start = md_end
        k += 1


def build_antaras(bhukti):
    """
    Subdivide one bhukti period (a dict from build_periods) into its 9 antaras in order.
    The antara sequence starts with the bhukti lord and follows Vimshottari order.
    Duration: antara = bhukti_days * antara_lord_years / TOTAL_YEARS.
    The last antara is pinned to the bhukti's end so float drift cannot open a gap.
    """
    md_years = next(y for l, y in DASHA_SEQUENCE if l == bhukti["md"])
    bd_years = next(y for l, y in DASHA_SEQUENCE if l == bhukti["bd"])
    bhukti_days = md_years * bd_years / TOTAL_YEARS * YEAR_DAYS
    start_idx = next(i for i, (l, _) in enumerate(DASHA_SEQUENCE) if l == bhukti["bd"])
    out, a_start = [], bhukti["start"]
    for j in range(9):
        a_lord, a_years = DASHA_SEQUENCE[(start_idx + j) % 9]
        a_end = bhukti["end"] if j == 8 else a_start + timedelta(days=bhukti_days * a_years / TOTAL_YEARS)
        out.append({"md": bhukti["md"], "bd": bhukti["bd"], "ad": a_lord,
                    "start": a_start, "end": a_end})
        a_start = a_end
    return out


def planet_significations(planet, planets, planet_houses, ownership, agent_fn):
    """Houses a planet signifies: its own occupation/ownership + its Star Lord's occupation/ownership."""
    def occ(x):
        h = planet_houses.get(x)
        return {h} if h else set()

    def own(x):
        return set(ownership.get(agent_fn(x, planets), []))

    star = kp_math.get_star_lord(planets[planet])
    houses = occ(planet) | own(planet) | occ(star) | own(star)
    return {"star_lord": star, "houses": sorted(houses)}


def compute_timing(planets, planet_houses, ownership, positive_set, negative_set, chart_time, agent_fn,
                   verdict_class=None, horizon_years=40, max_upcoming=3, ruling_planets=None):
    """
    ruling_planets: the set of this chart's Ruling Planets (Day Lord + Asc/Moon sign/star/sub lords).
    Per KP, RPs are a FILTER: a dasha/bhukti lord only counts as a "fruitful significator" if it both
    signifies a positive house AND is a Ruling Planet. next_supportive therefore prefers a period where
    at least one of the two lords (Mahadasha or Bhukti) is an RP; if none exists within the search
    horizon, it falls back to a signification-only match and says so explicitly (no silent fallback).
    """
    pos, neg = set(positive_set), set(negative_set)
    rp = set(ruling_planets) if ruling_planets else set()
    sig = {p: planet_significations(p, planets, planet_houses, ownership, agent_fn) for p in planets}

    def lord_info(p):
        hs = sig[p]["houses"]
        return {"planet": p, "star_lord": sig[p]["star_lord"], "houses": hs,
                "positive": sorted(set(hs) & pos), "negative": sorted(set(hs) & neg)}

    def describe(per):
        m, b = lord_info(per["md"]), lord_info(per["bd"])
        qualifies = bool(m["positive"]) and bool(b["positive"])
        rp_supported = qualifies and ((per["md"] in rp) or (per["bd"] in rp))
        also_neg = bool(m["negative"] or b["negative"])
        s, e = per["start"].date().isoformat(), per["end"].date().isoformat()

        def part(x):
            posr = kp_math.format_house_list(x["positive"]) if x["positive"] else "no positive house"
            return f"{x['planet']} signifies {kp_math.format_house_list(x['houses'])} (positive: {posr})"

        verdict = "both lords signify positive houses" if qualifies else "does not support (a lord signifies no positive house)"
        extra = ""
        if qualifies and also_neg:
            negs = sorted(set(m["negative"]) | set(b["negative"]))
            extra = f"; also touches negative {kp_math.format_house_list(negs)}"
        rp_text = ""
        if qualifies:
            rp_text = (" Both lords are also Ruling Planets, so this is a fruitful (RP-confirmed) period."
                       if (per["md"] in rp and per["bd"] in rp) else
                       f" {per['md'] if per['md'] in rp else per['bd']} is also a Ruling Planet, so this is a "
                       "fruitful (RP-confirmed) period." if rp_supported else
                       " Neither lord is a Ruling Planet for this chart, so KP would not call this a fruitful period.")
        return {
            "maha": per["md"], "bhukti": per["bd"], "start": s, "end": e,
            "maha_start": per["md_start"].date().isoformat(), "maha_end": per["md_end"].date().isoformat(),
            "maha_lord": m, "bhukti_lord": b,
            "qualifies": qualifies, "rp_supported": rp_supported, "also_touches_negative": also_neg,
            "text": f"{per['md']} Mahadasha / {per['bd']} Bhukti ({s} to {e}): {part(m)}; {part(b)} -> {verdict}{extra}{rp_text}",
        }

    active, active_per, seen_active = None, None, False
    qualifying, rp_confirmed = [], []
    qualifying_raw, rp_confirmed_raw = [], []
    for per in build_periods(planets["Moon"], chart_time, horizon_years):
        if not seen_active:
            if per["start"] <= chart_time < per["end"]:
                active, active_per, seen_active = describe(per), per, True
            continue
        d = describe(per)
        if d["qualifies"]:
            qualifying.append(d)
            qualifying_raw.append(per)
            if d["rp_supported"]:
                rp_confirmed.append(d)
                rp_confirmed_raw.append(per)
        if len(rp_confirmed) >= max_upcoming or len(qualifying) >= max_upcoming * 4:
            break

    used_fallback = rp and not rp_confirmed and bool(qualifying)
    upcoming = (rp_confirmed if rp_confirmed else qualifying)[:max_upcoming]

    def describe_antara(a):
        m, b, ad = lord_info(a["md"]), lord_info(a["bd"]), lord_info(a["ad"])
        qualifies = bool(m["positive"]) and bool(b["positive"]) and bool(ad["positive"])
        rp_lords = [x for x in (a["md"], a["bd"], a["ad"]) if x in rp]
        rp_ok = qualifies and bool(rp_lords)
        s, e = a["start"].date().isoformat(), a["end"].date().isoformat()
        verdict = ("all three lords signify positive houses" if qualifies
                   else "does not support (the antara lord signifies no positive house)")
        rp_text = ""
        if qualifies:
            rp_text = (f" {', '.join(rp_lords)} {'is' if len(rp_lords) == 1 else 'are'} also Ruling "
                       f"Planet(s) - fruitful antara." if rp_ok else
                       " No antara lord is a Ruling Planet, so KP would not call this a fruitful antara.")
        return {
            "maha": a["md"], "bhukti": a["bd"], "antara": a["ad"],
            "start": s, "end": e, "_start_dt": a["start"], "_end_dt": a["end"],
            "antara_lord": {"planet": a["ad"], "star_lord": ad["star_lord"], "houses": ad["houses"],
                            "positive": ad["positive"], "negative": ad["negative"]},
            "qualifies": qualifies, "rp_supported": rp_ok,
            "text": f"{a['md']} MD / {a['bd']} BD / {a['ad']} AD ({s} to {e}): {a['ad']} signifies "
                    f"{kp_math.format_house_list(ad['houses'])} -> {verdict}{rp_text}",
        }

    raw_upcoming = (rp_confirmed_raw if rp_confirmed_raw else qualifying_raw)[:max_upcoming]
    for d, per in zip(upcoming, raw_upcoming):
        good = [x for x in (describe_antara(a) for a in build_antaras(per)) if x["qualifies"]]
        d["antaras"] = good
        d["antara_text"] = ("Supportive antaras within this bhukti: " + " | ".join(x["text"] for x in good)
                            if good else
                            "No antara within this bhukti has all three lords signifying positive houses.")

    next_supportive_antara = None
    for d in upcoming:
        for x in d["antaras"]:
            if x["_end_dt"] > chart_time:
                next_supportive_antara = x
                break
        if next_supportive_antara:
            break

    if active is not None and active_per is not None:
        active_antara = None
        for x in (describe_antara(a) for a in build_antaras(active_per)):
            if x["_start_dt"] <= chart_time < x["_end_dt"]:
                active_antara = x
                break
        active["active_antara"] = active_antara
        active["antara_text"] = ("Currently running antara: " + active_antara["text"] if active_antara
                                 else "The current antara could not be determined.")

    # _start_dt/_end_dt are working datetimes only: strip them so the payload stays JSON-serializable.
    for d in upcoming:
        for x in d["antaras"]:
            x.pop("_start_dt", None)
            x.pop("_end_dt", None)
    if active is not None and active.get("active_antara"):
        active["active_antara"].pop("_start_dt", None)
        active["active_antara"].pop("_end_dt", None)

    md_idx, frac = moon_dasha_state(planets["Moon"])
    md_lord, md_years = DASHA_SEQUENCE[md_idx]
    moon_lon = planets["Moon"]
    note = ("A period 'supports' the question when both its Mahadasha lord and Bhukti lord signify at least one positive "
            "house (own and Star Lord's occupied/owned houses; Rahu/Ketu ownership through their agent). It shows when the "
            "positive houses are activated; it does not by itself prove the event will happen. Supportive bhuktis are "
            "further divided into antaras: an antara supports only when all three lords (Mahadasha, Bhukti, Antara) "
            "signify a positive house, and the finest supportive window is reported as next_supportive_antara.")
    if verdict_class == "NO":
        note += " The chart's verdict is NO, so treat these only as periods when the positive houses are active."

    rp_note = ""
    if rp:
        rp_note = (" No Ruling-Planet-confirmed period was found in the searched range, so the periods below "
                   "only satisfy the house-signification test, not the RP filter." if used_fallback else
                   " Ruling Planets were used to filter for fruitful periods (a period needs a lord that is "
                   "also a Ruling Planet to be shown here), per the KP rule that RPs select the fruitful "
                   "significators." if rp_confirmed else "")

    return {
        "method": f"Vimshottari dasha from the Moon's position in the chart (dasha year = {YEAR_DAYS} days)",
        "ruling_planet_filter_applied": bool(rp) and not used_fallback,
        "chart_moment_utc": chart_time.isoformat(),
        "moon": {
            "sign": kp_math.get_sign_name(moon_lon),
            "degree_in_sign": kp_math.format_degree_in_sign(moon_lon),
            "star_lord": kp_math.get_star_lord(moon_lon),
            "mahadasha_at_chart_moment": md_lord,
            "balance_of_mahadasha": _fmt_span((1 - frac) * md_years * YEAR_DAYS),
        },
        "positive_houses": sorted(pos),
        "active": active,
        "next_supportive": upcoming[0] if upcoming else None,
        "next_supportive_antara": next_supportive_antara,
        "upcoming_supportive": upcoming,
        "significations": {p: {"star_lord": v["star_lord"], "houses": v["houses"]} for p, v in sig.items()},
        "note": (note if upcoming else note + f" No supporting period was found within {horizon_years} years.") + rp_note,
    }