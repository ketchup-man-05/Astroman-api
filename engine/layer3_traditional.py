"""v5 Layer 3 (traditional) — the verdict WITHOUT scoring.

Replaces the numeric weighted engine (-10..+10, lean tiers, thresholds)
with Krishnamurti's own judgment method, verified passage by passage in
Reader VI:

  1. The deciding planet is the SUB-LORD of the primary cusp.
     (promotion R6:16368; love R6:10570; donation R6:14512; marriage R6:7976)
  2. Its signification is read through the four KP levels — the houses
     occupied and owned by its star lord and by itself
     (the significator scheme R6:13748-13773). Rahu/Ketu act through their
     agent (R6:10335).
  3. If it signifies the success houses -> YES; the denial houses -> NO.
     (R6:16368: "if the same sub-lord is also a significator of houses
     2 or 6 or 10 or 11, then promotion is promised. Otherwise not.")

No weights, no thresholds, no lean tiers. Mixed signification (both) or
empty signification (neither) -> OTHER: an honest cannot-judge (OURS —
the book gives no formula for ties).

The frozen engine (~/workspace/kp_phase0) is used READ-ONLY for chart
facts. Its internal weighted score and verdict text are ignored entirely.

Retrograde: per the user's standing ruling (2026-09-27), a retrograde
deciding planet / star lord is DELAY/friction, never a denial. Reported,
not gated. (The book's promotion passage gates on retro; the user's
corpus-tested ruling overrides it here.)
"""
import os
import sys


from kp import chart_caster  # noqa: E402  (frozen engine; read-only use)
from engine import layer2b_exception_router as L2B  # noqa: E402


JUDGE_NAME = 'traditional'

def judge(router_out, city, horary_number, as_of=None, coords=None):
    """Traditional verdict. Returns a result dict; never raises."""
    try:
        return _judge(router_out, city, horary_number,
                      as_of=as_of, coords=coords)
    except Exception as e:
        return {'status': 'error', 'reason': f'judgment failed: {e}'[:200]}


def _judge(router_out, city, horary_number, as_of=None, coords=None):
    if router_out.get('status') == 'exception':
        return _judge_exception(router_out, city, horary_number,
                                as_of=as_of, coords=coords)
    if router_out.get('status') != 'ok':
        return {'status': 'error',
                'reason': 'layer-2 did not produce a routable result',
                'router': router_out}

    success = set(router_out['success'])
    denial = set(router_out['denial'])
    primary = int(router_out['primary_cusp'])

    # Chart facts from the frozen engine. Its verdict/score are ignored.
    reading = chart_caster.execute_kp_reading(
        city, int(horary_number), sorted(success), sorted(denial),
        key_house=primary, as_of=as_of, coords=coords,
        chart_time_mode='query', log=False, include_timing=False)
    if not reading or 'error' in reading:
        return {'status': 'error',
                'reason': reading.get('error', 'engine returned nothing')[:200]}

    sig = reading.get('significators', {})
    signified = {sig.get('step_1_house'), sig.get('step_2_house')}
    signified |= set(sig.get('step_3_houses') or [])
    signified |= set(sig.get('step_4_houses') or [])
    signified.discard(0)
    signified.discard(None)

    s_hit = sorted(signified & success)
    d_hit = sorted(signified & denial)

    if s_hit and not d_hit:
        verdict = 'YES'
    elif d_hit and not s_hit:
        verdict = 'NO'
    else:
        verdict = 'OTHER'  # mixed or empty: the book gives no tie-break

    # --- House-coverage confidence gate (2026-09-29, user-approved) ---
    # coverage = |success ∪ denial| / 12: how much of the chart can even
    # speak on this question. Thin tables should lean, not declare.
    # Applies ONLY to OURS tables (never overrides the book's authority).
    # Special-path events (empty success+denial) are skipped: they don't
    # use this mechanism and already resolve to OTHER above.
    coverage = 0.0
    coverage_lean = False
    coverage_note = ''
    if success or denial:
        coverage = len(success | denial) / 12.0
        tables_prov = ((router_out.get('provenance') or {}).get('tables') or '')
        if coverage < 0.34 and tables_prov == 'OURS' and verdict in ('YES', 'NO'):
            coverage_lean = True
            coverage_note = (
                'low-coverage OURS table (%.2f): %s downgraded to OTHER' % (coverage, verdict))
            verdict = 'OTHER'

    # --- Additive diagnostic keys for Layer-4 overrides and report signals ---
    # These do NOT alter the verdict logic above in any way. They expose the
    # raw signification levels, per-planet retrograde flags (same source the
    # frozen engine uses for is_retrograde), and the frozen engine's own
    # report-only 11th-CSL / Moon signals, so pipeline.py can apply labeled
    # overrides and report signals without re-casting the chart.
    planet_retro = {}
    try:
        for f in (reading.get('planet_facts') or []):
            planet_retro[f.get('planet')] = bool(f.get('is_retrograde'))
    except Exception:
        planet_retro = {}
    _decision = ((reading.get('ai_facts') or {}).get('decision')) or {}

    return {
        'status': 'ok',
        'verdict_class': verdict,
        'method': 'traditional-sub-lord-signification',
        'deciding_planet': reading.get('deciding_planet'),
        'cusp_sub_lord': reading.get('cusp_sub_lord'),
        'star_lord': (sig.get('true_star_lord')),
        'signified_houses': sorted(signified),
        'success_hit': s_hit,
        'denial_hit': d_hit,
        'house_coverage': round(coverage, 3),
        'coverage_lean': coverage_lean,
        'coverage_note': coverage_note,
        'retrograde_delay': bool(reading.get('is_retrograde')),
        'primary_cusp': primary,
        'positive': sorted(success),
        'negative': sorted(denial),
        'levels': {
            'step_1_house': sig.get('step_1_house'),
            'step_2_house': sig.get('step_2_house'),
            'step_3_houses': list(sig.get('step_3_houses') or []),
            'step_4_houses': list(sig.get('step_4_houses') or []),
        },
        'planet_retro': planet_retro,
        # Additive chart passthrough for the app's SVG (no logic impact).
        'chart_data': reading.get('chart_data') or {},
        'horary_ascendant_longitude': reading.get('horary_ascendant_longitude'),
        'eleventh_csl': _decision.get('eleventh_csl_check'),
        'moon_genuineness': _decision.get('moon_genuineness'),
        'provenance': {
            'layer3': 'traditional-no-score (BOOK method; OTHER-on-tie OURS)',
            'tables': router_out.get('provenance', {}).get('tables'),
            'denial': router_out.get('provenance', {}).get('denial'),
            'rotation': router_out.get('provenance', {}).get('rotation'),
        },
    }


def _judge_exception(router_out, city, horary_number, as_of=None, coords=None):
    """Exception path unchanged: Layer-2b procedure, no house arrays."""
    reading = chart_caster.execute_kp_reading(
        city, int(horary_number), [], [],
        key_house=router_out.get('key_house') or 11,
        as_of=as_of, coords=coords,
        chart_time_mode='query', log=False, include_timing=False)
    if not reading or 'error' in reading:
        return {'status': 'error',
                'reason': reading.get('error', 'engine returned nothing')[:200]}
    proc = L2B.run_exception(router_out, reading)
    verdict_class = {'YES': 'YES', 'NO': 'NO'}.get(proc['verdict'], 'OTHER')
    return {'status': 'ok',
            'verdict_class': verdict_class,
            'method': 'layer2b-exception',
            'procedure': proc,
            'exception': True,
            'key_house': router_out.get('key_house'),
            'levels': None,
            'planet_retro': {},
            'eleventh_csl': None,
            'moon_genuineness': None,
            'retrograde_delay': False,
            'provenance': {'layer3': 'exception-procedure',
                           **router_out.get('provenance', {})}}
