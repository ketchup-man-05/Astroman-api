"""KP horary timing engine — Vimshottari DBA-sookshma windows, downstream of L3 verdicts ONLY.

Book method (see TIMING_RESEARCH.md for full citations):
- Step 0 (promise gate): runs ONLY on YES / YES-WITH-DELAYS. Never on NO/OTHER.
  (Shanmugam Part 2 pp.214-215; Hariharan pp.57-58; Bhatnagar p.111)
- Step 2: Vimshottari from judgment-moment Moon. (Taneja p.13; Hariharan p.106)
- Step 3: fruitful significators = planets signifying the event's success houses,
  using the engine's own chains (4-level; 7-level for relationship).
  (Shanmugam Part 1 pp.276-277)
- Step 4-5: Ruling Planets as ELIMINATIVE filter — KSK's "universal rule":
  common planets between fruitful significators and RPs. (Part 2 p.151)
- Step 6-7: walk dasha -> bhukti -> antara -> sookshma; all levels' lords must
  signify; skip non-signifying periods. (Taneja p.25; Hariharan p.58; KSK
  Reader III p.385 for sookshma depth)
- Step 9: dasha horizon (one full 120y Vimshottari cycle); no user window needed.
  (Taneja pp.155-156)
- Step 8 (transit day-pinning): NOT implemented in v1 — noted as future work.
  Windows are given at antara/sookshma granularity, not exact days.

User rulings applied (2026-10-06): RP filter (not tie-breaker), sookshma depth
(not antara), dasha horizon (not window-required).

This module NEVER flips a verdict. It only attaches a timing window to an
already-decided YES / YES-WITH-DELAYS.
"""
import os
import sys
from datetime import datetime, timezone, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_KP = '/home/hatch/workspace/kp_phase0'
if _KP not in sys.path:
    sys.path.insert(0, _KP)

from kp import kp_math  # noqa: E402
from kp.timing_engine import (  # noqa: E402
    build_periods, build_antaras, YEAR_DAYS, DASHA_SEQUENCE, TOTAL_YEARS,
)
from engine.layer3_v9 import _chain_of, _chain_of_7level, _R, MARRIAGE_EVENTS  # noqa: E402
from kp import chart_caster  # noqa: E402

# One full Vimshottari cycle = the natural "dasha horizon" (Taneja pp.155-156).
HORIZON_YEARS = 120

# Planets in Vimshottari order (for index lookups).
_PLANETS = [p for p, _ in DASHA_SEQUENCE]
_YEARS = {p: y for p, y in DASHA_SEQUENCE}


def build_sookshmas(antara):
    """Subdivide an antara dict (md/bd/ad/start/end) into its 9 sookshmas.

    Sookshma sequence starts with the antara lord, in Vimshottari order.
    Duration: sookshma = antara_days * sookshma_lord_years / TOTAL_YEARS.
    The last sookshma is pinned to the antara's end (no float drift gaps).
    """
    md_years = _YEARS[antara['md']]
    bd_years = _YEARS[antara['bd']]
    ad_years = _YEARS[antara['ad']]
    antara_days = md_years * bd_years * ad_years / (TOTAL_YEARS ** 2) * YEAR_DAYS
    start_idx = _PLANETS.index(antara['ad'])
    out, s_start = [], antara['start']
    for j in range(9):
        s_lord = _PLANETS[(start_idx + j) % 9]
        s_end = (antara['end'] if j == 8
                 else s_start + timedelta(days=antara_days * _YEARS[s_lord] / TOTAL_YEARS))
        out.append({'md': antara['md'], 'bd': antara['bd'],
                    'ad': antara['ad'], 'sk': s_lord,
                    'start': s_start, 'end': s_end})
        s_start = s_end
    return out


def _planet_chain(planet, reading, event_key):
    """Engine chain for a planet: 7-level for relationship, 4-level otherwise.

    Mirrors which chain L3 used for the verdict, so timing significators agree
    with the promise judgment.
    """
    if event_key in MARRIAGE_EVENTS:
        return _chain_of_7level(planet, reading)
    return _chain_of(planet, reading)


def fruitful_significators(success_houses, reading, router_out, event_key):
    """Planets signifying the event's success houses (natal chains vs target set).

    success_houses arrives ALREADY in chart frame: pipeline passes
    out3['positive'], which _judge built from router_out['success'] that
    layer2_router._block() rotated. Do NOT _R() it again (2026-10-15:
    double-rotation corrupted dasha windows and fixed-date vetoes on every
    turned chart).
    Returns {planet: sorted_houses}.
    """
    target = set(success_houses)
    out = {}
    for planet in _PLANETS:
        try:
            chain = _planet_chain(planet, reading, event_key)
        except Exception:
            continue
        hit = sorted(set(chain) & target)
        if hit:
            out[planet] = hit
    return out


def ruling_planet_set(reading):
    """Ruling Planets at judgment, from the chart caster's computation.

    Day lord + Lagna sign/star lord + Moon sign/star lord
    (Hariharan p.72; KSK Reader III p.173).
    """
    rp = reading.get('ruling_planets') or {}
    names = [rp.get('day_lord'), rp.get('asc_sign_lord'), rp.get('asc_star_lord'),
             rp.get('moon_sign_lord'), rp.get('moon_star_lord')]
    return {n for n in names if n}


def _as_utc(dt):
    if dt is None:
        return datetime.now(timezone.utc)
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def find_window(event_key, reading, router_out, success_houses, judgment_dt,
                horizon_years=HORIZON_YEARS):
    """First DBA-sookshma window where all 4 lords signify + RP filter passes.

    Returns a dict with window dates, lords, confidence — or None when no
    qualifying period exists inside the horizon ("timing not clear").
    """
    judgment_dt = _as_utc(judgment_dt)
    planets = ((reading.get('chart_data') or {}).get('planets')) or {}
    moon_lon = planets.get('Moon')
    if moon_lon is None:
        return None

    fruitful = fruitful_significators(success_houses, reading, router_out, event_key)
    if not fruitful:
        return None
    rp = ruling_planet_set(reading)
    # KSK's "universal rule": the pool is fruitful significators that are also RPs.
    pool = set(fruitful) & rp

    def signifies(planet):
        return planet in fruitful

    def in_pool(planet):
        return planet in pool

    # Walk the tree, pruning whole branches whose lord doesn't signify.
    # Per Taneja p.25 ("dasa gets maximum weightage") and KSK Ex.1: the dasa
    # and bhukti lords must be in the RP-filtered pool (common planets);
    # antara/sookshma lords must be fruitful significators.
    for bhukti in build_periods(moon_lon, judgment_dt, horizon_years):
        if bhukti['end'] <= judgment_dt:
            continue
        if not in_pool(bhukti['md']):
            continue
        if not in_pool(bhukti['bd']):
            continue
        for antara in build_antaras(bhukti):
            if antara['end'] <= judgment_dt:
                continue
            if not signifies(antara['ad']):
                continue
            for sk in build_sookshmas(antara):
                if sk['end'] <= judgment_dt:
                    continue
                if not signifies(sk['sk']):
                    continue
                lords = (sk['md'], sk['bd'], sk['ad'], sk['sk'])
                rp_lords = [l for l in lords if l in pool]
                start = max(sk['start'], judgment_dt)
                return {
                    'md': sk['md'], 'bd': sk['bd'],
                    'ad': sk['ad'], 'sk': sk['sk'],
                    'window_start': start,
                    'window_end': sk['end'],
                    'rp_lords': rp_lords,
                    'all_rp': len(rp_lords) >= 2,
                    'pool_empty': False,
                }
    # No qualifying period: distinguish "pool empty" (RP filter blocked
    # everything) from "no signification match".
    return None


def _fmt_date(dt):
    return dt.strftime('%d %b %Y')


def _fmt_period(start, end):
    days = (end - start).days
    if days <= 45:
        return '%s to %s' % (_fmt_date(start), _fmt_date(end))
    if days <= 400:
        return '%s to %s' % (start.strftime('%b %Y'), end.strftime('%b %Y'))
    return '%s to %s' % (start.strftime('%Y'), end.strftime('%Y'))


def phrase_window(window, delayed=False):
    """User-facing phrasing. No jargon (no dasa/bhukti/antana/RP/transit)."""
    # Karma disclaimer (user-approved 2026-10-06): timing shows the window,
    # not a guarantee — the person must act.
    _karma = (" This shows the next window when success is most likely \u2014 "
              "not a promise. The stars open the door, but you have to walk "
              "through it. If the window comes and no effort is made, it will "
              "pass like any other day.")
    if window is None:
        return ("Yes, this looks like it will happen \u2014 but I can't pin down "
                "exactly when yet. The signs point to it happening, though the "
                "timing isn't clear. Ask me again closer to the time and I'll "
                "narrow it down." + _karma)
    start, end = window['window_start'], window['window_end']
    period = _fmt_period(start, end)
    if delayed:
        # Delay phrasing (user-approved 2026-10-06): later date emphasized,
        # early date explicitly disclaimed.
        return ("Yes, it will happen \u2014 but not quickly. Expect it closer to "
                "%s. There are delays in the way, so don't count on %s."
                % (_fmt_date(end), _fmt_date(start)) + _karma)
    return "Most likely between %s." % period + _karma


def _confidence(window, judgment_dt):
    """Confidence tier for the found window."""
    if window is None:
        return 'unclear'
    days_out = (window['window_start'] - judgment_dt).days
    if window.get('all_rp') and days_out <= 365:
        return 'clear'
    if days_out <= 365 * 5:
        return 'moderate'
    return 'far'


def check_transit_agreement(target_date, fruitful, reading, dba_lords=None):
    """Book-method transit check (v10.8 extended 2026-10-06 per TRANSIT_PLANETS.md).

    Checks whether transiting planets agree with the event's significators.

    KP method (Shanmugam Part 3): "WHEN WE GET ALTERNATE DATES WE SHOULD
    REJECT THOSE DATES WHEN TRANSIT DOES NOT AGREE WE SHOULD FIX THE DATE
    WHEN TRANSIT AGREES."

    Planets checked (bounded KP set):
    1. Transiting DBA lords (Rao's "first consideration" — KSK Reader IV,
       Hariharan, Bosmia): their sign/star/sub vs significator chains.
    2. Jupiter (year marker — Rao/Bhatnagar): in significator's sign/star?
    3. Sun (month) + Moon (day) — the original check (Rao/Bhatnagar/Shanmugam).
    Saturn: NOT gated by default (Shanmugam p.179 — only when sublords weak).
    Explicitly excluded: Uranus/Neptune, vedha, Ashtakvarga, Shadbala (Parashari).

    "Transit agrees" = transiting Sun/Moon are in the SIGN, STAR, or SUB of
    the event's fruitful significators (worked example: "BY TRANSIT SUN WAS
    IN MARS SIGN VENUS STAR RAHU SUB... THUS THE SIGNIFICATOR WERE IN GREAT
    ADVANTAGEOUS POSITION").

    KSK Reader V: transit is subordinate to dasha — "JUST LIKE A SECOND HAND
    TO NOTE WHEN EXACTLY A MATTER WILL MATERIALISE." Transit confirms or
    rejects DATES; it never vetoes the event itself.

    KSK explicitly rejects exaltation/debilitation as deterministic:
    "IT IS ABSURD IF ONE WERE TO INTERPRET IN THAT MANNER" (Reader V).
    Retrograde in transit = DELAY until direct (Part 5 p.230), not denial.

    Returns dict:
      agrees: bool — True if Sun or Moon connects to significators
      sun_detail / moon_detail: {sign_lord, star_lord, sub_lord, hits}
      verdict_hint: 'agrees' | 'disagrees' | 'neutral'
    Never raises; returns neutral on any failure.
    """
    neutral = {
        'agrees': False,
        'sun_detail': {},
        'moon_detail': {},
        'jupiter_detail': {},
        'dba_detail': {},
        'verdict_hint': 'neutral',
        'error': None,
    }
    try:
        import swisseph as swe
        # 2026-10-15 (review 3.1): use the module-global kp_math (imported at
        # top as `from kp import kp_math`). The old code inserted a hardcoded
        # dev path (/home/hatch/workspace/kp_phase0) and did a bare
        # `import kp_math`, which fails everywhere except this dev VM — the
        # except swallowed it and the transit check silently returned
        # 'neutral', bypassing transit agreement on every reading.

        target_date = _as_utc(target_date)
        sig_set = set(fruitful.keys()) if isinstance(fruitful, dict) else set(fruitful)
        if not sig_set:
            out = dict(neutral)
            out['error'] = 'no fruitful significators'
            return out

        # Julian day at noon UTC on target date
        jd = swe.julday(target_date.year, target_date.month, target_date.day,
                        12.0)

        # Planet name -> swisseph ID (Ketu = Rahu + 180)
        _PID = {'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS,
                'Mercury': swe.MERCURY, 'Jupiter': swe.JUPITER,
                'Venus': swe.VENUS, 'Saturn': swe.SATURN,
                'Rahu': swe.MEAN_NODE, 'Ketu': swe.MEAN_NODE}

        def transit_lords(planet_id, is_ketu=False):
            pos, _ = swe.calc_ut(jd, planet_id)
            lon = pos[0] % 360.0
            if is_ketu:
                lon = (lon + 180.0) % 360.0
            return {
                'longitude': round(lon, 2),
                'sign_lord': kp_math.get_sign_lord(lon),
                'star_lord': kp_math.get_star_lord(lon),
                'sub_lord': kp_math.get_sub_lord(lon),
                'retrograde': pos[3] < 0,
            }

        sun = transit_lords(swe.SUN)
        moon = transit_lords(swe.MOON)

        def hits(detail):
            return sorted({detail['sign_lord'], detail['star_lord'],
                           detail['sub_lord']} & sig_set)

        sun['hits'] = hits(sun)
        moon['hits'] = hits(moon)

        # v10.8: transiting DBA lords (Rao's "first consideration").
        # Check each running lord's transit sign/star/sub vs significators.
        dba_detail = {}
        dba_hits = []
        if dba_lords:
            _lords = (dba_lords.values() if isinstance(dba_lords, dict)
                      else dba_lords)
            for lord in sorted(set(_lords)):
                if lord in _PID:
                    try:
                        d = transit_lords(_PID[lord], is_ketu=(lord == 'Ketu'))
                        d['hits'] = hits(d)
                        dba_detail[lord] = d
                        dba_hits.extend(d['hits'])
                    except Exception:
                        continue

        # v10.8: Jupiter year marker (Rao/Bhatnagar) — in significator's
        # sign/star? Confirmation only, part of the cascade.
        jupiter = transit_lords(swe.JUPITER)
        jupiter['hits'] = hits(jupiter)

        # Agreement = ANY checked planet connects (confirmation logic).
        # Transit never vetoes the event itself (KSK Reader V: "second hand").
        agrees = bool(sun['hits'] or moon['hits'] or dba_hits
                      or jupiter['hits'])

        return {
            'agrees': agrees,
            'sun_detail': sun,
            'moon_detail': moon,
            'jupiter_detail': jupiter,
            'dba_detail': dba_detail,
            'verdict_hint': 'agrees' if agrees else 'disagrees',
            'error': None,
        }
    except Exception as e:
        out = dict(neutral)
        out['error'] = 'transit check failed safely: %s: %s' % (
            type(e).__name__, str(e)[:120])
        return out


def check_fixed_date(event_key, reading, router_out, success_houses,
                     judgment_dt, target_date):
    """Check if a SPECIFIC date falls in a supportive dasha period.

    For time-bound questions ("will I clear my exam on Dec 15?"): instead of
    finding the next window, check which dasha/bhukti/antara/sookshma is
    running ON the target date and whether those lords signify the event's
    success houses (+ RP filter on dasha/bhukti).

    Book basis: the dasha veto — cusp promises, but if the period running on
    the event date isn't among significators, the event fails on that date.

    Returns dict:
      supported: bool — True if all 4 lords signify + RP filter passes
      running_lords: {dasha, bhukti, antara, sookshma}
      significator_match: {lord: bool} per level
      rp_pass: bool — dasha+bhukti in RP-filtered pool
      verdict_hint: 'supports_YES' | 'vetoes' | 'neutral'
    Never raises; returns neutral on any failure.
    """
    neutral = {
        'supported': False,
        'running_lords': {},
        'significator_match': {},
        'rp_pass': False,
        'verdict_hint': 'neutral',
        'transit': {'agrees': False, 'verdict_hint': 'neutral', 'error': None},
        'error': None,
    }
    try:
        judgment_dt = _as_utc(judgment_dt)
        target_date = _as_utc(target_date)
        if target_date <= judgment_dt:
            # Date is in the past — can't check a period that's already passed
            # with the judgment-anchored sequence in a meaningful way.
            out = dict(neutral)
            out['error'] = 'target date is not in the future'
            return out

        planets = ((reading.get('chart_data') or {}).get('planets')) or {}
        moon_lon = planets.get('Moon')
        if moon_lon is None:
            out = dict(neutral)
            out['error'] = 'no Moon longitude in reading'
            return out

        fruitful = fruitful_significators(success_houses, reading, router_out,
                                          event_key)
        if not fruitful:
            out = dict(neutral)
            out['error'] = 'no fruitful significators'
            return out
        rp = ruling_planet_set(reading)
        pool = set(fruitful) & rp

        def signifies(planet):
            return planet in fruitful

        # Walk the dasha tree to find the period containing target_date.
        # Use a generous horizon so far-future dates are covered.
        found = None
        for bhukti in build_periods(moon_lon, judgment_dt, HORIZON_YEARS):
            if not (bhukti['start'] <= target_date < bhukti['end']):
                continue
            for antara in build_antaras(bhukti):
                if not (antara['start'] <= target_date < antara['end']):
                    continue
                for sk in build_sookshmas(antara):
                    if sk['start'] <= target_date < sk['end']:
                        found = sk
                        break
                if found:
                    break
            if found:
                break

        if not found:
            out = dict(neutral)
            out['error'] = 'target date beyond dasha horizon'
            return out

        lords = {
            'dasha': found['md'],
            'bhukti': found['bd'],
            'antara': found['ad'],
            'sookshma': found['sk'],
        }
        match = {level: signifies(lord) for level, lord in lords.items()}
        rp_pass = (found['md'] in pool) and (found['bd'] in pool)

        # Veto rule (mirrors find_window): dasha+bhukti must be in the
        # RP-filtered pool; antara+sookshma must be fruitful significators.
        # ALL four must signify for the date to be supported.
        all_signify = all(match.values())
        supported = all_signify and rp_pass

        # Transit agreement check (book method, v10.8 extended): transiting
        # DBA lords + Jupiter/Sun/Moon vs significator sign/star/sub.
        # Per KSK, transit is subordinate to dasha ("second hand") —
        # disagreement is a caution, not an independent veto.
        transit = check_transit_agreement(target_date, fruitful, reading,
                                          dba_lords=lords)

        return {
            'supported': supported,
            'running_lords': lords,
            'significator_match': match,
            'rp_pass': rp_pass,
            'verdict_hint': 'supports_YES' if supported else 'vetoes',
            'transit': transit,
            'error': None,
        }
    except Exception as e:
        out = dict(neutral)
        out['error'] = 'check failed safely: %s: %s' % (type(e).__name__,
                                                        str(e)[:120])
        return out


def check_current_period(event_key, reading, router_out, success_houses,
                         judgment_dt, denial_houses=None):
    """Dasha veto v10.8 (recalibrated 2026-10-06 per DASHA_VETO_CALIBRATION.md).

    Book rule from 33 worked examples: veto on NEGATION, not mere pool absence.

    Rule 1 (Khullar KCIL p.85): a lord "fails" only if its chain contains a
      DENIAL-house signification (negation-linkage). Mere absence of success
      houses is NOT failure (Bush marriage N1: bhukti signified only 1,12 yet
      marriage happened; Taneja court N2: neutral dasa yet settlement happened).
    Rule 2: veto only when 2+ of (dasha, bhukti, antara) fail by negation — or
      when the DASA fails by negation regardless (Taneja hard veto V10: Ketu
      dasa denied despite fully-positive bhukti; Apr-2015 2nd-marriage V12).
    Rule 3: full-chain signification counts (planet+star+sub levels via
      _planet_chain). A lord touching success houses at ANY level signifies;
      touching denial houses at ANY level negates. (Khullar N3, Taneja V11.)
    Rule 4: widen the pool before vetoing — if fruitful∩RP < 2, fall back to
      fruitful-only (Bhatnagar N6 widened RP/fruitful rather than vetoing).
    SEPARATE mechanism (Bosmia Ex.169 type): antara not among Ruling Planets
      themselves (not the pool intersection) → veto. Outcome-verified x6
      (V1, V2, V7, V18-V21). Reported as veto_type='rp_membership', distinct
      from the negation veto.

    denial_houses: the event's denial houses (for negation-linkage). If not
    provided, Path A (negation) cannot fire; only Path B (RP) applies.

    Returns dict:
      vetoes: bool
      veto_type: 'negation' | 'rp_membership' | 'negation+rp_membership' | None
      running_lords: {dasha, bhukti, antara}
      significator_match / negation_match: {level: bool}
      rp_pass: bool — dasha+bhukti in (widened) pool
      verdict_hint: 'supports_YES' | 'vetoes' | 'neutral'
    Never raises; returns neutral on any failure.
    """
    neutral = {
        'vetoes': False,
        'veto_type': None,
        'running_lords': {},
        'significator_match': {},
        'negation_match': {},
        'rp_pass': False,
        'pool_size': 0,
        'verdict_hint': 'neutral',
        'error': None,
    }
    try:
        judgment_dt = _as_utc(judgment_dt)
        planets = ((reading.get('chart_data') or {}).get('planets')) or {}
        moon_lon = planets.get('Moon')
        if moon_lon is None:
            out = dict(neutral)
            out['error'] = 'no Moon longitude in reading'
            return out

        fruitful = fruitful_significators(success_houses, reading, router_out,
                                          event_key)
        if not fruitful:
            out = dict(neutral)
            out['error'] = 'no fruitful significators'
            return out
        rp = ruling_planet_set(reading)

        # Rule 4: widen pool before vetoing — never veto on a tiny intersection
        pool = set(fruitful) & rp
        if len(pool) < 2:
            pool = set(fruitful)

        # Target sets arrive already in chart frame (see fruitful_significators
        # note 2026-10-15: pipeline passes out3['positive'/'negative'],
        # rotated by layer2_router._block — no second _R() here).
        success_target = set(success_houses)
        denial_target = set(denial_houses or [])

        # Find the bhukti containing judgment_dt, then the antara within it.
        found_bhukti = None
        for bhukti in build_periods(moon_lon, judgment_dt, HORIZON_YEARS):
            if bhukti['start'] <= judgment_dt < bhukti['end']:
                found_bhukti = bhukti
                break
        if not found_bhukti:
            out = dict(neutral)
            out['error'] = 'no running bhukti found at judgment'
            return out

        found_antara = None
        for antara in build_antaras(found_bhukti):
            if antara['start'] <= judgment_dt < antara['end']:
                found_antara = antara
                break
        if not found_antara:
            out = dict(neutral)
            out['error'] = 'no running antara found at judgment'
            return out

        lords = {
            'dasha': found_bhukti['md'],
            'bhukti': found_bhukti['bd'],
            'antara': found_antara['ad'],
        }

        # Per-level checks (Rule 3: full chain via _planet_chain)
        signifies = {}
        negates = {}
        for level, lord in lords.items():
            try:
                chain = set(_planet_chain(lord, reading, event_key))
            except Exception:
                chain = set()
            sig = bool(chain & success_target)
            signifies[level] = sig
            # Rule 1 (refined per Dec 2007 §33): negation = chain touches a
            # DENIAL house AND does NOT touch success houses ("signify ONLY
            # totally adverse houses"). A lord touching both is mixed, not
            # negating — books do not veto on mixed lords (Bush N1, Taneja N2).
            neg = bool(chain & denial_target) if denial_target else False
            negates[level] = neg and not sig

        # Path A: negation veto (Rules 1+2)
        # - dasa negates → hard veto regardless (Taneja V10, Ezine V12)
        # - 2+ levels negate → veto (synthesis of N1/N2/N10: never veto on a
        #   single failing level when the others support)
        n_negating = sum(1 for lvl in lords if negates.get(lvl))
        negation_veto = negates.get('dasha', False) or (n_negating >= 2)

        # Path B: RP-membership veto (Bosmia Ex.169 type — SEPARATE mechanism)
        # Book pattern (V1, V2, V7, V18-V21): dasa AND bhukti are IN RP
        # (supportive backdrop), and ONLY the antara fails RP membership.
        # NOTE (2026-10-06): DISABLED as blanket rule — lab RP computation
        # differs from books' (e.g., W157: lab RP lacks Mercury), causing
        # false vetoes (exam 76.2%→57.1%). Kept as separate veto_type for
        # targeted use; Path A (negation) is the primary mechanism.
        # To re-enable: set _RP_VETO_ENABLED = True.
        _RP_VETO_ENABLED = False
        dasa_in_rp = bool(rp) and (lords['dasha'] in rp)
        bhukti_in_rp = bool(rp) and (lords['bhukti'] in rp)
        antara_in_rp = bool(rp) and (lords['antara'] in rp)
        rp_veto = _RP_VETO_ENABLED and dasa_in_rp and bhukti_in_rp and (not antara_in_rp)

        vetoes = negation_veto or rp_veto
        if negation_veto and rp_veto:
            veto_type = 'negation+rp_membership'
        elif negation_veto:
            veto_type = 'negation'
        elif rp_veto:
            veto_type = 'rp_membership'
        else:
            veto_type = None

        return {
            'vetoes': vetoes,
            'veto_type': veto_type,
            'running_lords': lords,
            'significator_match': signifies,
            'negation_match': negates,
            'rp_pass': (lords['dasha'] in pool) and (lords['bhukti'] in pool),
            'pool_size': len(pool),
            'verdict_hint': 'vetoes' if vetoes else 'supports_YES',
            'error': None,
        }
    except Exception as e:
        out = dict(neutral)
        out['error'] = 'check failed safely: %s: %s' % (type(e).__name__,
                                                        str(e)[:120])
        return out


def phrase_fixed_date(check, target_date, event_label=''):
    """User-facing phrasing for fixed-date check. No jargon."""
    date_str = _fmt_date(_as_utc(target_date))
    _karma = (" Remember: this shows whether the period on that date supports "
              "success \u2014 not a guarantee. The stars open the door, but "
              "you have to walk through it.")
    if check.get('verdict_hint') == 'supports_YES':
        return ("Yes \u2014 and the timing on %s looks favorable." % date_str
                + _karma)
    if check.get('verdict_hint') == 'vetoes':
        return ("The signs say yes in general, but not on %s. "
                "The period running then doesn't support it." % date_str
                + _karma)
    return ("I can't read the timing for %s clearly." % date_str + _karma)


def compute_timing_for_answer(city, horary_number, as_of, coords, event_key,
                              success_houses, router_out, verdict, modifiers):
    """Top-level entry for pipeline.py. Never raises; returns timing dict or None.

    Promise gate: verdict must be YES or YES-WITH-DELAYS, else None.
    Re-casts the chart (deterministic given same inputs) to get Moon/RPs.
    """
    try:
        return _compute_timing(city, horary_number, as_of, coords, event_key,
                               success_houses, router_out, verdict, modifiers)
    except Exception as e:
        return {'window_start': None, 'window_end': None,
                'phrasing': phrase_window(None),
                'confidence': 'unclear',
                'error': 'timing failed safely: %s: %s' % (type(e).__name__, str(e)[:120]),
                'lords': {}}


def compute_dasha_veto_for_answer(city, horary_number, as_of, coords,
                                  event_key, success_houses, router_out,
                                  denial_houses=None):
    """Top-level dasha-veto entry for pipeline.py. Never raises.

    Re-casts the chart to get the reading, then runs check_current_period().
    For non-date YES/YES-WITH-DELAYS: if the currently running dasha/bhukti/
    antara at judgment vetoes by the book negation rule → veto (downgrade).

    Book basis: DASHA_VETO_CALIBRATION.md (33 examples) — veto on negation,
    not mere pool absence; Bosmia Ex.169-type RP-membership veto as separate
    mechanism.

    Returns the check dict (with verdict_hint, veto_type) or neutral on failure.
    """
    try:
        judgment_dt = _as_utc(as_of)
        reading = chart_caster.execute_kp_reading(
            city, int(horary_number), sorted(success_houses), [],
            key_house=(router_out or {}).get('primary_cusp') or 1,
            as_of=judgment_dt, coords=coords,
            chart_time_mode='query', log=False, include_timing=False)
        if not reading or 'error' in reading:
            return {
                'vetoes': False, 'running_lords': {},
                'significator_match': {}, 'rp_pass': False,
                'verdict_hint': 'neutral',
                'error': 'chart re-cast failed',
            }
        return check_current_period(event_key, reading, router_out,
                                    success_houses, judgment_dt,
                                    denial_houses=denial_houses)
    except Exception as e:
        return {
            'vetoes': False, 'running_lords': {},
            'significator_match': {}, 'rp_pass': False,
            'verdict_hint': 'neutral',
            'error': 'dasha veto failed safely: %s: %s'
                     % (type(e).__name__, str(e)[:120]),
        }


def compute_fixed_date_for_answer(city, horary_number, as_of, coords, event_key,
                                   success_houses, router_out, target_date):
    """Top-level fixed-date entry for pipeline.py. Never raises.

    Re-casts the chart to get the reading, then runs check_fixed_date().
    Returns the check dict (with verdict_hint) or a neutral dict on failure.
    """
    try:
        judgment_dt = _as_utc(as_of)
        reading = chart_caster.execute_kp_reading(
            city, int(horary_number), sorted(success_houses), [],
            key_house=(router_out or {}).get('primary_cusp') or 1,
            as_of=judgment_dt, coords=coords,
            chart_time_mode='query', log=False, include_timing=False)
        if not reading or 'error' in reading:
            out = {
                'supported': False, 'running_lords': {},
                'significator_match': {}, 'rp_pass': False,
                'verdict_hint': 'neutral',
                'error': 'chart re-cast failed',
            }
            out['phrasing'] = phrase_fixed_date(out, target_date)
            return out
        result = check_fixed_date(event_key, reading, router_out,
                                  success_houses, judgment_dt, target_date)
        result['phrasing'] = phrase_fixed_date(result, target_date)
        return result
    except Exception as e:
        out = {
            'supported': False, 'running_lords': {},
            'significator_match': {}, 'rp_pass': False,
            'verdict_hint': 'neutral',
            'error': 'fixed-date check failed safely: %s: %s'
                     % (type(e).__name__, str(e)[:120]),
        }
        try:
            out['phrasing'] = phrase_fixed_date(out, target_date)
        except Exception:
            out['phrasing'] = 'Timing check unavailable.'
        return out


def _compute_timing(city, horary_number, as_of, coords, event_key,
                    success_houses, router_out, verdict, modifiers):
    # ---- Step 0: promise gate ----
    if verdict not in ('YES', 'YES-WITH-DELAYS'):
        return None
    if not success_houses:
        return None

    judgment_dt = _as_utc(as_of)
    reading = chart_caster.execute_kp_reading(
        city, int(horary_number), sorted(success_houses), [],
        key_house=(router_out or {}).get('primary_cusp') or 1,
        as_of=judgment_dt, coords=coords,
        chart_time_mode='query', log=False, include_timing=False)
    if not reading or 'error' in reading:
        return {'window_start': None, 'window_end': None,
                'phrasing': phrase_window(None), 'confidence': 'unclear',
                'error': 'chart re-cast failed', 'lords': {}}

    window = find_window(event_key, reading, router_out, success_houses,
                         judgment_dt)
    # v10.7 (user ruling 2026-10-06): only show the window when BOTH dasha
    # timing and transit agree. Transit is the "second hand" (KSK Reader V) —
    # it confirms the date, never vetoes the event. If transit disagrees,
    # the window is withheld (not shown) rather than shown with doubt.
    if window:
        fruitful = fruitful_significators(success_houses, reading,
                                          router_out, event_key)
        # Check transit at window midpoint (representative of the window)
        mid = window['window_start'] + (
            window['window_end'] - window['window_start']) / 2
        # v10.8: pass the window's own DBA lords (Rao's first rule)
        _dba = {'dasha': window.get('md'), 'bhukti': window.get('bd'),
                'antara': window.get('ad')}
        _dba = {k: v for k, v in _dba.items() if v}
        t_check = check_transit_agreement(mid, fruitful, reading,
                                          dba_lords=_dba or None)
        if t_check.get('verdict_hint') == 'disagrees':
            window = None  # transit doesn't agree — withhold the window
    delayed = (verdict == 'YES-WITH-DELAYS') or ('DELAYS' in (modifiers or []))
    confidence = _confidence(window, judgment_dt)
    phrasing = phrase_window(window, delayed=delayed)

    lords = {}
    if window:
        lords = {'dasha': window['md'], 'bhukti': window['bd'],
                 'antara': window['ad'], 'sookshma': window['sk'],
                 'rp_lords': window['rp_lords']}
    return {
        'window_start': window['window_start'].date().isoformat() if window else None,
        'window_end': window['window_end'].date().isoformat() if window else None,
        'phrasing': phrasing,
        'confidence': confidence,
        'delayed': delayed,
        'lords': lords,  # technical trace; never shown to the user
        'method': ('Vimshottari DBA-sookshma from judgment Moon; RP eliminative '
                   'filter; %dy horizon' % HORIZON_YEARS),
    }
