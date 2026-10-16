"""v5 Layer 3 (weighted) — hierarchical-evidence verdict with sub-lord gate.

BOOK basis (all verified in KP Reader VI):

  1. The deciding planet is the SUB-LORD of the primary cusp.
     (promotion R6:16368; love R6:10570; donation R6:14512; marriage R6:7976)
  2. Signification is read through four levels, OCCUPATION OUTRANKING
     OWNERSHIP: "Planet occupying a house is stronger than the owners of the
     sign. Tenant is stronger than the owner." (R6)
     "All these planets will, however, give the results of that house, but
     in a varying degree." -> owners keep WEAKENED signification; they are
     NOT dropped when the house is occupied.
     Level order (strongest first) — USER-RULING 2026-09-30: the user's
     4-level table is authoritative over their hastily-written example:
       L1 star_lord_occupation  (1.00) - house occupied by the star-lord
       L2 planet_occupation     (0.75) - house occupied by deciding planet
       L3 star_lord_ownership   (0.50) - houses owned by the star-lord
       L4 planet_ownership      (0.25) - houses owned by deciding planet
     ("The planet in a constellation will offer the results of the
     Bhava-house occupied by the lord of the constellation." -> L1 strongest.)
     The numeric weights are an ENGINEERING convention (versioned/tunable),
     not KP doctrine.
  3. SUB-LORD GATE (user ruling 2026-09-30; doctrine "star-lord delivers,
     sub-lord permits/denies" cross-checked via Luna as foundational KP;
     the formal sub-sub chain stays USER-RULING and is NOT used):
       - STAR PROMISE: levels L1+L3 (the star-lord's testimony — what the
         star delivers) scored on their own -> YES / NO / WEAK.
       - SUB-LORD PERMISSION: levels L2+L4 (the sub-lord planet's OWN
         placement — where it sits/what it owns) read as permission:
           SUPPORTIVE if it strongly hits required houses,
           DENYING    if it strongly hits blocking houses,
           MIXED      otherwise.
       - Combine:
           promise YES + SUPPORTIVE -> YES
           promise YES + DENYING    -> NO   (gate flip; permission withheld)
           promise YES + MIXED      -> DELAYED if mildly adverse (any
                                       blocking testimony) or decider
                                       retrograde (retro = delay/friction,
                                       standing ruling); else OTHER
           promise WEAK + SUPPORTIVE -> OTHER_WITH_SUPPORT (a supportive
                                       sub-lord can never manufacture YES)
           promise WEAK + else       -> OTHER
           promise NO  + SUPPORTIVE -> NO, flagged PENDING_REVIEW (a
                                       supportive sub-lord never overrides
                                       a clear denial; investigate, don't flip)
           promise NO  + else       -> NO
     MECHANICS LABEL: the star-vs-sub-lord level split is OURS (the only
     non-circular reading that makes every gate case constructible); the
     underlying star-delivers/sub-lord-filters doctrine is the user's.
     For a node sub-lord, permission is read from the DECIDING planet
     (agent-resolved); the raw node's own chain stays exposed in
     node_resolution for audit (user ruling A5).
  4. Rahu/Ketu act through their agent (R6:10335); the resolution path is
     exposed in the output instead of being silent. Node's own stellar
     significations and agent significations are recorded separately.

Verdicts: YES / NO / OTHER / DELAYED / OTHER_WITH_SUPPORT.
Timing is eligible ONLY on YES (strict gate, user ruling 2026-09-30:
showing a window next to a weak/delayed/denied verdict is a product bug).

Stability: the chart is re-cast at -30s/-10s/+10s/+30s around question time.
If the primary cusp's sub-lord is not stable, the verdict is not trusted.

The frozen engine (~/workspace/kp_phase0) is used READ-ONLY for chart facts.

TUNABLE (flagged for the user): LEVEL_WEIGHTS, STRONG, MARGIN,
STABILITY thresholds, DELAYED rule. Calibrate on the corpus; do not
hand-tune to it.
"""
import os
import sys
from datetime import timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))

from kp import chart_caster  # noqa: E402  (frozen engine; read-only use)
from engine import layer3_traditional as L3T  # noqa: E402  (exception path delegate)

# --- Tunable weights (user-flagged; engineering convention, NOT doctrine) --
LEVEL_WEIGHTS = {
    'star_lord_occupation': 1.00,   # L1: house occupied by the star-lord
    'planet_occupation': 0.75,      # L2: house occupied by deciding planet
    'star_lord_ownership': 0.50,    # L3: houses owned by the star-lord
    'planet_ownership': 0.25,       # L4: houses owned by deciding planet
}
LEVEL_ORDER = ['star_lord_occupation', 'planet_occupation',
               'star_lord_ownership', 'planet_ownership']
STAR_SOURCES = {'star_lord_occupation', 'star_lord_ownership'}    # promise
SUB_SOURCES = {'planet_occupation', 'planet_ownership'}           # permission
STRONG = 0.75        # evidence at/above this weight counts as "strong"
MARGIN = 0.30        # success must lead denial by this much for YES (mirror NO)
STABILITY_MIN = 0.60     # below -> OTHER (boundary_sensitive)
STABILITY_NOTE = 0.80    # below -> verdict stands but flagged uncertain
TIME_DELTAS = [-30, -10, 0, 10, 30]  # seconds around question time
COVERAGE_FLOOR = 0.34   # OURS tables below this lean to OTHER (kept)


JUDGE_NAME = 'weighted+gate'

def _build_evidence(reading):
    """Per-evidence records: house, source, level, weight, planet, path."""
    sig = reading.get('significators', {}) or {}
    decider = reading.get('deciding_planet')
    star = sig.get('true_star_lord')
    raw_csl = reading.get('cusp_sub_lord')
    ev = []

    def add(house, source, planet):
        if house in (None, 0):
            return
        try:
            h = int(house)
        except (TypeError, ValueError):
            return
        if not 1 <= h <= 12:
            return
        ev.append({
            'house': h,
            'source': source,
            'level': LEVEL_ORDER.index(source) + 1,
            'weight': LEVEL_WEIGHTS[source],
            'planet': planet,
            'path': _path_text(source, planet, star, decider, raw_csl, h),
        })

    add(sig.get('step_1_house'), 'star_lord_occupation', star)
    add(sig.get('step_2_house'), 'planet_occupation', decider)
    for h in (sig.get('step_3_houses') or []):
        add(h, 'star_lord_ownership', star)
    for h in (sig.get('step_4_houses') or []):
        add(h, 'planet_ownership', decider)
    return ev


def _path_text(source, planet, star, decider, raw_csl, house):
    node_bit = f'{raw_csl}->agent {decider} ' if raw_csl != decider else ''
    if source == 'star_lord_occupation':
        return (f'{node_bit}{decider} -> star-lord {planet} occupies '
                f'house {house}')
    if source == 'planet_occupation':
        return f'{node_bit}{planet} occupies house {house}'
    if source == 'star_lord_ownership':
        return (f'{node_bit}{decider} -> star-lord {planet} owns '
                f'house {house}')
    return f'{node_bit}{planet} owns house {house}'


def _score_subset(evidence, success, denial, sources):
    """Per-house strongest weight within one level-subset.

    Returns (s_score, d_score, strong_s, strong_d).
    """
    best = {}
    for e in evidence:
        if e['source'] not in sources:
            continue
        h = e['house']
        if h not in best or e['weight'] > best[h]['weight']:
            best[h] = e
    s_score = d_score = 0.0
    strong_s = strong_d = 0.0
    for h, e in best.items():
        if h in success:
            s_score += e['weight']
            strong_s = max(strong_s, e['weight'])
            e['classification'] = 'success'
        elif h in denial:
            d_score += e['weight']
            strong_d = max(strong_d, e['weight'])
            e['classification'] = 'denial'
        else:
            e['classification'] = 'neutral'
    return s_score, d_score, strong_s, strong_d


def _score(evidence, success, denial):
    """Full-chain score (diagnostic; verdict now comes from the gate)."""
    return _score_subset(evidence, success, denial, set(LEVEL_ORDER))


def _promise_and_gate(evidence, success, denial, decider_retro=False):
    """Star promise (L1+L3) + sub-lord permission gate (L2+L4).

    Returns (verdict, gate_detail). Verdicts: YES / NO / OTHER / DELAYED /
    OTHER_WITH_SUPPORT. Mechanics are OURS; doctrine is the user's.
    """
    s_star, d_star, ss_star, sd_star = _score_subset(
        evidence, success, denial, STAR_SOURCES)
    s_sub, d_sub, ss_sub, sd_sub = _score_subset(
        evidence, success, denial, SUB_SOURCES)

    if s_star == 0 and d_star == 0:
        promise, star_reason = 'WEAK', 'no_evidence'
    elif s_star - d_star >= MARGIN and ss_star >= STRONG:
        promise, star_reason = 'YES', ''
    elif d_star - s_star >= MARGIN and sd_star >= STRONG:
        promise, star_reason = 'NO', ''
    elif max(s_star, d_star) < STRONG:
        promise, star_reason = 'WEAK', 'weak_evidence_only'
    else:
        promise, star_reason = 'WEAK', 'conflicting_evidence'

    if s_sub >= STRONG and s_sub > d_sub:
        permission = 'SUPPORTIVE'
    elif d_sub >= STRONG and d_sub > s_sub:
        permission = 'DENYING'
    else:
        permission = 'MIXED'

    flipped = False
    pending_review = False
    reason = star_reason
    if promise == 'YES' and permission == 'SUPPORTIVE':
        verdict = 'YES'
    elif promise == 'YES' and permission == 'DENYING':
        verdict, reason, flipped = 'NO', 'sub_lord_denial', True
    elif promise == 'YES':  # MIXED permission
        if d_sub > 0 or decider_retro:
            verdict, reason = 'DELAYED', 'sub_lord_mixed_adverse'
        else:
            verdict, reason = 'OTHER', 'sub_lord_uncommitted'
    elif promise == 'WEAK' and permission == 'SUPPORTIVE':
        verdict, reason = 'OTHER_WITH_SUPPORT', 'weak_star_strong_sub_lord'
    elif promise == 'WEAK':
        verdict = 'OTHER'
    elif permission == 'SUPPORTIVE':
        verdict, reason, pending_review = 'NO', star_reason, True
    else:
        verdict, reason = 'NO', star_reason

    gate_detail = {
        'star_promise': promise,
        'star_scores': {'success': round(s_star, 3),
                        'denial': round(d_star, 3)},
        'sub_permission': permission,
        'sub_scores': {'success': round(s_sub, 3),
                       'denial': round(d_sub, 3)},
        'gate_flipped_to_no': flipped,
        'pending_review': pending_review,
        'decider_retrograde': bool(decider_retro),
        'mechanics': ('OURS: star levels (L1+L3) = promise; sub-lord own '
                      'levels (L2+L4) = permission gate'),
    }
    return verdict, reason, gate_detail


def _retro_map(reading):
    try:
        return {f.get('planet'): bool(f.get('is_retrograde'))
                for f in (reading.get('planet_facts') or [])}
    except Exception:
        return {}


def _decide_from_reading(reading, success, denial):
    """Full verdict path for one chart reading (nominal or perturbed)."""
    evidence = _build_evidence(reading)
    verdict, reason, gate = _promise_and_gate(
        evidence, success, denial,
        decider_retro=bool(reading.get('is_retrograde')))
    return verdict, reason, gate, evidence


def _cast(city, horary_number, success, denial, primary, as_of, coords):
    return chart_caster.execute_kp_reading(
        city, int(horary_number), sorted(success), sorted(denial),
        key_house=primary, as_of=as_of, coords=coords,
        chart_time_mode='query', log=False, include_timing=False)


def _stability(city, horary_number, success, denial, primary, as_of, coords,
               nominal_verdict, nominal_sub_lord):
    """Re-cast at time perturbations; compare sub-lord and verdict."""
    if as_of is None:
        return {'samples': 1, 'same_sub_lord_rate': 1.0,
                'same_verdict_rate': 1.0, 'score': 1.0,
                'note': 'no question time given; stability skipped',
                'boundary_sensitive': False}
    same_sub = 0
    same_verd = 0
    n = 0
    for dt in TIME_DELTAS:
        try:
            r = _cast(city, horary_number, success, denial, primary,
                      as_of + timedelta(seconds=dt), coords)
        except Exception:
            continue
        if not r or 'error' in r:
            continue
        n += 1
        if r.get('cusp_sub_lord') == nominal_sub_lord:
            same_sub += 1
        v, _, _, _ = _decide_from_reading(r, set(success), set(denial))
        if v == nominal_verdict:
            same_verd += 1
    if n == 0:
        return {'samples': 0, 'same_sub_lord_rate': 0.0,
                'same_verdict_rate': 0.0, 'score': 0.0,
                'note': 'stability casts failed',
                'boundary_sensitive': True}
    sub_rate = same_sub / n
    verd_rate = same_verd / n
    score = min(sub_rate, verd_rate)
    return {
        'samples': n,
        'same_sub_lord_rate': round(sub_rate, 3),
        'same_verdict_rate': round(verd_rate, 3),
        'score': round(score, 3),
        'boundary_sensitive': score < STABILITY_MIN,
        'uncertain': STABILITY_MIN <= score < STABILITY_NOTE,
        'note': ('sub-lord stable' if sub_rate >= STABILITY_NOTE
                 else 'sub-lord boundary-sensitive' if score < STABILITY_MIN
                 else 'sub-lord mildly unstable'),
    }


def _node_resolution(reading):
    """Expose Rahu/Ketu agent resolution; None when not a node.

    Diagnostic only — never changes the verdict. Returns the review's
    node_evidence shape: raw node record, ALL agent candidates per
    cascade level (the book aggregates, R6:14044; the engine selects one
    — recorded as an open discrepancy), selection reason, raw vs agent
    significations, and disagreement status. See rebuild/node_audit.md.
    """
    raw = reading.get('cusp_sub_lord')
    agent = reading.get('deciding_planet')
    if raw == agent or raw not in ('Rahu', 'Ketu'):
        return None
    facts = {f.get('planet'): f for f in (reading.get('planet_facts') or [])}
    node_f = facts.get(raw, {})
    agent_f = facts.get(agent, {})
    rule = ''
    candidates = {'conjoined': [], 'star_lord': [], 'aspecting': [],
                  'sign_lord': []}
    try:
        longs = {}
        hc = reading.get('horary_chart') or {}
        for p, v in (hc.get('longitudes') or {}).items():
            longs[p] = v
        if longs:
            _ag, rule_name, rule_text = chart_caster.get_node_agent_info(
                raw, longs)
            rule = f'{rule_name}: {rule_text}'
            node_lon = longs.get(raw)
            if node_lon is not None:
                # Level 1: conjoined within 3°20' (orb is OURS; no book orb)
                for p, plon in longs.items():
                    if p in ('Rahu', 'Ketu'):
                        continue
                    d = abs(node_lon - plon)
                    if d > 180:
                        d = 360 - d
                    if d <= 3.34:
                        candidates['conjoined'].append(p)
                # Level 2: star-lord (classical planet only)
                star = chart_caster.get_star_lord(node_lon)
                if star not in ('Rahu', 'Ketu'):
                    candidates['star_lord'].append(star)
                # Level 3: Vedic aspects within 3°20'
                _ASP = {'Sun': (180,), 'Moon': (180,), 'Mars': (180, 90, 240),
                        'Mercury': (180,), 'Jupiter': (180, 120, 240),
                        'Venus': (180,), 'Saturn': (180, 60, 270)}
                for p, plon in longs.items():
                    if p in ('Rahu', 'Ketu'):
                        continue
                    d = (node_lon - plon) % 360
                    for a in _ASP.get(p, (180,)):
                        if abs(d - a) <= 3.34:
                            candidates['aspecting'].append(p)
                            break
                # Level 4: sign-lord (last resort)
                candidates['sign_lord'].append(
                    chart_caster.get_sign_lord(node_lon))
    except Exception:
        rule = ''
    n_cand = sum(len(v) for v in candidates.values())
    disagreement = ('MULTIPLE_CANDIDATES_AGGREGATION_OPEN'
                    if n_cand > 1 else 'single-candidate')
    return {
        'node': raw,
        'agent': agent,
        'rule': rule,
        'cascade_source': ('R6:10335 conjoined -> star-lord -> aspecting -> '
                           'sign-lord; R3:8287 order tension noted; '
                           "3°20' orb is OURS (no book orb found)"),
        'agent_candidates': candidates,
        'selection_reason': rule,
        'node_star_lord': node_f.get('star_lord'),
        'node_occupies': node_f.get('house_occupied'),
        'raw_significations': {'occupies': node_f.get('house_occupied')},
        'agent_occupies': agent_f.get('house_occupied'),
        'agent_owns': agent_f.get('owns_houses'),
        'agent_significations': {
            'occupies': agent_f.get('house_occupied'),
            'owns': agent_f.get('owns_houses')},
        'disagreement_status': disagreement,
        'audit': ('book aggregates multiple agents (R6:14044); engine '
                  'selects closest single — open, needs user ruling'),
    }


def _planet_profile(facts, planet):
    """One planet's 4-level signification profile (user's planet-significator
    data model). Nodes: no ownership; agent link via sign-lord only (PARTIAL —
    the full book cascade is computed only for the deciding planet)."""
    f = facts.get(planet, {})
    star = f.get('star_lord')
    star_f = facts.get(star, {})
    occ = f.get('house_occupied')
    owns = list(f.get('owns_houses') or [])
    star_occ = star_f.get('house_occupied')
    star_owns = list(star_f.get('owns_houses') or [])
    notes = []
    sigs = []

    def add(house, level, source, path):
        try:
            h = int(house)
        except (TypeError, ValueError):
            return
        if not 1 <= h <= 12:
            return
        sigs.append({'house': h, 'level': level, 'source': source,
                     'weight': LEVEL_WEIGHTS[source], 'path': path})

    add(star_occ, 1, 'star_lord_occupation',
        f'{planet} -> star-lord {star} occupies house {star_occ}')
    add(occ, 2, 'planet_occupation', f'{planet} occupies house {occ}')
    for h in star_owns:
        add(h, 3, 'star_lord_ownership',
            f'{planet} -> star-lord {star} owns house {h}')
    if planet in ('Rahu', 'Ketu'):
        notes.append('nodes own no houses; agent link via sign-lord '
                     f'{f.get("sign_lord")} (PARTIAL)')
    else:
        for h in owns:
            add(h, 4, 'planet_ownership', f'{planet} owns house {h}')
    return {'planet': planet, 'star_lord': star,
            'occupation': occ, 'ownership': owns,
            'star_lord_occupation': star_occ,
            'star_lord_ownership': star_owns,
            'significations': sigs, 'notes': notes}


def _build_planet_profiles(reading):
    facts = {f.get('planet'): f for f in (reading.get('planet_facts') or [])}
    order = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
             'Rahu', 'Ketu']
    return {p: _planet_profile(facts, p) for p in order if p in facts}


def _build_house_table(planet_profiles):
    """Invert planet profiles: house -> significator planets with level,
    source and path (user's house-significator table)."""
    table = {h: [] for h in range(1, 13)}
    for planet, prof in planet_profiles.items():
        for s in prof['significations']:
            table[s['house']].append({
                'planet': planet, 'level': s['level'],
                'source': s['source'], 'weight': s['weight'],
                'path': s['path']})
    for h in table:
        table[h].sort(key=lambda r: (r['level'], r['planet']))
    return table


def judge(router_out, city, horary_number, as_of=None, coords=None):
    """Weighted-evidence verdict with sub-lord gate. Never raises."""
    try:
        return _judge(router_out, city, horary_number,
                      as_of=as_of, coords=coords)
    except Exception as e:
        return {'status': 'error', 'reason': f'judgment failed: {e}'[:200]}


def _judge(router_out, city, horary_number, as_of=None, coords=None):
    # Exception path: delegate to the traditional module (procedure unchanged)
    if router_out.get('status') == 'exception':
        out = L3T.judge(router_out, city, horary_number,
                        as_of=as_of, coords=coords)
        out['method'] = 'layer2b-exception'
        return out
    if router_out.get('status') != 'ok':
        return {'status': 'error',
                'reason': 'layer-2 did not produce a routable result',
                'router': router_out}

    success = set(router_out['success'])
    denial = set(router_out['denial'])
    primary = int(router_out['primary_cusp'])

    reading = _cast(city, horary_number, success, denial, primary,
                    as_of, coords)
    if not reading or 'error' in reading:
        return {'status': 'error',
                'reason': reading.get('error', 'engine returned nothing')[:200]}

    # --- Promise + sub-lord gate ---
    verdict, reason, gate, evidence = _decide_from_reading(
        reading, success, denial)
    s_score, d_score, strong_s, strong_d = _score(evidence, success, denial)

    # --- Stability test (time perturbation) ---
    stab = _stability(city, horary_number, success, denial, primary, as_of,
                      coords, verdict, reading.get('cusp_sub_lord'))
    answerability_reasons = []
    if reason:
        answerability_reasons.append(reason)
    if gate['gate_flipped_to_no']:
        answerability_reasons.append('gate_flipped_yes_to_no')
    if gate['pending_review']:
        answerability_reasons.append('pending_review')
    if stab['boundary_sensitive']:
        verdict = 'OTHER'
        answerability_reasons.append('boundary_sensitive')
    elif stab.get('uncertain'):
        answerability_reasons.append('mildly_unstable_chart')

    # --- House-coverage confidence gate (kept; OURS tables only) ---
    coverage = 0.0
    coverage_lean = False
    coverage_note = ''
    if success or denial:
        coverage = len(success | denial) / 12.0
        tables_prov = ((router_out.get('provenance') or {}).get('tables') or '')
        if coverage < COVERAGE_FLOOR and tables_prov == 'OURS' \
                and verdict in ('YES', 'NO', 'DELAYED'):
            coverage_lean = True
            coverage_note = (
                'low-coverage OURS table (%.2f): %s downgraded to OTHER'
                % (coverage, verdict))
            verdict = 'OTHER'
            answerability_reasons.append('low_coverage_ours')

    # --- Node agent exposure ---
    node_res = _node_resolution(reading)

    # --- House-centric significator table + planet profiles ---
    planet_profiles = _build_planet_profiles(reading)
    house_table = _build_house_table(planet_profiles)

    # --- Diagnostic keys (pipeline compat + Layer-4/report use) ---
    planet_retro = _retro_map(reading)
    _decision = ((reading.get('ai_facts') or {}).get('decision')) or {}
    sig = reading.get('significators', {}) or {}

    signified = sorted({e['house'] for e in evidence})
    s_hit = sorted({e['house'] for e in evidence
                    if e.get('classification') == 'success'})
    d_hit = sorted({e['house'] for e in evidence
                    if e.get('classification') == 'denial'})

    if verdict in ('YES', 'NO'):
        answer_status = 'OK'
    elif verdict in ('DELAYED', 'OTHER_WITH_SUPPORT'):
        answer_status = 'PARTIAL'
    else:
        answer_status = 'INSUFFICIENT'

    return {
        'status': 'ok',
        'verdict_class': verdict,
        'method': 'weighted-evidence+sublord-gate',
        # Strict timing gate (user ruling 2026-09-30): timing runs ONLY on
        # YES. NO / OTHER / DELAYED / OTHER_WITH_SUPPORT -> NO_TIMING_WINDOW.
        'timing_eligible': verdict == 'YES',
        'answerability': {
            'status': answer_status,
            'reasons': answerability_reasons,
        },
        'evidence': evidence,
        'gate': gate,
        'scores': {'success': round(s_score, 3), 'denial': round(d_score, 3),
                   'strong_success': round(strong_s, 3),
                   'strong_denial': round(strong_d, 3),
                   'margin': MARGIN, 'strong_threshold': STRONG},
        'stability': stab,
        'node_resolution': node_res,
        'deciding_planet': reading.get('deciding_planet'),
        'cusp_sub_lord': reading.get('cusp_sub_lord'),
        'star_lord': sig.get('true_star_lord'),
        'signified_houses': signified,
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
        'planet_profiles': planet_profiles,
        'house_table': house_table,
        'planet_retro': planet_retro,
        'chart_data': reading.get('chart_data') or {},
        'horary_ascendant_longitude': reading.get('horary_ascendant_longitude'),
        'eleventh_csl': _decision.get('eleventh_csl_check'),
        'moon_genuineness': _decision.get('moon_genuineness'),
        'provenance': {
            'layer3': ('weighted-evidence + sub-lord gate (BOOK level order; '
                       'weights + gate mechanics TUNABLE/OURS)'),
            'tables': router_out.get('provenance', {}).get('tables'),
            'denial': router_out.get('provenance', {}).get('denial'),
            'rotation': router_out.get('provenance', {}).get('rotation'),
        },
    }
