"""Layer 2.5 — Moon genuineness gate (v5 lab pipeline only).

Sits between Layer 2 (routing) and Layer 3 (judgment). Casts the chart
READ-ONLY through the frozen engine and runs the KP Moon-genuineness suite
before any judgment is allowed:

  M1 (REMOVED per user ruling 2026-10-05): the old hard block (Moon's chain
      must signify an event house, else FAIL) had zero book support and
      blocked KSK's own correct YES. M1 now always passes; the check runs
      for the record but never fails.
  M2 (caution): Moon in the first or last navamsha of its sign
      (0°–3°20' / 26°40'–30°) — querent not serious / has lost hope.
      Source: Sharad Joshi, Krishnamurthy Padhdhati ch.XI (secondary tier).
  M3 (informational): Saturn/Mars occupying or aspecting (Vedic aspects)
      the 7th house. Source: practitioner forum post (weakest tier).
      Never changes the grade.

Grading: FAIL is disabled (M1 removed). CAUTION iff M2 fires, else PASS.
M3 is diagnostic only.

Gate (config.MOON_GATE_MODE):
  'hard' — FAIL blocks Layer 3; the pipeline returns OTHER with the
           MOON_GENUINENESS_FAIL modifier ("should not be judged").
  'flag' — the result is recorded as modifiers/notes; Layer 3 always runs.

Ruling note (2026-10-01): the 2026-09-25 standing design made genuineness a
reported signal only. The user's 2026-10-01 instruction ("only then it will
move to 3rd layer") overrules it to a hard gate for the v5 lab pipeline.
Measure block-rate and blocked-vs-passed accuracy on the 369 corpus before
trusting the gate — every hard gate tested so far has needed data.
"""

import os as _os
import re
import sys as _sys

_FROZEN = '/home/hatch/workspace/kp_phase0'
if _FROZEN not in _sys.path:
    _sys.path.insert(0, _FROZEN)
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

from kp import chart_caster  # noqa: E402  (frozen engine; read-only use)

NODES = {"Rahu", "Ketu"}
NAVPADA_MIN = 200  # one navamsha = 3°20' = 200 arc-minutes (exact)

# Vedic special aspects: houses counted inclusively from the planet's house.
_SPECIAL_ASPECTS = {"Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10)}

_M1_CITE = ("KP Step by Step (Punneswara Rao) §2.1; KP E-zine Apr 2009 "
            "'Reading a KP Horary Chart'")
_M2_CITE = "Sharad Joshi, Krishnamurthy Padhdhati ch.XI (secondary tier)"
_M3_CITE = "practitioner forum post (weakest tier; diagnostic only)"


def _facts_by_planet(reading):
    facts = {}
    for f in reading.get("planet_facts") or []:
        facts[f.get("planet")] = f
    return facts


def _agent(name, facts):
    """Resolve Rahu/Ketu to the agent recorded in planet_facts."""
    if name in NODES:
        ag = (facts.get(name) or {}).get("acts_as_agent_of")
        return ag or name
    return name


def _houses_of(name, facts):
    f = facts.get(name) or {}
    hs = set()
    h = f.get("house_occupied")
    if isinstance(h, int) and h:
        hs.add(h)
    # 2026-10-14 (Gemini 4 audit): Rahu/Ketu occupy a house and signify it
    # directly, in addition to their agent chain. The old code dropped the
    # node's own occupied house when it had an agent.
    for o in f.get("owns_houses") or []:
        if isinstance(o, int) and o:
            hs.add(o)
    return hs


def _moon_chain_houses(facts):
    """All houses the Moon signifies via its own occupation and its
    star-lord's / sub-lord's occupation + ownership (nodes via agents)."""
    moon = facts.get("Moon") or {}
    star = _agent(moon.get("star_lord"), facts)
    sub = _agent(moon.get("sub_lord"), facts)
    hs = _houses_of("Moon", facts) | _houses_of(star, facts) | _houses_of(sub, facts)
    # 2026-10-14 (Gemini 4 audit): when the star/sub lord is a node,
    # _agent() resolves to the agent and the node's OWN occupied house is
    # dropped. Add it back explicitly.
    for raw in (moon.get("star_lord"), moon.get("sub_lord")):
        if raw in NODES:
            hs |= _houses_of(raw, facts)
    return hs, {"moon_star_lord": moon.get("star_lord"), "star_agent": star,
                "moon_sub_lord": moon.get("sub_lord"), "sub_agent": sub,
                "moon_house": moon.get("house_occupied")}


def _deg_in_sign(deg_str):
    m = re.match(r"\s*(\d+)\s*°\s*(\d+)", str(deg_str or ""))
    if not m:
        return None
    return int(m.group(1)) + int(m.group(2)) / 60.0


def _aspects_house(planet, from_house, to_house):
    if from_house == to_house:
        return True
    rel = (to_house - from_house) % 12 + 1  # inclusive count
    if rel == 7:
        return True  # all planets aspect the 7th from themselves
    return rel in _SPECIAL_ASPECTS.get(planet, ())


def check(router_out, city, horary_number, as_of=None, coords=None):
    """Run the Moon-genuineness suite. Never raises; fail-open on errors."""
    checks = []
    try:
        success = set(router_out.get("success") or [])
        primary = router_out.get("primary_cusp")
        relevant = set(success)
        if isinstance(primary, int) and 1 <= primary <= 12:
            relevant.add(primary)
        if not relevant:
            return _result("PASS", [], "no event houses to check against; gate skipped open",
                           blocked=False, mode_note="n/a")

        reading = chart_caster.execute_kp_reading(
            city, int(horary_number), sorted(success),
            sorted(set(router_out.get("denial") or [])),
            key_house=int(primary) if primary else 11,
            as_of=as_of, coords=coords,
            chart_time_mode="query", log=False, include_timing=False)
        if not reading or "error" in reading:
            return _result("PASS", [], "chart unavailable; gate skipped open",
                           blocked=False, mode_note="n/a")
        facts = _facts_by_planet(reading)

        # ---- M1: REMOVED per user ruling 2026-10-05 ----
        # The old M1 (Moon's chain must touch a relevant house, else FAIL)
        # had zero book support and blocked KSK's own correct YES
        # (Reader III p.383). M1 now always passes; Moon genuineness is
        # diagnostic only (M2/M3). The check still runs for the record,
        # but never fails.
        moon_houses, chain = _moon_chain_houses(facts)
        matched = sorted(moon_houses & relevant)
        m1_pass = True  # M1 removed; always pass
        checks.append({
            "name": "M1-moon-reflects-question", "passed": m1_pass,
            "detail": (f"Moon chain (Moon in {chain['moon_house']}, star lord "
                       f"{chain['moon_star_lord']} via {chain['star_agent']}, sub lord "
                       f"{chain['moon_sub_lord']} via {chain['sub_agent']}) signifies "
                       f"{sorted(moon_houses)}; relevant houses {sorted(relevant)}; "
                       f"match: {matched or 'none'}. [M1 REMOVED per user ruling "
                       f"2026-10-05; diagnostic only]"),
        })

        # ---- M2: Moon in first/last navamsha (exact arc-minute arithmetic) ----
        deg = _deg_in_sign((facts.get("Moon") or {}).get("degree_in_sign"))
        # Convert to arc-minutes: deg is float degrees → ×60, compare to 200'.
        extreme = (deg is not None
                   and (deg * 60 < NAVPADA_MIN or deg * 60 > 1800 - NAVPADA_MIN))
        checks.append({
            "name": "M2-moon-sign-extreme", "passed": not extreme,
            "detail": (f"Moon at {deg:.2f}° in sign — "
                       f"{'first/last navamsha: querent may not be serious / may have lost hope' if extreme else 'not at sign extreme'}. [{_M2_CITE}]"
                       if deg is not None else "Moon degree unavailable."),
        })

        # ---- M3: Saturn/Mars vs 7th house (diagnostic only) ----
        occupants_7 = [p for p, f in facts.items()
                       if f.get("house_occupied") == 7]
        m3_notes = []
        for p in ("Saturn", "Mars"):
            f = facts.get(p) or {}
            h = f.get("house_occupied")
            if h == 7:
                m3_notes.append(f"{p} occupies the 7th house")
            elif isinstance(h, int) and h and _aspects_house(p, h, 7):
                m3_notes.append(f"{p} (in {h}) aspects the 7th house")
        checks.append({
            "name": "M3-saturn-mars-vs-7th", "passed": True,
            "detail": ("; ".join(m3_notes) + f". [{_M3_CITE}]" if m3_notes
                       else f"Saturn/Mars neither occupy nor aspect the 7th "
                            f"(occupants: {occupants_7 or 'none'}). [{_M3_CITE}]"),
        })

        # M1 removed per user ruling 2026-10-05: grade can never be FAIL from M1.
        # Only M2 (extreme) can cause CAUTION; otherwise PASS.
        if extreme:
            grade = "CAUTION"
        else:
            grade = "PASS"
        summary = "; ".join(
            f"{c['name']}: {'pass' if c['passed'] else 'CHECK'}" for c in checks)
        return _result(grade, checks, summary, blocked=None,
                       moon_houses=sorted(moon_houses), matched=matched)
    except Exception as e:  # fail open, like the other gates
        return _result("PASS", checks,
                       f"layer-2.5 error ({type(e).__name__}); gate skipped open",
                       blocked=False, mode_note="n/a")


def _result(grade, checks, summary, blocked=None, mode_note=None,
            moon_houses=None, matched=None):
    return {
        "genuineness": grade,
        "checks": checks,
        "summary": summary,
        "moon_houses": moon_houses or [],
        "matched_houses": matched or [],
        # 'blocked' is resolved by the pipeline from the config mode;
        # kept here for direct callers.
        "blocked": bool(blocked),
        "mode_note": mode_note,
        "report": {
            "genuineness": grade,
            "summary": summary,
            "checks": [{"name": c["name"], "passed": c["passed"],
                        "detail": c["detail"]} for c in checks],
        },
    }


# ---------------------------------------------------------------------------
# Standalone tester: Layer 2.5 only. No Layer 1/2/3 involved.
# Inputs: horary number + question time + city/coords + event key (or houses).
#   ~/workspace/kp_phase0/.venv/bin/python layer2_5_moon.py \
#       --number 42 --time "2026-10-01T10:30:00+05:30" \
#       --coords 28.61,77.21 --event job_get_service
#   ... --houses 2,6,10,11 --cusp 10        (instead of --event)
# ---------------------------------------------------------------------------
def _standalone():
    import argparse
    import json
    from datetime import datetime, timezone, timedelta

    ap = argparse.ArgumentParser(description="Test Layer 2.5 (Moon gate) only.")
    ap.add_argument("--number", type=int, required=True,
                    help="horary number 1-249")
    ap.add_argument("--time", required=True,
                    help='question moment, ISO e.g. "2026-10-01T10:30:00+05:30" '
                         "(naive = IST)")
    ap.add_argument("--city", default="Unknown")
    ap.add_argument("--coords", default=None,
                    help='"lat,lon" (skips geocoding)')
    ap.add_argument("--event", default=None,
                    help="event key from events.json (gives success/denial/cusp)")
    ap.add_argument("--houses", default=None,
                    help='"2,6,10,11" (instead of --event)')
    ap.add_argument("--cusp", type=int, default=None,
                    help="primary cusp (instead of --event)")
    a = ap.parse_args()

    # --- time: ISO; naive assumed IST ---
    try:
        as_of = datetime.fromisoformat(a.time)
    except ValueError:
        raise SystemExit(f"bad --time {a.time!r}; use ISO like "
                         '"2026-10-01T10:30:00+05:30"')
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        print("(naive time assumed IST)")

    coords = None
    if a.coords:
        try:
            lat, lon = a.coords.split(",")
            coords = (float(lat), float(lon))
        except ValueError:
            raise SystemExit("--coords must look like \"28.61,77.21\"")

    # --- relevant houses: from event table or explicit ---
    if a.event:
        ev = json.load(open(_os.path.join(_HERE, "events.json"))).get(a.event)
        if not ev:
            raise SystemExit(f"event {a.event!r} not in events.json")
        success = list(ev.get("success") or [])
        denial = list(ev.get("denial") or [])
        cusp = ev.get("relative_house") or 11
        src = f"event table '{a.event}'"
    elif a.houses:
        success = [int(x) for x in a.houses.split(",") if x.strip().isdigit()]
        denial, cusp, src = [], a.cusp or 11, "explicit --houses"
    else:
        raise SystemExit("give --event or --houses")
    if a.cusp and not a.event:
        cusp = a.cusp

    router_out = {"status": "ok", "success": success, "denial": denial,
                  "primary_cusp": cusp}
    print(f"number={a.number} time={as_of.isoformat()} city={a.city} "
          f"coords={coords}")
    print(f"relevant houses from {src}: success={success} cusp={cusp}")

    out = check(router_out, a.city, a.number, as_of=as_of, coords=coords)

    import config as _cfg
    blocked = (out["genuineness"] == "FAIL"
               and _cfg.MOON_GATE_MODE == "hard")
    print(f"\n== Layer 2.5 verdict: {out['genuineness']} "
          f"(gate mode={_cfg.MOON_GATE_MODE}, blocked={blocked}) ==")
    print(f"Moon signifies houses: {out['moon_houses']}")
    print(f"matched relevant houses: {out['matched_houses'] or 'none'}")
    for c in out["checks"]:
        print(f"\n[{'pass' if c['passed'] else 'CHECK'}] {c['name']}\n  {c['detail']}")


if __name__ == "__main__":
    _standalone()
