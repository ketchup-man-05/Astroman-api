"""layer3_rules — rule-based judge. NO scores, NO weights.

Implements the book's cusp-sub-lord promise procedure as a sequence of
binary rule checks (signifies / does not signify), replacing the weighted
"numbering system".

Book procedure (Reader VI worked procedures — promotion R6:L16360-70,
borrowing R6:L12815-35, overseas R6:L14932-44, lottery R6:L11833-45,
imprisonment R6:L17811-20):
  the relevant cusp's sub-lord must be direct, its star lord must be direct,
  and the sub-lord must signify the event houses -> promise (YES).

Verdicts: YES / NO / MIXED only (user 2026-10-01: the old OTHER label is renamed MIXED — mixed signals or insufficient evidence to call).
  DELAYED and SUPPORT are modifiers, never standalone verdicts
  (user ruling 2026-09-30).
There is no PARTIAL verdict in the Readers (searched, zero hits) — mixed
signals resolve to MIXED.

Lab-only. Frozen v1 and the live app are untouched.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

from kp import chart_caster  # noqa: E402  (frozen engine; read-only use)
from engine import layer3_traditional as L3T  # noqa: E402  (exception path delegate)

JUDGE_NAME = 'rules-no-score'

# Doctrine switch (user owns this ruling).
# False (default) = user's 2026-09-27 standing rule: retrograde CSL/star-lord
#   in the promise test means delay/friction, never hard denial — EXCEPT the
#   book-verbatim loan procedure (handled by the Layer-2b exception route).
# True = the book's hard reading (borrowing R6:L12815-35; 11th CSL R3:L25516-18).
# Measured 2026-10-01: True makes retrograde alone produce ~54% NO — the
# corpus-tested hard retro veto fails at ~40% (Variant UB), so False is default.
RETRO_PROMISE_BOOK_STRICT = False
# Exact book citations for each rule (Reader line refs from the gap audit).
CIT = {
    'promise_form': 'R6:L16360-70 (promotion); R6:L12815-35 (borrowing); '
                    'R6:L14932-44 (overseas); R6:L11833-45 (lottery)',
    'retro_promise_denial': 'R6:L12815-35 ("lord of the sub of the 6th cusp '
                    'is either retrograde or deposited in a constellation '
                    'whose lord is retrograde ... one cannot either borrow '
                    'or recover")',
    'eleventh_retro_denial': 'R3:L25516-18 ("If the sub-lord of the 11th cusp '
                    'is retrograde then only whatever he desires to have '
                    'will not be had")',
    'marriage_denial': 'R4:L9300-03 (reject planets in the sub of 1/6/10 '
                    'significators)',
    'childbirth_denial': 'R3:L25786-89 (1/4/10 detrimental, 12th to 2/5/11)',
    'eleventh_confirms': 'R3:L22533-35 (11th CSL connected with event houses '
                    '-> "positive answer")',
    'punarphoo': 'R4:L4569+ ("Whenever Saturn has got any connection '
                    'whatsoever with Moon ... causes delay, though '
                    'ultimately both of them do much more good"); '
                    'R5:L14750 ("Moon in conjunction with Saturn is called '
                    'Punarphoo ... Either it may be delayed or denied. Only '
                    'on the subsequent attempts the native will be crowned '
                    'with success")',
    'saturn_delay': 'R4:L6604-15 ("Whenever Sani happens to be a '
                    'significator of a particular matter, it will not deny '
                    'but will cause delay ... But if Sani has no connection '
                    'with houses 2 and 11 but only throws its aspect, this '
                    'portends denial")',
    'retro_deferred': 'R3:L13541-47; R3:L13616-20; R6:~L10340-44 '
                    '(retrograde results deferred till direct)',
}


def _cast(city, horary_number, success, denial, primary, as_of, coords):
    return chart_caster.execute_kp_reading(
        city, int(horary_number), sorted(success), sorted(denial),
        key_house=primary, as_of=as_of, coords=coords,
        chart_time_mode='query', log=False, include_timing=False)


def _signified_set(reading):
    """Binary signification: the decider's 4-level house chain as a SET.

    No weights — a house is signified or it is not (the book's logic).
    """
    sig = reading.get('significators', {}) or {}
    houses = set()
    for h in (sig.get('step_1_house'), sig.get('step_2_house')):
        if isinstance(h, int) and 1 <= h <= 12:
            houses.add(h)
    for h in (sig.get('step_3_houses') or []) + (sig.get('step_4_houses') or []):
        if isinstance(h, int) and 1 <= h <= 12:
            houses.add(h)
    return houses


def _retro_map(reading):
    try:
        return {f.get('planet'): bool(f.get('is_retrograde'))
                for f in (reading.get('planet_facts') or [])}
    except Exception:
        return {}


def _planet_fact(reading, name):
    for f in (reading.get('planet_facts') or []):
        if f.get('planet') == name:
            return f
    return {}


def _punarphoo(reading):
    """Punarphoo = Moon-Saturn CONJUNCTION (R5:L14750: "Moon in conjunction
    with Saturn is called Punarphoo").

    The engine measures this as Moon-Saturn within 3deg20. R4's wider "any
    connection whatsoever" (R4:L4569+) describes obstacles generally; wider
    connections are reported by _moon_saturn_link() as friction, not Punarphoo.
    Returns (active, kind).
    """
    if reading.get('punarphoo'):
        return True, 'conjunction (Moon-Saturn within 3deg20, engine-measured)'
    return False, ''


def _moon_saturn_link(reading):
    """Wider Saturn-Moon connection (R4:L4569+: "any connection whatsoever
    with Moon ... some obstacle or impediment"). Informational only."""
    moon = _planet_fact(reading, 'Moon')
    sat = _planet_fact(reading, 'Saturn')
    if not moon or not sat:
        return False, ''
    mh, sh = moon.get('house_occupied'), sat.get('house_occupied')
    if isinstance(sh, int) and isinstance(mh, int):
        aspected = {((sh + 1) % 12) + 1, ((sh + 5) % 12) + 1,
                    ((sh + 8) % 12) + 1}
        if mh in aspected:
            return True, 'Saturn aspects the house Moon occupies'
    if moon.get('star_lord') == 'Saturn' or moon.get('sub_lord') == 'Saturn':
        return True, 'Moon in Saturn star/sub'
    if sat.get('star_lord') == 'Moon' or sat.get('sub_lord') == 'Moon':
        return True, 'Saturn in Moon star/sub'
    return False, ''


def _saturn_role(reading, success):
    """R4:L6604-15 — Saturn connected to event houses: delay, not denial;
    merely aspecting them without connection: denial signal.

    Tightened: "significator" here = Saturn OCCUPIES a success house (the
    book's own example is Saturn IN the 11th). Ownership-only links are
    trace notes — otherwise ~1 in 2 readings would read DELAYED and the
    modifier would mean nothing."""
    sat = _planet_fact(reading, 'Saturn')
    if not sat:
        return 'none', ''
    sh = sat.get('house_occupied')
    owns = set(sat.get('owns_houses') or [])
    if isinstance(sh, int) and sh in set(success):
        return ('delay',
                'Saturn occupies event house %d -> delay, not denial' % sh)
    star = sat.get('star_lord')
    star_fact = _planet_fact(reading, star) if star else {}
    star_houses = set()
    if isinstance(star_fact.get('house_occupied'), int):
        star_houses.add(star_fact['house_occupied'])
    star_houses |= set(star_fact.get('owns_houses') or [])
    weak_link = bool((owns & set(success)) or (star_houses & set(success)))
    if isinstance(sh, int):
        aspected = {((sh + 1) % 12) + 1, ((sh + 5) % 12) + 1,
                    ((sh + 8) % 12) + 1}
        if aspected & set(success) and not weak_link:
            return ('denial_signal',
                    'Saturn only aspects event houses without connection -> '
                    'denial signal')
    if weak_link:
        return ('note', 'Saturn linked to event houses via ownership/star '
                        'only (note only)')
    return 'none', ''


def _decide(reading, success, denial):
    """Core rule sequence. Returns (verdict, modifiers, rules_trace)."""
    trace = []
    modifiers = []
    signified = _signified_set(reading)
    s_hit = sorted(signified & set(success))
    d_hit = sorted(signified & set(denial))
    retro = _retro_map(reading)
    sig = reading.get('significators', {}) or {}
    csl = reading.get('deciding_planet')
    star = sig.get('true_star_lord')
    csl_retro = bool(reading.get('is_retrograde'))
    star_retro = bool(retro.get(star, False))

    def fired(rule, detail):
        trace.append({'rule': rule, 'citation': CIT[rule], 'detail': detail})

    # -- Rule 1: book's promise-test retrograde check (R6 borrowing procedure).
    # Book states denial; the user's standing rule says delay/friction.
    # Default follows the user (measured: hard version over-denies at ~54%).
    retro_friction = []
    if csl_retro or star_retro:
        who = []
        if csl_retro:
            who.append('%s (CSL) retrograde' % csl)
        if star_retro:
            who.append('%s (CSL star lord) retrograde' % star)
        retro_friction.append('; '.join(who))
        if RETRO_PROMISE_BOOK_STRICT:
            fired('retro_promise_denial', '; '.join(who))
            modifiers.append('RETROGRADE_DENIAL')
            return ('NO', modifiers, trace, s_hit, d_hit, signified)
        trace.append({'rule': 'retro_promise_denial',
                      'citation': CIT['retro_promise_denial'],
                      'detail': 'book states denial for: %s — user ruling '
                                '2026-09-27 applies delay/friction instead' %
                                '; '.join(who)})

    # -- Rule 2: 11th CSL retrograde = desire not fulfilled (R3:L25516-18).
    # Same doctrine switch: book says denial, user says delay/friction.
    decision = ((reading.get('ai_facts') or {}).get('decision') or {})
    e11 = decision.get('eleventh_csl_check') or {}
    e11_retro = bool(e11.get('applicable') and e11.get('is_retrograde'))
    if e11_retro:
        if RETRO_PROMISE_BOOK_STRICT:
            fired('eleventh_retro_denial',
                  '11th CSL %s retrograde' % e11.get('cusp_sub_lord'))
            modifiers.append('ELEVENTH_CSL_RETROGRADE_DENIAL')
            return ('NO', modifiers, trace, s_hit, d_hit, signified)
        trace.append({'rule': 'eleventh_retro_denial',
                      'citation': CIT['eleventh_retro_denial'],
                      'detail': 'book states denial: 11th CSL %s retrograde — '
                                'user ruling 2026-09-27 applies '
                                'delay/friction instead' %
                                e11.get('cusp_sub_lord')})

    # -- Rule 3: denial houses signified, success houses not -> NO
    if d_hit and not s_hit:
        fired('marriage_denial', 'denial houses signified: %s; success: none'
              % d_hit)
        return ('NO', modifiers, trace, s_hit, d_hit, signified)

    # -- Rule 4: success houses signified, denial houses not -> YES
    if s_hit and not d_hit:
        fired('promise_form', 'CSL %s (direct, star lord %s direct) signifies '
              'success houses %s' % (csl, star, s_hit))
        verdict = 'YES'
    else:
        # -- Rule 5: mixed or no evidence -> MIXED (no book tie formula)
        if s_hit and d_hit:
            detail = ('mixed signals: success %s, denial %s — the book gives '
                      'no tie formula' % (s_hit, d_hit))
        else:
            detail = 'no success or denial houses signified'
        trace.append({'rule': 'no_tie_formula',
                      'citation': 'layer3_traditional docstring (OURS): '
                                  '"the book gives no formula for ties"',
                      'detail': detail})
        return ('MIXED', modifiers, trace, s_hit, d_hit, signified)

    # -- Rule 6: 11th CSL confirmation (user's standing design; book R3:L22533-35)
    if e11.get('applicable') and e11.get('classification') in (
            'positive', 'strong'):
        fired('eleventh_confirms',
              '11th CSL %s connected with event houses' %
              e11.get('cusp_sub_lord'))
        modifiers.append('ELEVENTH_CSL_CONFIRMS')

    # -- Rule 7: Punarphoo -> delay on a promised YES (R4/R5)
    pun_active, pun_kind = _punarphoo(reading)
    if pun_active and verdict == 'YES':
        fired('punarphoo', 'Saturn-Moon conjunction: %s' % pun_kind)
        modifiers.append('DELAYED')
        modifiers.append('PUNARPHOO')
    elif pun_active:
        trace.append({'rule': 'punarphoo',
                      'citation': CIT['punarphoo'],
                      'detail': 'Punarphoo present; verdict is %s so no delay '
                                'applies' % verdict})
    link_active, link_kind = _moon_saturn_link(reading)
    if link_active and not pun_active:
        trace.append({'rule': 'punarphoo',
                      'citation': CIT['punarphoo'],
                      'detail': 'wider Saturn-Moon link (%s): some '
                                'obstacle/impediment possible (R4); not '
                                'Punarphoo proper' % link_kind})
        modifiers.append('MOON_SATURN_FRICTION')

    # -- Rule 8: Saturn significator nuance (R4:L6604-15)
    role, why = _saturn_role(reading, success)
    if role == 'delay' and verdict == 'YES':
        trace.append({'rule': 'saturn_delay', 'citation': CIT['saturn_delay'],
                      'detail': why})
        if 'DELAYED' not in modifiers:
            modifiers.append('DELAYED')
        modifiers.append('SATURN_DELAY')
    elif role == 'denial_signal':
        trace.append({'rule': 'saturn_delay', 'citation': CIT['saturn_delay'],
                      'detail': why})
        modifiers.append('SATURN_DENIAL_SIGNAL')
    elif role == 'note':
        trace.append({'rule': 'saturn_delay', 'citation': CIT['saturn_delay'],
                      'detail': why + ' (note only)'})

    if csl_retro or star_retro or e11_retro:
        modifiers.append('RETROGRADE')
    # -- Rule 9: retrograde friction on a promised YES (user's rule).
    # Friction is NOT delay: DELAYED is reserved for Punarphoo and
    # Saturn-occupation (Rules 7-8). A retrograde CSL/star-lord means the
    # path has friction — the event still comes, not necessarily late.
    if (retro_friction or e11_retro) and verdict == 'YES':
        modifiers.append('RETROGRADE_FRICTION')
    elif retro_friction or e11_retro:
        modifiers.append('RETROGRADE_FRICTION')
    return (verdict, modifiers, trace, s_hit, d_hit, signified)


def _judge(router_out, city, horary_number, as_of=None, coords=None):
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
                'reason': 'chart casting failed: %s'
                          % (reading.get('error') if reading else 'no reading')}

    verdict, modifiers, trace, s_hit, d_hit, signified = _decide(
        reading, success, denial)

    sig = reading.get('significators', {}) or {}
    timing_eligible = (verdict == 'YES' and 'DELAYED' not in modifiers)
    if verdict in ('YES', 'NO'):
        answerability = {'status': 'OK'}
    else:
        answerability = {'status': 'INSUFFICIENT',
                         'why': 'no decisive promise or denial from the '
                                'cusp-sub-lord rules'}

    reason_bits = []
    for t in trace:
        reason_bits.append('%s [%s]' % (t['detail'], t['rule']))
    reason = ' | '.join(reason_bits) if reason_bits else 'no rules fired'

    return {
        'status': 'ok',
        'judge': JUDGE_NAME,
        'verdict_class': verdict,
        'legacy_verdict_class': verdict,
        'positive': sorted(success),
        'negative': sorted(denial),
        'cusp_sub_lord': reading.get('cusp_sub_lord'),
        'deciding_planet': reading.get('deciding_planet'),
        'star_lord': sig.get('true_star_lord'),
        'signified_houses': sorted(signified),
        'success_hit': s_hit,
        'denial_hit': d_hit,
        'modifiers': modifiers,
        'rules_trace': trace,
        'reason': reason,
        'timing_eligible': timing_eligible,
        'answerability': answerability,
        'retrograde_delay': 'DELAYED' in modifiers,
        'exception': False,
        'mechanics': ('BOOK RULES, no scores: cusp-sub-lord promise test + '
                      'denial arrays + Punarphoo + Saturn nuance. Citations '
                      'in rules_trace.'),
    }


def judge(router_out, city, horary_number, as_of=None, coords=None):
    """Public entry — never raises (same contract as the other judges)."""
    try:
        return _judge(router_out, city, horary_number, as_of=as_of,
                      coords=coords)
    except Exception as e:
        return {'status': 'error',
                'reason': 'rules judgment failed: %s' % str(e)[:200]}
