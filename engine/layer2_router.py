"""v5 Layer 2 — the derivative math router (Bhavat Bhavam).

Pure arithmetic, no language understanding. Takes Layer 1's
{subject_base, event_rel} and produces the exact houses the frozen
engine must judge on.

Math (verified against R3:L22938, where Krishnamurti himself rotates the
promotion group 2,6,10,11 from the 7th to 8,12,4,5):
    target = ((base - 1) + (rel - 1)) % 12 + 1
    shift  : h -> ((h - 1) + (base - 1)) % 12 + 1

Rules:
- RELATIONAL GUARD: when the question is about the querent's own bond with a
  7th-house person, do NOT rotate — judge straight from lagna with the
  event's own groups. Triggers when (a) a relational phrase was flagged
  ("will my wife return to me"), or (b) subject_base == 7 and event_rel == 7
  ("will my wife get the divorce": the divorce IS the 7th-house matter).
  Note this is deliberately NOT a general base==rel rule: mother's property
  (4,4) MUST rotate to the 7th (4th from 4th) — the property is the mother's
  own affair, not the querent's bond.
- Denial fallback: where events.json has denial:[] (GROUP NOT GIVEN in the
  books), use 12th-from negation of each success house, tagged 'OURS'.
  Sanity: marriage success [2,7,11] -> fallback [1,6,10], which is exactly
  the book's stated denial — the fallback reproduces doctrine where both
  are known.
- Events with empty success groups and no exception procedure
  (theft_identify_thief, love_affair) -> status 'unsupported' with an honest
  reason. The books give no yes/no group and no verified procedure; v5
  refuses to invent one.
- EXCEPTION events (loan_repay_clear, missing_person_status, rumor_true)
  carry an "exception" descriptor in events.json -> status 'exception'
  with {procedure, params}. Layer-2b runs the registered procedure against
  the cast chart; no house arrays are involved.
- Per-event "provenance" in events.json (BOOK / OURS / BOOK-premise/OURS-array
  / OURS-WEAK) is surfaced as provenance['tables']; exception events carry
  the procedure's own provenance instead.
"""
import json
import os
import warnings

from engine import config as _cfg

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, 'events.json'), encoding='utf-8') as f:
    EVENTS = json.load(f)


# 2026-10-14: canonical bond-event set, shared with Layer 1 (layer1_stage1
# imports this). A bond event is one about the querent's own relational
# bond -- for these, the chart is judged from lagna (no rotation) when the
# bond belongs to the querent. Keep in sync: this is the single source.
BOND_EVENTS = frozenset({
    'marriage', 'marriage_love_specific', 'divorce', 'second_marriage',
    'spouse_return_estranged', 'romance_materialise', 'romance_breakup',
    'romance_reunion', 'romance_new_entry', 'friend_to_romance',
    'love_affair', 'love_reciprocation', 'relationship_longevity',
})


def derived_house(base, rel):
    """Relative house: count `rel` houses forward from `base` (1-indexed)."""
    return ((base - 1) + (rel - 1)) % 12 + 1


def shift_house(h, base):
    """Rotate house h as if `base` were the lagna."""
    return ((h - 1) + (base - 1)) % 12 + 1


def twelfth_from(h):
    """The house of negation for h (12th from it)."""
    return ((h - 2) % 12) + 1



def _denial_meta(denial, tables_prov, used_fallback):
    """Structured denial metadata (v5.1 schema).

    The OURS 12th-from fallback is CANDIDATE_NEGATION: diagnostic,
    OTHER-supporting, possible-delay — never an automatic NO or a gate
    flip. Book-given denial arrays keep DOCTRINE status.
    """
    if used_fallback:
        return {'houses': list(denial), 'provenance': 'OURS_FALLBACK',
                'status': 'CANDIDATE_NEGATION',
                'allowed_effects': ['diagnostic', 'support_for_OTHER',
                                    'possible_delay'],
                'forbidden_effects': ['automatic_NO', 'gate_flip']}
    if tables_prov == 'BOOK':
        return {'houses': list(denial), 'provenance': 'BOOK',
                'status': 'DOCTRINE', 'allowed_effects': ['verdict_use'],
                'forbidden_effects': []}
    return {'houses': list(denial), 'provenance': tables_prov,
            'status': 'PROVISIONAL',
            'allowed_effects': ['diagnostic', 'support_for_OTHER'],
            'forbidden_effects': ['gate_flip', 'automatic_NO']}

def route(dissect_out):
    """Returns a router dict; never raises.

    ok:          {primary_cusp, success, denial, key_house, rotated,
                  provenance, event_key, subject_key}
    unsupported: {status:'unsupported', reason, ...}
    """
    try:
        return _route(dissect_out)
    except Exception as e:
        return {'status': 'unsupported',
                'reason': f'router error: {e}'[:160]}


def _block(base, rel, success, denial, tables_prov, relational):
    """Judge one cusp block: returns
    (primary_cusp, success, denial, denial_meta, rotated, rotation_note).
    Used for the primary cusp and, identically, for the dual-cusp secondary
    (user ruling 2026-09-29 #9)."""
    success = sorted(success)
    used_fallback = not denial
    if relational:
        if not denial:
            denial = sorted({twelfth_from(h) for h in success})
            if _cfg.DENIAL_DEDUP_OVERLAP:
                denial = sorted(set(denial) - set(success))
        return (rel, success, sorted(denial),
                _denial_meta(sorted(denial), tables_prov, used_fallback),
                False, 'relational guard: no rotation')
    target = derived_house(base, rel)
    shifted_success = sorted({shift_house(h, base) for h in success})
    if denial:
        shifted_denial = sorted({shift_house(h, base) for h in denial})
    else:
        shifted_denial = sorted({twelfth_from(h) for h in shifted_success})
        if _cfg.DENIAL_DEDUP_OVERLAP:
            shifted_denial = sorted(set(shifted_denial) - set(shifted_success))
    return (target, shifted_success, shifted_denial,
            _denial_meta(shifted_denial, tables_prov, used_fallback),
            True, f'{rel}th from {base}th = {target}th (Bhavat Bhavam)')


def _route(d):
    subject_key = d['subject_key']
    event_key = d['event_key']
    base = int(d['subject_base'])
    if not 1 <= base <= 12:
        return {'status': 'unsupported',
                'reason': f"subject_base {base} out of range 1-12; refusing to rotate.",
                'subject_key': subject_key, 'event_key': event_key}
    rel = d.get('event_rel')
    # 'denial' starts unset; it is assigned below from the event's own label
    # (explicit denial arrays inherit the event's tables provenance) or from
    # the OURS 12th-from fallback. It is never silently 'BOOK'.
    provenance = {'tables': 'BOOK', 'denial': None, 'rotation': 'BOOK'}

    ev = EVENTS.get(event_key, {})
    # 2026-10-14: unknown event → clean unsupported (not misleading OURS-unlabeled).
    if event_key not in EVENTS:
        return {'status': 'unsupported',
                'reason': f"unknown event_key '{event_key}'",
                'subject_key': subject_key, 'event_key': event_key}
    # 2026-10-14: follow superseded_by chain (e.g. reinstatement → position_regain).
    while ev.get('superseded_by') and ev['superseded_by'] in EVENTS:
        event_key = ev['superseded_by']
        ev = EVENTS[event_key]
    # Provenance hygiene (2026-09-28): a missing 'provenance' key must NEVER
    # silently default to 'BOOK'. Unlabeled events are flagged 'OURS-unlabeled'
    # with a loud warning so the audit stays honest.
    tables_prov = ev.get('provenance')
    if not tables_prov:
        warnings.warn(
            f"layer2_router: event '{event_key}' has no provenance label in "
            f"events.json; treating tables as OURS-unlabeled (not BOOK).",
            UserWarning, stacklevel=2)
        tables_prov = 'OURS-unlabeled'
    provenance['tables'] = tables_prov
    # Election/contest handoff from Stage 1 (OURS, not BOOK): the Readers are
    # silent on third-party election routing in one chart, so any rotation
    # applied below is an owned OURS rule, never Krishnamurti doctrine.
    if d.get('election_handoff'):
        provenance['rotation'] = 'OURS-election-handoff'

    # EXCEPTION EVENTS: no house arrays — Layer 2b runs a registered
    # procedure against the cast chart instead. This branch carries no
    # event-specific logic; the procedure name and params come from the
    # events.json data.
    exc = ev.get('exception')
    if exc:
        # 2026-10-14: rotate key_house by subject_base (Bhavat Bhavam).
        # "Will my father repay his loan?" (base=9, cusp=12) → key_house=8.
        _raw_cusp = exc.get('params', {}).get('cusp') or rel or 11
        _key = derived_house(base, _raw_cusp) if base != 1 else _raw_cusp
        return {'status': 'exception',
                'procedure': exc['procedure'],
                'params': dict(exc.get('params', {})),
                'subject_key': subject_key, 'event_key': event_key,
                'subject_base': base,
                'key_house': _key,
                'provenance': {'tables': exc.get('provenance', 'OURS'),
                               'type': 'exception'}}

    # F21 (2026-10-01, batch-3 T30a ROUTER-ENFORCEMENT): events whose tables
    # were reviewed but NOT authorized for verdicts (verdict_active:false in
    # events.json) must not feed the judge scoring arrays. The router refuses
    # with 'unsupported' instead of returning de-facto-live success/denial
    # groups. Placed after the exception branch: exception procedures carry
    # their own authorization via the procedure's provenance. pipeline.py maps
    # router 'unsupported' to _unanswerable and layer3_v6._judge returns
    # {'status':'error'} for non-'ok' router output, so no verdict is ever
    # produced from an unauthorized table; the judge formula itself is
    # untouched.
    if ev.get('verdict_active') is False:
        return {'status': 'unsupported',
                'reason': (f"event '{event_key}': house tables reviewed but "
                           f"not authorized for verdicts (verdict_active:false; "
                           f"see batch table-review record); refusing to score."),
                'subject_key': subject_key, 'event_key': event_key,
                'verdict_inactive': True}

    # ---- PRIMARY block: nested 'primary' {"cusp","success","denial"} wins, but
    # ONLY when the dual is active (dual_active + secondary block). Proposals
    # (dual_active false) keep today's flat fields as the live behavior.
    _sec_present = isinstance(ev.get('secondary'), dict)
    _dual_on = bool(ev.get('dual_active')) and _sec_present
    prim = ev.get('primary') if (_dual_on and isinstance(ev.get('primary'), dict)) else None
    if prim:
        rel = prim.get('cusp', rel)
        success = list(prim.get('success') or [])
        denial = list(prim.get('denial') or [])
        tables_prov = prim.get('provenance') or tables_prov
        provenance['tables'] = tables_prov
    else:
        success = list(ev.get('success') or [])
        denial = list(ev.get('denial') or [])
    if denial:
        # Explicit denial arrays inherit the event's own tables provenance.
        provenance['denial'] = tables_prov

    if rel is None:
        # e.g. missing_person_return: books give timing methods, no houses.
        return {'status': 'unsupported',
                'reason': (f"event '{event_key}': the books give no house group "
                           f"for a yes/no judgment (see TABLES_NOTES.md)."),
                'subject_key': subject_key, 'event_key': event_key}
    if not success:
        return {'status': 'unsupported',
                'reason': (f"event '{event_key}': no book-given success group; "
                           f"v5 will not invent one."),
                'subject_key': subject_key, 'event_key': event_key}

    # RELATIONAL GUARD (Rule 1, USER-RULING, book-consistent): the question is
    # about the querent's own bond -> judge straight from lagna, never rotate.
    # Bystanders still rotate ('will my brother get a divorce' -> his 7th).
    # Book consistency: R6:13857 judges a lady's own reunion on HER 2,7,11.
    # The guard applies identically to the secondary cusp (ruling #9).
    # 2026-10-14 (Gemini 4 audit): scoped to BOND_EVENTS. The old
    # (base == 7 and rel == 7) leaked — "Will Rahul get married?" (stranger,
    # base=7) and "Will my wife's business profit?" (base=7, rel=7) were judged
    # from the querent's chart instead of rotating. Also, relational_7 must
    # not fire for non-bond events ("my son, come back to me" + missing_person).
    # 2026-10-14: use the canonical module-level BOND_EVENTS (single source,
    # shared with Layer 1).
    _BOND_EVENTS_L2 = BOND_EVENTS
    relational = (
        event_key in _BOND_EVENTS_L2
        and (bool(d.get('relational_7')) or bool(d.get('bond_no_rotate')))
    )

    # A2.2 (2026-10-02, Dutta case A2): self-posed third-party contest
    # questions (Stage-1 election_handoff) are judged WITHOUT rotation, on
    # the table's own houses (election_win: primary 6, [6,11]). Rotating the
    # named stranger to 9th produced [2,7]/primary 2 — a routing bug wearing
    # the costume of a judgment. Dutta's explicit skip-rule: "Do not rotate
    # the chart AND check only the houses and cusps that pertain to the main
    # theme of the query." Scoped to election_win/contest_win + handoff only.
    # 2026-10-14 (Gemini 4 audit): scoped to stranger candidates only.
    # "Will my father win the election?" (base=9) must rotate to the 9th.
    contest_no_rotate = (bool(d.get('election_handoff'))
                         and event_key in ('election_win', 'contest_win')
                         and subject_key in ('stranger_unknown', 'competitor_enemy_open', 'self'))

    # 2026-10-14 (Gemini 4 audit, KSK Reader VI): missing_person_return is
    # querent-centric — KSK's [2,8,11] is already written in the unrotated
    # Querent-vs-Missing-Person frame (8 = 2nd from the 7th). Rotating by
    # subject_base double-rotates house 8 (e.g. son base=5 → 8 becomes 12).
    mpr_no_rotate = (event_key == 'missing_person_return')

    p_cusp, p_suc, p_den, p_meta, rotated, rot_note = _block(
        base, rel, success, denial, tables_prov,
        relational or contest_no_rotate or mpr_no_rotate)
    if mpr_no_rotate:
        rot_note = ('missing_person_return querent-centric (KSK R6: '
                    '[2,8,11] already in Querent-vs-Missing-Person frame; '
                    'no subject rotation)')
    elif contest_no_rotate:
        rot_note = ('contest no-rotation (Dutta A2: self-posed third-party '
                    'contest judged on 6/11 directly, no stranger->9th rotation)')
        provenance['rotation'] = 'OURS-election-no-rotate (Dutta A2)'
    if not denial:
        provenance['denial'] = 'OURS-fallback'
    out = {'status': 'ok',
           'primary_cusp': p_cusp, 'key_house': p_cusp,
           'success': p_suc, 'denial': p_den,
           'denial_meta': p_meta,
           'soft_houses': sorted({shift_house(h, base)
                                for h in (ev.get('soft_houses') or [])})
           if rotated else sorted(ev.get('soft_houses') or []),
           'rotated': rotated, 'rotation_note': rot_note,
           'subject_key': subject_key, 'event_key': event_key,
           'provenance': provenance}

    # ---- SECONDARY block (dual-cusp, user ruling 2026-09-29 #9): rotates
    # identically to primary. Active only when dual_active is True; proposals
    # (dual_active false / OURS-PENDING) stay single-cusp and verdict-unchanged.
    sec = ev.get('secondary') if _sec_present else None
    if sec and _dual_on:
        s_rel = sec.get('cusp', sec.get('relative_house'))
        s_suc = list(sec.get('success') or [])
        s_den = list(sec.get('denial') or [])
        s_prov = sec.get('provenance') or 'OURS-unlabeled'
        if s_rel is None or not s_suc:
            out['secondary_error'] = (
                f"event '{event_key}': dual_active but secondary block has no "
                f"cusp/success; judging primary only.")
        else:
            # 2026-10-15 (review 1.5): the secondary block honors the same
            # no-rotation conditions as the primary (mpr_no_rotate for
            # missing_person_return's querent-centric [2,8,11]; the old code
            # rotated the secondary by subject_base).
            s_cusp, ss, sd, sm, s_rot, s_note = _block(
                base, s_rel, s_suc, s_den, s_prov,
                relational or contest_no_rotate or mpr_no_rotate)
            out['secondary'] = {
                'primary_cusp': s_cusp, 'key_house': s_cusp,
                'success': ss, 'denial': sd, 'denial_meta': sm,
                'rotated': s_rot, 'rotation_note': s_note,
                'cusp_label': f'secondary {s_rel}th',
                'provenance': {'tables': s_prov,
                               'denial': s_prov if s_den else 'OURS-fallback',
                               'rotation': provenance['rotation']}}
    return out
