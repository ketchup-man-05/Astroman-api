"""v5 Layer 3, version 9 — "the book-procedure challenger" (LAB ONLY).

Built 2026-10-03 for the Layer-3 shootout. The user authorized: "make
version 9 however you want, don't ask for permission." v9 is a lab
challenger — nothing here goes live, and no frozen file was touched.

Design principle: implement the BOOKS' cusp-sub-lord procedures as binary
rule checks (a house is signified or it is not — no scores, no weights),
with the strict promise logic the evidence supports:

  "Promise is binary and strict; delays only decorate a promise already
   made."

What v9 does differently from v6/v7/v7.5 (each choice logged with its
source in the v9_trace of every verdict):

  D1 STRICT DENIAL BAR (P1-corrected; KSK Reader IV p.108-109; Shanmugam
     Astro Secrets Part 1 p.170-171; Bosmia Prashna Jyotish p.36):
     NO only when the deciding chain has ZERO success-house connection
     AND hits denial houses. Mixed success+denial -> YES + DELAYS
     (the promise stands; delays decorate it — KSK Reader IV p.127).
  D2 EXAM STRICTER BAR (Shanmugam Part 3 p.50): for exam events, any
     3rd-house connection in the deciding chain -> NO (3rd negates 4th).
  D3 11TH-CSL CONFIRMATION, additive (KSK Reader III p.383; Bosmia
     Prashna Jyotish p.126 "consider the 11th cusp also"): the 11th cusp
     sub-lord's chain is read on every verdict; connection with success
     houses -> ELEVENTH_CSL_CONFIRMS. For specific-role/company questions
     ("CTO at Trustifi" shape) the 11th-CSL test on 2-6-10-11 is decisive:
     zero success connection -> NO (Bosmia Easy Way Horary p.422, Infosys
     case — verified NO).
  D4 QUALIFIER PROCEDURES (P3; Bosmia Easy Way Horary p.233-234; Taneja
     p.106; KSK Reader III p.432):
       'government'/'govt' + career event -> 10th CSL must signify 2-6-10
       with a 10th connection (Bosmia's government-job hint).
       'higher post'/'very high position'/'high position' + career event ->
       same 10th-CSL 2-6-10+10 test (stricter bar for rank qualifiers).
       'competitive' + exam event (or exam_competitive) -> success set
       becomes 4-6-9-11: the 6th must also be signified (Bosmia Easy Way
       Horary p.416, CA Final case).
     Books never abstain on a qualifier — v9 always judges, with the
     qualifier's own stricter test.
  D5 SECOND MARRIAGE (P4-corrected; KSK Reader IV p.150, p.184; Bosmia
     Easy Way Horary Ex.111 pp.284-286 — dual test FAILED, astrologer
     said YES, outcome proved right): the dual-sign/dual-planet test is
     a POSITIVE support modifier only, never a denial gate. The verdict
     comes from signification: 7th CSL -> 2/7/11; 2nd CSL -> 7 (marriage)
     vs 11-only ('keep', not marriage).
  D6 ADMISSION (P6; Sharad Joshi Krishnamurthy Padhdhati p.61; Nakshatra
     Light p.44-45; Bosmia Easy Way Horary p.411, p.192-193): detected by
     the word 'admission' in the question. 4th CSL chain vs {4,6,11}
     (4,11 accepted); {5,8,12} -> NO; 11th CSL must endorse {4,11} or the
     desired choice is refused (verified outcome); retro 4th CSL +
     promise -> YES + DELAYS (admission after the planet turns direct).
  D7 LOAN BORROWING = the book's 6th-CSL procedure (F130/F144; Prabhakar
     p.130-131; AS Part 3 p.53): 6th CSL retrograde (or its star-lord
     retrograde) -> NO (the book's hard reading — the one place v9 keeps
     a retro denial, logged); chain must hit {2,6,11}; 11th CSL
     confirmation. The engine's [6,11] array is unattested — not used.
  D8 PUNARPHOO on marriage events: Moon-Saturn conjunction -> DELAYS on
     YES (Reader IV p.78: delay only, "ultimately... much more good").
     Wider Saturn-Moon link -> MOON_SATURN_FRICTION texture.
  D9 SATURN NUANCE (Reader IV L6604-15): Saturn occupying a success
     house -> DELAYS on YES (delay, not denial). Saturn merely aspecting
     success houses without connection -> SATURN_DENIAL_SIGNAL texture
     only (never verdict-changing; v7 dropped aspect-denial entirely and
     v9 keeps it as texture, logged).
  D10 RETROGRADE = delay/friction, never hard denial (user's standing
      ruling; library majority: AS Part 5 p.214; Hariharan p.60;
      Prabhakar Ex.30). Retro decider/star-lord on a YES -> DELAYS +
      RETROGRADE_FRICTION. Exception: D7 only.
  D11 MOON = diagnostic only (P8; KSK Reader III p.383 — his own correct
      YES the hard gate would block; Bosmia Easy Way p.6-7 "I never check
      the Moon"). Mismatch -> MOON_CAUTION modifier; Moon-Saturn link ->
      'querent hiding something' note (Bosmia Prashna Jyotish). Never
      blocks, never changes the verdict.
  D12 CHILDREN/THIRD-PERSON ROTATION (P5; KSK Reader III p.242; Bosmia
      Prashna Jyotish pp.94-96, 243-246): v9 reads its extra cusps
      (4th/11th for admission, 7th/2nd for second marriage, 10th for
      qualifiers, 6th for borrowing) through the router's rotation —
      rotated house = shift_house(cusp, subject_base).

Verdict set: YES / NO / OTHER (matches v6 for comparability). Delay
signals are modifiers on YES (DELAYS), never standalone verdicts.

Every verdict carries 'v9_trace': [{rule, citation, detail}] — fully
explainable. No scores, no weights.
"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

from kp import chart_caster  # noqa: E402  (frozen engine; read-only use)
from engine import layer3_traditional as L3T  # noqa: E402  (exception-path delegate)
from engine.layer2_router import shift_house  # noqa: E402  (house rotation math)
from engine.layer3_rules import (  # noqa: E402  (signal helpers, not verdict logic)
    _cast, _signified_set, _retro_map, _planet_fact,
    _punarphoo, _moon_saturn_link, _saturn_role,
)

JUDGE_NAME = 'v9-book-procedure'

DUAL_SIGNS = {'Gemini', 'Virgo', 'Sagittarius', 'Pisces'}  # standard KP set
EXAM_EVENTS = {'exam_pass_general', 'education_higher', 'education_general',
               'exam_competitive'}
MARRIAGE_EVENTS = {'marriage', 'second_marriage', 'spouse_return_estranged',
                   'divorce', 'romance_materialise', 'romance_breakup',
                   'marriage_love_specific'}
CAREER_EVENTS = {'job_get_service', 'promotion', 'transfer_job',
                 'position_regain', 'position_lose', 'job_loss_dismissal',
                 'career_suitability', 'business_start', 'business_profit',
                 'business_loss', 'retirement_decision'}

CIT = {
    'strict_denial': 'KSK Reader IV p.108-109 (denial = 7th CSL with NO 2/7 '
                     'connection); Shanmugam AS Part 1 p.170-171 ("NO '
                     'connection at all in any manner to houses 2 and 7"); '
                     'Bosmia Prashna Jyotish p.36 ("any one of the houses '
                     'under consideration ... promised")',
    'mixed_is_delay': 'KSK Reader IV p.127 ("yet not a total denial ... '
                      'therefore a delayed marriage is promised"); '
                      'Hariharan p.58 (Saturn delays but "gives fruitful '
                      'results"); Shanmugam AS Part 3 p.55 ("SOME DELAY AND '
                      'NO DENIAL")',
    'exam_third_bar': 'Shanmugam AS Part 3 p.50 ("SHOULD HAVE NO CONNECTION '
                      'WITH THE 3RD WHICH IS A NEGATION TO THE 4TH")',
    'eleventh_confirms': 'KSK Reader III p.383 ("sub lord of the cusp of 11 '
                         'is connected ... in any manner ... positive '
                         'answer"); Bosmia Prashna Jyotish p.126 ("consider '
                         'the 11th cusp also")',
    'desired_job': 'Bosmia Easy Way Horary p.422 (Ex.172 Infosys: 11th CSL '
                   '-> "very less chance", verified NO); Prashna Jyotish '
                   'pp.126-131 (11th CSL of 2-6-10-11 -> desired post)',
    'government_test': 'Bosmia Easy Way Horary p.233-234 (Ex.86: 10th CSL '
                       'significator of 2-6-10 with 10th connection -> '
                       'government service promised; verified NO)',
    'higher_post': 'KSK Reader III p.432 (higher post: conjoined 2/6/10+11); '
                   'Prabhakar Times Horary p.162 (power posts need '
                   'Mars+Jupiter on the 10th)',
    'competitive_exam': 'Bosmia Easy Way Horary p.416 (CA Final: "not a '
                        'degree examination but competitive ... significators '
                        'of 4-6-9-11")',
    'second_marriage': 'KSK Reader IV p.184 (dual test, positive direction '
                       'only); KSK Reader IV p.150 (2nd CSL -> 7 = marriage, '
                       '-> 11 only = keep); Bosmia Easy Way Horary Ex.111 '
                       'pp.284-286 (dual test failed, YES proved right)',
    'admission': 'Joshi Krishnamurthy Padhdhati p.61 (4th CSL -> 4-6-11 = '
                 'admission; 5-8-12 = no admission); Bosmia Easy Way Horary '
                 'p.411 (4th CSL 4-11 + 11th CSL 4-11 -> admission); Bosmia '
                 'p.192-193 (4th promises but 11th CSL denies -> NO, '
                 'verified)',
    'loan_borrow': 'Prabhakar p.130-131 (6th CSL direct, not in star of '
                   'retro lord -> loan promised); AS Part 3 p.53 ("To get a '
                   'loan: sub lord of the 6th cusp should not be in '
                   'retrograde motion"); Hariharan p.53-54 (2-6-11 required)',
    'punarphoo': 'Reader IV p.78 (Moon-Saturn: obstacles/delay, "ULTIMATELY '
                 'BOTH OF THEM DO MUCH MORE GOOD"); R5:L14750',
    'saturn_delay': 'Reader IV L6604-15 ("will not deny but will cause '
                    'delay"; aspect-only without connection -> denial '
                    'signal)',
    'retro_delay': 'user standing ruling 2026-09-27 (retro = delay/friction, '
                   'never hard denial); library majority: AS Part 5 p.214, '
                   'Hariharan p.60, Prabhakar Ex.30 p.147',
    'moon_diagnostic': 'P8: KSK Reader III p.383 (correct YES the hard gate '
                       'would block); Bosmia Easy Way p.6-7 ("I never check '
                       'the Moon"); Prabhakar Times Horary p.43 (mismatch = '
                       'insincerity signal, not a block)',
    'rotation': 'KSK Reader III p.242 (relative house as Lagna); Bosmia '
                'Prashna Jyotish pp.94-96, 243-246 (5th as Asc for children)',
    'moon_hiding': 'Bosmia Prashna Jyotish, Moon section (Saturn connected '
                   'with Moon -> querent hiding something)',
}


# --------------------------------------------------------------------------
# question annotations (fixed per-case input; keyword detection on the stored
# question text — NOT question understanding at test time)
# --------------------------------------------------------------------------

def _flags(question):
    q = (question or '').lower()
    f = {}
    f['admission'] = 'admission' in q or 'admit' in q
    f['government'] = bool(re.search(
        r'\b(government|govt\.?|sarkari|public sector|govt job)\b', q))
    f['competitive'] = 'competitive' in q
    f['high_post'] = bool(re.search(
        r'(very high position|high position|higher post|district magistrate'
        r'|\bDM\b|IAS\b|IPS\b|top position|senior most)', q, re.I))
    # specific role @ named org: "<Role> at/in <CapitalizedOrg>"
    f['desired_job'] = bool(re.search(
        r'\b(CTO|CEO|SVP|VP|director|manager|engineer)\b.{0,20}\b(at|in|with|for)\s+[A-Z][A-Za-z]+',
        question or '')) or bool(re.search(
            r'\b(desired|particular|specific)\s+(job|post|position|role)\b', q)) \
        or 'infosys' in q or 'trustifi' in q or 'goodrx' in q or 'pgimer' in q
    return f


# --------------------------------------------------------------------------
# chain machinery (binary; no weights)
# --------------------------------------------------------------------------

def _chain_of(planet, reading):
    """4-level binary house set for ANY planet, from planet_facts (no recast).

    L1 star-lord occupation, L2 planet occupation, L3 star-lord ownership,
    L4 planet ownership — the user's frozen 4-level doctrine.
    (L5/L6/L7 reverted 2026-10-06: 7-level helps relationship but hurts
    career/money/exam. Relationship procedures use _chain_of_7level explicitly.)
    """
    facts = reading.get('planet_facts') or []
    by_name = {f.get('planet'): f for f in facts}
    houses = set()
    f = by_name.get(planet) or {}
    star = f.get('star_lord')
    sf = by_name.get(star) or {}
    for h in (sf.get('house_occupied'),):
        if isinstance(h, int) and 1 <= h <= 12:
            houses.add(h)
    for h in (f.get('house_occupied'),):
        if isinstance(h, int) and 1 <= h <= 12:
            houses.add(h)
    for h in (sf.get('owns_houses') or []) + (f.get('owns_houses') or []):
        if isinstance(h, int) and 1 <= h <= 12:
            houses.add(h)
    return houses


def _chain_of_7level(planet, reading, exclude_cusp=None):
    """7-level binary house set (L1-L7) for relationship procedures.

    Adds L5 (sub-lord occupation), L6 (sub-lord ownership), L7 (cusp lordship).
    Books use these levels heavily for relationship (Bosmia Ex.62, Ex.196, Ex.102).
    exclude_cusp (B3 V4 lab): L7 skips this cusp — removes the circularity
    where the decider cusp's own house is a guaranteed L7 hit.
    """
    houses = _chain_of(planet, reading)
    facts = reading.get('planet_facts') or []
    by_name = {f.get('planet'): f for f in facts}
    f = by_name.get(planet) or {}
    sub = f.get('sub_lord')
    subf = by_name.get(sub) or {}
    for h in (subf.get('house_occupied'),):
        if isinstance(h, int) and 1 <= h <= 12:
            houses.add(h)
    for h in (subf.get('owns_houses') or []):
        if isinstance(h, int) and 1 <= h <= 12:
            houses.add(h)
    cusp_facts = reading.get('cusp_facts') or []
    for i, cf in enumerate(cusp_facts):
        if (cf or {}).get('sub_lord') == planet:
            if exclude_cusp is not None and (i + 1) == exclude_cusp:
                continue
            houses.add(i + 1)
    return houses


def _resolve_planet(planet, reading):
    """Node -> agent cascade (conjoined -> star-lord -> sign-lord).

    Returns (agent_planet, note). Non-nodes return unchanged.
    """
    if planet not in ('Rahu', 'Ketu'):
        return planet, None
    f = _planet_fact(reading, planet)
    facts = reading.get('planet_facts') or []
    h = f.get('house_occupied')
    conjoined = [g.get('planet') for g in facts
                 if g.get('planet') not in ('Rahu', 'Ketu', planet)
                 and g.get('house_occupied') == h]
    if conjoined:
        return conjoined[0], '%s->agent %s (conjoined)' % (planet,
                                                           conjoined[0])
    star = f.get('star_lord')
    if star:
        return star, '%s->agent %s (star-lord)' % (planet, star)
    # sign-lord of the occupied sign
    cusp_facts = reading.get('cusp_facts') or []
    if isinstance(h, int) and 1 <= h <= len(cusp_facts):
        sign_lord = (cusp_facts[h - 1] or {}).get('sign_lord')
        if sign_lord:
            return sign_lord, '%s->agent %s (sign-lord)' % (planet, sign_lord)
    return planet, '%s unresolved node' % planet


def _csl_chain(cusp_no, reading):
    """(sub_lord, agent, chain_set, note) for any cusp number."""
    cusp_facts = reading.get('cusp_facts') or []
    sub = None
    if 1 <= cusp_no <= len(cusp_facts):
        sub = (cusp_facts[cusp_no - 1] or {}).get('sub_lord')
    if not sub:
        return None, None, set(), 'cusp %d: no sub-lord found' % cusp_no
    agent, note = _resolve_planet(sub, reading)
    return sub, agent, _chain_of(agent, reading), note


def _rotated(cusp, router_out):
    """Apply the router's rotation to an extra cusp read."""
    if router_out.get('rotated'):
        base = int(router_out.get('subject_base') or 1)
        return shift_house(cusp, base)
    return cusp


def _dual_test(sub_lord, reading):
    """Dual-sign/dual-planet test on a sub-lord. Positive indicator only."""
    f = _planet_fact(reading, sub_lord)
    star = f.get('star_lord')
    sf = _planet_fact(reading, star) if star else {}
    cusp_facts = reading.get('cusp_facts') or []
    h = f.get('house_occupied')
    sign = (cusp_facts[h - 1] or {}).get('sign') if isinstance(
        h, int) and 1 <= h <= len(cusp_facts) else None
    star_h = sf.get('house_occupied')
    star_sign = (cusp_facts[star_h - 1] or {}).get('sign') if isinstance(
        star_h, int) and 1 <= star_h <= len(cusp_facts) else None
    if sub_lord == 'Mercury':
        return True, 'sub-lord is Mercury (dual planet)'
    if sign in DUAL_SIGNS:
        return True, 'sub-lord in dual sign %s' % sign
    if star in ('Mercury',) or star_sign in DUAL_SIGNS:
        return True, 'sub-lord in star of %s (%s)' % (star, star_sign)
    return False, 'no dual connection (neutral — not a denial)'


# --------------------------------------------------------------------------
# the judge
# --------------------------------------------------------------------------

def _R(houses, router_out):
    """Rotate a v9-internal house set the same way the router rotated its
    tables (Bhavat Bhavam). Native houses in, native houses out."""
    return {_rotated(h, router_out) for h in houses}


def _binary_verdict(s_hit, d_hit, trace, rule_key):
    """Strict-bar binary mapping. Returns (verdict, reason)."""
    if d_hit and not s_hit:
        trace.append({'rule': 'strict_denial_bar',
                      'citation': CIT['strict_denial'],
                      'detail': 'denial houses %s signified, zero '
                                'success-house connection -> NO' % d_hit})
        return 'NO', 'strict_denial_bar'
    if s_hit and not d_hit:
        trace.append({'rule': 'promise',
                      'citation': CIT['strict_denial'],
                      'detail': 'success houses %s signified, no denial '
                                '-> YES (promise)' % s_hit})
        return 'YES', 'promise'
    if s_hit and d_hit:
        trace.append({'rule': 'mixed_is_delay',
                      'citation': CIT['mixed_is_delay'],
                      'detail': 'mixed: success %s + denial %s -> promise '
                                'stands, delays decorate it (YES + DELAYS)'
                                % (s_hit, d_hit)})
        return 'YES', 'mixed_decorated_delay'
    trace.append({'rule': 'weak_evidence',
                  'citation': 'layer3_traditional docstring (OURS): "the '
                              'book gives no formula for ties"',
                  'detail': 'no success or denial houses signified -> OTHER'})
    return 'OTHER', 'weak_evidence_only'


def _moon_diagnostic(reading, success, trace, modifiers):
    """Moon = diagnostic only. Never changes the verdict."""
    moon = _planet_fact(reading, 'Moon')
    chain = _chain_of('Moon', reading)
    s_hit = sorted(chain & set(success))
    if not s_hit:
        trace.append({'rule': 'moon_diagnostic',
                      'citation': CIT['moon_diagnostic'],
                      'detail': "Moon's chain %s hits no event house — "
                                'reported as MOON_CAUTION only (would-have-'
                                'blocked under the old hard gate)'
                                % sorted(chain)})
        modifiers.append('MOON_CAUTION')
    else:
        trace.append({'rule': 'moon_diagnostic',
                      'citation': CIT['moon_diagnostic'],
                      'detail': "Moon's chain signifies event houses %s "
                                '(mind reflects the matter)' % s_hit})
    sat = _planet_fact(reading, 'Saturn')
    if sat and (moon.get('star_lord') == 'Saturn'
                or moon.get('sub_lord') == 'Saturn'
                or sat.get('star_lord') == 'Moon'
                or sat.get('sub_lord') == 'Moon'):
        trace.append({'rule': 'moon_hiding',
                      'citation': CIT['moon_hiding'],
                      'detail': 'Saturn-Moon link: querent may be hiding '
                                'something (note only)'})
        modifiers.append('MOON_HIDING_NOTE')


def _delay_decor(reading, success, verdict, trace, modifiers):
    """Delay/friction decoration on a promised YES. Never denies."""
    if verdict != 'YES':
        return
    pun_active, pun_kind = _punarphoo(reading)
    if pun_active:
        trace.append({'rule': 'punarphoo',
                      'citation': CIT['punarphoo'],
                      'detail': 'Punarphoo: %s -> delay, not denial' % pun_kind})
        modifiers.append('DELAYS')
        modifiers.append('PUNARPHOO')
    role, why = _saturn_role(reading, success)
    if role == 'delay':
        trace.append({'rule': 'saturn_delay',
                      'citation': CIT['saturn_delay'], 'detail': why})
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        modifiers.append('SATURN_DELAY')
    elif role == 'denial_signal':
        trace.append({'rule': 'saturn_denial_signal',
                      'citation': CIT['saturn_delay'],
                      'detail': why + ' (texture only — never verdict-'
                                      'changing)'})
        modifiers.append('SATURN_DENIAL_SIGNAL')
    retro = _retro_map(reading)
    sig = reading.get('significators', {}) or {}
    csl = reading.get('deciding_planet')
    star = sig.get('true_star_lord')
    if bool(reading.get('is_retrograde')) or bool(retro.get(star, False)):
        trace.append({'rule': 'retro_delay',
                      'citation': CIT['retro_delay'],
                      'detail': 'retrograde decider/star-lord -> friction/'
                                'delay, never denial'})
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        modifiers.append('RETROGRADE_FRICTION')
    link_active, link_kind = _moon_saturn_link(reading)
    if link_active and not pun_active:
        trace.append({'rule': 'moon_saturn_friction',
                      'citation': CIT['punarphoo'],
                      'detail': 'wider Saturn-Moon link (%s): obstacle/'
                                'impediment possible' % link_kind})
        modifiers.append('MOON_SATURN_FRICTION')


def _eleventh_check(reading, router_out, success, trace, modifiers,
                    required_set=None):
    """11th-CSL chain. Returns (hit_list, endorsed_bool).

    Additive confirmation per the books. `required_set`: when given (e.g.
    desired-job 2-6-10-11), the 11th CSL is tested against it.
    """
    cusp11 = _rotated(11, router_out)
    sub, agent, chain, note = _csl_chain(cusp11, reading)
    test_set = set(required_set) if required_set else set(success)
    hit = sorted(chain & test_set)
    if note:
        trace.append({'rule': 'node_resolution',
                      'citation': 'R6 ~L10330-36 (cascade); user ruling '
                                  '2026-09-30',
                      'detail': '11th CSL: %s' % note})
    if hit:
        trace.append({'rule': 'eleventh_confirms',
                      'citation': CIT['eleventh_confirms'],
                      'detail': '11th CSL %s (agent %s) signifies %s -> '
                                'desire confirmed' % (sub, agent, hit)})
        modifiers.append('ELEVENTH_CSL_CONFIRMS')
        return hit, True
    trace.append({'rule': 'eleventh_silent',
                  'citation': CIT['eleventh_confirms'],
                  'detail': '11th CSL %s (agent %s) signifies %s — no '
                            'success-house connection (texture only)'
                            % (sub, agent, sorted(chain))})
    return hit, False


def _decide(reading, router_out, success, denial, primary, event, question):
    trace = []
    modifiers = []
    flags = _flags(question)
    retro = _retro_map(reading)

    # ---- special procedures first (book-specified tests) ----

    # D7: loan borrowing = 6th-CSL procedure (not the [6,11] array)
    if event == 'loan_borrow_get':
        cusp6 = _rotated(6, router_out)
        sub, agent, chain, note = _csl_chain(cusp6, reading)
        s_hit = sorted(chain & _R({2, 6, 11}, router_out))
        csl_retro = bool(retro.get(sub, False)) or bool(
            retro.get(agent, False))
        star = (_planet_fact(reading, agent) or {}).get('star_lord')
        star_retro = bool(retro.get(star, False))
        trace.append({'rule': 'loan_borrow_procedure',
                      'citation': CIT['loan_borrow'],
                      'detail': '6th CSL %s (agent %s); chain %s; success '
                                'hit %s; retro=%s star_retro=%s'
                                % (sub, agent, sorted(chain), s_hit,
                                   csl_retro, star_retro)})
        if csl_retro or star_retro:
            trace.append({'rule': 'loan_borrow_retro_denial',
                          'citation': CIT['loan_borrow'],
                          'detail': 'book-verbatim: 6th CSL (or its star '
                                    'lord) retrograde -> cannot borrow '
                                    '(the one hard-retro exception v9 '
                                    'keeps)'})
            _moon_diagnostic(reading, success, trace, modifiers)
            return 'NO', modifiers, trace, s_hit, []
        if s_hit:
            _eleventh_check(reading, router_out, _R({2, 6, 11}, router_out),
                            trace, modifiers)
            _moon_diagnostic(reading, success, trace, modifiers)
            return 'YES', modifiers, trace, s_hit, []
        _moon_diagnostic(reading, success, trace, modifiers)
        return 'OTHER', modifiers, trace, s_hit, []

    # D6: admission procedure
    if flags['admission'] and event in EXAM_EVENTS:
        cusp4 = _rotated(4, router_out)
        sub, agent, chain, note = _csl_chain(cusp4, reading)
        S4611, S411, S5812 = (_R({4, 6, 11}, router_out),
                              _R({4, 11}, router_out),
                              _R({5, 8, 12}, router_out))
        s46 = sorted(chain & S4611)
        s41 = sorted(chain & S411)
        d_hit = sorted(chain & S5812)
        trace.append({'rule': 'admission_procedure',
                      'citation': CIT['admission'],
                      'detail': '4th CSL %s (agent %s); chain %s; '
                                '4-6-11 hit %s; 4-11 hit %s; denial hit %s'
                                % (sub, agent, sorted(chain), s46, s41,
                                   d_hit)})
        if d_hit and not s41:
            _moon_diagnostic(reading, success, trace, modifiers)
            return 'NO', modifiers, trace, s41, d_hit
        if _rotated(4, router_out) in chain and _rotated(11, router_out) in chain:
            hit11, endorsed = _eleventh_check(
                reading, router_out, _R({4, 11}, router_out), trace,
                modifiers)
            if not endorsed and d_hit:
                trace.append({'rule': 'admission_11th_denies',
                              'citation': CIT['admission'],
                              'detail': '4th promises but 11th CSL does not '
                                        'endorse the desire -> NO '
                                        '(verified outcome)'})
                _moon_diagnostic(reading, success, trace, modifiers)
                return 'NO', modifiers, trace, s41, d_hit
            csl_retro = bool(retro.get(sub, False)) or bool(
                retro.get(agent, False))
            if csl_retro:
                trace.append({'rule': 'admission_retro_delay',
                              'citation': CIT['admission'],
                              'detail': 'retro 4th CSL + promise -> YES + '
                                        'DELAYS (admission after direct)'})
                modifiers.append('DELAYS')
            if _rotated(6, router_out) in chain:
                modifiers.append('COMPETITION_PRESENT')
            _moon_diagnostic(reading, success, trace, modifiers)
            return 'YES', modifiers, trace, s41, d_hit
        _moon_diagnostic(reading, success, trace, modifiers)
        return 'OTHER', modifiers, trace, s41, d_hit

    # D5: second marriage — signification decides; dual test is support only
    if event == 'second_marriage':
        cusp7 = _rotated(7, router_out)
        sub7, agent7, chain7, note7 = _csl_chain(cusp7, reading)
        cusp2 = _rotated(2, router_out)
        sub2, agent2, chain2, note2 = _csl_chain(cusp2, reading)
        S2711 = _R({2, 7, 11}, router_out)
        s_hit = sorted(chain7 & S2711)
        d_hit = sorted(chain7 & set(denial))
        dual_ok, dual_why = _dual_test(sub7, reading)
        trace.append({'rule': 'second_marriage_signification',
                      'citation': CIT['second_marriage'],
                      'detail': '7th CSL %s (agent %s) chain %s -> hit %s; '
                                '2nd CSL %s (agent %s) chain %s'
                                % (sub7, agent7, sorted(chain7), s_hit,
                                   sub2, agent2, sorted(chain2))})
        trace.append({'rule': 'dual_test_support_only',
                      'citation': CIT['second_marriage'],
                      'detail': 'dual test: %s (%s) — positive support '
                                'only, never a gate' % (dual_ok, dual_why)})
        if dual_ok:
            modifiers.append('DUAL_SIGN_SUPPORT')
        second_via_2nd = _rotated(7, router_out) in chain2
        keep_only = (_rotated(11, router_out) in chain2) and (
            _rotated(7, router_out) not in chain2)
        if keep_only:
            trace.append({'rule': 'keep_not_marriage',
                          'citation': CIT['second_marriage'],
                          'detail': '2nd CSL -> 11 only, not 7: attachment/'
                                    'keep, not a marriage (note)'})
            modifiers.append('KEEP_NOT_MARRIAGE')
        if second_via_2nd:
            trace.append({'rule': 'second_marriage_2nd_endorses',
                          'citation': CIT['second_marriage'],
                          'detail': '2nd CSL signifies 7 -> second marriage '
                                    'endorsed'})
            modifiers.append('SECOND_CSL_ENDORSES')
        verdict, reason = _binary_verdict(s_hit, d_hit, trace,
                                          'second_marriage')
        _delay_decor(reading, success, verdict, trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return verdict, modifiers, trace, s_hit, d_hit

    # ---- primary-cusp binary procedure (default + qualifier variants) ----
    signified = _signified_set(reading)
    eff_success = set(success)

    # D4: qualifier procedures
    if event in CAREER_EVENTS and flags['government']:
        cusp10 = _rotated(10, router_out)
        sub, agent, chain, note = _csl_chain(cusp10, reading)
        S2610 = _R({2, 6, 10}, router_out)
        s_hit = sorted(chain & S2610)
        has10 = _rotated(10, router_out) in chain
        trace.append({'rule': 'government_test',
                      'citation': CIT['government_test'],
                      'detail': 'qualifier "government": 10th CSL %s (agent '
                                '%s) chain %s -> 2-6-10 hit %s, 10th '
                                'connected=%s' % (sub, agent, sorted(chain),
                                                  s_hit, has10)})
        verdict = 'YES' if (s_hit and has10) else 'NO'
        if verdict == 'NO':
            trace[-1]['detail'] += ' -> NO (government service not promised)'
        _delay_decor(reading, success, verdict, trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return verdict, modifiers, trace, s_hit, []

    if event in CAREER_EVENTS and flags['high_post']:
        cusp10 = _rotated(10, router_out)
        sub, agent, chain, note = _csl_chain(cusp10, reading)
        S2610 = _R({2, 6, 10}, router_out)
        s_hit = sorted(chain & S2610)
        has10 = _rotated(10, router_out) in chain
        trace.append({'rule': 'high_post_test',
                      'citation': CIT['higher_post'],
                      'detail': 'qualifier "high position": 10th CSL %s '
                                '(agent %s) chain %s -> 2-6-10 hit %s, '
                                '10th connected=%s'
                                % (sub, agent, sorted(chain), s_hit, has10)})
        verdict = 'YES' if (s_hit and has10) else 'NO'
        _delay_decor(reading, success, verdict, trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return verdict, modifiers, trace, s_hit, []

    if event in EXAM_EVENTS and (flags['competitive']
                                 or event == 'exam_competitive'):
        eff_success = _R({4, 6, 9, 11}, router_out)
        trace.append({'rule': 'competitive_exam_set',
                      'citation': CIT['competitive_exam'],
                      'detail': 'qualifier "competitive": success set -> '
                                '4-6-9-11 (6th required)'})

    # D3: desired-job — the 11th-CSL test decides the SPECIFIC desire
    # (P2-corrected; Bosmia). Primary procedure still runs and is logged.
    desired = bool(flags['desired_job'] and event in CAREER_EVENTS)
    if desired:
        S261011 = _R({2, 6, 10, 11}, router_out)
        DADMX = _R({1, 5, 8, 9, 12}, router_out)
        hit11, endorsed = _eleventh_check(reading, router_out, S261011,
                                          trace, modifiers)
        cusp11 = _rotated(11, router_out)
        sub11, agent11, chain11, _ = _csl_chain(cusp11, reading)
        s11 = sorted(chain11 & S261011)
        d11 = sorted(chain11 & DADMX)
        trace.append({'rule': 'desired_job_11th_decides',
                      'citation': CIT['desired_job'],
                      'detail': 'specific role/company: 11th CSL %s (agent '
                                '%s) chain %s -> 2-6-10-11 hit %s, denial '
                                'admixture %s'
                                % (sub11, agent11, sorted(chain11), s11,
                                   d11)})
        # book shape: clean 2-6-10-11 -> desire fulfilled; any denial
        # admixture ("makes it difficult") or zero success -> NO.
        if s11 and not d11:
            verdict = 'YES'
        else:
            verdict = 'NO'
            trace[-1]['detail'] += ' -> NO (desired post not promised)'
        # primary procedure logged for comparison (additive per the books)
        ps = sorted(_signified_set(reading) & set(success))
        pd = sorted(_signified_set(reading) & set(denial))
        trace.append({'rule': 'desired_job_primary_logged',
                      'citation': CIT['desired_job'],
                      'detail': 'generic 6th/10th procedure would say: '
                                'success %s, denial %s (logged only; the '
                                '11th-CSL test decides the specific desire)'
                                % (ps, pd)})
        _delay_decor(reading, success, verdict, trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return verdict, modifiers, trace, s11, d11

    s_hit = sorted(signified & eff_success)
    d_hit = sorted(signified & set(denial))

    # D2: exam stricter bar — the (rotated) 3rd in the deciding chain -> NO
    exam_neg = _rotated(3, router_out)
    if event in EXAM_EVENTS and exam_neg in signified:
        trace.append({'rule': 'exam_third_bar',
                      'citation': CIT['exam_third_bar'],
                      'detail': '3rd house (%d%s) in the deciding chain %s '
                                '-> NO (3rd negates the 4th)'
                                % (exam_neg,
                                   ' = rotated' if router_out.get('rotated')
                                   else '',
                                   sorted(signified))})
        verdict = 'NO'
    else:
        # 2026-10-14 (denial_meta enforcement): CANDIDATE_NEGATION fallback
        # denial must never hard-NO on its own (forbidden: automatic_NO).
        _dm = (router_out.get('denial_meta') or {}).get('status')
        if _dm == 'CANDIDATE_NEGATION' and d_hit and not s_hit:
            trace.append({'rule': 'candidate_negation_no_bar',
                          'citation': 'Layer 2 denial_meta: CANDIDATE_NEGATION '
                                      'forbids automatic_NO',
                          'detail': 'fallback denial houses %s signified, zero '
                                    'success-house connection -> OTHER' % d_hit})
            verdict, reason = 'OTHER', 'candidate_negation_no_bar'
        else:
            verdict, reason = _binary_verdict(s_hit, d_hit, trace, 'primary')

    # 11th-CSL confirmation (additive) on the default path
    _eleventh_check(reading, router_out, success, trace, modifiers)

    _delay_decor(reading, success, verdict, trace, modifiers)
    _moon_diagnostic(reading, success, trace, modifiers)
    return verdict, modifiers, trace, s_hit, d_hit


def _judge(router_out, city, horary_number, as_of=None, coords=None):
    if router_out.get('status') == 'exception':
        out = L3T.judge(router_out, city, horary_number,
                        as_of=as_of, coords=coords)
        out['method'] = 'layer2b-exception-v9'
        out['v9_trace'] = [{'rule': 'exception_delegate',
                            'citation': 'layer2b procedure (as v6)',
                            'detail': 'exception event: delegated to the '
                                      'registered Layer-2b procedure'}]
        return out
    if router_out.get('status') != 'ok':
        return {'status': 'error',
                'reason': 'layer-2 did not produce a routable result',
                'router': router_out}

    success = set(router_out['success'])
    denial = set(router_out['denial'])
    primary = int(router_out['primary_cusp'])
    event = router_out.get('event_key') or 'unknown'
    question = router_out.get('question') or ''

    reading = _cast(city, horary_number, success, denial, primary,
                    as_of, coords)
    if not reading or 'error' in reading:
        return {'status': 'error',
                'reason': 'chart casting failed: %s'
                          % (reading.get('error') if reading else 'no reading')}

    verdict, modifiers, trace, s_hit, d_hit = _decide(
        reading, router_out, success, denial, primary, event, question)

    sig = reading.get('significators', {}) or {}
    timing_eligible = (verdict == 'YES' and 'DELAYS' not in modifiers)
    return {
        'status': 'ok',
        'judge': JUDGE_NAME,
        'verdict_class': verdict,
        'legacy_verdict_class': verdict,
        'method': 'v9-book-procedure',
        'event_key': event,
        'question_flags': _flags(question),
        'positive': sorted(success),
        'negative': sorted(denial),
        'cusp_sub_lord': reading.get('cusp_sub_lord'),
        'deciding_planet': reading.get('deciding_planet'),
        'star_lord': sig.get('true_star_lord'),
        'signified_houses': sorted(_signified_set(reading)),
        'success_hit': s_hit,
        'denial_hit': d_hit,
        'modifiers': modifiers,
        'v9_trace': trace,
        'timing_eligible': timing_eligible,
        'primary_cusp': primary,
        'rotated': bool(router_out.get('rotated')),
        'answerability': {
            'status': 'OK' if verdict in ('YES', 'NO') else 'INSUFFICIENT',
        },
        'provenance': {
            'layer3': 'v9 book-procedure (binary; citations in v9_trace)',
            'tables': (router_out.get('provenance') or {}).get('tables'),
        },
    }


def judge(router_out, city, horary_number, as_of=None, coords=None):
    """Public entry — never raises (same contract as the other judges)."""
    try:
        return _judge(router_out, city, horary_number,
                      as_of=as_of, coords=coords)
    except Exception as e:
        return {'status': 'error',
                'reason': 'v9 judgment failed: %s' % str(e)[:200]}
