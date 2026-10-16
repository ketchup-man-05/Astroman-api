"""v5 pipeline — the single public contract: answer().

Full flow:
    layer1_stage1.dissect
      -> layer2_router.route (+ layer2b exceptions via layer3)
      -> [second-marriage BOOK gate, before judgment]
      -> chart_caster.execute_kp_reading (READ-ONLY; frozen engine's
         score/verdict are ignored)
      -> layer3_traditional.judge (traditional core, zero scoring)
      -> layer4_overrides (toggleable OURS flips, at most one)
      -> report-only signals (11th CSL, Moon genuineness)

answer(question, city, horary_number, as_of=None) -> dict with EXACTLY these
keys (plus 'why' on UNANSWERABLE):
    verdict, verdict_source, question, city, number, subject, event,
    primary_cusp, rotated, success, denial, denial_provenance, cusp_sub_lord,
    deciding_planet, star_lord, signified, success_hit, denial_hit,
    retrograde_delay, overrides_applied (list), report_signals
    {eleventh_csl, moon_genuineness}, exception, notes

NO kp_score anywhere. NO timing (timing_v5 is never called — timing is
excluded by the user's standing order until they teach the method).
If dissection or routing fails -> verdict 'UNANSWERABLE' with the same keys
present as None.

verdict_source values:
    'traditional'                              pure Krishnamurti judgment
    'weighted'                                 hierarchical-evidence judgment
    'OVERRIDE:<name>'                          one Layer-4 OURS flip applied
    'BOOK-GATE:second-marriage-dual-condition' gate failed -> NO
    'exception'                                layer2b procedure verdict
    'UNANSWERABLE'                             could not judge honestly
"""
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))

from kp import chart_caster  # noqa: E402  (frozen engine; read-only use)
from engine import config as _cfg  # noqa: E402
from engine import layer1_stage1 as L1  # noqa: E402
from engine import layer2_router as L2  # noqa: E402
from engine import layer2_5_moon as L25  # noqa: E402
from engine import dual_cusp as DUAL  # noqa: E402
from engine import layer3_traditional as L3T  # noqa: E402
from engine import layer3_weighted as L3W  # noqa: E402
import layer3_v10_2 as L3V102  # noqa: E402
from engine import layer4_overrides as L4  # noqa: E402
from engine import timing as TIMING  # noqa: E402  (v10.5: DBA-sookshma windows, downstream of verdict only)

# Active Layer-3 judge (config.L3_WEIGHTED selects the weighted-evidence
# judge; the traditional flat-set judge stays available as fallback).
L3 = L3V102 if _cfg.L3_V10_2 else (L3W if _cfg.L3_WEIGHTED else L3T)

ANSWER_KEYS = ['verdict', 'verdict_source', 'question', 'city', 'number',
               'subject', 'event', 'primary_cusp', 'rotated', 'success',
               'denial', 'denial_provenance', 'cusp_sub_lord',
               'deciding_planet', 'star_lord', 'signified', 'success_hit',
               'denial_hit', 'retrograde_delay', 'overrides_applied', 'modifiers',
               'report_signals', 'exception', 'notes',
               'chart_data', 'horary_ascendant_longitude', 'complication',
               'resolution', 'timing']

DUAL_SIGNS = {'Gemini', 'Virgo', 'Sagittarius', 'Pisces', 3, 6, 9, 12}
# Planets that OWN a dual sign (fixed Vedic sign lordship):
# Mercury -> Gemini + Virgo; Jupiter -> Sagittarius + Pisces.
DUAL_SIGN_OWNERS = {'Mercury', 'Jupiter'}

GATE_CITE = 'R6 p.165 (R6:9029-9044)'


def _horary_number_status(number):
    """Explicit horary-number status (v5.1, compendium review).

    Book note: numbers above 249 indicate non-fulfillment (KSK; see
    decision_lab/kp_origins/KP_INVENTION_REPORT.md). The engine does NOT
    currently apply that as a fulfillment verdict — the frozen Layer 3
    refuses numbers outside 1-249 outright, so the de-facto behavior is
    reject-with-UNANSWERABLE. Whether out-of-range should instead mean
    clarify-the-number or a book non-fulfillment reading is a USER RULING
    pending.
    """
    try:
        n = int(number)
    except (TypeError, ValueError):
        n = None
    in_range = n is not None and 1 <= n <= 249

    return {
        'number': n,
        'range': 'valid' if in_range else 'out_of_range',
        'engine_behavior': ('reject: frozen Layer 3 requires 1-249; '
                            'out-of-range returns UNANSWERABLE '
                            '(USER RULING PENDING: keep reject / ask to '
                            're-pick / apply book non-fulfillment)'),
        'book_note': '>249 = desire unfulfilled (KSK); not applied as a veto',
    }



def _question_validity(d, number_status):
    """Question-validity block (v5.1, compendium review).

    Derived honestly from the Layer-1 dissection plus the horary-number
    status. Fields the current Layer 1 does not track are labeled
    'not_tracked_yet' — NOT invented. The frame extractor prototype
    (rebuild/frame_extractor.py) is the vehicle for the full version:
    one_event_only, time_scope, querent_intent, clarification_count.
    """
    d = d or {}
    subj = d.get('subject_key')
    return {
        'one_event_only': 'not_tracked_yet (frame extractor vehicle)',
        'subject_identified': subj not in (None, 'stranger_unknown'),
        'subject_key': subj,
        'event_identified': d.get('event_key') is not None,
        'event_key': d.get('event_key'),
        'time_scope_present_or_not':
            'not_tracked_yet (frame extractor vehicle)',
        'querent_intent_clear':
            'not_tracked_yet (frame extractor vehicle)',
        'horary_number_valid':
            (number_status or {}).get('range') == 'valid',
        'clarification_count': 'not_tracked_yet (frame extractor vehicle)',
        'dissection_status': d.get('status'),
    }



def _abstention_reason_unanswerable(why):
    """One-word reason code for UNANSWERABLE. Measurement only; never affects logic."""
    w = why or ''
    if 'Layer-1 clarify' in w:
        return 'dissect-clarify'
    if 'Layer-2 unsupported' in w:
        return 'routing-unsupported'
    if 'Layer-1' in w:
        return 'dissect-fail'
    if 'Layer-2' in w:
        return 'routing-failed'
    if 'Layer-3' in w:
        return 'judgment-failed'
    if 'horary' in w.lower() or 'number' in w.lower():
        return 'number-out-of-range'
    if 'pipeline error' in w:
        return 'pipeline-error'
    return 'unknown'


def _abstention_reason_other(judge_out, moon25):
    """One-word reason code for OTHER verdicts. Measurement only."""
    if moon25 and moon25.get('blocked'):
        return 'moon-gate'
    trace = (judge_out or {}).get('v9_5_trace') or []
    if trace:
        return 'judge:' + str(trace[-1].get('rule') or 'unknown')
    return 'judge:unknown'


def _unanswerable(question, city, number, why, validity=None):
    out = {k: None for k in ANSWER_KEYS}
    out.update({'verdict': 'UNANSWERABLE', 'verdict_source': 'UNANSWERABLE',
                'question': question, 'city': city, 'number': number,
                'overrides_applied': [], 'notes': [why], 'why': why,
                'abstention_reason': _abstention_reason_unanswerable(why),
                'horary_number_status': _horary_number_status(number),
                'question_validity': validity})
    return out


def check_dual_condition(sub_lord, planet_facts):
    """Pure BOOK gate condition (i), R6 p.165: the 7th-cusp sub-lord must be
    Mercury itself, OR be deposited in a dual sign (Gemini/Virgo/Sagittarius/
    Pisces), OR be in the constellation of a planet that is in or owns a dual
    sign. 'Owns a dual sign' = is Mercury or Jupiter (fixed sign lordship).

    planet_facts: {planet_name: {'sign': name_or_number, 'star_lord': name}}.
    Returns (passed: bool, detail: str).
    """
    facts = planet_facts or {}
    sub = sub_lord
    if sub == 'Mercury':
        return True, '7th-cusp sub-lord is Mercury itself'
    f = facts.get(sub) or {}
    if f.get('sign') in DUAL_SIGNS:
        return True, f'{sub} is deposited in dual sign {f.get("sign")}'
    star = f.get('star_lord')
    sf = facts.get(star) or {}
    if sf.get('sign') in DUAL_SIGNS:
        return True, (f'{sub} is in the constellation of {star}, which is '
                      f'deposited in dual sign {sf.get("sign")}')
    if star in DUAL_SIGN_OWNERS:
        return True, (f'{sub} is in the constellation of {star}, which owns '
                      f'a dual sign')
    return False, (f'{sub} is not Mercury, is not in a dual sign '
                   f'({f.get("sign")}), and its star-lord {star} neither '
                   f'occupies nor owns one')


def second_marriage_gate(city, horary_number, as_of=None, coords=None):
    """BOOK gate for second_marriage (R6 p.165), checked BEFORE judgment.

    Casts the chart with key_house=7 through the same read-only path
    layer3_traditional uses, then applies check_dual_condition to the 7th
    cusp's sub-lord. Condition (ii) — signification of 2 or 11 — is the normal
    Layer-3 signification check and is not duplicated here.
    Returns {'passed': bool, 'detail': str, 'sub_lord': str}."""
    try:
        reading = chart_caster.execute_kp_reading(
            city, int(horary_number), [], [],
            key_house=7, as_of=as_of, coords=coords,
            chart_time_mode='query', log=False, include_timing=False)
    except Exception as e:
        return {'passed': True, 'detail': f'gate chart failed ({e}); gate skipped open',
                'sub_lord': None, 'gate_error': str(e)[:120]}
    if not reading or 'error' in reading:
        return {'passed': True,
                'detail': 'gate chart failed; gate skipped open',
                'sub_lord': None}
    sub = reading.get('cusp_sub_lord')
    facts = {}
    for f in (reading.get('planet_facts') or []):
        facts[f.get('planet')] = {'sign': f.get('sign'),
                                  'star_lord': f.get('star_lord')}
    passed, detail = check_dual_condition(sub, facts)
    return {'passed': passed, 'detail': detail, 'sub_lord': sub}


def _report_signals(judge_out):

    """Report-only signals (never touch the verdict), mirroring what frozen
    v1 reported: the 11th-CSL fulfillment check and the Moon genuineness check
    (KP Reader VI; the Moon reflects the querent's mind, R8)."""
    eleventh = judge_out.get('eleventh_csl') or {}
    cls = (eleventh.get('classification') or '').lower()
    if cls == 'confirms':
        e = 'supports'
    elif cls == 'contradicts':
        e = 'contradicts'
    else:
        e = 'neutral'
    moon = judge_out.get('moon_genuineness') or {}
    if moon.get('reflected'):
        m = 'genuine'
    elif (moon.get('score') if isinstance(moon.get('score'), (int, float))
          else 0) <= -1:
        m = 'reserve'
    else:
        m = 'neutral'
    return {
        'eleventh_csl': {
            'reading': e,
            'cusp_sub_lord': eleventh.get('cusp_sub_lord'),
            'deciding_planet': eleventh.get('deciding_planet'),
            'star_lord': eleventh.get('deciding_planet_star_lord'),
            'source': eleventh.get('source'),
        },
        'moon_genuineness': {
            'reading': m,
            'moon_house': moon.get('moon_house'),
            'moon_star_lord': moon.get('moon_star_lord'),
            'source': moon.get('source'),
        },
    }


def _t1_extract_decider(trace):
    """Tier 1: extract decider planet from trace (report-only)."""
    import re
    for x in reversed(trace or []):
        d = x.get('detail') or ''
        m = re.search(r'CSL (\w+)', d)
        if m:
            return m.group(1)
    return None


def _t1_chain_depth(trace):
    """Tier 1: count distinct chain levels mentioned (report-only)."""
    # Proxy: number of trace rules that mention chain/hit
    return sum(1 for x in (trace or [])
               if 'hit' in (x.get('detail') or '').lower())


def _shadow_record(out3, router_out, verdict, modifiers):
    """Shadow log for future margin calibration (2026-10-13).
    Captures S/D/margin signals on every reading WITHOUT affecting the verdict.
    When 'did it come true' labels arrive, fit thresholds on this data.
    Returns a dict; the app persists it (Sheets/DB). No PII.
    """
    import re, datetime
    trace = out3.get('v9_5_trace') or []
    rules = [x.get('rule') for x in trace if x.get('rule')]
    # verdict-determining rule: last non-diagnostic rule
    _diag = {'moon_diagnostic', 'moon_hiding', 'moon_saturn_friction',
             'punarphoo_sub_form', 'eleventh_confirms', 'eleventh_silent'}
    last_rule = next((x for x in reversed(rules) if x not in _diag),
                     rules[-1] if rules else 'unknown')
    s_hit = out3.get('success_hit') or []
    d_hit = out3.get('denial_hit') or []
    # weighted margin where instrumented (marriage_margin trace entry)
    w_margin = None
    for x in trace:
        if x.get('rule') == 'marriage_margin':
            m = re.search(r'margin=(-?[\d.]+)', x.get('detail', ''))
            if m:
                w_margin = float(m.group(1))
    return {
        'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'event': router_out.get('event_key') or 'unknown',
        'verdict': verdict,
        'modifiers': modifiers or [],
        'last_rule': last_rule,
        's_count': len(s_hit),
        'd_count': len(d_hit),
        'count_margin': len(s_hit) - len(d_hit),
        'weighted_margin': w_margin,
        # Tier 1 report-only (2026-10-14, Claude): collect now, analyze when
        # outcomes arrive. Zero verdict risk.
        't1_decider': _t1_extract_decider(trace),
        't1_chain_depth': _t1_chain_depth(trace),
    }


def answer(question, city, horary_number, as_of=None, coords=None,
           use_gemini=True):
    """The v5 public contract. Never raises; returns the ANSWER_KEYS dict.
    coords: optional (lat, lon) to skip geocoding (used by the corpus test).
    use_gemini: Layer-1 Gemini fallback for unknown words (default True;
    lab measurement scripts pass False for deterministic results)."""
    try:
        return _answer(question, city, horary_number, as_of=as_of,
                       coords=coords, use_gemini=use_gemini)
    except Exception as e:
        return _unanswerable(question, city, horary_number,
                             f'pipeline error: {e}'[:200])


def _answer(question, city, horary_number, as_of=None, coords=None,
            use_gemini=True):
    notes = []
    # 2026-10-15 (Claude review A10): freeze the judgment moment once, so
    # every chart cast in this answer (L3 dual path, L2.5, timing, gates)
    # uses the same instant instead of each calling now() independently.
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    # ---- Layer 1: dissect ----
    # 2026-10-13: pass as_of as ref so date parsing uses the question time,
    # not now(). (Was: ref=None -> now() -> past dates rejected in re-runs.)
    d = L1.dissect(question or '', ref=as_of, use_gemini=use_gemini)
    if d.get('status') == 'out_of_scope':
        # v10.4 Phase 4: clean handoff to human chat (premium tier).
        # Distinct from UNANSWERABLE dead-ends — the question is preserved
        # for a human agent with the detected topic and reason.
        out = {k: None for k in ANSWER_KEYS}
        out.update({'verdict': 'HUMAN_CHAT', 'verdict_source': 'OUT_OF_SCOPE',
                    'question': question, 'city': city, 'number': horary_number,
                    'overrides_applied': [],
                    'notes': ['Out of scope: %s. Handing to human chat.'
                              % (d.get('reason') or 'outside the 4 topics')],
                    'why': d.get('reason') or 'out of scope',
                    'handoff': 'human_chat',
                    'out_of_scope_topic': d.get('topic'),
                    'out_of_scope_reason': d.get('reason'),
                    'horary_number_status': _horary_number_status(horary_number),
                    'question_validity': _question_validity(
                        d, _horary_number_status(horary_number))})
        return out
    if d.get('status') != 'ok':
        why = ('clarify' if d.get('status') == 'clarify' else 'dissect-fail')
        return _unanswerable(
            question, city, horary_number,
            f"Layer-1 {why}: {d.get('question') or d.get('error') or d.get('gap') or 'question not understood'}",
            _question_validity(d, _horary_number_status(horary_number)))
    qv = _question_validity(d, _horary_number_status(horary_number))
    subject_key, event_key = d['subject_key'], d['event_key']

    # ---- Layer 2: route ----
    r = L2.route(d)
    # v10.1 plumbing fix: L2 router doesn't include question text, but L3
    # procedures need it (e.g., interview detector, named-job branches).
    # Inject here so all judges benefit.
    if isinstance(r, dict) and not r.get('question'):
        r['question'] = question
    if r.get('status') == 'unsupported':
        return _unanswerable(question, city, horary_number,
                             f"Layer-2 unsupported: {r.get('reason')}", qv)
    if r.get('status') not in ('ok', 'exception'):
        return _unanswerable(question, city, horary_number,
                             f"Layer-2 routing failed: {r.get('status')}", qv)
    is_exception = (r.get('status') == 'exception')

    # ---- BOOK gate: second marriage (before judgment) ----
    if event_key == 'second_marriage' and _cfg.SECOND_MARRIAGE_GATE \
            and not is_exception:
        gate = second_marriage_gate(city, horary_number, as_of=as_of,
                                     coords=coords)
        notes.append(f"Second-marriage gate ({GATE_CITE}): "
                     f"7th-cusp sub-lord {gate.get('sub_lord')}; {gate['detail']}")
        if not gate['passed']:
            out = {k: None for k in ANSWER_KEYS}
            out.update({
                'verdict': 'NO',
                'verdict_source': 'BOOK-GATE:second-marriage-dual-condition',
                'question': question, 'city': city, 'number': horary_number,
                'horary_number_status': _horary_number_status(horary_number),
                'question_validity': qv,
                'subject': subject_key, 'event': event_key,
                'overrides_applied': [],
                'modifiers': [],
                'report_signals': {'eleventh_csl': None,
                                  'moon_genuineness': None},
                'exception': False,
                'notes': notes + [
                    f"BOOK gate failed ({GATE_CITE}): condition (i) not met -> "
                    f"NO. No signification judgment was run."]})
            return out

    # ---- Layer 2.5: Moon genuineness gate (user ruling 2026-10-01) ----
    # The Moon must reflect the question before any judgment is attempted.
    # 'hard' (default): FAIL blocks Layer 3 -> OTHER. 'flag': record only.
    moon25 = None
    if _cfg.MOON_GATE_ENABLED:
        moon25 = L25.check(r, city or 'Unknown', int(horary_number),
                           as_of=as_of, coords=coords)
        notes.append(f"Layer-2.5 Moon genuineness: {moon25['genuineness']} — "
                     f"{moon25['summary']}")
        blocked = (moon25['genuineness'] == 'FAIL'
                   and _cfg.MOON_GATE_MODE == 'hard')
        moon25['blocked'] = blocked
        if blocked:
            out = {k: None for k in ANSWER_KEYS}
            out.update({
                'verdict': 'OTHER',
                'verdict_source': 'MOON-GATE:layer-2.5',
                'question': question, 'city': city, 'number': horary_number,
                'horary_number_status': _horary_number_status(horary_number),
                'question_validity': qv,
                'subject': subject_key, 'event': event_key,
                'primary_cusp': r.get('primary_cusp'),
                'success': sorted(r.get('success') or []),
                'denial': sorted(r.get('denial') or []),
                'overrides_applied': [],
                'modifiers': ['MOON_GENUINENESS_FAIL'],
                'abstention_reason': 'moon-gate',
                'report_signals': {'eleventh_csl': None,
                                   'moon_genuineness': moon25['report']},
                'exception': bool(is_exception),
                'notes': notes + [
                    "Layer-2.5 blocked judgment: the Moon's chain does not "
                    "signify any house of this question, so the chart is not "
                    "valid to judge (mode=hard)."]})
            return out

    # ---- Layer 3: traditional judgment (frozen engine read-only) ----
    out3 = L3.judge(r, city or 'Unknown', int(horary_number), as_of=as_of,
                      coords=coords)
    if out3.get('status') != 'ok':
        return _unanswerable(question, city, horary_number,
                             f"Layer-3 judgment failed: {out3.get('reason')}", qv)

    # ---- Dual-cusp branch (user ruling 2026-09-29): an ACTIVE secondary
    # block -> judge each cusp with the existing judge, then synthesize
    # (YY->YES, NN->NO, else OTHER + PARTIAL_OR_MIXED). Report signals and
    # Layer-4 flags keep coming from the primary run; only the verdict is
    # replaced. Proposals (dual_active false) never reach this branch.
    resolution = None
    if r.get('secondary'):
        dual = DUAL.judge_dual(L3.judge, r, city or 'Unknown',
                               int(horary_number), as_of=as_of, coords=coords)
        if dual.get('status') != 'ok':
            return _unanswerable(
                question, city, horary_number,
                f"Layer-3 dual-cusp judgment failed: {dual.get('reason')}", qv)
        out3 = dual['out3']
        notes.extend(dual['notes'])
        resolution = (out3.get('dual') or {}).get('resolution')
        notes.append(f"Dual-cusp synthesis: primary {out3['dual']['primary_cusp']}th "
                     f"= {out3['dual']['primary_verdict']}, secondary "
                     f"{out3['dual']['secondary_cusp']}th = "
                     f"{out3['dual']['secondary_verdict']} -> {out3['verdict_class']}"
                     + (f" [{resolution}]" if resolution else ""))

    verdict = out3['verdict_class']
    verdict_source = ('exception' if out3.get('exception')
                      else getattr(L3, 'JUDGE_NAME',
                                   'weighted' if _cfg.L3_WEIGHTED
                                   else 'traditional'))
    if r.get('secondary'):
        verdict_source += '+dual-cusp'

    # ---- Layer 4: flag-only OURS modifiers (v5.1: no verdict reversals) ----
    overrides_applied = []
    modifiers = []
    # v10.3 fix (2026-10-06): merge L3's modifiers (e.g., DELAYS from
    # mixed->YES+DELAYS doctrine). Previously dropped — YES+DELAYS never
    # surfaced in pipeline output.
    for m in (out3.get('modifiers') or []):
        if m not in modifiers:
            modifiers.append(m)
    if moon25 and moon25['genuineness'] == 'CAUTION':
        modifiers.append('MOON_GENUINENESS_CAUTION')
        notes.append('Layer-2.5 caution: the Moon reflects the question but '
                     'sits at a sign extreme (or equivalent) — treat the '
                     'judgment with reserve.')
    if not out3.get('exception'):
        ctx = {'event_key': event_key,
               'success': set(out3.get('positive') or []),
               'denial': set(out3.get('negative') or [])}
        flags, _considered = L4.apply_overrides(out3, ctx)
        for flag in flags:
            notes.append(f"Layer-4 flag [{flag['label']}]: "
                         f"{flag['name']}: {flag['why']}")
            modifiers.append(flag['modifier'])
            overrides_applied.append(flag)


    # ---- Report-only signals ----
    signals = _report_signals(out3) if not out3.get('exception') else \
        {'eleventh_csl': None, 'moon_genuineness': None}
    if not out3.get('exception'):
        notes.append(f"11th-CSL fulfillment: {signals['eleventh_csl']['reading']}; "
                     f"Moon genuineness: {signals['moon_genuineness']['reading']} "
                     f"(report-only, never change the verdict).")
    if out3.get('retrograde_delay'):
        notes.append('Retrograde noted: delay/friction only; the verdict is '
                     'unchanged (standing user ruling).')

    # ---- USER-RULING soft-house complication (report-only, never verdict) ----
    # 2026-09-28 refinement: on romance events, 10th/12th are NOT denial.
    # They mean delay, or that the relationship ends abruptly/painfully.
    complication = None
    soft = set(r.get('soft_houses') or [])
    if soft and not out3.get('exception'):
        soft_hits = sorted(set(out3.get('signified_houses') or []) & soft)
        if soft_hits and verdict != 'NO':
            if event_key == 'romance_breakup':
                reading = ('10th/12th house(s) %s signified: the breakup may be delayed, '
                           'or it may come abruptly/painfully. Not a denial of the breakup; '
                           'the verdict stands.') % soft_hits
            else:
                reading = ('10th/12th house(s) %s signified: delay in the matter, or the '
                           'relationship may end abruptly/painfully. Not a denial; '
                           'the verdict stands.') % soft_hits
            complication = {'houses': soft_hits, 'label': 'USER-RULING',
                            'reading': reading}
            notes.append('User-rule complication [USER-RULING]: ' + reading +
                         ' Report-only; the verdict is unchanged.')

    # ---- House-coverage confidence gate (2026-09-29, user-approved) ----
    # Thin OURS tables lean instead of declaring; surfaced here so the
    # reason is visible in the final answer's notes.
    if out3.get('coverage_lean') and out3.get('coverage_note'):
        notes.append('Coverage gate: ' + out3['coverage_note'] + '.')
        verdict_source += '+coverage-lean'

    # ---- Weighted-evidence diagnostics (answerability + stability) ----
    ans = out3.get('answerability') or {}
    if ans.get('reasons'):
        notes.append('Answerability: ' + ', '.join(ans['reasons']) + '.')
    sc = out3.get('scores') or {}
    if sc:
        notes.append('Evidence scores: success=%.2f denial=%.2f '
                     '(strong>=%.2f, margin=%.2f).'
                     % (sc.get('success', 0), sc.get('denial', 0),
                        sc.get('strong_threshold', 0), sc.get('margin', 0)))
    stab = out3.get('stability') or {}
    if stab.get('samples', 0) > 1:
        notes.append('Stability: %d/5 time samples agree on sub-lord '
                     '(score %.2f)%s.'
                     % (round(stab.get('same_sub_lord_rate', 0) * 5),
                        stab.get('score', 0),
                        '; mildly unstable' if stab.get('uncertain') else ''))
    nr = out3.get('node_resolution')
    if nr:
        notes.append('Node resolution: %s acts through agent %s%s.'
                     % (nr['node'], nr['agent'],
                        f" ({nr['rule']})" if nr.get('rule') else ''))

    # ---- Timing (v10.5): DBA-sookshma window, downstream of verdict ONLY ----
    # Promise gate: YES / YES-WITH-DELAYS get timing; everything else -> None.
    # Never flips the verdict. (User rulings 2026-09-30 + 2026-10-06.)
    timing = None
    fixed_date_check = None
    # v10.6 fixed-date check (2026-10-06): for time-bound questions ("exam on
    # Dec 15?"), check if THAT date falls in a supportive dasha period instead
    # of finding the next window. Veto downgrades YES -> NO (book dasha veto).
    target_date = d.get('window_end')
    # 2026-10-13 (SCOPE FIX, not new rule): exempt exam_appear from the veto.
    # KSK Reader VI p.198 gives the lagna-deposition test with NO dasha
    # qualifier: "If the horary lagna is spoiled... the native will not be
    # able to make an attempt. If, however, the lagna is not spoiled, the
    # native will be able to act as he likes." The veto was built for outcome
    # events (pass/fail); applying it to appear/attend overrides the book.
    _VETO_EXEMPT = {'exam_appear'}
    # 2026-10-15: fixed-date veto REMOVED per user approval (Oct 6 ruling:
    # dasha veto is dead; Luna's recommendation accepted).
    if False:  # was: verdict in ('YES','YES-WITH-DELAYS') and target_date...
        fixed_date_check = TIMING.compute_fixed_date_for_answer(
            city, horary_number, as_of, coords, event_key,
            sorted(out3.get('positive') or []), r, target_date)
        hint = (fixed_date_check or {}).get('verdict_hint')
        if hint == 'vetoes':
            # Book dasha veto: cusp promises, but the period on the event
            # date doesn't support it. Downgrade to NO.
            verdict = 'NO'
            verdict_source += '+fixed-date-veto'
            notes.append('Fixed-date check: the dasha period running on %s '
                         'does not support this outcome — verdict downgraded '
                         'from YES to NO.'
                         % target_date.strftime('%d %b %Y')
                         if hasattr(target_date, 'strftime') else str(target_date))
        elif hint == 'supports_YES':
            notes.append('Fixed-date check: the period on %s supports this '
                         'outcome.'
                         % target_date.strftime('%d %b %Y')
                         if hasattr(target_date, 'strftime') else str(target_date))
        # Skip the open-window timing for fixed-date questions — the check
        # above IS the timing answer.
        timing = {
            'window_start': None,
            'window_end': None,
            'phrasing': (fixed_date_check or {}).get('phrasing', ''),
            'confidence': 'fixed-date',
            'fixed_date_check': fixed_date_check,
        }
    elif verdict in ('YES', 'YES-WITH-DELAYS'):
        # v10.8 dasha veto (2026-10-06): DISABLED 2026-10-06 — tested, hurts.
        # Negation veto (Path A) flips 2 correct YES→wrong NO (A3, E4-1);
        # RP-membership veto (Path B) flips 6 (exam 76.2%→57.1%).
        # Book cases are real (DASHA_VETO_CALIBRATION.md) but don't translate
        # to a reliable automated rule — astrologer judgment calls, not
        # mechanical. Mechanism preserved in timing.py:check_current_period
        # (veto_type='negation'|'rp_membership') for future calibration.
        # W157/W155 already NO from L3; veto can't improve them.
        if False:  # _DASHA_VETO_ENABLED
            _DASHA_VETO_EVENTS = {'exam_pass_general', 'exam_competitive',
                                  'exam_distinction_rank', 'education_general',
                                  'education_higher'}
            if event_key in _DASHA_VETO_EVENTS:
                veto_check = TIMING.compute_dasha_veto_for_answer(
                    city, horary_number, as_of, coords, event_key,
                    sorted(out3.get('positive') or []), r,
                    denial_houses=sorted(out3.get('negative') or []))
                if (veto_check or {}).get('verdict_hint') == 'vetoes':
                    verdict = 'NO'
                    verdict_source += '+dasha-veto'
                    vtype = (veto_check or {}).get('veto_type') or 'dasha'
                    lords = (veto_check or {}).get('running_lords', {})
                    notes.append('Dasha veto (%s): the current period does not '
                                 'support this yet — the timing isn\'t right, '
                                 'even though the promise is there. '
                                 '(running: %s/%s/%s)'
                                 % (vtype, lords.get('dasha'), lords.get('bhukti'),
                                    lords.get('antara')))
        # Only compute timing if the veto didn't fire (verdict still YES)
        if verdict in ('YES', 'YES-WITH-DELAYS'):
            timing = TIMING.compute_timing_for_answer(
                city, horary_number, as_of, coords, event_key,
                sorted(out3.get('positive') or []), r, verdict, modifiers)

    # ---- Polarity framing (2026-09-29; MOVED 2026-10-14, Gemini 4) ----
    # "Will my visa get rejected?" — the chart's YES means the visa is
    # GRANTED, but the user asked about rejection. Applied LAST, after the
    # fixed-date veto and open-window timing (which judge the canonical
    # positive event on the un-inverted verdict).
    if d.get('invert_verdict') and not out3.get('exception') \
            and verdict in ('YES', 'NO'):
        verdict = 'NO' if verdict == 'YES' else 'YES'
        verdict_source += '+polarity-flip'
        notes.append('Polarity framing: the question was asked in negative '
                     'terms ("rejected/cancelled/denied…") while the chart '
                     'judges the positive outcome — the verdict is presented '
                     'flipped so it answers what was asked.')

    _abs_reason = (_abstention_reason_other(out3, moon25)
                   if verdict == 'OTHER' else None)
    return {
        'verdict': verdict,
        'verdict_source': verdict_source,
        'abstention_reason': _abs_reason,
        'question': question,
        'city': city,
        'number': horary_number,
                'horary_number_status': _horary_number_status(horary_number),
                'question_validity': qv,
        'subject': subject_key,
        'event': event_key,
        'primary_cusp': r.get('primary_cusp') or r.get('key_house'),
        'rotated': r.get('rotated'),
        'success': sorted(out3.get('positive') or []),
        'denial': sorted(out3.get('negative') or []),
        'denial_provenance': (r.get('provenance') or {}).get('denial'),
        'cusp_sub_lord': out3.get('cusp_sub_lord'),
        'deciding_planet': out3.get('deciding_planet'),
        'star_lord': out3.get('star_lord'),
        'signified': sorted(out3.get('signified_houses') or []),
        'success_hit': sorted(out3.get('success_hit') or []),
        'denial_hit': sorted(out3.get('denial_hit') or []),
        'retrograde_delay': bool(out3.get('retrograde_delay')),
        'overrides_applied': overrides_applied,
        'modifiers': modifiers,
        'report_signals': signals,
        'exception': bool(out3.get('exception')),
        'notes': notes,
        'chart_data': out3.get('chart_data') or {},
        'horary_ascendant_longitude': out3.get('horary_ascendant_longitude'),
        'complication': complication,
        'resolution': resolution,
        'dual': out3.get('dual'),
        'timing': timing,
        'v9_5_trace': out3.get('v9_5_trace') or [],
        'shadow': _shadow_record(out3, r, verdict, modifiers),
    }
