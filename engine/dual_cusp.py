"""v5 dual-cusp judgment (user ruling 2026-09-29).

Single-cusp is the default. Events with an ACTIVE secondary block
(events.json: secondary {...} + dual_active true) are judged TWICE with the
existing single-cusp judge - once per cusp (ruling #1: no parallel
evaluator) - and the two verdicts are synthesized:

    YES  + YES  -> YES
    NO   + NO   -> NO
    anything else -> OTHER with resolution PARTIAL_OR_MIXED (ruling #8)

Report-only signals (11th CSL, Moon genuineness) and Layer-4 flags keep
coming from the PRIMARY run; only the verdict class is replaced by the
synthesis. Everything is logged in out['dual'].
"""

YES, NO, OTHER = 'YES', 'NO', 'OTHER'
PARTIAL_OR_MIXED = 'PARTIAL_OR_MIXED'


def synthesize_dual(v_primary, v_secondary, p_cusp, s_cusp):
    """(verdict, resolution_or_None, explanation). Pure function, no I/O."""
    vp, vs = (v_primary or OTHER), (v_secondary or OTHER)
    agree = f'Primary cusp ({p_cusp}th): {vp}; secondary cusp ({s_cusp}th): {vs}.'
    if vp == YES and vs == YES:
        return YES, None, agree + ' Both agree -> YES.'
    if vp == NO and vs == NO:
        return NO, None, agree + ' Both agree -> NO.'
    return (OTHER, PARTIAL_OR_MIXED,
            agree + ' Split verdict -> OTHER (partial/mixed): the two cusps '
                    'do not agree, so no clean YES/NO is given.')


def _secondary_route(route):
    """Route dict with the secondary block swapped into the primary slots."""
    sec = route['secondary']
    r2 = dict(route)
    r2['primary_cusp'] = sec['primary_cusp']
    r2['key_house'] = sec['key_house']
    r2['success'] = sec['success']
    r2['denial'] = sec['denial']
    r2['denial_meta'] = sec['denial_meta']
    r2['rotation_note'] = sec['rotation_note']
    # 2026-10-15 (review 1.5): the secondary block's own rotated flag must
    # travel with its houses — otherwise r2 claims unrotated while carrying
    # rotated success/denial.
    r2['rotated'] = sec['rotated']
    r2.pop('secondary', None)
    return r2


def judge_dual(judge_fn, route, city, horary_number, as_of=None, coords=None):
    """Runs judge_fn twice (primary, then secondary) and synthesizes.

    Returns {'status':'ok','out3':<primary run with synthesized verdict>,
             'notes':[...]}
    or {'status':'error','reason':...} when either run fails - a half
    synthesis would be dishonest, so the pipeline must go UNANSWERABLE.
    """
    notes = []
    sec = route.get('secondary')
    if not sec:
        return {'status': 'error',
                'reason': 'judge_dual called without an active secondary block'}

    out_p = judge_fn(route, city, int(horary_number), as_of=as_of,
                     coords=coords)
    if not isinstance(out_p, dict) or out_p.get('status') != 'ok':
        return {'status': 'error',
                'reason': 'dual-cusp: primary-cusp judgment failed: %s'
                          % ((out_p or {}).get('reason') if isinstance(out_p, dict) else out_p)}
    out_s = judge_fn(_secondary_route(route), city, int(horary_number),
                     as_of=as_of, coords=coords)
    if not isinstance(out_s, dict) or out_s.get('status') != 'ok':
        return {'status': 'error',
                'reason': 'dual-cusp: secondary-cusp judgment failed: %s'
                          % ((out_s or {}).get('reason') if isinstance(out_s, dict) else out_s)}

    vp = out_p.get('verdict_class')
    vs = out_s.get('verdict_class')
    verdict, resolution, text = synthesize_dual(
        vp, vs, route.get('primary_cusp'), sec.get('primary_cusp'))
    notes.append('Dual-cusp judgment [USER-RULING]: ' + text)

    out = dict(out_p)
    out['verdict_class'] = verdict
    out['dual'] = {
        'active': True,
        'primary_cusp': route.get('primary_cusp'),
        'secondary_cusp': sec.get('primary_cusp'),
        'primary_verdict': vp,
        'secondary_verdict': vs,
        'primary_success': list(route.get('success') or []),
        'secondary_success': list(sec.get('success') or []),
        'synthesized_verdict': verdict,
        'resolution': resolution,
        'secondary_report': {k: out_s.get(k) for k in
                             ('positive', 'negative', 'signified_houses')
                             if out_s.get(k) is not None},
    }
    return {'status': 'ok', 'out3': out, 'notes': notes}
