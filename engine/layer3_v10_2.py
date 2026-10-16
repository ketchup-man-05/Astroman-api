"""v5 Layer 3, version 9.7 — "money-batch-2" (LAB ONLY).

Built 2026-10-05. v9.7 = v9.6 + the user's money batch-2 rulings
(2026-10-05), nothing else:

  B1  Lottery dedicated procedure (new `lottery` event): 11th CSL ->
      2-6-11 + 3rd connection, clean of 5/8/12, CSL + star-lord direct
      -> YES; retro/star-retro -> NO; 5/8/12 signified -> NO; else NO
      (strict school). Bosmia Prashna Jyotish Ex 31 true pp.158-159 and
      KSK Reader VI true pp.213-214, both outcome-verified. The user
      picked the Bosmia/KSK-VI school from the 5-way split (S-a).
      Replaces the contradicted [2,5,11] array for lottery questions;
      stock_speculation keeps its (unsourced) array for share-market
      questions.
  B2  Planet modes (KSK Reader VI true pp.230/238; AS Part 5; Reader VI
      via AS Part 2 true pp.199-200):
      - money_lent_recovery: mode table on the 11th CSL planet
        (Saturn=delay, Mercury=instalments, Jupiter=court/lawful,
        Mars=threats, Moon=quick, Venus=compromise, Sun=government);
        Saturn aspecting the sub-lord -> PARTIAL ("only a part of it
        or part by part").
      - loan_borrow_get: v9.7-native procedure (was v9 D7): nodes exempt
        from the retro gate (engine marks nodes direct, per AS Part 5);
        Sun=Moon=Venus modes (government / very quick / friendly);
        Saturn-aspect -> PARTIAL ("part of the loan applied for, or
        part by part").
      - loan_repay_clear: v9.7-native procedure (replaces layer2b
        delegation; layer2b untouched): hard retro gate kept
        (book-verbatim); all 7 modes incl. NEW Venus ("compromise and
        sweet words") and Sun ("help of father / government officials");
        Saturn-aspect -> PARTIAL ("only a part of the whole, or part
        by part"; Prabhakar: "never full loan").
  B3  Provident fund / pension / gratuity (new `provident_fund_pension`
      event): 11th CSL -> 8,2,6,11 (+Mercury/Jupiter) -> YES ("assured").
      KP Ezine Nov 2020-Dec 2021 true p.291 (hint + worked case: 11th
      CSL Jupiter -> 2,6,8,11 & Jupiter -> assured).
  B4  Donation receive (new `donation_receive` event): 8th CSL ->
      2-6-11 -> YES+DELAYS ("getting donation is sure, but 8 gives you
      some delay and dejection"); partial -> PARTIAL ("did not get as
      expected"). Bosmia Ex.125 true pp.316-318 (outcome-verified).

v9.6 and everything before it are byte-identical. Frozen v1, GitHub,
and the live app are untouched.

"""


import os
import re
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from engine import layer3_v9 as V9  # noqa: E402  (read-only: helpers + fallback dispatch)
from engine.layer3_v9 import (  # noqa: E402
    CAREER_EVENTS, EXAM_EVENTS, MARRIAGE_EVENTS, DUAL_SIGNS, L3T,
    _R, _binary_verdict, _cast, _chain_of, _csl_chain,
    _decide as _v9_decide, _delay_decor as _v9_delay_decor, _dual_test,
    _eleventh_check,
    _flags as _v9_flags, _moon_diagnostic, _planet_fact, _resolve_planet,
    _retro_map, _rotated, _signified_set, shift_house,
)

JUDGE_NAME = 'v10.2-exam'

# 2026-10-15 (_NODE_CHAIN_FIX): shadow v9's _csl_chain with a node-aware
# wrapper. When the flag is on and the CSL is Rahu/Ketu, the chain is built
# from the node's own levels (not the agent's).
_v9_csl_chain_orig = _csl_chain


def _csl_chain(cusp_no, reading):
    sub, agent, chain, note = _v9_csl_chain_orig(cusp_no, reading)
    if _NODE_CHAIN_FIX and sub in ('Rahu', 'Ketu'):
        nlv = _node_chain_levels(sub, reading)
        chain = set()
        for _lv in ('L1', 'L2', 'L3', 'L4'):
            chain |= nlv.get(_lv, set())
        note = (note or '') + ' (node-fix)'
    return sub, agent, chain, note


CIT = dict(V9.CIT)
CIT.update({
    'bosmia_11th_mixed_no': 'Bosmia Easy Way Horary true p.420 (Ex.171: 11th '
                            'CSL -> 2-6-10 mixed with 1-5-9 -> NO) and true '
                            'p.422 (Ex.172: 2-6 mixed with 9-8-12 -> NO); '
                            'outcome-verified correct x2; user ruling '
                            '2026-10-03, NARROWED 2026-10-05: fires only on '
                            'desired-job 11th-CSL-decider paths and '
                            'chitfund (explicit 2026-10-04 ruling); '
                            'financial_help and money_lent_recovery use '
                            'the general mixed->YES+DELAYS doctrine '
                            '(Ex.192 re-run 2026-10-05)',
    'reinstatement': 'KSK Reader VI true pp.309-310 (reinstatement: the '
                     'lord of the constellation the 10th sub-lord sits in '
                     'signifying 2/6/10 -> reinstated; 1/5/9/12 and NOT '
                     '2/6/10 -> never reinstated; "The sub-lord of the 10th '
                     'decides"); Part 5 true p.189 (10th CSL -> 2,6,10 = '
                     'regain position)',
    'retirement': 'Bosmia Prashna Jyotish Ex.18 true pp.120-121 (10th/6th '
                  'CSL -> 1,5,9,12 = retirement from service/business)',
    'job_abroad': 'KSK Reader VI true p.310 (horary 98: a 3,9,12 '
                  'significator that also signifies 6th -> abroad ON '
                  'foreign assignment); Bosmia Easy Way Horary Ex.16 true '
                  'p.80 (2nd CSL -> 9/12 + 2,6,11 = foreign assignment)',
    'promotion_11th': 'Bosmia Prashna Jyotish Ex.11 p.102 (11th CSL -> '
                      '2/6/10/11 = promotion; verified)',
    'transfer': 'Bhatnagar p.181 (transfer: 10th CSL signifying 2 of '
                '{3,9,12})',
    'business_start': 'Bosmia Prashna Jyotish Ex.29 p.154 (10th CSL -> '
                      '2,7,10 = independent business)',
    'business_profit': 'ezine master table true p.476: gain in business = '
                       '2,7,10,11 operating jointly (7,11 / 7,2 / 10,7,2 / '
                       '7,10,11)',
    'dismissal': 'KSK Reader VI true pp.310,317 + K.P. Sub Lord and the '
                 'Principle true pp.21,26: denial = [1,5,9,12] on '
                 '2nd/6th/10th CSL (8 dropped per mining); Joshi true p.87 '
                 'suspension-vs-dismissal split',
    'interview': 'Naik K.P. Dynamics printed pp.44-45 (3rd CSL decider); '
                 'Bansal p.58; Taneja Ill-10',
    'money_gain': 'Bosmia Easy Way true p.73 / PDF p.74 (Ex.13: 2nd CSL -> '
                  '2-6-11 full set; partial -> "some wealth"); '
                  'pp.85-86 (Ex.18: enormous wealth = 2-6-10-11 clean of '
                  '5-8-12, verified)',
    'lottery': 'Bosmia Prashna Jyotish Ex 31 true pp.158-159 '
               '(outcome-verified: 11th CSL -> 2-6-11 + 3rd connection, '
               'NOT 5/8/12, CSL + star-lord direct -> win); KSK Reader VI '
               'true pp.213-214 (outcome-verified: 11th CSL retro or in '
               'retro lord\'s star -> cannot win; direct + 2/6/11 -> wins). '
               'User picked the Bosmia/KSK-VI school from the 5-way split '
               '(money batch-2, 2026-10-05)',
    'recovery_modes': 'KSK Reader VI true pp.230/238 (entangled-money '
                      'planet modes: Saturn=delay+obstacles, Mercury='
                      'instalments/correspondence, Jupiter=court/lawful, '
                      'Mars=threats, Moon=quick, Venus=compromise, Sun='
                      'government help; Saturn aspecting the sub-lord -> '
                      '"one recovers only a part of it or part by part"); '
                      'ezine Jan 2016 hand-loan case (8 modes worked)',
    'borrow_modes': 'AS Part 5 (Sun=government loan; Moon=lender agrees '
                    'very quickly; Venus=friendly; Rahu/Ketu always direct; '
                    'Saturn aspecting sub-lord -> "part of the loan applied '
                    'for, or part by part" = PARTIAL)',
    'repay_modes': 'Reader VI via AS Part 2 true pp.199-200 (12th CSL: '
                   'Saturn=delay+obstacles, Mercury=instalments, Jupiter='
                   'lawful full amount, Mars=lender threatens then repays, '
                   'Venus="with a spirit of compromise and sweet words", '
                   'Sun="through the help of either father or Government '
                   'Officials"; Saturn aspecting the sub-lord -> "one '
                   'repays only a part of the whole or repays part by '
                   'part" = PARTIAL; Prabhakar Times p.185: Saturn -> '
                   '"never full loan")',
    'provident_fund': 'KP Ezine Nov 2020-Dec 2021 true p.291 (hint: 11th '
                      'CSL -> 8 (long-term income like PF), 2 (money), 6 '
                      '(service earnings), 11 (success) and/or Mercury/'
                      'Jupiter -> "getting money of provident fund is '
                      'assured"; worked case: 11th CSL Jupiter -> 2,6,8,11 '
                      '& Jupiter -> assured)',
    'donation_receive': 'Bosmia Easy Way Ex.125 true pp.316-318 '
                        '(outcome-verified: 8th CSL Jupiter -> '
                        '11-6-9-10-5-4-7-8-2 -> "getting donation is sure, '
                        'but 8 gives you some delay and dejection"; actual: '
                        '"Prediction proved right. He did not get as '
                        'expected" = PARTIAL)',
    'career_floor_shadow': 'Bosmia "in the star of the occupant or owner" '
                           '(SHADOW measurement only — never verdict-'
                           'changing in v9.2)',
    'unknown_job': 'user rule 2026-10-03 (named job not in knowledge table '
                   '-> judge 11th CSL + 11th lord); 11th = fulfilment of '
                   'desire (Subramaniam Beginners Vol 3 p.145)',
    'known_job': 'known_jobs.json (book-cited profession -> cusp/planet '
                 'mappings mined from the 46-book library)',
})

# L12R (2026-10-03 funnel repair): citations for the 12 new-event
# procedures. Every page below is a TRUE PDF page verified with pdftotext
# (see l12_repair/layer3_procedures.json for the mining notes).
CIT.update({
    'job_continuity': 'USER RULING 2026-10-04 (books only): decider = 6th '
                      'CSL (service); 6th CSL -> 2,10,11 = permanent/ '
                      'continuing. Book: Bosmia Easy Way Horary Ex.79 true '
                      'pp.218-219 (verified): 6th/10th CSL -> 2-6-10 = '
                      'continue; -> 1-5-9-12 = will leave/change; KSK '
                      'Reader III p.383 (reinstatement = 2-6-10-11 '
                      'significators); ezine p.503 (6th sublord -> 2,10,11 '
                      '= permanent job). Denial [5,8,12] is book-adjacent '
                      'inference from the dismissal family [1,5,8,9,12], '
                      'flagged as such. REMOVED: the [1,2,4,10,11] '
                      '"retained" formula (K.P. Sub Lord and the Principle '
                      'true p.19) -- NOT found in the 46-book library; the '
                      '11th-CSL secondary confirm is gone with it (it '
                      'would have tripped the Bosmia 11th exception).',
    'business_partnership': 'Astro Secrets & KP Part 3 true p.54 '
                            '(verified): 7th CSL in the constellation of a '
                            'planet signifying 6+11 = "you can have a '
                            'partner in business"; 6+12 = "Partnership will '
                            'break"; 5+8+12 = partner exploits you',
    'exam_appear': 'KSK KP Reader VI: Horary Astrology true p.198 '
                   '(verified): "Whether one will be able to appear for the '
                   'examination or not is to be seen from the horary lagna. '
                   'If the horary lagna is spoiled due to the deposition of '
                   'natural malefics or lord of 6 or 8 or 12, the native '
                   'will not be able to make an attempt."',
    'scholarship': 'Astro Secrets & KP Part 2 true p.265 (verified): "The '
                   'sublord of the 4th cusp should be connected with 6 or '
                   '11 for one to receive scholarship." Corroborating: '
                   'Naik K.P. Dynamics true p.56: Scholarship -> 2,6,11',
    'job_voluntary_exit': 'Bosmia Easy Way Horary Ex.79 hint true '
                          'pp.218-219 (verified): 10th/6th CSL -> 1-5-9-12 '
                          '= will leave/change ("during the joint period of '
                          'the significators of 1-5-9"); -> 2-6-10 = stays. '
                          'Pure voluntary exit with no next job: '
                          'NEEDS-USER-RULING',
    'job_relocation': 'DEFAULT synthesis (NEEDS-USER-RULING): KSK Reader '
                      'III true p.390 (10th CSL 2-of-3 {3,9,12} = place '
                      'change with the job) + K.P. Sub Lord and the '
                      'Principle true p.19 (verified: 4th CSL -> 3,12 = '
                      'change in residence). No book covers voluntary '
                      'career-driven relocation.',
    'money_lent_recovery': 'Astro Secrets & KP Part 3 true pp.16-17 '
                           '(verified): "THE AMOUNT WILL BE REALISED IF '
                           'THERE IS ANY CONNECTION BETWEEN SUB LORD OF THE '
                           '11TH CUSP AND THE CONCERNED HOUSES 2ND AND '
                           '11TH." Corroborating: Bhatnagar Unlocking Time '
                           'Prediction true pp.51,53 (verified): recovery '
                           'houses 2,6,10,11',
    'chitfund_kitty': 'USER RULING 2026-10-04: chit fund payout = sudden '
                      'wealth -> 5th house, judged by the 11th CSL. 11th '
                      'CSL -> 2,5,6,11 = YES (2 = money in hand, 5 = '
                      'sudden wealth per user, 6 = gain/regularity, 11 = '
                      'gains/fulfillment); denial = 8,12. The 5th is '
                      'EXPLICITLY not denial here -- the user rejects '
                      'Bosmia Prashna Jyotish true p.158 "5th negates" for '
                      'chit funds. The 3rd-house lottery reading (KSK '
                      'Reader VI true pp.213-214) is skipped per the user '
                      '("both are correct... keep 5th and judged by '
                      '11th"). No chit-fund doctrine exists in the books; '
                      'the 3rd-vs-5th split is a KSK-internal contradiction '
                      '(Reader III p.212: 2+5 for lottery/sudden gains). '
                      'Replaces the 2026-10-03 lottery-default (11th CSL '
                      '-> 2/6/11 + 3rd, clean of 5/8/12, retrograde check).',
    'business_closure': 'Bosmia Easy Way Horary Ex.160 true pp.395-397 '
                        '(verified; outcome "Prediction proved right. He '
                        'closed his Delhi office."): 10th CSL -> 2-7-10 '
                        'promised / 7th CSL -> 2-10-11 gain; mixed 2-7-11 '
                        'with 1-5-9-8 -> "your decision to close business is '
                        'perfect". Corroborating Ex.159 true pp.393-394.',
    'financial_help': 'Joshi Krishnamurthy Padhdhati true p.72 (verified): '
                      '"SL of the 6-8-11 with 2-3-6-11 HS, then the native '
                      'will get the loan. 5-8-12 HS negative for loans." '
                      'Corroborating: Naik K.P. Dynamics true p.56: '
                      'Financial Help -> 8,2,6,11. Keep book-form denial '
                      '[5,8,12] or drop 8: NEEDS-USER-RULING',
    'financial_crisis': 'Bosmia Easy Way Horary Ex.13 true pp.73-74 '
                        '(verified): 2nd CSL -> 2-6-11 = relief ("during the '
                        'joint period of 2-6-11"); book-given negative '
                        'form: "Positive bhava are 2-6 and negative bhava '
                        'are 1-9-8-12."',
    'thesis_submission': 'Bosmia Easy Way Horary Ex.129 true pp.324-325 '
                         '(verified): "If the sub lord of the 9th (Higher '
                         'education) cusp be the significator of 4-9-11 '
                         'higher education is assured." (PhD synopsis '
                         'presentation case). Denial array: '
                         'NEEDS-USER-RULING',
})

CIT['mixed_delays_flag'] = (
    'user ruling 2026-10-03 (formal doctrine): mixed evidence -> YES with '
    'DELAYS, never NO; the DELAYS modifier is the flag that makes the '
    'ruling visible on the verdict'
)


CIT['weak_mixed_no_promise'] = (
    'user ruling 2026-10-05 (mixed refinement): the promise must be STRONG '
    '(full success set signified) for mixed evidence to stand as YES+DELAYS; '
    'partial success + denial -> OTHER -- no promise was made, so there is '
    'nothing for delays to decorate. Keeps the "delays only decorate a '
    'promise already made" thesis (2026-10-02).'
)

# Level weights for 7-level significator table (2026-10-06).
# L1/L2 are strong (occupation levels); L3/L4 medium (ownership);
# L5/L6/L7 weak (sub-lord levels + cusp lordship).
# Books use sub-lord levels but weight them less than star-lord/planet levels.
LEVEL_WEIGHTS = {
    'L1': 1.00,  # star-lord's occupation
    'L2': 0.75,  # planet's own occupation
    'L3': 0.50,  # star-lord's ownership
    'L4': 0.25,  # planet's own ownership
    'L5': 0.50,  # sub-lord's occupation
    'L6': 0.25,  # sub-lord's ownership
    'L7': 0.25,  # cusp lordship
}
# Threshold: a house counts as "strongly signified" if weighted score >= this
STRONG_THRESHOLD = 0.75

# B3 LAB VARIANTS (2026-10-13, Claude design). Module-level switch for the lab
# harness only — production default is 'V0' (current behavior).
# V0: current (7-level chain, S5 OFF for marriage)
# V0S5: current 7-level chain, S5 ON (full_success passed) — isolates S5 effect
# V1: strong-only chain (>=0.75) + S5 ON + core-7-strong gate
# V1C: strong-only chain, S5 OFF (check c — isolates chain effect)
# V2: L1/L2-only chain + S5 ON + core-7 occupation gate
# V3: strong-only chain + S5 ON, NO core gate (interpolation)
# V4: 7-level chain, L7 excludes decider cusp (circularity fix), S5 OFF
_B3_VARIANT = 'V0'

# 2026-10-15 (LAB VARIANT, default OFF): agenda/verdict split (Gemini #4).
# When True, _binary_verdict_d1 applies the sub-lord veto: agenda (L1-L4)
# promises + sub-lord (L5-L6) purely denies -> NO (not YES-WITH-DELAYS).
# Book: Taneja Prasana p.27; K.P. Sub Lord and the Principle p.12.
_AGENDA_VERDICT = False

# 2026-10-15 (LAB VARIANT, default OFF): KP-correct Rahu/Ketu chains.
# When True, a node CSL builds its chain from the NODE's own star-lord /
# sub-lord / occupation (plus sign-lord ownership), not from the resolved
# agent. Book: KSK Reader IV pp.56-59; Reader VI pp.146-147.
# SHIPPED 2026-10-15 (user approved): lab trial 55.3% vs 54.7% baseline,
# zero breaks — verified correctness bug, not tuning.
_NODE_CHAIN_FIX = True

# 2026-10-15 (LAB VARIANT, default OFF): untenanted-planet gate (Gemini #4.2).
# When True, L4/L6 passive ownership is dropped for tenanted planets
# (a planet with tenants in its stars). Book: Reader IV p.55; VI p.119.
_UNTENANTED_GATE = False

# 2026-10-15 (LAB VARIANT, default OFF): promise strength floor.
# When True, the `promise` branch (s_hit, no d_hit -> YES) requires minimum
# strength: max level-weight of s_hit >= 0.50. A lone weak L5/L6/L7 hit
# routes to OTHER instead of YES. Targets the 4 weak-promise false-YES
# cases from the 2026-10-15 career autopsy (A46, W167, W168, W87).
_PROMISE_FLOOR = True

# 2026-10-13 (USER RULING, engineering convention — NOT book-derived):
# L7 (cusp lordship) excludes the decider cusp. A planet that is sub-lord of
# cusp N does not credit house N via L7 when N is the decider — removes the
# circularity where "the decider signifies its own house" is true by
# construction. Adopted on logic, not on numbers (B3 lab: no measured harm).
# Roll back: set _L7_EXCLUDE_DECIDER = False.
_L7_EXCLUDE_DECIDER = True


def _weighted_hits(levels, house_set):
    """Return (strong_hits, weak_hits, scores) for a house set.

    levels: dict from _chain_levels (L1..L7 -> set of houses)
    house_set: set of houses to check (e.g., success or denial)

    strong_hits: houses with weighted score >= STRONG_THRESHOLD
    weak_hits: houses with 0 < score < STRONG_THRESHOLD
    scores: dict house -> weighted score
    """
    scores = {}
    for house in house_set:
        score = 0.0
        for level, houses in levels.items():
            if house in houses:
                score += LEVEL_WEIGHTS.get(level, 0)
        if score > 0:
            scores[house] = score
    strong = sorted(h for h, s in scores.items() if s >= STRONG_THRESHOLD)
    weak = sorted(h for h, s in scores.items() if s < STRONG_THRESHOLD)
    return strong, weak, scores


def _csl_chain_strong(cusp_no, reading):
    """Return (sub_lord, agent, strong_chain_set, note) for a cusp.

    strong_chain_set: only houses with weighted score >= STRONG_THRESHOLD.
    Use for topics tuned on 4-level chains (exam, career, money) where
    L5/L6/L7 weak hits create noise. Relationship uses the full 7-level chain.
    """
    # Get the flat chain and levels
    from layer3_v9 import _csl_chain as _v9_csl_chain
    sub, agent, chain, note = _v9_csl_chain(cusp_no, reading)
    if not sub:
        return sub, agent, set(), note
    # Get levels (node-aware when the CSL is a node: _levels_planet)
    levels = _chain_levels(_levels_planet(sub, agent), reading)
    # Build strong-only set: houses with score >= threshold
    strong = set()
    for house in chain:
        score = sum(LEVEL_WEIGHTS.get(lv, 0) for lv, hs in levels.items()
                    if house in hs)
        if score >= STRONG_THRESHOLD:
            strong.add(house)
    return sub, agent, strong, (note or '') + ' (strong-only)'


def _levels_planet(sub, agent):
    """Which planet's levels feed the weighted gates.

    2026-10-15 (Claude review A4): the _NODE_CHAIN_FIX shadow builds HIT
    sets from the node's own chain, so the LEVELS (weights) must come from
    the node too — otherwise hit houses get weight 0 and mixed cases flip
    spuriously. Mirrors the pattern _csl_chain_4level always used. With the
    fix off, hits and levels both come from the agent (consistent).
    """
    return sub if (_NODE_CHAIN_FIX and sub in ('Rahu', 'Ketu')) else agent


def _csl_chain_4level(cusp_no, reading):
    """Return (sub_lord, agent, chain_set, note) using ONLY L1-L4.

    For exam procedures tuned on the original 4-level table.
    L5/L6/L7 (sub-lord levels + cusp lordship) are excluded.
    """
    # 2026-10-15: use the module-level _csl_chain (node-aware shadow when
    # _NODE_CHAIN_FIX is on), not v9's directly.
    sub, agent, _, note = _csl_chain(cusp_no, reading)
    if not sub:
        return sub, agent, set(), note
    # 2026-10-15 (_NODE_CHAIN_FIX): node CSL uses the node's own levels.
    _lvp = _levels_planet(sub, agent)
    levels = _chain_levels(_lvp, reading)
    chain = set()
    for lv in ('L1', 'L2', 'L3', 'L4'):
        chain |= levels.get(lv, set())
    return sub, agent, chain, (note or '') + ' (4-level)'


def _d4_star_retro_check(reading, decider, trace, event_label, sub_lord=None):
    """D4 (user ruling 2026-10-13, approved): decider's star-lord retrograde
    -> denial. Reader VI pp.146-147: a direct planet in the constellation of
    a retrograde planet "cannot have success." Returns True if the veto fires
    (caller should return NO). Distinct from the 2026-10-13 user ruling on
    the decider ITSELF being retrograde (hard NO for relationship).

    2026-10-14 (Gemini 4 audit): when the CSL is a node (Rahu/Ketu), check
    BOTH the sub-lord's star-lord and the agent's star-lord. Passing only
    the agent misses the node's own retrograde star-lord.
    """
    retro = _retro_map(reading)
    # Check sub_lord first, then decider (agent) — deduplicated, order kept.
    for p in dict.fromkeys([x for x in (sub_lord, decider) if x]):
        star = (_planet_fact(reading, p) or {}).get('star_lord')
        if star and bool(retro.get(star, False)):
            trace.append({'rule': 'd4_star_retro_denial',
                          'citation': 'Reader VI pp.146-147: planet in star of '
                                      'retrograde planet cannot have success',
                          'detail': '%s decider %s star-lord %s is retrograde -> '
                                    'deciding vote incapable -> NO'
                                    % (event_label, p, star)})
            return True
    return False


def _csl_chain_7level(cusp_no, reading):
    """Return (sub_lord, agent, chain_set, note) using L1-L7.

    For relationship procedures — books use sub-lord levels heavily
    (Bosmia Ex.62, Ex.196, Ex.102; Prasad H-R26). Added 2026-10-06
    per user ruling. Gives relationship 85.4% (vs 75.6% on 4-level).
    """
    from layer3_v9 import _chain_of_7level, _resolve_planet
    cusp_facts = reading.get('cusp_facts') or []
    sub = None
    if 1 <= cusp_no <= len(cusp_facts):
        sub = (cusp_facts[cusp_no - 1] or {}).get('sub_lord')
    if not sub:
        return None, None, set(), 'cusp %d: no sub-lord found' % cusp_no
    agent, note = _resolve_planet(sub, reading)
    _exc = cusp_no if (_L7_EXCLUDE_DECIDER or _B3_VARIANT == 'V4') else None
    # 2026-10-15 (_NODE_CHAIN_FIX): node CSL builds from the node's own
    # levels (not the agent's chain).
    if _NODE_CHAIN_FIX and sub in ('Rahu', 'Ketu'):
        _nlv = _node_chain_levels(sub, reading)
        _chain = set()
        for _lv in ('L1', 'L2', 'L3', 'L4', 'L5', 'L6'):
            _chain |= _nlv.get(_lv, set())
        # L7 with decider-cusp exclusion
        for _h in _nlv.get('L7', set()):
            if _exc is None or _h != _exc:
                _chain.add(_h)
        return sub, agent, _chain, (note or '') + ' (7-level, node-fix)'
    return sub, agent, _chain_of_7level(agent, reading, exclude_cusp=_exc), (note or '') + ' (7-level)'


def _binary_verdict_d1(s_hit, d_hit, trace, modifiers, rule_key, full_success=None,
                       levels=None, denial_meta=None):
    """D1: v9's _binary_verdict + the user's mixed rulings made consistent.

    Mixed refinement (user ruling 2026-10-05): when success AND denial both
    hit, the promise must be STRONG -- the FULL success set signified -- for
    YES+DELAYS. Partial success + denial -> OTHER (no promise made, nothing
    to decorate). v9/v9.1/v9.2 wrote "YES + DELAYS" in the trace on the mixed
    branch but never appended the DELAYS modifier -- the ruling was words
    without the flag. v9.3 appends it.

    v10 (S5 bugfix): if full_success is provided and we're in a mixed case
    (s_hit and d_hit) but s_hit is not the full set -> OTHER. Callers that
    don't pass full_success get the legacy mixed->YES+DELAYS behavior.

    2026-10-14 (Gemini 4 audit): when S5 is OFF (full_success=None) and the
    caller passes `levels` (from _chain_levels), a weak L6/L7 success hit
    (weight 0.25) must not flip strong L1/L2 denial into YES+DELAYS.
    Weighted-margin rule: denial dominating (weighted_d - weighted_s >= 1.0
    with max success weight < 0.75) -> NO; else require max success weight
    >= 0.50 or weighted_s >= weighted_d for YES+DELAYS.

    2026-10-14 (denial_meta enforcement): when denial_meta status is
    CANDIDATE_NEGATION (Layer 2's 12th-from fallback, not book doctrine),
    a d_hit with zero s_hit must NEVER produce a hard NO (forbidden:
    automatic_NO). It routes to OTHER instead. Mixed cases still run the
    normal S5 logic (denial may support OTHER, which is allowed).
    Callers using hardcoded BOOK denial sets leave denial_meta=None.
    """
    # 2026-10-15 (LAB VARIANT _AGENDA_VERDICT, default OFF): sub-lord veto.
    # Split the chain into agenda (L1-L4: planet + star-lord, what the matter
    # proposes) and confirmation (L5-L6: sub-lord, what decides). If the agenda
    # promises (s_hit at L1-L4) but the sub-lord is PURELY denial (d_hit at
    # L5-L6, zero s_hit there) -> NO (sub-lord veto), not YES-WITH-DELAYS.
    # Book: Taneja Prasana p.27 ("If the Cuspal Sub lord negates the event
    # the event may not take place even in the DBA promising the event
    # strongly"); K.P. Sub Lord and the Principle p.12.
    if _AGENDA_VERDICT and levels and s_hit and d_hit:
        _ag_s, _ag_d, _cf_s, _cf_d = [], [], [], []
        _ss, _ds = set(s_hit), set(d_hit)
        for _lv, _hs in levels.items():
            _hss = set(_hs)
            if _lv in ('L1', 'L2', 'L3', 'L4'):
                _ag_s.extend(sorted(_hss & _ss))
                _ag_d.extend(sorted(_hss & _ds))
            elif _lv in ('L5', 'L6'):
                _cf_s.extend(sorted(_hss & _ss))
                _cf_d.extend(sorted(_hss & _ds))
        if _ag_s and _cf_d and not _cf_s:
            trace.append({'rule': 'sub_lord_veto',
                          'citation': 'Taneja Prasana p.27; K.P. Sub Lord and '
                                      'the Principle p.12 (lab variant)',
                          'detail': 'agenda (L1-L4) promises %s but sub-lord '
                                    '(L5-L6) purely denies %s (zero success '
                                    'at sub level) -> NO (veto, not '
                                    'YES-WITH-DELAYS)' % (_ag_s, _cf_d)})
            return 'NO', 'sub_lord_veto'
    # v10 S5: partial success + denial -> OTHER (no promise to decorate)
    if full_success is not None and s_hit and d_hit:
        if set(s_hit) != set(full_success):
            trace.append({'rule': 'weak_mixed_no_promise',
                          'citation': CIT['weak_mixed_no_promise'],
                          'detail': 'mixed but success %s is partial (full '
                                    'set %s) -> no promise made -> OTHER'
                                    % (s_hit, sorted(full_success))})
            return 'OTHER', 'weak_mixed_no_promise'
    # 2026-10-14: weighted-margin gate (S5 OFF + levels provided)
    if full_success is None and levels and s_hit and d_hit:
        def _maxw(houses):
            return max((LEVEL_WEIGHTS.get(lv, 0)
                        for lv, hs in levels.items()
                        for h in houses if h in hs), default=0)
        def _sumw(houses):
            return round(sum(LEVEL_WEIGHTS.get(lv, 0)
                             for lv, hs in levels.items()
                             for h in houses if h in hs), 2)
        _sw_max, _dw_max = _maxw(s_hit), _maxw(d_hit)
        _sw, _dw = _sumw(s_hit), _sumw(d_hit)
        if _dw - _sw >= 1.0 and _sw_max < 0.75:
            trace.append({'rule': 'weighted_denial_dominates',
                          'citation': '2026-10-14 Gemini 4 audit: denial '
                                      'dominates at strong levels',
                          'detail': 'weighted D=%.2f vs S=%.2f (margin %.2f), '
                                    'max success weight %.2f < 0.75 -> NO '
                                    '(weak L6/L7 hit cannot decorate strong '
                                    'denial)' % (_dw, _sw, _dw - _sw, _sw_max)})
            return 'NO', 'weighted_denial_dominates'
        if not (_sw_max >= 0.50 or _sw >= _dw):
            trace.append({'rule': 'weak_mixed_no_promise_weighted',
                          'citation': '2026-10-14 Gemini 4 audit',
                          'detail': 'mixed but success weight too weak '
                                    '(max %.2f, sum %.2f vs denial %.2f) -> '
                                    'OTHER' % (_sw_max, _sw, _dw)})
            return 'OTHER', 'weak_mixed_no_promise_weighted'
        # else: strong enough -> fall through to legacy mixed->YES+DELAYS
        trace.append({'rule': 'weighted_mixed_pass',
                      'detail': 'mixed passes weighted gate (S=%.2f D=%.2f) '
                                '-> YES+DELAYS' % (_sw, _dw)})
    # 2026-10-14 (denial_meta enforcement): CANDIDATE_NEGATION fallback
    # denial must never produce a hard NO on its own (forbidden:
    # automatic_NO). d_hit with zero s_hit -> OTHER, not NO.
    _dm_status = (denial_meta or {}).get('status')
    if _dm_status == 'CANDIDATE_NEGATION' and d_hit and not s_hit:
        trace.append({'rule': 'candidate_negation_no_bar',
                      'citation': 'Layer 2 denial_meta: CANDIDATE_NEGATION '
                                  'forbids automatic_NO',
                      'detail': 'fallback denial houses %s signified, zero '
                                'success-house connection -> OTHER (fallback '
                                'denial cannot hard-NO)' % d_hit})
        return 'OTHER', 'candidate_negation_no_bar'
    # 2026-10-15 (_PROMISE_FLOOR, lab variant): weak promise -> OTHER.
    # A lone weak-level success hit (max weight < 0.50, i.e. L4/L6/L7 only)
    # with zero denial is not a promise -- it's noise. Route to OTHER.
    # Targets career-autopsy weak-promise false-YES (A46, W167, W168, W87).
    if _PROMISE_FLOOR and levels and s_hit and not d_hit:
        _pw = max((LEVEL_WEIGHTS.get(_lv, 0) for _lv, _hs in levels.items()
                   for _h in s_hit if _h in _hs), default=0)
        if _pw < 0.50:
            trace.append({'rule': 'promise_floor_other',
                          'citation': '2026-10-15 career autopsy (lab variant)',
                          'detail': 'success %s max level-weight %.2f < 0.50 '
                                    '(weak L4/L6/L7 only), zero denial -> '
                                    'OTHER (not a promise)' % (s_hit, _pw)})
            return 'OTHER', 'promise_floor_other'
    verdict, reason = _binary_verdict(s_hit, d_hit, trace, rule_key)
    if reason == 'mixed_decorated_delay' and 'DELAYS' not in modifiers:
        modifiers.append('DELAYS')
        trace.append({'rule': 'mixed_delays_flag',
                      'citation': CIT['mixed_delays_flag'],
                      'detail': 'mixed evidence -> YES stands, DELAYS '
                                'modifier applied per the ruling'})
    return verdict, reason


def _nur_tag(trace, text):
    """Tag a trace with an explicit NEEDS-USER-RULING flag.

    L12R (2026-10-03): the 8 open doctrine questions from
    l12_repair/layer3_procedures.json -> needs_user_ruling. Nothing under
    this tag is settled doctrine; the user rules on each.
    """
    trace.append({'rule': 'NEEDS-USER-RULING',
                  'citation': 'l12_repair/layer3_procedures.json -> '
                              'needs_user_ruling (user has not ruled yet)',
                  'detail': text})


def _bosmia_11th_mixed_no(s_hit, d_hit, trace, modifiers, rule_key):
    """The Bosmia exception (user ruling 2026-10-03, NARROWED 2026-10-05):
    when the 11th CSL is the DECIDER and its chain shows mixed
    success+denial signification -> verdict NO (not YES+DELAYS).

    Basis: Bosmia Ex 171/172 (Easy Way, true pp.420/422) -- 11th CSL ->
    2-6-10 mixed with 1-5-9 / 2-6 mixed with 9-8-12 -> NO,
    outcome-verified correct both times. FIRES ONLY on desired-job
    11th-CSL-decider paths and chitfund (explicit 2026-10-04 ruling).
    financial_help and money_lent_recovery use the general
    mixed->YES+DELAYS doctrine (user ruling 2026-10-05; Ex.192 re-run).
    The general mixed->YES+DELAYS thesis stands everywhere else.
    """
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
        trace.append({'rule': 'bosmia_11th_mixed_no',
                      'citation': CIT['bosmia_11th_mixed_no'],
                      'detail': '11th CSL decider: mixed success %s + '
                                'denial %s -> NO per the Bosmia exception '
                                '(user ruling 2026-10-03; NOT YES+DELAYS)'
                                % (s_hit, d_hit)})
        return 'NO', 'bosmia_11th_mixed_no'
    trace.append({'rule': 'weak_evidence',
                  'citation': 'layer3_traditional docstring (OURS): "the '
                              'book gives no formula for ties"',
                  'detail': 'no success or denial houses signified -> OTHER'})
    return 'OTHER', 'weak_evidence_only'


def _delay_decor(reading, success, verdict, trace, modifiers):
    """v9's _delay_decor + E5 (v9.4): the Bosmia Punarphoo sub-form.

    The audit (row 26) found a definition mismatch: the engine detects
    Punarphoo as Moon-Saturn conjunction <=3.33deg (R5:L14750), but
    Bosmia's job-timing examples use "Moon in Saturn's sub" (Easy Way
    Ex 80/81, true pp.220-223: "Moon is in Saturn sub hence, Punarphoo
    yoga ... shows delay in getting job"). Both forms are book-cited and
    both are DELAY-ONLY, so the sub-form is added as a second detector.
    Verdicts never change; at most DELAYS+PUNARPHOO modifiers are added
    to a YES."""
    _v9_delay_decor(reading, success, verdict, trace, modifiers)
    if verdict != 'YES':
        return
    if 'PUNARPHOO' in modifiers:
        return
    moon = _planet_fact(reading, 'Moon')
    if moon.get('sub_lord') == 'Saturn':
        trace.append({'rule': 'punarphoo_sub_form',
                      'citation': "Bosmia Easy Way Horary Ex 80/81 true "
                                  "pp.220-223 (\"Moon is in Saturn sub "
                                  "hence, Punarphoo yoga ... shows delay in "
                                  "getting job\")",
                      'detail': "Moon in Saturn's sub -> Punarphoo delay "
                                "(Bosmia's job-timing form; the conjunction "
                                "form is v9's)"})
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        modifiers.append('PUNARPHOO')


# ---------------------------------------------------------------------------
# Level helpers (per-level house sets; needed for the floor shadow)
# ---------------------------------------------------------------------------

def _node_chain_levels(node, reading):
    """KP-correct L1-L7 for Rahu/Ketu (lab variant _NODE_CHAIN_FIX).

    A node is not its agent. Per KSK Reader IV pp.56-59:
    L1 = node's star-lord's occupation; L2 = node's own occupation;
    L3 = node's star-lord's ownership;
    L4 = node's sign-lord's (dispositor's) ownership (nodes own nothing);
    L5 = node's sub-lord's occupation; L6 = node's sub-lord's ownership;
    L7 = cusps where the node is sub-lord.
    """
    facts = reading.get('planet_facts') or []
    by_name = {f.get('planet'): f for f in facts}
    nf = by_name.get(node) or {}
    star = nf.get('star_lord')
    sub = nf.get('sub_lord')
    occ = nf.get('house_occupied')
    sf = by_name.get(star) or {}
    subf = by_name.get(sub) or {}

    def _one(v):
        return {v} if isinstance(v, int) and 1 <= v <= 12 else set()

    def _many(vs):
        return {h for h in (vs or [])
                if isinstance(h, int) and 1 <= h <= 12}

    # sign-lord (dispositor) for L4 ownership. 2026-10-15 (Claude review A5):
    # the old code read the sign lord off the occupied HOUSE's cusp, but
    # under Placidus a house can span two signs. planet_facts already carries
    # the dispositor from the node's own longitude — use it directly.
    sign_lord = nf.get('sign_lord')
    slf = by_name.get(sign_lord) or {}

    # L2 = the node's own occupation. (2026-10-15: removed a conjunction
    # loop that re-added the occupied house — a no-op. Conjunction effects
    # travel via the agent chain, which _csl_chain returns separately.)
    l2 = _one(occ)

    l7 = set()
    cusp_facts = reading.get('cusp_facts') or []
    for i, cf in enumerate(cusp_facts):
        if (cf or {}).get('sub_lord') == node:
            l7.add(i + 1)

    return {'L1': _one(sf.get('house_occupied')),
            'L2': l2,
            # 2026-10-15 (review blind spot 3): node as star/sub of a node —
            # dispositor's ownership, not the node's empty one.
            'L3': _many((by_name.get(sf.get('sign_lord')) or {}).get('owns_houses'))
                  if star in ('Rahu', 'Ketu') else _many(sf.get('owns_houses')),
            'L4': _many(slf.get('owns_houses')),
            'L5': _one(subf.get('house_occupied')),
            'L6': _many((by_name.get(subf.get('sign_lord')) or {}).get('owns_houses'))
                  if sub in ('Rahu', 'Ketu') else _many(subf.get('owns_houses')),
            'L7': l7}


def _chain_levels(planet, reading):
    """Per-level binary house sets (L1..L7) for ANY planet.

    L1 = star-lord's occupation, L2 = planet's occupation,
    L3 = star-lord's ownerships, L4 = planet's ownerships.
    (User's 4-level significator table, ruling 2026-09-30.)
    L5 = sub-lord's occupation, L6 = sub-lord's ownerships.
    (Added 2026-10-06 per user ruling: books routinely use sub-lord levels.
    Bosmia Ex.62, Ex.196, Ex.102; Prasad H-R26.)
    L7 = cusp lordship: cusps where this planet is the sub-lord.
    (Added 2026-10-06: Bosmia Ex.102 "Moon is CSL of 2-5-7-12".)
    """
    # 2026-10-15 (_NODE_CHAIN_FIX): nodes build from their own facts.
    if _NODE_CHAIN_FIX and planet in ('Rahu', 'Ketu'):
        return _node_chain_levels(planet, reading)
    facts = reading.get('planet_facts') or []
    by_name = {f.get('planet'): f for f in facts}
    f = by_name.get(planet) or {}
    star = f.get('star_lord')
    sf = by_name.get(star) or {}
    sub = f.get('sub_lord')
    subf = by_name.get(sub) or {}

    def _one(v):
        return {v} if isinstance(v, int) and 1 <= v <= 12 else set()

    def _many(vs):
        return {h for h in (vs or [])
                if isinstance(h, int) and 1 <= h <= 12}

    # L7: cusps where this planet is the sub-lord
    cusp_facts = reading.get('cusp_facts') or []
    l7 = set()
    for i, cf in enumerate(cusp_facts):
        if (cf or {}).get('sub_lord') == planet:
            l7.add(i + 1)

    _lv = {'L1': _one(sf.get('house_occupied')),
           'L2': _one(f.get('house_occupied')),
           # 2026-10-15 (review blind spot 3): when the star-lord (L3) or
           # sub-lord (L6) is Rahu/Ketu, it owns nothing — but per KSK
           # Reader IV pp.56-59 a node acts through its dispositor
           # (sign-lord). Use the dispositor's ownership so L3/L6 are not
           # silently empty for the 6 node-ruled nakshatras (22% of zodiac).
           'L3': _many((by_name.get(sf.get('sign_lord')) or {}).get('owns_houses'))
                 if star in ('Rahu', 'Ketu') else _many(sf.get('owns_houses')),
           'L4': _many(f.get('owns_houses')),
           'L5': _one(subf.get('house_occupied')),
           'L6': _many((by_name.get(subf.get('sign_lord')) or {}).get('owns_houses'))
                 if sub in ('Rahu', 'Ketu') else _many(subf.get('owns_houses')),
           'L7': l7}
    # 2026-10-15 (_UNTENANTED_GATE, lab variant): a tenanted planet's passive
    # ownership (L4/L6) is weak noise -- tenants usurp its ownership agenda.
    # Drop L4/L6 when another planet sits in this planet's stars.
    # Book: Reader IV p.55; Reader VI p.119; Bosmia Easy Way p.9.
    if _UNTENANTED_GATE and planet not in ('Rahu', 'Ketu'):
        _tenanted = any((p.get('star_lord') == planet)
                        for p in facts if p.get('planet') != planet)
        if _tenanted:
            _lv['L4'] = set()
            _lv['L6'] = set()
    return _lv


def _csl_chain_levels(cusp_no, reading):
    """(sub_lord, agent, levels_dict, note) for any cusp number."""
    cusp_facts = reading.get('cusp_facts') or []
    sub = None
    if 1 <= cusp_no <= len(cusp_facts):
        sub = (cusp_facts[cusp_no - 1] or {}).get('sub_lord')
    if not sub:
        empty = {'L1': set(), 'L2': set(), 'L3': set(), 'L4': set()}
        return None, None, empty, 'cusp %d: no sub-lord found' % cusp_no
    agent, note = _resolve_planet(sub, reading)
    return sub, agent, _chain_levels(_levels_planet(sub, agent), reading), note


def _v9_default_binary(reading, router_out, success, denial, trace,
                      modifiers):
    """v9's default binary path, extracted for fallback use.

    When a book procedure is SILENT (positive-only test fails), v9.2 falls
    back to v9's measured generic binary instead of abstaining. Round-1
    measured: on transfer's 9 silent cases v9's default was right on 7 —
    abstaining throws away real accuracy. The book procedure still decides
    whenever it speaks clearly.

    2026-10-15 (review 1.3): REMOVED the "Bug B" rotation of signified.
    Both _signified_set(reading) and success/denial are already in chart
    frame (layer2_router._block rotated success/denial into it); v9's own
    _decide intersects them directly with no rotation. The extra shift
    misaligned turned charts (e.g. mother's house 9 -> 12, flipping YES
    to NO).
    """
    signified = _signified_set(reading)
    s_hit = sorted(signified & set(success))
    d_hit = sorted(signified & set(denial))
    verdict, reason = _binary_verdict_d1(s_hit, d_hit, trace, modifiers,
                                         'v9_default_fallback')
    trace.append({'rule': 'book_silent_v9_fallback',
                  'citation': 'v9 default binary (measured baseline)',
                  'detail': 'book procedure silent -> v9 generic binary: '
                            '%s (success %s, denial %s)'
                            % (verdict, s_hit, d_hit)})
    _eleventh_check(reading, router_out, success, trace, modifiers)
    _delay_decor(reading, success, verdict, trace, modifiers)
    _moon_diagnostic(reading, success, trace, modifiers)
    return verdict, modifiers, trace, s_hit, d_hit


def _suitability_procedure(reading, router_out, trace, modifiers, success, denial, job_key,
                           mapping):
    """career_suitability + KNOWN job: judge the job's own cusp.

    "Will I become a successful X?" is not a job-getting question — the
    11th-CSL desired-post test is the wrong tool (it broke W128/W129).
    The job's cusp (from the knowledge table, default 10th = nature of
    profession) must signify the service success set {2,6,10,11}.
    Silent -> v9's default binary (never invent a denial).
    """
    cusps = (mapping or {}).get('cusps') or [10]
    cusp = cusps[0]
    rc = _rotated(cusp, router_out)
    sub, agent, chain, _ = _csl_chain(rc, reading)
    S = _R({2, 6, 10, 11}, router_out)
    D = _R({1, 5, 8, 9, 12}, router_out)
    s = sorted(chain & S)
    d = sorted(chain & D)
    trace.append({'rule': 'suitability_job_cusp',
                  'citation': (mapping or {}).get('citation',
                                                  CIT['known_job']),
                  'detail': 'suitability for "%s": %dth CSL %s (agent %s) '
                            'chain %s -> 2/6/10/11 hit %s, denial %s'
                            % (job_key, cusp, sub, agent, sorted(chain),
                               s, d)})
    if s and not d:
        verdict = 'YES'
    elif d and not s:
        verdict = 'NO'
    else:
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(rc, reading)
        _career_floor_shadow([('%dth CSL' % cusp, levels)], S, verdict,
                             trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, d


def _career_floor_shadow(deciders, success_set, verdict, trace, modifiers):
    """Star-level floor as MEASUREMENT ONLY. Never changes the verdict.

    deciders: list of (label, levels_dict). If verdict is YES but no
    success house is testified at star level (L1/L3), flag THIN_PROMISE_SHADOW.
    v9.1 proved the floor cuts FPs but costs 19.2pp coverage; v9.2 measures
    first, decides later.
    """
    if verdict != 'YES':
        return
    parts = []
    met = False
    for label, levels in deciders:
        hit = sorted((levels.get('L1', set()) | levels.get('L3', set()))
                     & set(success_set))
        parts.append('%s: L1=%s L3=%s star_hit=%s'
                     % (label, sorted(levels.get('L1', set())),
                        sorted(levels.get('L3', set())), hit))
        if hit:
            met = True
    if not met:
        trace.append({'rule': 'career_floor_shadow_thin',
                      'citation': CIT['career_floor_shadow'],
                      'detail': 'thin promise — no success house at star '
                                'level (L1/L3): ' + '; '.join(parts) +
                                ' (shadow only; verdict unchanged)'})
        modifiers.append('THIN_PROMISE_SHADOW')


# ---------------------------------------------------------------------------
# Known-jobs table (user's job rule)
# ---------------------------------------------------------------------------

# 2026-10-15 (Claude review A6): the table used to live at
# ../layer3_shootout/known_jobs.json, which is NOT shipped with the app —
# so in production KNOWN_JOBS was silently {}. It now lives in-package.
_KNOWN_JOBS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'known_jobs.json')

def _load_known_jobs():
    try:
        with open(_KNOWN_JOBS_PATH, encoding='utf-8') as f:
            data = json.load(f)
        jobs = data.get('jobs', {}) or {}
        return {k.lower(): v for k, v in jobs.items()}
    except Exception:
        return {}


KNOWN_JOBS = _load_known_jobs()

# Generic job-title words for the "unknown job" bucket. Only specific
# titles — never bare "job". Kept conservative to avoid false triggers.
_JOB_TITLE_WORDS = [
    'astronaut', 'cosmonaut', 'pilot', 'doctor', 'surgeon', 'physician',
    'engineer', 'architect', 'lawyer', 'advocate', 'judge', 'teacher',
    'professor', 'lecturer', 'tutor', 'nurse', 'pharmacist', 'scientist',
    'researcher', 'journalist', 'reporter', 'actor', 'actress', 'singer',
    'musician', 'dancer', 'artist', 'writer', 'author', 'poet', 'chef',
    'cook', 'driver', 'sailor', 'soldier', 'policeman', 'constable',
    'fireman', 'politician', 'minister', 'diplomat', 'ambassador',
    'banker', 'accountant', 'auditor', 'clerk', 'stenographer',
    'manager', 'executive', 'consultant', 'analyst', 'developer',
    'programmer', 'designer', 'photographer', 'model', 'athlete',
    'cricketer', 'footballer', 'coach', 'trainer', 'farmer',
    'trader', 'broker', 'agent', 'dealer', 'merchant', 'shopkeeper',
    'priest', 'veterinarian',
    'librarian', 'translator', 'editor', 'anchor', 'officer',
    'ifs', 'ias', 'ips', 'irs', 'ifs officer', 'civil servant',
]


def _detect_named_job(question, flags):
    """User's job rule — detection step.

    Returns (job_key, mapping) where mapping is None for unknown jobs.
    Never fires when v9's qualifier flags already claimed the question
    (government / high_post / desired_job are measured v9 behavior).
    """
    q = (question or '').lower()
    if flags.get('government') or flags.get('high_post') \
            or flags.get('desired_job'):
        return None
    # Strip parentheticals: they carry background/metadata ("(retired Chief
    # Engineer...)", "(querent = the author himself...)"), not the ask.
    # The user's rule is about the job the querent NAMES as their desire.
    q_ask = re.sub(r'\([^)]*\)', ' ', q)
    # (a) known jobs first — longest keys first so "civil servant" beats "servant"
    for key in sorted(KNOWN_JOBS.keys(), key=len, reverse=True):
        # keys may use underscores ("civil_service_exam") — match spaces too
        pat = r'\b%s\b' % re.escape(key).replace(r'\ ', r'\s+').replace('_', r'\s+')
        if re.search(pat, q_ask):
            return key, KNOWN_JOBS[key]
    # (b) unknown: a specific job title word is named in the ask
    for word in _JOB_TITLE_WORDS:
        if re.search(r'\b%s\b' % re.escape(word), q_ask):
            return word, None
    return None


# ---------------------------------------------------------------------------
# Flags (v9's + v9.2 additions)
# ---------------------------------------------------------------------------

_INTERVIEW_CORE = re.compile(
    r'clear (the |my |this )?interview|'
    r'succeed in (the |this |my )?(\w+ )?interview|'
    r'succeed in it|'
    r'crack (the |my )?interview|'
    r'pass (the |this )?interview|'
    r'get through (the |my )?interview|'
    r'selected in (the |my )?interview|'
    r'interview (round|letter|call)|'
    r'call for (the |an )?interview|'
    r'success in interview|'
    r'interview[^.]{0,40}(tomorrow|scheduled|to be held|upcoming)',
    re.I)

_INTERVIEW_BLOCKER = re.compile(
    r'offer letter|appointment letter|joining letter|get the job|'
    r'job offer|for promotion|promot|'
    r'admission|m\.?phil|ph\.?d|college|university|course|degree|'
    r'school interview|visa interview',
    re.I)


def _is_interview_question(question):
    """Tight interview detector (v9.2).

    v9.1 fired on bare \\binterview\\b and broke H92-C12 ("offer letter ...
    given one interview" — a JOB question). v9.2 fires only on
    interview-centric phrasings and never when the ask is about the
    offer letter / the job itself / a promotion.
    v9.4: also blocked on admission/education interviews (MPhil, PhD,
    college — Naik's procedure is for employment interviews; an
    admission interview is a different domain and routes to v9's
    default)."""
    q = question or ''
    if not re.search(r'\binterview\b', q, re.I):
        return False
    if _INTERVIEW_BLOCKER.search(q):
        return False
    return bool(_INTERVIEW_CORE.search(q))


_ABROAD_JOB = re.compile(
    r'foreign\s+(job|assignment|posting|service|employment)|'
    r'\bjob\b[^.]{0,30}\b(abroad|overseas)\b|'
    r'\b(abroad|overseas)\b[^.]{0,30}\bjob\b|'
    r'work\s+abroad|onsite\s+(job|opportunity|assignment)|'
    r'\bjob\b[^.]{0,30}\bin\s+(a\s+)?foreign\b',
    re.I)

_ABROAD_BLOCKER = re.compile(r'\bvisa\b|\bpassport\b', re.I)


def _is_abroad_job_question(question):
    """Narrow foreign-job detector (v9.4, E4).

    Fires only on explicit foreign-JOB wording ("foreign job", "job
    abroad", "onsite opportunity"...). Never on visa/passport questions
    (separate event) or bare "going abroad" without a job in the ask.
    """
    q = question or ''
    if _ABROAD_BLOCKER.search(q):
        return False
    return bool(_ABROAD_JOB.search(q))


def _flags(question):
    f = _v9_flags(question)
    f['interview'] = _is_interview_question(question)
    q = (question or '').lower()
    f['enormous_wealth'] = bool(re.search(
        r'\ba lot of\b|\bcrore\b|\black?h\b|\bmillion\b|\benormous\b|'
        r'\bhuge\b|\bhandsome\b', q))
    return f


# ---------------------------------------------------------------------------
# Cherry-picked procedures (C1, C2) — from v9.1, shadow calls removed
# ---------------------------------------------------------------------------

def _second_marriage_procedure(reading, router_out, trace, modifiers, denial):
    """Second marriage: 2nd CSL is the DECIDER vs {2,7,11} strict bar
    (KSK Reader IV p.149); Bosmia OR-branch (7th CSL Mercury/dual + {2,11}
    -> YES); dual test on the 2nd sub-lord, support-only (AS Part 1 p.130).
    Cherry-pick C1: measured net +2 (fixed W103, W106, B3-004; broke W104 —
    the keep_not_marriage branch, kept: KSK p.149 supports it)."""
    cusp7 = _rotated(7, router_out)
    cusp2 = _rotated(2, router_out)
    sub7, agent7, chain7, note7 = _csl_chain_7level(cusp7, reading)
    sub2, agent2, chain2, note2 = _csl_chain_7level(cusp2, reading)
    S2711 = _R({2, 7, 11}, router_out)
    r2, r7, r11 = (_rotated(2, router_out), _rotated(7, router_out),
                   _rotated(11, router_out))
    s2 = sorted(chain2 & S2711)
    d2 = sorted(chain2 & set(denial))
    trace.append({'rule': 'second_marriage_2nd_primary',
                  'citation': CIT['second_marriage'],
                  'detail': '2nd CSL %s (agent %s) chain %s -> 2/7/11 hit %s, '
                            'denial hit %s; 7th CSL %s (agent %s) chain %s'
                            % (sub2, agent2, sorted(chain2), s2, d2, sub7,
                               agent7, sorted(chain7))})
    dual2, dual2_why = _dual_test(sub2, reading)
    trace.append({'rule': 'dual_test_support_only',
                  'citation': CIT['second_marriage'],
                  'detail': 'dual test on 2nd sub-lord: %s (%s) — positive '
                            'support only, never a gate' % (dual2, dual2_why)})
    if dual2:
        modifiers.append('DUAL_SIGN_SUPPORT')
    dual7, dual7_why = _dual_test(sub7, reading)
    or_hit = sorted(chain7 & _R({2, 11}, router_out))
    if dual7 and or_hit:
        verdict = 'YES'
        trace.append({'rule': 'second_marriage_bosmia_or_branch',
                      'citation': CIT['second_marriage'],
                      'detail': '7th CSL %s dual/Mercury (%s) + signifies '
                                '%s -> YES (Bosmia Ex.111 hint, positive '
                                'only)' % (sub7, dual7_why, or_hit)})
        modifiers.append('BOSMIA_OR_BRANCH')
    elif (r11 in chain2) and (r7 not in chain2) and (r2 not in chain2):
        # Round-3: this branch fired on exactly 1 case (C155-W104) and got
        # it WRONG. Book-cited (KSK p.149) but data-unsupported as a hard
        # NO. Doctrine call (overrulable): soften to OTHER (caution, not
        # a confident denial). The main P4 win (2nd-CSL decider) is
        # unaffected.
        verdict = 'OTHER'
        trace.append({'rule': 'keep_not_marriage_softened',
                      'citation': CIT['second_marriage'],
                      'detail': '2nd CSL -> 11 only (no 7, no 2): book '
                                'denial shape (KSK p.149), but fired 0/1 in '
                                'data -> OTHER (caution, not NO)'})
        modifiers.append('KEEP_NOT_MARRIAGE_SHAPE')
    else:
        verdict, reason = _binary_verdict_d1(s2, d2, trace, modifiers,
                                           'second_marriage',
                                           levels=_chain_levels(_levels_planet(sub2, agent2), reading) if agent2 else None)
    _delay_decor(reading, S2711, verdict, trace, modifiers)
    _moon_diagnostic(reading, S2711, trace, modifiers)
    return verdict, modifiers, trace, s2, d2


def _money_gain_procedure(reading, router_out, trace, modifiers, flags):
    """2nd-CSL money procedure (Bosmia true p.73 / PDF p.74) + enormous-wealth
    qualifier test (Bosmia pp.85-86).

    M2 (v9.6): ordinary branch is a gradation -- full 2-6-11 (clean) ->
    YES; full but mixed -> YES+DELAYS; partial hits -> PARTIAL ("some
    wealth"); none -> OTHER (never NO). The old any-of test was falsified
    by Bosmia's own worked case (2+6 without 11 -> "does not indicate
    good financial position", Ex.13).
    Cherry-pick C2: money 65.5% -> 90.0% measured (v9.4, any-of bar)."""
    cusp2 = _rotated(2, router_out)
    sub2, agent2, chain2, note2 = _csl_chain(cusp2, reading)
    S2611 = _R({2, 6, 11}, router_out)
    if flags['enormous_wealth']:
        BIG = _R({2, 6, 10, 11}, router_out)
        NOV = _R({5, 8, 12}, router_out)
        s_big = sorted(chain2 & BIG)
        d_big = sorted(chain2 & NOV)
        trace.append({'rule': 'money_gain_enormous_test',
                      'citation': CIT['money_gain'],
                      'detail': 'enormous-wealth qualifier: 2nd CSL %s (agent '
                                '%s) chain %s -> 2-6-10-11 hit %s, 5-8-12 '
                                'hit %s' % (sub2, agent2, sorted(chain2),
                                            s_big, d_big)})
        if set(s_big) == BIG and not d_big:
            verdict = 'YES'
            trace.append({'rule': 'enormous_wealth_promised',
                          'citation': CIT['money_gain'],
                          'detail': '2nd signifies 2-6-10-11 clean of 5-8-12 '
                                    '-> enormous wealth promised (Bosmia '
                                    'Ex.18, verified)'})
        elif d_big and not s_big:
            verdict = 'NO'
            trace.append({'rule': 'no_wealth_denial',
                          'citation': CIT['money_gain'],
                          'detail': '2nd signifies 5-8-12 with no 2-6-10-11 '
                                    '-> "no wealth" (denial-form; Bosmia '
                                    'Ex.18)'})
        else:
            verdict = 'OTHER'
            trace.append({'rule': 'wealth_gradation_unclear',
                          'citation': CIT['money_gain'],
                          'detail': 'partial wealth testimony — the asked '
                                    'enormous amount is not promised; '
                                    'positive-only test -> OTHER, never NO'})
        s_hit, d_hit = s_big, d_big
    else:
        s2 = sorted(chain2 & S2611)
        d2 = sorted(chain2 & _R({5, 8, 12}, router_out))
        trace.append({'rule': 'money_gain_2nd_csl',
                      'citation': CIT['money_gain'],
                      'detail': '2nd CSL %s (agent %s) chain %s -> 2-6-11 '
                                'hit %s, 5-8-12 hit %s'
                                % (sub2, agent2, sorted(chain2), s2, d2)})
        # v10 (user ruling 2026-10-05, money ablation): partial hits ->
        # YES+DELAYS (not PARTIAL). The ablation showed partial house hits
        # still yield full outcomes (M3 + 3 new cases); "promise is binary,
        # delays decorate." PARTIAL reserved for book-explicit partials.
        if set(s2) == S2611:
            verdict, reason = _binary_verdict_d1(s2, d2, trace, modifiers,
                                                 'money_gain',
                                                 levels=_chain_levels(_levels_planet(sub2, agent2), reading) if agent2 else None)
        elif s2:
            verdict = 'YES'
            if 'DELAYS' not in modifiers:
                modifiers.append('DELAYS')
            trace.append({'rule': 'money_gain_partial',
                          'citation': CIT['money_gain'],
                          'detail': '2nd CSL signifies only %s of 2-6-11 -> '
                                    'promise present, delayed (v10: partial '
                                    'hits -> YES+DELAYS, not PARTIAL; Bosmia '
                                    'Ex.13)' % s2})
        else:
            # 2026-10-14 (Gemini 4 audit): pure denial with zero success hits
            # is a NO, not OTHER. "Will I get my bonus?" with 2nd CSL -> pure
            # 5,8,12 deserves a straight NO.
            if d2 and not s2:
                # Strong denial (2+ hits or L1/L2) -> NO; weak single hit -> OTHER
                _lv2 = _chain_levels(_levels_planet(sub2, agent2), reading) if agent2 else {}
                _strong = any(LEVEL_WEIGHTS.get(lv, 0) >= 0.75
                              for lv, hs in _lv2.items()
                              for h in d2 if h in hs)
                if len(d2) >= 2 or _strong:
                    verdict = 'NO'
                    trace.append({'rule': 'money_gain_denied',
                                  'citation': '2026-10-14 Gemini 4 audit',
                                  'detail': '2nd CSL signifies %s (denial) with '
                                            'zero 2-6-11 -> NO' % d2})
                else:
                    verdict = 'OTHER'
                    trace.append({'rule': 'money_gain_not_promised',
                                  'citation': CIT['money_gain'],
                                  'detail': '2nd CSL signifies none of 2-6-11, '
                                            'only weak %s -> OTHER' % d2})
            else:
                verdict = 'OTHER'
                trace.append({'rule': 'money_gain_not_promised',
                              'citation': CIT['money_gain'],
                              'detail': '2nd CSL signifies none of 2-6-11 -> no '
                                        'promise; positive-only test -> OTHER '
                                        '(never NO)'})
        s_hit, d_hit = s2, d2
    _eleventh_check(reading, router_out, S2611, trace, modifiers)
    _delay_decor(reading, S2611, verdict, trace, modifiers)
    _moon_diagnostic(reading, S2611, trace, modifiers)
    return verdict, modifiers, trace, s_hit, d_hit


# ---------------------------------------------------------------------------
# Career deep module (C5–C11)
# ---------------------------------------------------------------------------

def _promotion_procedure(reading, router_out, trace, modifiers, success, denial):
    """Promotion: 11th CSL -> 2/6/10/11 (Bosmia Ex.11 p.102).

    v10 (user ruling 2026-10-05, career ablation ca17): YES requires 6 AND
    10 both in the chain (Shanmugam Part 1 p.198). The old any-of bar fired
    YES on 6-alone or 10-alone.

    D2 (v9.3): the book gives no denial array, but the user's mixed->YES+
    DELAYS ruling needs a denial set to detect "mixed". Use the event's
    standard denial houses [1,5,9] (frozen router tables) on the 11th CSL
    chain. Mixed -> YES + DELAYS per the ruling; clean denial -> NO.
    """
    cusp11 = _rotated(11, router_out)
    sub11, agent11, chain11, note11 = _csl_chain(cusp11, reading)
    S = _R({2, 6, 10, 11}, router_out)
    D = _R({1, 5, 9}, router_out)
    s11 = sorted(chain11 & S)
    d11 = sorted(chain11 & D)
    has_6_10 = _rotated(6, router_out) in chain11 and _rotated(10, router_out) in chain11
    trace.append({'rule': 'promotion_11th_csl',
                  'citation': CIT['promotion_11th'],
                  'detail': '11th CSL %s (agent %s) chain %s -> 2-6-10-11 '
                            'hit %s, denial [1,5,9] hit %s; 6+10 both=%s '
                            '(v10 ca17: Shanmugam requires 6 AND 10)'
                            % (sub11, agent11, sorted(chain11), s11, d11,
                               has_6_10)})
    if not has_6_10:
        # 6+10 not both present -> v9's default binary, not OTHER
        # (avoids hard-NO; ablation ca17: 4 fixed, 3 breaks)
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    verdict, reason = _binary_verdict_d1(s11, d11, trace, modifiers,
                                         'promotion',
                                         levels=_chain_levels(_levels_planet(sub11, agent11), reading) if agent11 else None)
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(cusp11, reading)
        _career_floor_shadow([('11th CSL', levels)], S, verdict, trace,
                             modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s11, []


# 2026-10-15 (Claude review A7): geographic anchors for place-change
# detection. Bare 'job in '/'job at ' substrings used to misroute
# "job at TCS" (a company) and "job in a bank" (a sector) to the transfer
# procedure. 'job in X' / 'job at X' now only count when X is geographic.
_GEO_ANCHORS = frozenset((
    'abroad', 'foreign', 'overseas',
    'delhi', 'mumbai', 'bombay', 'bangalore', 'bengaluru', 'chennai',
    'madras', 'kolkata', 'calcutta', 'hyderabad', 'pune', 'ahmedabad',
    'jaipur', 'surat', 'lucknow', 'kanpur', 'nagpur', 'indore', 'thane',
    'bhopal', 'patna', 'ludhiana', 'agra', 'nashik', 'faridabad',
    'meerut', 'rajkot', 'varanasi', 'srinagar', 'aurangabad', 'amritsar',
    'prayagraj', 'ranchi', 'howrah', 'coimbatore', 'jabalpur', 'gwalior',
    'vijayawada', 'jodhpur', 'madurai', 'raipur', 'kota', 'guwahati',
    'chandigarh', 'solapur', 'mysuru', 'mysore', 'gurugram', 'gurgaon',
    'noida', 'dehradun', 'shimla', 'bhubaneswar', 'trivandrum', 'kochi',
    'london', 'america', 'canada', 'australia', 'germany', 'dubai',
    'singapore', 'europe', 'uk', 'usa',
))


def _place_change_hit(question):
    """True when the question is really about a change of place.

    'job elsewhere' / 'change of place' / 'relocate' / 'transfer to' are
    unambiguous. 'job in X' / 'job at X' only count when X is a geographic
    anchor — 'job at TCS' (company) and 'job in a bank' (sector) are NOT
    transfers and stay on the job-getting path.
    """
    q_low = (question or '').lower()
    if any(kw in q_low for kw in (
            'job elsewhere', 'change of place', 'relocate',
            'transfer to ', 'posting to ', 'north india', 'south india',
            'east india', 'west india')):
        return True
    m = re.search(r'job\s+(?:in|at)\s+([a-z]+)', q_low)
    return bool(m and m.group(1) in _GEO_ANCHORS)


def _transfer_procedure(reading, router_out, trace, modifiers, success, denial):
    """Transfer: 10th CSL, 2-of-3 from {3,9,12} (KSK Reader III true p.390;
    Bhatnagar p.181) OR 2-of-3 from {3,10,12} (Shanmugam Part 5 true
    pp.36-37; ezine master table true p.476 accepts both schools).
    D4 (v9.3): the Shanmugam {3,10,12} variant was a GAP — added.

    PLACE-CHANGE (2026-10-06, W25/Bosmia Ex.27): "job in <place>" questions
    use the 3rd CSL (change of residence) with 3-12+10, not the 10th CSL.
    """
    # Check for place-change phrasing via the shared geographic-anchor
    # helper (2026-10-15: bare 'job in '/'job at ' was too greedy).
    is_place_change = _place_change_hit(router_out.get('question'))
    if is_place_change:
        # Bosmia Ex.27: 3rd CSL must signify 3-12 with 10
        cusp3 = _rotated(3, router_out)
        sub3, agent3, chain3, _ = _csl_chain(cusp3, reading)
        S = _R({3, 12}, router_out)
        T = _R({10}, router_out)
        hit_s = sorted(chain3 & S)
        hit_t = sorted(chain3 & T)
        trace.append({'rule': 'transfer_3rd_csl_place_change',
                      'citation': 'Bosmia Ex.27: 3rd CSL -> 3-12 with 10',
                      'detail': '3rd CSL %s -> [3,12] hit %s, [10] hit %s'
                                % (sub3, hit_s, hit_t)})
        if hit_s and hit_t:
            trace.append({'rule': 'transfer_place_change_yes',
                          'citation': 'Bosmia Ex.27',
                          'detail': '3rd CSL signifies 3-12 with 10 -> '
                                    'place change promised -> YES'})
            return 'YES', modifiers, trace, hit_s + hit_t, []
        else:
            trace.append({'rule': 'transfer_place_change_no',
                          'citation': 'Bosmia Ex.27: "3rd sub lord does not '
                                      'signify 3 or 12 so no chance"',
                          'detail': '3rd CSL lacks 3-12+10 -> no place '
                                    'change -> NO'})
            return 'NO', modifiers, trace, hit_s, []
    cusp10 = _rotated(10, router_out)
    sub10, agent10, chain10, note10 = _csl_chain(cusp10, reading)
    S1 = _R({3, 9, 12}, router_out)
    S2 = _R({3, 10, 12}, router_out)
    hit1 = sorted(chain10 & S1)
    hit2 = sorted(chain10 & S2)
    trace.append({'rule': 'transfer_10th_csl',
                  'citation': CIT['transfer'],
                  'detail': '10th CSL %s (agent %s) chain %s -> 3/9/12 hit '
                            '%s; 3/10/12 hit %s'
                            % (sub10, agent10, sorted(chain10), hit1, hit2)})
    if len(hit1) >= 2:
        verdict = 'YES'
        trace.append({'rule': 'transfer_2of3',
                      'citation': CIT['transfer'],
                      'detail': '2+ of {3,9,12} signified -> transfer '
                                'promised (Bhatnagar: "either two or all '
                                'the three houses")'})
        hit = hit1
    elif len(hit2) >= 2:
        verdict = 'YES'
        trace.append({'rule': 'transfer_2of3_shanmugam',
                      'citation': 'Shanmugam Astro Secrets Part 5 true '
                                  'pp.36-37; ezine master table true p.476',
                      'detail': '2+ of {3,10,12} signified -> transfer '
                                'promised (Shanmugam school variant)'})
        hit = hit2
    else:
        # book silent -> v9's default binary (round-1: v9 right on 7/9 silent
        # transfer cases; OTHER throws that away)
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(cusp10, reading)
        _career_floor_shadow([('10th CSL', levels)], S1 | S2, verdict, trace,
                             modifiers)
    _eleventh_check(reading, router_out, S1 | S2, trace, modifiers)
    _delay_decor(reading, S1 | S2, verdict, trace, modifiers)
    _moon_diagnostic(reading, S1 | S2, trace, modifiers)
    return verdict, modifiers, trace, hit, []


def _business_start_procedure(reading, router_out, trace, modifiers, success, denial):
    """Independent business: v10 (user ruling 2026-10-05, career ablation ca16):
    7th CSL -> 6 AND 11 (KSK Reader VI p.331). The old 10th-CSL {2,7,10}
    any-of bar is directly contradicted by KSK's own rule. Both 6 and 11
    required for YES; else v9's default binary (not a hard NO)."""
    cusp7 = _rotated(7, router_out)
    sub7, agent7, chain7, _ = _csl_chain(cusp7, reading)
    S611 = _R({6, 11}, router_out)
    s611 = sorted(chain7 & S611)
    trace.append({'rule': 'business_start_procedure',
                  'citation': 'KSK Reader VI p.331 (7th CSL -> 6+11)',
                  'detail': '7th CSL %s (agent %s) chain %s -> 6/11 hit %s'
                            % (sub7, agent7, sorted(chain7), s611)})
    verdict = 'YES' if set(s611) == S611 else None
    if verdict is None:
        # 6+11 not both present -> v9's default binary, not OTHER
        # (avoids hard-NO on true YESes; ablation ca16: 3 fixed, 1 break)
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(cusp7, reading)
        _career_floor_shadow([('7th CSL', levels)], S611, verdict, trace,
                             modifiers)
    _eleventh_check(reading, router_out, S611, trace, modifiers)
    _delay_decor(reading, S611, verdict, trace, modifiers)
    _moon_diagnostic(reading, S611, trace, modifiers)
    return verdict, modifiers, trace, s611, []


def _business_profit_procedure(reading, router_out, trace, modifiers, success, denial):
    """Gain in business: 7th CSL -> joint combos all containing 7
    (ezine master table true p.476: 7,11 / 7,2 / 10,7,2 / 7,10,11
    "operating jointly, not separately each alone").

    D7 (v9.3): the bot's {2,10,11}-any-hit dropped 7; every book combo
    includes 7 (the self-as-businessman). New test: 7th CSL chain must
    contain 7 AND at least one of {2,10,11}."""
    cusp7 = _rotated(7, router_out)
    sub7, agent7, chain7, _ = _csl_chain(cusp7, reading)
    S = _R({2, 7, 10, 11}, router_out)
    s = sorted(chain7 & S)
    has7 = _rotated(7, router_out) in chain7
    has_gain = bool(chain7 & _R({2, 10, 11}, router_out))
    trace.append({'rule': 'business_profit_procedure',
                  'citation': 'ezine master table true p.476 (7,11 / 7,2 / '
                              '10,7,2 / 7,10,11 operating jointly)',
                  'detail': '7th CSL %s (agent %s) chain %s -> 2/7/10/11 '
                            'hit %s; 7 present=%s, gain-house present=%s'
                            % (sub7, agent7, sorted(chain7), s, has7,
                               has_gain)})
    verdict = 'YES' if (has7 and has_gain) else None
    if verdict is None:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(cusp7, reading)
        _career_floor_shadow([('7th CSL', levels)], S, verdict, trace,
                             modifiers)
    _eleventh_check(reading, router_out, S, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, []


def _business_loss_procedure(reading, router_out, trace, modifiers, success,
                           denial):
    """D5 (v9.3): Business loss / "will the business recover?". NEW — the bot
    had no dedicated procedure (C155-W91 was a FP through the generic path).

    Ezine master table (true p.476): 7th CSL -> 5,8,12 = loss in business
    (5,8,12 are 11,2,6 for the opponent = opponent gains). Subramaniam Vol 5
    (true p.299): "10th in the sub of 5 and 12: Heavy Business Loss".
    Deciding-cusp disagreement (7th vs 10th) is flagged; both are checked,
    5+12 is the agreed loss core. Doctrine call (overrulable): loss pattern
    clean (5+12 present, no 2/10/11 rescue) -> NO; gain pattern without loss
    core -> YES; mixed -> YES + DELAYS per the ruling."""
    cusp7 = _rotated(7, router_out)
    cusp10 = _rotated(10, router_out)
    sub7, agent7, chain7, _ = _csl_chain(cusp7, reading)
    sub10, agent10, chain10, _ = _csl_chain(cusp10, reading)
    LOSS = _R({5, 8, 12}, router_out)
    GAIN = _R({2, 10, 11}, router_out)
    loss7 = sorted(chain7 & LOSS)
    gain7 = sorted(chain7 & GAIN)
    loss10 = sorted(chain10 & _R({5, 12}, router_out))
    trace.append({'rule': 'business_loss_procedure',
                  'citation': 'ezine master table true p.476 (7th CSL -> '
                              '5,8,12); Subramaniam Vol 5 true p.299 (10th '
                              'sub -> 5,12 = Heavy Business Loss)',
                  'detail': '7th CSL %s chain %s -> loss %s, gain %s; 10th '
                            'CSL %s chain %s -> 5/12 hit %s'
                            % (sub7, sorted(chain7), loss7, gain7,
                               sub10, sorted(chain10), loss10)})
    # 2026-10-15 (review 1.6): loss7/loss10 hold ROTATED houses (hits against
    # _R-rotated sets); the 5+12 membership test must be rotated too.
    _LOSS_5_12 = _R({5, 12}, router_out)
    has_loss = set(loss7) >= _LOSS_5_12 or set(loss10) >= _LOSS_5_12
    has_gain = bool(gain7)
    if has_loss and not has_gain:
        verdict = 'NO'
        trace.append({'rule': 'business_loss_confirmed',
                      'citation': 'ezine master table true p.476',
                      'detail': 'loss pattern 5+12 clean, no 2/10/11 rescue '
                                '-> NO (no recovery)'})
    elif has_gain and not has_loss:
        verdict = 'YES'
        trace.append({'rule': 'business_loss_gain_present',
                      'citation': 'ezine master table true p.476',
                      'detail': 'gain pattern %s without loss core -> YES '
                                '(recovery promised)' % gain7})
    elif has_loss and has_gain:
        verdict = 'YES'
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        trace.append({'rule': 'business_loss_mixed',
                      'citation': CIT['mixed_delays_flag'],
                      'detail': 'loss %s + gain %s mixed -> YES + DELAYS per '
                                'the ruling' % (loss7, gain7)})
    else:
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _delay_decor(reading, GAIN, verdict, trace, modifiers)
    _moon_diagnostic(reading, GAIN, trace, modifiers)
    return verdict, modifiers, trace, gain7, loss7


def _dismissal_procedure(reading, router_out, trace, modifiers, success, denial):
    """Dismissal: [1,5,9,12] on the 2nd/6th/10th CSL.

    2026-10-14 (3-AI adjudication, USER RULING): the 8 is OUT. Bosmia
    Prashna Jyotish: retirement/dismissal = 1,5,9,12; Taneja: suspension =
    5,8,12 combination. The v10 note's "full 1-5-8-9-12 array" conflated
    dismissal with suspension -- the 8 belongs to the separate
    suspension_from_service event, never standalone dismissal.

    D9 (v9.3): denial array corrected to 1/5/9/12 — KSK Reader VI (true
    pp.310, 317) and K.P. Sub Lord and the Principle (true pp.21, 26) are
    unanimous (reinstatement denial = 1/5/9/12, "and not 2/6/10"). The 8
    belongs to Taneja's suspension/loss combination (5,8,12, true p.107),
    a different question.

    D6 (v9.3): Sharad Joshi splits SUSPENSION-WITH-REINSTATEMENT from
    DISMISSAL — 10th SL with 5,9 *plus 6,11* = suspended but reinstated
    with full benefits; with 5,9,12 (no 6,11 rescue) = dismissal. The
    6+11 alongside 5+9 is the rescue signal. For "will I be dismissed?":
    rescue pattern -> NO + SUSPENSION_LIKELY modifier; clean dismissal
    pattern -> YES."""
    # 2026-10-14 (3-AI adjudication, book-verified): 8 REMOVED from the
    # dismissal set. Bosmia Prashna Jyotish: retirement/dismissal = 1,5,9,12;
    # Taneja: suspension = 5,8,12 combination. The 8 belongs to suspension
    # (separate event), never standalone dismissal. Flat removal (not gated):
    # no book describes a conditional-8 mechanic.
    D = _R({1, 5, 9, 12}, router_out)
    RESCUE = _R({6, 11}, router_out)
    s_union = set()
    rescue_union = set()
    deciders = []
    parts = []
    for c in (2, 6, 10):
        rc = _rotated(c, router_out)
        sub, agent, chain, _ = _csl_chain(rc, reading)
        _, _, levels, _ = _csl_chain_levels(rc, reading)
        hit = sorted(chain & D)
        resc = sorted(chain & RESCUE)
        s_union |= set(hit)
        rescue_union |= set(resc)
        deciders.append(('%d%s CSL' % (c, '' if rc == c else '->%d' % rc),
                         levels))
        parts.append('%dth CSL %s (agent %s) -> dismissal %s, rescue %s'
                     % (c, sub, agent, hit, resc))
    s_union = sorted(s_union)
    rescue_union = sorted(rescue_union)
    trace.append({'rule': 'dismissal_procedure',
                  'citation': CIT['dismissal'],
                  'detail': '2nd/6th/10th CSLs vs [1,5,9,12]: '
                            + '; '.join(parts)})
    # 2026-10-15 (Claude review A2/A3): s_union and rescue_union hold ROTATED
    # houses (hits against the _R-rotated D/RESCUE sets). Every literal below
    # is therefore rotated too — native literals misjudge third-party
    # (turned) questions, e.g. dismissal could never be YES for "will my
    # husband be dismissed?". A2: the suspension test is additionally guarded
    # against empty s_union (an empty set is a subset of everything, which
    # used to yield a spurious NO + SUSPENSION_LIKELY).
    # NOTE: the suspension exclusion stays {5}-only (ca19, W69): Bosmia
    # Ex.75 — 1/8/9/12 without a clean 5 is suspension, not dismissal. The 9
    # belongs to the suspension set; only the 5 excludes it.
    CORE = _R({5, 9}, router_out)
    HARD = _R({8, 12}, router_out)
    SUSP = _R({1, 8, 9, 12}, router_out)
    CLEAN5 = _R({5}, router_out)
    has_dismissal_core = bool(set(s_union) & CORE)
    has_hard_loss = bool(set(s_union) & HARD)
    has_rescue = bool(rescue_union)
    # ca19: check suspension pattern FIRST (2026-10-06 fix). The [1,8,9,12]
    # suspension pattern contains 9, so has_dismissal_core would fire first
    # and give YES. But Bosmia Ex.75 says 1-alone (even with 8/9/12) is not
    # dismissal — needs clean 5/9 without the suspension markers.
    is_suspension_pattern = (bool(s_union) and set(s_union) <= SUSP
                             and not (set(s_union) & CLEAN5))
    if is_suspension_pattern:
        # ca19: {1,8,9,12} without 5 = suspension, not dismissal -> NO
        verdict = 'NO'
        trace.append({'rule': 'suspension_not_dismissal',
                      'citation': 'Bosmia Ex.75 (1 alone != dismissal; needs '
                                  '5-9); Sharad Joshi p.87; ca19',
                      'detail': 'suspension pattern %s (1,8,9,12 without 5) '
                                '-> not dismissal -> NO + SUSPENSION_LIKELY'
                                % s_union})
        modifiers.append('SUSPENSION_LIKELY')
        _career_floor_shadow(deciders, D, verdict, trace, modifiers)
    elif has_dismissal_core and has_rescue and not has_hard_loss:
        # D6 (v9.3, REVISED round-1): Joshi's suspension-with-reinstatement
        # pattern. Originally flipped to NO; round-1 testing showed this
        # breaks "losing job / change of job" questions (C155-W70: the
        # 5,9+6,11 pattern means job CHANGE, not "nothing happens").
        # Revised: keep YES (the disruption IS indicated) + SUSPENSION_LIKELY
        # modifier distinguishing it from permanent dismissal. The NO-flip
        # is staged for the user's adjudication on pure "will I be
        # dismissed?" wording.
        verdict = 'YES'
        trace.append({'rule': 'suspension_with_reinstatement',
                      'citation': 'Sharad Joshi Krishnamurthy Padhdhati true '
                                  'p.87 (10th SL with 5,9,6,11 = suspension, '
                                  'reinstated with full benefits)',
                      'detail': 'dismissal houses %s but 6+11 rescue %s '
                                'present, no 8/12 -> suspension with '
                                'reinstatement (not permanent dismissal) -> '
                                'YES + SUSPENSION_LIKELY'
                                % (s_union, rescue_union)})
        modifiers.append('SUSPENSION_LIKELY')
        _career_floor_shadow(deciders, D, verdict, trace, modifiers)
    elif has_dismissal_core:
        # ca19 RESTORED (2026-10-06, W69 regression fix): clean dismissal
        # needs 5 or 9 (without suspension pattern, checked above).
        # Bosmia Ex.75: "single indication of 1 alone does not prove
        # negative. 1 is self effort. Gives negative result only when
        # joined by 5-9." Joshi p.87: dismissal needs 5-9.
        verdict = 'YES'
        trace.append({'rule': 'dismissal_indicated',
                      'citation': CIT['dismissal'],
                      'detail': 'dismissal/suspension houses %s signified on '
                                'the 2nd/6th/10th CSLs -> YES' % s_union})
        _career_floor_shadow(deciders, D, verdict, trace, modifiers)
    elif s_union:
        # Any other partial hit -> NO + SUSPENSION_LIKELY (not clean dismissal)
        verdict = 'NO'
        trace.append({'rule': 'suspension_not_dismissal',
                      'citation': 'Bosmia Ex.75; ca19',
                      'detail': 'houses %s lack clean 5/9 dismissal core -> '
                                'NO + SUSPENSION_LIKELY' % s_union})
        modifiers.append('SUSPENSION_LIKELY')
        _career_floor_shadow(deciders, D, verdict, trace, modifiers)
    else:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _delay_decor(reading, D, verdict, trace, modifiers)
    _moon_diagnostic(reading, D, trace, modifiers)
    return verdict, modifiers, trace, s_union, []


def _position_lose_procedure(reading, router_out, trace, modifiers, success,
                             denial):
    """position_lose: "will he lose power?", "will the ruler step down?".

    BOOK (2026-10-06, user ruling): Kanak Bosmia, Easy Way to Learn KP
    Horary Astrology, Ex.124, PDF pp.314-315: "If 8th Sublord... signifies
    5 (12th from 6th), 9th (12th from 10), 12th (loss), ruler faces trouble
    and end of his govt."
    Deciding cusp: 8th. Success (YES = loses position): {5,9,12}.
    Verdict YES = the person loses power/position.
    Book silent -> v9's default binary."""
    rc = _rotated(8, router_out)
    sub, agent, chain, _ = _csl_chain(rc, reading)
    S = _R({5, 9, 12}, router_out)
    s = sorted(chain & S)
    d = sorted(chain & _R(set(denial) if denial else {2, 6, 10, 11},
                          router_out))
    trace.append({'rule': 'position_lose_8th',
                  'citation': 'Bosmia Ex.124, pp.314-315',
                  'detail': '8th CSL %s (agent %s) -> 5/9/12 hit %s, denial %s'
                            % (sub, agent, s, d)})
    verdict, _ = _binary_verdict_d1(s, d, trace, modifiers,
                                    'position_lose', S,
                                    levels=_chain_levels(_levels_planet(sub, agent), reading) if agent else None)
    return verdict, modifiers, trace, s, d


def _reinstatement_procedure(reading, router_out, trace, modifiers,
                             success, denial):
    """E2 (v9.4): Reinstatement / regaining position ("will I be reinstated?",
    "will I get my position back?").

    KSK Reader VI (true pp.309-310), horary on reappointment: "Note the
    lord of the constellation in which the sub-lord of the 10th cusp is
    deposited — if that lord of the constellation is also the significator
    of the houses 2 or 6 or 10 he must be reinstated. But if the sub-lord
    is deposited in a constellation the lord of which is the significator
    of 1 or 5 or 9 or 12 and at the same time not a significator of 2 or
    6 or 10 he will never be reinstated. The meridian decides. The
    sub-lord of the 10th decides."
    Bosmia Easy Way Ex.87 (true p.234): 6th/10th CSL -> 2-6-10-11 AND NOT
    1-5-9 = reinstated (second book form, checked alongside).
    Part 5 (true p.189): 10th CSL -> 2,6,10 = regain position (full-chain
    form of the same test).
    KSK Reader VI (true p.317), re-appointment: judge the 6th cusp —
    6th CSL -> 6/10/2 = yes; -> 1/5/9/12 = no (third book form).
    Book silent -> v9's default binary, never invented denial."""
    cusp10 = _rotated(10, router_out)
    sub10, agent10, chain10, _ = _csl_chain(cusp10, reading)
    _, _, levels, _ = _csl_chain_levels(cusp10, reading)
    star_level = levels.get('L1', set()) | levels.get('L3', set())
    S2610 = _R({2, 6, 10}, router_out)
    D15912 = _R({1, 5, 9, 12}, router_out)
    s_star = sorted(star_level & S2610)
    d_star = sorted(star_level & D15912)
    s_full = sorted(chain10 & S2610)
    # Bosmia Ex.87 form: 6th/10th CSL -> 2-6-10-11 clean of 1,5,9
    ex87_hit = []
    for c in (6, 10):
        rc = _rotated(c, router_out)
        _, _, ch, _ = _csl_chain(rc, reading)
        s87 = sorted(ch & _R({2, 6, 10, 11}, router_out))
        d87 = sorted(ch & _R({1, 5, 9}, router_out))
        if s87 and not d87:
            ex87_hit.append(c)
    # KSK p.317 form: judge the 6th cusp — 6th CSL -> 6/10/2 = yes;
    # -> 1/5/9/12 = no
    cusp6 = _rotated(6, router_out)
    sub6, agent6, chain6, _ = _csl_chain(cusp6, reading)
    s6 = sorted(chain6 & _R({6, 10, 2}, router_out))
    d6 = sorted(chain6 & D15912)
    trace.append({'rule': 'reinstatement_procedure',
                  'citation': CIT['reinstatement'],
                  'detail': '10th CSL %s (agent %s): star-level (L1/L3) %s '
                            '-> 2/6/10 hit %s, 1/5/9/12 hit %s; full chain '
                            '-> 2/6/10 hit %s; Ex.87 6th/10th clean form: %s; '
                            'KSK-p317 6th CSL %s -> 6/10/2 hit %s, 1/5/9/12 '
                            'hit %s'
                            % (sub10, agent10, sorted(star_level), s_star,
                               d_star, s_full, ex87_hit, sub6, s6, d6)})
    if s_star:
        verdict = 'YES'
        trace.append({'rule': 'reinstatement_promised',
                      'citation': CIT['reinstatement'],
                      'detail': '10th CSL star-lord signifies 2/6/10 -> '
                                'reinstated (KSK: "he must be reinstated")'})
    elif d_star and not s_full:
        verdict = 'NO'
        trace.append({'rule': 'reinstatement_never',
                      'citation': CIT['reinstatement'],
                      'detail': '10th CSL star-lord -> 1/5/9/12 and NOT '
                                '2/6/10 -> never reinstated (KSK)'})
    elif s6:
        verdict = 'YES'
        trace.append({'rule': 'reinstatement_ksk317_6th',
                      'citation': CIT['reinstatement'],
                      'detail': '6th CSL %s -> 6/10/2 %s -> reinstated (KSK '
                                'VI true p.317)' % (sub6, s6)})
    elif d6 and not (s_full or ex87_hit):
        verdict = 'NO'
        trace.append({'rule': 'reinstatement_ksk317_6th_denial',
                      'citation': CIT['reinstatement'],
                      'detail': '6th CSL %s -> 1/5/9/12 %s, no 2/6/10 form '
                                '-> not reinstated (KSK VI true p.317)'
                                % (sub6, d6)})
    elif ex87_hit:
        verdict = 'YES'
        trace.append({'rule': 'reinstatement_ex87',
                      'citation': CIT['reinstatement'],
                      'detail': '%s CSL -> 2-6-10-11 clean of 1,5,9 -> '
                                'reinstated (Bosmia Ex.87)' % ex87_hit})
    elif s_full:
        verdict = 'YES'
        trace.append({'rule': 'regain_position_full_chain',
                      'citation': CIT['reinstatement'],
                      'detail': '10th CSL full chain -> 2/6/10 %s -> regain '
                                'position (Part 5)' % s_full})
    else:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    if verdict == 'YES':
        _career_floor_shadow([('10th CSL', levels)], S2610, verdict, trace,
                             modifiers)
    _eleventh_check(reading, router_out, S2610, trace, modifiers)
    _delay_decor(reading, S2610, verdict, trace, modifiers)
    _moon_diagnostic(reading, S2610, trace, modifiers)
    return verdict, modifiers, trace, s_star or s_full, d_star


def _retirement_procedure(reading, router_out, trace, modifiers, success,
                          denial):
    """E3 (v9.4): Retirement ("will X retire?", "will I get VRS?").

    BOOK (2026-10-06, user ruling): Astro Secrets & KP Part 5, PDF p.109:
    "Houses 1,5,9 are to be consulted for retirement as these are negative
    houses to 2,6 & 10." S.P. Khullar, True Astrology, true p.597:
    "Voluntary Retirement: 10 / 5,9 (8) / 1,5,9."
    Deciding cusp: 10th. Success: {1,5,9} (12 removed — not in book arrays).
    Verdict YES = retirement happens. Book silent -> v9's default binary."""
    RET = _R({1, 5, 9}, router_out)
    parts = []
    ret_union = set()
    for c in (10,):
        rc = _rotated(c, router_out)
        sub, agent, chain, _ = _csl_chain(rc, reading)
        _, _, levels, _ = _csl_chain_levels(rc, reading)
        star_level = levels.get('L1', set()) | levels.get('L3', set())
        hit = sorted((chain | star_level) & RET)
        ret_union |= set(hit)
        parts.append('%dth CSL %s (agent %s) -> 1/5/9 hit %s'
                     % (c, sub, agent, hit))
    ret_union = sorted(ret_union)
    trace.append({'rule': 'retirement_procedure',
                  'citation': CIT['retirement'],
                  'detail': '10th/6th CSLs vs [1,5,9,12]: ' + '; '.join(parts)})
    if ret_union:
        verdict = 'YES'
        trace.append({'rule': 'retirement_indicated',
                      'citation': CIT['retirement'],
                      'detail': '1/5/9/12 signified %s -> retirement '
                                'happens (Bosmia Ex.18)' % ret_union})
        # Audit row 73 (ezine master table true p.476): 3,9,12 WITHOUT
        # 2,6,10 = giving up the present job = voluntary retirement.
        # Diagnostic modifier only, never verdict-changing.
        giveup = set()
        for c in (10, 6):
            rc = _rotated(c, router_out)
            _, _, ch, _ = _csl_chain(rc, reading)
            if (ch & _R({3, 9, 12}, router_out)) and not \
                    (ch & _R({2, 6, 10}, router_out)):
                giveup.add(c)
        if giveup:
            modifiers.append('VOLUNTARY_GIVING_UP')
            trace.append({'rule': 'voluntary_retirement_note',
                          'citation': 'ezine master table true p.476 (3,9,12 '
                                      'without 2,6,10 = giving up the '
                                      'present job)',
                          'detail': '%s CSL -> 3,9,12 without 2,6,10 -> '
                                    'voluntary giving-up flavour '
                                    '(diagnostic only)' % sorted(giveup)})
    else:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _delay_decor(reading, RET, verdict, trace, modifiers)
    _moon_diagnostic(reading, RET, trace, modifiers)
    return verdict, modifiers, trace, ret_union, []


def _job_abroad_procedure(reading, router_out, trace, modifiers, success,
                          denial):
    """E4 (v9.4): Foreign job / foreign assignment ("will I get a foreign
    job?").

    Bosmia Easy Way Horary Ex.16 (true p.80): 2nd CSL -> 9/12 + 2,6,11 =
    foreign assignment promised. KSK Reader VI (true p.310, horary 98):
    "If any of the significators of going abroad [3,9,12] is a
    significator of 6th house also, then one goes abroad on foreign
    assignment."
    Positive-only test -> YES on pass; silent -> v9's default binary
    (never NO — the book gives no denial form)."""
    cusp2 = _rotated(2, router_out)
    sub2, agent2, chain2, _ = _csl_chain(cusp2, reading)
    ABROAD = _R({9, 12}, router_out)
    EARN = _R({2, 6, 11}, router_out)
    S3912 = _R({3, 9, 12}, router_out)
    r6 = _rotated(6, router_out)
    has_abroad = sorted(chain2 & ABROAD)
    has_earn = sorted(chain2 & EARN)
    # KSK form: any going-abroad significator that also signifies 6th.
    # Approximated on the service cusps (2nd/6th/10th CSL chains).
    ksk_hit = []
    for c in (2, 6, 10):
        rc = _rotated(c, router_out)
        _, _, ch, _ = _csl_chain(rc, reading)
        if (ch & S3912) and (r6 in ch):
            ksk_hit.append(c)
    trace.append({'rule': 'job_abroad_procedure',
                  'citation': CIT['job_abroad'],
                  'detail': '2nd CSL %s (agent %s) chain %s -> 9/12 hit %s, '
                            '2/6/11 hit %s; KSK 3-9-12+6 form on 2/6/10 '
                            'CSLs: %s'
                            % (sub2, agent2, sorted(chain2), has_abroad,
                               has_earn, ksk_hit)})
    if (has_abroad and has_earn) or ksk_hit:
        verdict = 'YES'
        trace.append({'rule': 'foreign_assignment_promised',
                      'citation': CIT['job_abroad'],
                      'detail': 'foreign assignment promised (Bosmia Ex.16 '
                                '2nd-CSL form / KSK 3-9-12+6 form)'})
        _, _, levels, _ = _csl_chain_levels(cusp2, reading)
        _career_floor_shadow([('2nd CSL', levels)], ABROAD | EARN, verdict,
                             trace, modifiers)
    else:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _eleventh_check(reading, router_out, ABROAD | EARN, trace, modifiers)
    _delay_decor(reading, ABROAD | EARN, verdict, trace, modifiers)
    _moon_diagnostic(reading, ABROAD | EARN, trace, modifiers)
    return verdict, modifiers, trace, has_abroad + has_earn, []


def _interview_procedure(reading, router_out, trace, modifiers, success, denial):
    """Interview: 3rd CSL decider (Naik pp.44-45; Bansal p.58; Taneja Ill-10).

    11 AND >=1 of {3,5,6,9,10} -> YES; 12-without-11 -> NO;
    neutral 3rd CSL -> 11th CSL tiebreak.
    """
    cusp3 = _rotated(3, router_out)
    sub3, agent3, chain3, note3 = _csl_chain(cusp3, reading)
    S = _R({3, 5, 6, 9, 10, 11}, router_out)
    r11, r12 = _rotated(11, router_out), _rotated(12, router_out)
    has11 = r11 in chain3
    has_any = bool(chain3 & _R({3, 5, 6, 9, 10}, router_out))
    has12 = r12 in chain3
    trace.append({'rule': 'interview_procedure',
                  'citation': CIT['interview'],
                  'detail': '3rd CSL %s (agent %s); chain %s; 11=%s, '
                            '3/5/6/9/10=%s, 12=%s'
                            % (sub3, agent3, sorted(chain3), has11, has_any,
                               has12)})
    if has11 and has_any:
        verdict = 'YES'
        trace.append({'rule': 'interview_success',
                      'citation': CIT['interview'],
                      'detail': '3rd CSL signifies 11 + one of {3,5,6,9,10} '
                                '-> YES'})
    elif has12 and not has11:
        verdict = 'NO'
        trace.append({'rule': 'interview_loss',
                      'citation': CIT['interview'],
                      'detail': '3rd CSL signifies 12 without 11 -> NO '
                                '(Interview Loss, denial-form)'})
    else:
        cusp11 = _rotated(11, router_out)
        sub11, agent11, chain11, _ = _csl_chain(cusp11, reading)
        trace.append({'rule': 'interview_11th_tiebreak',
                      'citation': CIT['interview'],
                      'detail': 'neutral 3rd CSL -> 11th CSL %s (agent %s) '
                                'decides (Taneja Ill-10)' % (sub11, agent11)})
        # v9.4 round-3: the 11th cannot act alone (Shanmugam AS Part 2 true
        # p.230; audit row 75). A bare 11 on the 11th CSL — with no
        # interview event house {3,5,6,9,10} — is not a book-backed
        # promise. Require 11 + >=1 event house; else v9's default.
        r11_ok = (r11 in chain11) and bool(
            chain11 & _R({3, 5, 6, 9, 10}, router_out))
        if r11_ok:
            verdict = 'YES'
            modifiers.append('ELEVENTH_CSL_TIEBREAK')
            trace.append({'rule': 'interview_tiebreak_11_latched',
                          'citation': 'Shanmugam AS Part 2 true p.230 (11th '
                                      'must latch onto the event houses)',
                          'detail': '11th CSL -> 11 + interview house %s -> '
                                    'YES' % sorted(chain11 & _R(
                                        {3, 5, 6, 9, 10}, router_out))})
        else:
            trace.append({'rule': 'interview_tiebreak_11_bare',
                          'citation': 'Shanmugam AS Part 2 true p.230',
                          'detail': '11th CSL %s chain %s: bare/no 11 '
                                    'without an interview event house -> '
                                    'not a promise; v9 default decides'
                                    % (sub11, sorted(chain11))})
            # 11th CSL silent too -> v9's default binary, not OTHER
            return _v9_default_binary(reading, router_out, success,
                                      denial, trace, modifiers)
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(cusp3, reading)
        _career_floor_shadow([('3rd CSL', levels)], S, verdict, trace,
                             modifiers)
    _eleventh_check(reading, router_out, S, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    s_hit = sorted(chain3 & S)
    d_hit = sorted(chain3 & _R({12}, router_out))
    return verdict, modifiers, trace, s_hit, d_hit


# ---------------------------------------------------------------------------
# L12R new-event procedures (v9.5, 2026-10-03 funnel repair)
#
# One procedure per new Layer-1 event, per l12_repair/layer3_procedures.json
# (schema l12_l3proc/v1). Standing doctrine in every path: mixed evidence ->
# YES with DELAYS (general); the Bosmia exception (11th-CSL decider + mixed
# -> NO, user ruling 2026-10-03) wherever the 11th CSL decides.
# ---------------------------------------------------------------------------

def _job_continuity_procedure(reading, router_out, trace, modifiers, success,
                             denial):
    """Continuity of the CURRENT engagement -- USER RULING 2026-10-04
    ("do what the books say").

    Decider = 6th CSL (service). 6th CSL -> 2,10,11 = YES (permanent/
    continuing): KSK Reader III p.383 (reinstatement = 2-6-10-11
    significators); ezine p.503 (6th sublord -> 2,10,11 = permanent job);
    Bosmia Easy Way Horary Ex.79 true pp.218-219 (6th/10th CSL -> 2-6-10 =
    continue). Denial = 6th CSL chain -> 5,8,12 (affliction/loss of
    service) -- BOOK-ADJACENT INFERENCE from the dismissal family
    [1,5,8,9,12] (Bosmia Ex.79 leave = 1-5-9-12; Joshi dismiss =
    1,5,9,12,8), flagged as such, not direct book.
    REMOVED per the same ruling: the [1,2,4,10,11] "retained" formula
    (K.P. Sub Lord and the Principle true p.19) -- NOT found anywhere in
    the 46-book library -- including the 11th-CSL secondary confirm, which
    would have tripped the Bosmia 11th exception as a decider.
    Mixed -> YES + DELAYS: the decider is the 6th CSL, so the general
    doctrine applies, not the Bosmia 11th exception.
    """
    cusp6 = _rotated(6, router_out)
    sub6, agent6, chain6, _ = _csl_chain(cusp6, reading)
    S = _R({2, 10, 11}, router_out)
    D = _R({5, 8, 12}, router_out)
    s6 = sorted(chain6 & S)
    d6 = sorted(chain6 & D)
    trace.append({'rule': 'job_continuity_6th_csl',
                  'citation': CIT['job_continuity'],
                  'detail': '6th CSL %s (agent %s) chain %s -> [2,10,11] '
                            'hit %s, [5,8,12] hit %s'
                            % (sub6, agent6, sorted(chain6), s6, d6)})
    verdict, reason = _binary_verdict_d1(s6, d6, trace, modifiers,
                                         'job_continuity',
                                         levels=_chain_levels(_levels_planet(sub6, agent6), reading) if agent6 else None)
    if not s6 and not d6:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s6, d6


def _business_partnership_procedure(reading, router_out, trace, modifiers,
                                   success, denial, question):
    """Partnership formation (AS Part 3 true p.54): 7th CSL -> 6+11 = YES
    (can have a partner); 6+12 = NO (partnership breaks); 5+8+12 = NO +
    PARTNER_EXPLOIT_WARN (partner benefits, querent loses).

    Succeed-shapes ("will my partnership business succeed") layer the
    business_profit D7 test (7th CSL -> 7 + >=1 of {2,10,11}) as the profit
    half. No 11th-CSL involvement; general mixed->YES+DELAYS applies.
    """
    cusp7 = _rotated(7, router_out)
    sub7, agent7, chain7, _ = _csl_chain(cusp7, reading)
    S = _R({6, 11}, router_out)
    s_hit = sorted(chain7 & S)
    d_hit = sorted(chain7 & _R({5, 6, 8, 12}, router_out))
    exploit = sorted(chain7 & _R({5, 8, 12}, router_out))
    trace.append({'rule': 'business_partnership_7th_csl',
                  'citation': CIT['business_partnership'],
                  'detail': '7th CSL %s (agent %s) chain %s -> [6,11] hit '
                            '%s, denial hit %s, exploit-grade [5,8,12] hit %s'
                            % (sub7, agent7, sorted(chain7), s_hit, d_hit,
                               exploit)})
    if set(exploit) == _R({5, 8, 12}, router_out):
        verdict = 'NO'
        modifiers.append('PARTNER_EXPLOIT_WARN')
        trace.append({'rule': 'partnership_exploit',
                      'citation': CIT['business_partnership'],
                      'detail': '7th CSL signifies 5+8+12 -> "partner will '
                                'be benefited and you stand to loose much" '
                                '-> NO + PARTNER_EXPLOIT_WARN'})
        s_out, d_out = s_hit, d_hit
    else:
        verdict, reason = _binary_verdict_d1(s_hit, d_hit, trace, modifiers,
                                             'business_partnership',
                                             levels=_chain_levels(_levels_planet(sub7, agent7), reading) if agent7 else None)
        s_out, d_out = s_hit, d_hit
        if not s_hit and not d_hit:
            # book silent -> v9's default binary, not OTHER
            return _v9_default_binary(reading, router_out, success,
                                      denial, trace, modifiers)
    if verdict == 'YES':
        q = (question or '').lower()
        succeed_shape = bool(re.search(
            r'\bsucceed\b|\bsuccess\b|\bsuccessful\b|\bprofit\b|\bgain\b',
            q))
        if succeed_shape:
            has7 = bool(_R({7}, router_out) & chain7)
            has_gain = bool(chain7 & _R({2, 10, 11}, router_out))
            trace.append({'rule': 'partnership_profit_half',
                          'citation': 'ezine master table true p.476 (D7: '
                                      '7,11 / 7,2 / 10,7,2 / 7,10,11 '
                                      'operating jointly)',
                          'detail': 'succeed-shape: profit half = 7th CSL '
                                    '-> 7 present=%s, gain-house {2,10,11} '
                                    'present=%s' % (has7, has_gain)})
            if not (has7 and has_gain):
                verdict = 'OTHER'
                trace.append({'rule': 'partnership_profit_half_fail',
                              'citation': 'ezine master table true p.476',
                              'detail': 'partnership promised but the D7 '
                                        'profit half is silent -> the '
                                        '"succeed" ask is not promised '
                                        '(OTHER)'})
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s_out, d_out


def _exam_appear_procedure(reading, router_out, trace, modifiers, success,
                          denial):
    """KSK Reader VI true p.198: a LAGNA-DEPOSITION test, not a CSL-chain
    test. "If the horary lagna is spoiled due to the deposition of natural
    malefics or lord of 6 or 8 or 12, the native will not be able to make an
    attempt." Clean lagna -> YES. The engine HAS planet-in-bhava data
    (reading['planet_facts'][*]['house_occupied'] / ['owns_houses']), so the
    book test is implemented directly -- no CSL-chain approximation, no
    NEEDS-USER-RULING flag needed for the mechanism itself.

    The 3rd-CSL courage pre-test (Sun/Mars/Jupiter/Venus as 3rd sub-lord in
    the worked example) is diagnostic texture only.
    """
    MALEFICS = {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}
    spoilers = []  # (planet, [lord houses in 6/8/12], is_malefic)
    # 2026-10-15 (review 1.6): the "lagna" here is the SUBJECT's ascendant,
    # and 6/8/12 are relative to the subject — rotate both on turned charts.
    _lagna = _rotated(1, router_out)
    _bad = _R({6, 8, 12}, router_out)
    for f in (reading.get('planet_facts') or []):
        if f.get('house_occupied') != _lagna:
            continue
        p = f.get('planet')
        lord_bad = sorted({h for h in (f.get('owns_houses') or [])
                           if h in _bad})
        if p in MALEFICS or lord_bad:
            spoilers.append((p, lord_bad, p in MALEFICS))
    # 3rd CSL courage pre-test: diagnostic texture, never verdict-changing.
    cusp3 = _rotated(3, router_out)
    sub3, agent3, chain3, _ = _csl_chain(cusp3, reading)
    trace.append({'rule': 'exam_appear_courage',
                  'citation': CIT['exam_appear'],
                  'detail': '3rd CSL %s (agent %s) chain %s = courage / '
                            'confidence to compete (diagnostic texture '
                            'only)' % (sub3, agent3, sorted(chain3))})
    if spoilers:
        verdict = 'NO'
        d_hit = sorted({h for _, lh, _ in spoilers for h in lh})
        for p, lh, mal in spoilers:
            kinds = []
            if mal:
                kinds.append('natural malefic')
            if lh:
                kinds.append('lord of %s' % lh)
            trace.append({'rule': 'exam_appear_lagna_spoiled',
                          'citation': CIT['exam_appear'],
                          'detail': '%s deposited in lagna (%s) -> cannot '
                                    'attempt -> NO' % (p, ' + '.join(kinds))})
        s_hit = []
    else:
        verdict = 'YES'
        trace.append({'rule': 'exam_appear_lagna_clean',
                      'citation': CIT['exam_appear'],
                      'detail': 'no malefic and no 6/8/12-lord deposited in '
                                'lagna -> native can act as he likes -> YES'})
        s_hit, d_hit = [1], []
    # No _delay_decor: the book gives no delay form for appearing (it is
    # appear-or-not). Moon stays diagnostic-only per the standing rule.
    _moon_diagnostic(reading, {1}, trace, modifiers)
    return verdict, modifiers, trace, s_hit, d_hit


def _scholarship_procedure(reading, router_out, trace, modifiers, success,
                          denial):
    """USER RULING 2026-10-04 ("do what the book says"): KSK Reader III
    true pp.278-279 ("Scholarship for study": the 4th having connection
    with the 6th and the 11th indicates scholarship; "scholarship is a
    non-repayable loan... the 6th house is judged for a loan... the 11th
    house indicates benefit, profit, gains"); Astro Secrets & KP Part 2
    true p.265 ("sublord of the 4th cusp should be connected with 6 or 11
    for one to receive scholarship"). 4th CSL -> [6,11] = YES ([2]
    supporting per Naik K.P. Dynamics true p.56: houses 6,2). Books give
    NO denial form -> positive-only test; silent -> v9's default binary,
    never a hard NO. Decider is the 4th CSL, so the Bosmia 11th exception
    does not apply.
    """
    cusp4 = _rotated(4, router_out)
    sub4, agent4, chain4, _ = _csl_chain(cusp4, reading)
    S = _R({6, 11}, router_out)
    s = sorted(chain4 & S)
    s2 = sorted(chain4 & _R({2}, router_out))
    trace.append({'rule': 'scholarship_4th_csl',
                  'citation': CIT['scholarship'],
                  'detail': '4th CSL %s (agent %s) chain %s -> [6,11] hit '
                            '%s, supporting [2] hit %s'
                            % (sub4, agent4, sorted(chain4), s, s2)})
    if not s:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    verdict = 'YES'
    trace.append({'rule': 'scholarship_promised',
                  'citation': CIT['scholarship'],
                  'detail': '4th CSL connected with 6/11 -> scholarship '
                            'receivable -> YES'})
    s_hit = sorted(set(s) | set(s2))
    _eleventh_check(reading, router_out, S, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s_hit, []


def _job_voluntary_exit_procedure(reading, router_out, trace, modifiers,
                                 success, denial):
    """USER RULING 2026-10-04 ("do what the book says"): Bosmia Ex.79 hint
    true pp.218-219, inverted polarity: 10th/6th CSL -> 1-5-9-12 = YES
    (the querent leaves); -> 2-6-10 = NO (stays). Joshi true p.94 ("Leave
    the job" = MH-10, NH-1,5,9 vs "Dismiss" = MH-10, NH-1,5,9,12,8);
    Bosmia Ex.161 true p.397 (10th/6th CSL -> 1-5-9-12 = retire). Mixed ->
    YES + DELAYS (decider is the 10th CSL: general doctrine). Books do NOT
    distinguish quitting-with-nothing-lined-up from changing jobs (the
    library is silent on that distinction) -> the 1-5-9-12 leave-chain is
    used unchanged, documented. Timing is book-backed ("during the joint
    period of the significators of 1-5-9").
    """
    S = _R({1, 5, 9, 12}, router_out)
    D = _R({2, 6, 10}, router_out)
    decided = False
    s_hit, d_hit = [], []
    for cusp_no, tag in ((10, '10th'), (6, '6th')):
        rc = _rotated(cusp_no, router_out)
        sub, agent, chain, _ = _csl_chain(rc, reading)
        s = sorted(chain & S)
        d = sorted(chain & D)
        trace.append({'rule': 'job_exit_%s_csl' % tag,
                      'citation': CIT['job_voluntary_exit'],
                      'detail': '%s CSL %s (agent %s) chain %s -> '
                                'leave-set [1,5,9,12] hit %s, stay-set '
                                '[2,6,10] hit %s'
                                % (tag, sub, agent, sorted(chain), s, d)})
        if s or d:
            verdict, reason = _binary_verdict_d1(s, d, trace, modifiers,
                                                 'job_voluntary_exit',
                                                 levels=_chain_levels(_levels_planet(sub, agent), reading) if agent else None)
            s_hit, d_hit = s, d
            decided = True
            break
    if not decided:
        # book silent on both cusps -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s_hit, d_hit


def _job_relocation_procedure(reading, router_out, trace, modifiers,
                             success, denial):
    """USER RULING 2026-10-04 ("do what the book says"): combined test.
    KSK Reader III true p.390: for transfer judge houses 3, 9 and 12
    (change of residence included); they should be connected with house 6
    or 10. Bosmia Easy Way true p.100 corroborates (3rd/12th CSL
    signifying 3-12 connected with 10 -> transfer; timing in joint period
    of 3-10-12). K.P. Sub Lord and the Principle true p.19: 4th CSL in
    the star of a planet signifying 3rd and 12th = change in residence.
    10th CSL 2-of-3 {3,9,12} (career half) + 4th CSL -> 3,12 (residence
    half) -> YES. Career half promised but residence half silent ->
    OTHER. Books give no denial form for relocation -> no hard NO array;
    silent -> v9's default binary. Decider is the 10th CSL: general
    mixed->YES+DELAYS doctrine.
    """
    cusp10 = _rotated(10, router_out)
    sub10, agent10, chain10, _ = _csl_chain(cusp10, reading)
    hit = sorted(chain10 & _R({3, 9, 12}, router_out))
    cusp4 = _rotated(4, router_out)
    sub4, agent4, chain4, _ = _csl_chain(cusp4, reading)
    res = sorted(chain4 & _R({3, 12}, router_out))
    trace.append({'rule': 'job_relocation_10th_4th',
                  'citation': CIT['job_relocation'],
                  'detail': '10th CSL %s (agent %s) chain %s -> {3,9,12} hit '
                            '%s; 4th CSL %s (agent %s) chain %s -> {3,12} '
                            'hit %s'
                            % (sub10, agent10, sorted(chain10), hit,
                               sub4, agent4, sorted(chain4), res)})
    if len(hit) >= 2 and res:
        verdict = 'YES'
        trace.append({'rule': 'relocation_promised',
                      'citation': CIT['job_relocation'],
                      'detail': 'career half (2+ of {3,9,12}) + residence '
                                'half (4th -> 3/12) both promised -> YES'})
        s_hit, d_hit = hit, []
    elif len(hit) >= 2:
        verdict = 'OTHER'
        trace.append({'rule': 'relocation_residence_unconfirmed',
                      'citation': CIT['job_relocation'],
                      'detail': 'career half promised but the 4th-CSL '
                                'residence confirm is silent -> OTHER '
                                '(default wiring; user may rule otherwise)'})
        s_hit, d_hit = hit, []
    else:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    S = _R({3, 9, 12}, router_out)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s_hit, d_hit


# ---------------------------------------------------------------------------
# v9.7 money-batch-2 helpers
# ---------------------------------------------------------------------------

def _saturn_aspects(reading, planet):
    """Does Saturn aspect the given planet? Saturn's special aspects in KP:
    3rd, 7th (all planets), 10th from its occupied house. House-based;
    conjunction counts. Saturn does NOT aspect itself (v9.8 bugfix: the
    sat_h == pl_h conjunction branch fired when planet IS Saturn).
    Used for the book-verbatim Saturn-aspect -> PARTIAL rules
    (KSK Reader VI true pp.230/238; AS Part 2 true pp.199-200)."""
    try:
        if planet == 'Saturn':
            return False
        facts = {f.get('planet'): f for f in (reading.get('planet_facts') or [])}
        sat_h = (facts.get('Saturn') or {}).get('house_occupied')
        pl_h = (facts.get(planet) or {}).get('house_occupied')
        if not isinstance(sat_h, int) or not isinstance(pl_h, int):
            return False
        if sat_h == pl_h:
            return True
        rel = (pl_h - sat_h) % 12 + 1  # inclusive house count from Saturn
        return rel in (3, 7, 10)
    except Exception:
        return False


def _recovery_planet_modes(sub11, reading, trace, modifiers, verdict):
    """B2a (v9.7): KSK Reader VI true pp.230/238 entangled-money planet modes
    on the 11th CSL planet. Modes describe HOW recovery happens (narration);
    Saturn aspecting the sub-lord is verdict-changing -> PARTIAL."""
    if verdict not in ('YES', 'PARTIAL'):
        return verdict
    MODES = {
        'Saturn': ('delay and some obstacles to recover', 'DELAYS'),
        'Mercury': ('recover in instalments; correspond, give notice, send agents', None),
        'Jupiter': ('through court / by lawful means; full legitimate amount', None),
        'Mars': ('threatens the other and recovers', None),
        'Moon': ('money regained very quickly', None),
        'Venus': ('by compromise and sweet words', None),
        'Sun': ('through help of government officials / litigation', None),
    }
    mode = MODES.get(sub11)
    if mode:
        text, mod = mode
        trace.append({'rule': 'recovery_planet_mode',
                      'citation': CIT['recovery_modes'],
                      'detail': '11th CSL %s -> %s (Reader VI true pp.230/238)'
                                % (sub11, text)})
        if mod and mod not in modifiers:
            modifiers.append(mod)
    if verdict == 'YES' and _saturn_aspects(reading, sub11):
        trace.append({'rule': 'recovery_saturn_aspect_delay',
                      'citation': CIT['recovery_modes'],
                      'detail': 'Saturn aspects the 11th sub-lord %s -> '
                                'USER RULING 2026-10-05: softened from PARTIAL '
                                'to YES+DELAYS (Saturn = delay, never denial; '
                                '"delays only decorate a promise already made")'
                                % sub11})
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
    return verdict


def _money_lent_recovery_procedure(reading, router_out, trace, modifiers,
                                  success, denial):
    """USER RULING 2026-10-04 ("do what the book says"): KSK Reader II
    true p.327 (the 11th rules the lender's principal + interest; good
    aspects to 11th-connected significators -> return of capital and
    interest); Reader III true p.216 (11th = profit on lent money); Umang
    Taneja true p.109: 5,8,12 in DBA = losing lent money, 2,6,10,11 =
    getting it back (Ill. 6 p.116, Ill. 17 p.129); Maina Bhatnagar true
    p.101 ("ENTANGLED MONEY": houses 2,6,10,11). Reader VI true pp.230/238
    ("Entangled Money"): 6th-CSL retrograde check — retrograde (or in a
    retrograde lord's star) -> cannot recover.
    11th CSL -> [2,6,10,11] = YES; -> [5,8,12] = NO. BOSMIA EXCEPTION: the
    decider is the 11th CSL -> mixed success+denial -> NO (coded
    explicitly per user ruling 2026-10-03).
    """
    # Entangled-money retro gate (Reader VI true pp.230/238): 6th CSL
    # retrograde (or in a retrograde lord's star) -> the money is stuck.
    retro = _retro_map(reading)
    cusp6 = _rotated(6, router_out)
    sub6, agent6, chain6, _ = _csl_chain(cusp6, reading)
    csl_retro = bool(retro.get(sub6, False)) or bool(retro.get(agent6, False))
    star6 = (_planet_fact(reading, agent6) or {}).get('star_lord')
    star_retro = bool(retro.get(star6, False))
    if csl_retro or star_retro:
        trace.append({'rule': 'entangled_money_retro',
                      'citation': CIT['money_lent_recovery'],
                      'detail': '6th CSL %s (agent %s) retrograde=%s / in '
                                'retrograde lord\'s star=%s -> entangled '
                                'money cannot be recovered -> NO (Reader VI '
                                'true pp.230/238)' % (sub6, agent6, csl_retro,
                                                      star_retro)})
        return 'NO', modifiers, trace, [], []
    cusp11 = _rotated(11, router_out)
    sub11, agent11, chain11, _ = _csl_chain(cusp11, reading)
    S = _R({2, 6, 10, 11}, router_out)
    D = _R({5, 8, 12}, router_out)
    s = sorted(chain11 & S)
    d = sorted(chain11 & D)
    trace.append({'rule': 'money_lent_recovery_11th_csl',
                  'citation': CIT['money_lent_recovery'],
                  'detail': '11th CSL %s (agent %s) chain %s -> [2,6,10,11] '
                            'hit %s, [5,8,12] hit %s'
                            % (sub11, agent11, sorted(chain11), s, d)})
    if not s and not d:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    # v10.2 carve-out (user ruling 2026-10-05): recovery is EXCEPTED from v10's
    # blanket partial->YES+DELAYS. Book (debtor case): partial success WITHOUT
    # connection to 10th/7th (the other person's houses) -> "not assured" -> NO.
    # The connection matters for recovery specifically.
    if s and set(s) != S:
        r10 = _rotated(10, router_out)
        r7 = _rotated(7, router_out)
        has_connection = r10 in chain11 or r7 in chain11
        if not has_connection:
            trace.append({'rule': 'recovery_partial_no_connection',
                          'citation': 'Debtor case (book): partial without '
                                      '10th/7th connection -> "not assured"',
                          'detail': '11th CSL hits only %s (partial) with no '
                                    '10th/7th connection -> recovery not '
                                    'assured -> NO (v10.2 carve-out)' % s})
            return 'NO', modifiers, trace, s, d
    verdict, reason = _binary_verdict_d1(s, d, trace, modifiers,
                                            'money_lent_recovery',
                                            levels=_chain_levels(_levels_planet(sub11, agent11), reading) if agent11 else None)
    # M1 (v9.6, user ruling 2026-10-05): the Bosmia exception no longer
    # fires here -- its only cited basis is desired-job (Ex 171/172).
    # Mixed -> YES+DELAYS per the general doctrine. (Taneja p.109's
    # mixed->PARTIAL for recovery is staged, not ruled.)
    # B2a (v9.7): planet modes + Saturn-aspect -> PARTIAL.
    verdict = _recovery_planet_modes(sub11, reading, trace, modifiers,
                                     verdict)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, d


# ---------------------------------------------------------------------------
# v9.7 money-batch-2 procedures (B1, B2b, B2c, B3, B4)
# ---------------------------------------------------------------------------

def _lottery_procedure(reading, router_out, trace, modifiers, success,
                       denial):
    """B1 (v9.7, user ruling 2026-10-05): lottery = 11th CSL -> 2-6-11 +
    3rd connection, clean of 5/8/12, CSL + star-lord direct -> YES.
    Citations: Bosmia Prashna Jyotish Ex 31 true pp.158-159
    (outcome-verified); KSK Reader VI true pp.213-214 (outcome-verified).
    The user picked the Bosmia/KSK-VI school from the 5-way split (S-a);
    the strict "else NO" follows the approved R1 form."""
    cusp11 = _rotated(11, router_out)
    sub11, agent11, chain11, note11 = _csl_chain(cusp11, reading)
    retro = _retro_map(reading)
    csl_retro = bool(retro.get(sub11, False)) or bool(retro.get(agent11, False))
    star = (_planet_fact(reading, agent11) or {}).get('star_lord')
    star_retro = bool(retro.get(star, False))
    S = _R({2, 6, 11}, router_out)
    THIRD = _R({3}, router_out)
    DEN = _R({5, 8, 12}, router_out)
    s = sorted(chain11 & S)
    t = sorted(chain11 & THIRD)
    d = sorted(chain11 & DEN)
    trace.append({'rule': 'lottery_11th_csl',
                  'citation': CIT['lottery'],
                  'detail': '11th CSL %s (agent %s) chain %s -> 2-6-11 hit '
                            '%s, 3rd hit %s, 5/8/12 hit %s; retro=%s '
                            'star_retro=%s'
                            % (sub11, agent11, sorted(chain11), s, t, d,
                               csl_retro, star_retro)})
    if csl_retro or star_retro:
        verdict = 'NO'
        trace.append({'rule': 'lottery_retro_denial',
                      'citation': CIT['lottery'],
                      'detail': '11th CSL (or its star-lord) retrograde -> '
                                'cannot win (KSK Reader VI true pp.213-214)'})
    elif d:
        verdict = 'NO'
        trace.append({'rule': 'lottery_denial_bar',
                      'citation': CIT['lottery'],
                      'detail': '11th CSL signifies %s -> must NOT signify '
                                '8/12/5 (Bosmia Ex 31) -> NO' % d})
    elif set(s) == S and t:
        verdict = 'YES'
        trace.append({'rule': 'lottery_promised',
                      'citation': CIT['lottery'],
                      'detail': '11th CSL -> full 2-6-11 + 3rd connection, '
                                'clean of 5/8/12, direct -> win (Bosmia Ex '
                                '31; KSK VI, both outcome-verified)'})
    else:
        verdict = 'NO'
        trace.append({'rule': 'lottery_not_promised',
                      'citation': CIT['lottery'],
                      'detail': '11th CSL -> 2-6-11 hit %s, 3rd hit %s: the '
                                'strict lottery test is not met -> NO '
                                '(approved R1 form)' % (s, t)})
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, d


def _loan_borrow_procedure(reading, router_out, trace, modifiers, success,
                           denial):
    """B2b (v9.7): v9 D7 + AS Part 5 planet modes. 6th CSL direct (nodes
    count as direct -- the engine marks Rahu/Ketu is_retrograde=False,
    per AS Part 5 "Rahu always traverses in the reverse order... he is
    considered to be always direct in motion") + 2-6-11 -> YES.
    Modes: Sun = government loan; Moon = lender agrees very quickly;
    Venus = friendly. Saturn aspecting the sub-lord -> PARTIAL ("part of
    the loan applied for, or part by part")."""
    cusp6 = _rotated(6, router_out)
    sub, agent, chain, note = _csl_chain(cusp6, reading)
    retro = _retro_map(reading)
    s_hit = sorted(chain & _R({2, 6, 11}, router_out))
    csl_retro = bool(retro.get(sub, False)) or bool(retro.get(agent, False))
    star = (_planet_fact(reading, agent) or {}).get('star_lord')
    star_retro = bool(retro.get(star, False))
    trace.append({'rule': 'loan_borrow_procedure',
                  'citation': CIT['borrow_modes'],
                  'detail': '6th CSL %s (agent %s); chain %s; success hit '
                            '%s; retro=%s star_retro=%s (nodes count as '
                            'direct)'
                            % (sub, agent, sorted(chain), s_hit, csl_retro,
                               star_retro)})
    if csl_retro or star_retro:
        trace.append({'rule': 'loan_borrow_retro_denial',
                      'citation': CIT['borrow_modes'],
                      'detail': 'book-verbatim: 6th CSL (or its star lord) '
                                'retrograde -> cannot borrow (the one '
                                'hard-retro exception kept)'})
        _moon_diagnostic(reading, success, trace, modifiers)
        return 'NO', modifiers, trace, s_hit, []
    if not s_hit:
        _moon_diagnostic(reading, success, trace, modifiers)
        return 'OTHER', modifiers, trace, s_hit, []
    verdict = 'YES'
    if sub == 'Sun':
        trace.append({'rule': 'borrow_mode_sun', 'citation': CIT['borrow_modes'],
                      'detail': '6th CSL Sun -> government loan (AS Part 5)'})
    elif sub == 'Moon':
        trace.append({'rule': 'borrow_mode_moon', 'citation': CIT['borrow_modes'],
                      'detail': '6th CSL Moon -> lender agrees very quickly '
                                '(AS Part 5)'})
    elif sub == 'Venus':
        trace.append({'rule': 'borrow_mode_venus', 'citation': CIT['borrow_modes'],
                      'detail': '6th CSL Venus -> friendly loan (AS Part 5)'})
    if _saturn_aspects(reading, sub):
        trace.append({'rule': 'borrow_saturn_aspect_delay',
                      'citation': CIT['borrow_modes'],
                      'detail': 'Saturn aspects the 6th sub-lord %s -> '
                                'USER RULING 2026-10-05: softened from PARTIAL '
                                'to YES+DELAYS (Saturn = delay, never denial)'
                                % sub})
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
    _eleventh_check(reading, router_out, _R({2, 6, 11}, router_out),
                    trace, modifiers)
    _delay_decor(reading, _R({2, 6, 11}, router_out), verdict, trace,
                 modifiers)
    _moon_diagnostic(reading, success, trace, modifiers)
    return verdict, modifiers, trace, s_hit, []


def _loan_repay_procedure(reading, router_out, trace, modifiers):
    """B2c (v9.7): v9.7-native repay procedure (replaces the layer2b
    delegation for this judge; layer2b untouched). Book: Reader VI via AS
    Part 2 true pp.199-200 -- 12th CSL retro (or in retro lord's star) ->
    "one cannot either invest or repay loan" -> NO (hard gate, standing).
    Both direct -> YES + planet modes: Saturn = delay + obstacles;
    Mercury = instalments/correspondence; Jupiter = lawful full amount;
    Mars = lender threatens then repays; Venus = "with a spirit of
    compromise and sweet words" (NEW); Sun = "through the help of either
    father or Government Officials" (NEW). Saturn aspecting the sub-lord
    -> PARTIAL ("one repays only a part of the whole or repays part by
    part"; Prabhakar Times p.185: Saturn -> "never full loan").
    The cusp is turned-chart rotated (12th from the SUBJECT's ascendant),
    exactly as the layer2b procedure did -- established behavior kept."""
    base = int(router_out.get('subject_base') or 1)
    cusp12 = ((base - 1) + 11) % 12 + 1  # layer2b _shift(base, 12)
    sub, agent, chain, note = _csl_chain(cusp12, reading)
    retro = _retro_map(reading)
    csl_retro = bool(retro.get(sub, False)) or bool(retro.get(agent, False))
    star = (_planet_fact(reading, agent) or {}).get('star_lord')
    star_retro = bool(retro.get(star, False))
    trace.append({'rule': 'loan_repay_procedure',
                  'citation': CIT['repay_modes'],
                  'detail': '%dth CSL (12th from subject base %d) %s (agent '
                            '%s); chain %s; retro=%s star_retro=%s'
                            % (cusp12, base, sub, agent, sorted(chain),
                               csl_retro, star_retro)})
    if csl_retro or star_retro:
        who = sub if csl_retro else 'star lord %s of %s' % (star, sub)
        # 2026-10-15 (review 4.1): honor config.EXCEPTION_RETRO_BOOK_VERBATIM
        # like layer2b does. The user's ruling (retro=delay, not denial) sets
        # it False; the old code hard-NO'd regardless of the config.
        try:
            from engine import config as _cfg
            _book_verbatim = bool(getattr(_cfg, 'EXCEPTION_RETRO_BOOK_VERBATIM', True))
        except Exception:
            _book_verbatim = True
        if not _book_verbatim:
            trace.append({'rule': 'loan_repay_retro_softened',
                          'citation': CIT['repay_modes'],
                          'detail': 'book-verbatim would deny (%s retrograde), '
                                    'but config EXCEPTION_RETRO_BOOK_VERBATIM=False '
                                    '(user ruling: retro=delay, not denial) -> '
                                    'YES + DELAYS' % who})
            if 'DELAYS' not in modifiers:
                modifiers.append('DELAYS')
            return 'YES', modifiers, trace, [], []
        trace.append({'rule': 'loan_repay_retro_denial',
                      'citation': CIT['repay_modes'],
                      'detail': 'book-verbatim: %s retrograde -> "one cannot '
                                'either invest or repay loan" -> NO' % who})
        return 'NO', modifiers, trace, [], []
    verdict = 'YES'
    MODES = {
        'Saturn': ('delay and some obstacles to repay', 'DELAYS'),
        'Mercury': ('repay in instalments; correspond, send agent', None),
        'Jupiter': ('by lawful means; full legitimate amount repaid', None),
        'Mars': ('lender threatens first, then repayment', None),
        'Venus': ('with a spirit of compromise and sweet words', None),
        'Sun': ('through the help of either father or Government Officials', None),
    }
    mode = MODES.get(sub)
    if mode:
        text, mod = mode
        trace.append({'rule': 'repay_planet_mode',
                      'citation': CIT['repay_modes'],
                      'detail': '%dth CSL %s -> %s (Reader VI via AS Part 2 '
                                'true pp.199-200)' % (cusp12, sub, text)})
        if mod and mod not in modifiers:
            modifiers.append(mod)
    if _saturn_aspects(reading, sub):
        trace.append({'rule': 'repay_saturn_aspect_delay',
                      'citation': CIT['repay_modes'],
                      'detail': 'Saturn aspects the %dth sub-lord %s -> '
                                'USER RULING 2026-10-05: softened from PARTIAL '
                                'to YES+DELAYS (Saturn = delay, never denial)'
                                % (cusp12, sub)})
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
    _moon_diagnostic(reading, _R({2, 6, 11}, router_out), trace, modifiers)
    return verdict, modifiers, trace, [], []


def _provident_fund_procedure(reading, router_out, trace, modifiers,
                              success, denial):
    """v10.2 (user ruling 2026-10-05): PF/pension/gratuity = 8th CSL ->
    8 (pension/PF house), 2 (money), 6 (service earnings), 11 (success).
    User: "8th house is the house of pension and provident fund."
    (Changed from 11th CSL; Bosmia's position over the ezine's.)
    KP Ezine Nov 2020-Dec 2021 true p.291 (hint + worked case)."""
    cusp8 = _rotated(8, router_out)
    sub8, agent8, chain8, note8 = _csl_chain(cusp8, reading)
    S = _R({8, 2, 6, 11}, router_out)
    CORE = _R({2, 6, 11}, router_out)
    s = sorted(chain8 & S)
    c = sorted(chain8 & CORE)
    kj = sub8 in ('Mercury', 'Jupiter') or agent8 in ('Mercury', 'Jupiter')
    trace.append({'rule': 'provident_fund_8th_csl',
                  'citation': CIT['provident_fund'],
                  'detail': '8th CSL %s (agent %s) chain %s -> 8/2/6/11 '
                            'hit %s; Mercury/Jupiter connection: %s'
                            % (sub8, agent8, sorted(chain8), s, kj)})
    if set(s) == S:
        verdict = 'YES'
        trace.append({'rule': 'provident_fund_assured',
                      'citation': CIT['provident_fund'],
                      'detail': '8th CSL -> full 8-2-6-11 -> "getting money '
                                'of provident fund is assured" (ezine '
                                '2020-2021 p.291)'})
    elif set(c) == CORE:
        verdict = 'YES'
        trace.append({'rule': 'provident_fund_core',
                      'citation': CIT['provident_fund'],
                      'detail': '8th CSL -> 2-6-11 (Joshi form) -> assured'})
    elif s:
        verdict = 'YES'
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        trace.append({'rule': 'provident_fund_partial',
                      'citation': CIT['provident_fund'],
                      'detail': '8th CSL signifies only %s of 8-2-6-11 -> '
                                'promise present, delayed (v10: partial hits '
                                '-> YES+DELAYS, not PARTIAL; M2 got full PF '
                                'with only [6])' % s})
    else:
        verdict = 'OTHER'
        trace.append({'rule': 'provident_fund_silent',
                      'citation': CIT['provident_fund'],
                      'detail': '8th CSL signifies none of 8-2-6-11 -> no '
                                'promise; positive-only test -> OTHER '
                                '(never NO)'})
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, []


def _donation_receive_procedure(reading, router_out, trace, modifiers,
                                success, denial):
    """B4 (v9.7, user ruling 2026-10-05): donation = 8th CSL -> 2-6-11 ->
    YES+DELAYS ("getting donation is sure, but 8 gives you some delay and
    dejection"); partial -> PARTIAL ("did not get as expected"). Bosmia
    Ex.125 true pp.316-318 (outcome-verified). The 8th is the receiving
    channel here (standing 2026-10-04 ruling: 8th is helper's money,
    never denial for receiving)."""
    cusp8 = _rotated(8, router_out)
    sub8, agent8, chain8, note8 = _csl_chain(cusp8, reading)
    S = _R({2, 6, 11}, router_out)
    s = sorted(chain8 & S)
    trace.append({'rule': 'donation_8th_csl',
                  'citation': CIT['donation_receive'],
                  'detail': '8th CSL %s (agent %s) chain %s -> 2-6-11 hit %s'
                            % (sub8, agent8, sorted(chain8), s)})
    if set(s) == S:
        verdict = 'YES'
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        trace.append({'rule': 'donation_promised_delayed',
                      'citation': CIT['donation_receive'],
                      'detail': '8th CSL -> full 2-6-11 -> "getting donation '
                                'is sure, but 8 gives you some delay and '
                                'dejection" -> YES+DELAYS (Bosmia Ex.125)'})
    elif s:
        verdict = 'PARTIAL'
        trace.append({'rule': 'donation_partial',
                      'citation': CIT['donation_receive'],
                      'detail': '8th CSL signifies only %s of 2-6-11 -> '
                                '"did not get as expected" -> PARTIAL '
                                '(Bosmia Ex.125 actual outcome)' % s})
    else:
        verdict = 'OTHER'
        trace.append({'rule': 'donation_silent',
                      'citation': CIT['donation_receive'],
                      'detail': '8th CSL signifies none of 2-6-11 -> no '
                                'promise; positive-only test -> OTHER '
                                '(never NO)'})
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, []


def _chitfund_kitty_procedure(reading, router_out, trace, modifiers,
                             success, denial):
    """USER RULING 2026-10-04: chit fund payout = sudden wealth -> 5th
    house, judged by the 11th CSL ("both are correct... we see sudden
    wealth from 3rd house too, but skip it, keep 5th and judged by 11th").

    11th CSL -> 2,5,6,11 = YES (2 = money in hand, 5 = sudden wealth per
    the user, 6 = gain/regularity, 11 = gains/fulfillment of desire).
    Denial = 8,12. The 5th is EXPLICITLY not denial here: the user rejects
    Bosmia Prashna Jyotish true p.158's "5th negates" for chit funds. The
    3rd-house lottery reading (KSK Reader VI true pp.213-214: lottery under
    the 3rd, 11th CSL -> 2/6/11) is skipped per the user. No chit-fund
    doctrine exists in the books; the 3rd-vs-5th split is a KSK-internal
    contradiction (Reader III p.212: 2+5 for lottery/sudden gains).
    Replaces the 2026-10-03 lottery-default procedure (11th CSL -> 2/6/11
    + 3rd connection, clean of 5/8/12, retrograde check) wholesale.
    BOSMIA EXCEPTION: the decider is the 11th CSL -> mixed -> NO (user
    ruling 2026-10-03), NOT YES+DELAYS.
    """
    cusp11 = _rotated(11, router_out)
    sub11, agent11, chain11, _ = _csl_chain(cusp11, reading)
    S = _R({2, 5, 6, 11}, router_out)
    D = _R({8, 12}, router_out)
    s = sorted(chain11 & S)
    d = sorted(chain11 & D)
    trace.append({'rule': 'chitfund_kitty_11th_csl',
                  'citation': CIT['chitfund_kitty'],
                  'detail': '11th CSL %s (agent %s) chain %s -> [2,5,6,11] '
                            'hit %s, [8,12] hit %s (5th is a success house '
                            'per user ruling 2026-10-04, never denial)'
                            % (sub11, agent11, sorted(chain11), s, d)})
    if not s and not d:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    verdict, reason = _bosmia_11th_mixed_no(s, d, trace, modifiers,
                                            'chitfund_kitty')
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, d


def _business_closure_procedure(reading, router_out, trace, modifiers,
                               success, denial):
    """Bosmia Ex.160 true pp.395-397. POLARITY INVERTED: YES = close it
    (the decision is right); NO = keep running. 10th CSL -> [1,5,9]
    (end-of-business houses; 8/12 supporting per Ex.159) = YES; ->
    [2,7,10,11] (business thriving) = NO. Mixed -> YES + DELAYS: the
    decider is the 10th CSL, and Bosmia's own mixed opinion (2-7-11 with
    1-5-9-8 -> "your decision to close business is perfect") matches the
    general doctrine. 7th CSL is the secondary decider (gain check),
    diagnostic only.
    """
    cusp10 = _rotated(10, router_out)
    sub10, agent10, chain10, _ = _csl_chain(cusp10, reading)
    S = _R({1, 5, 9}, router_out)
    D = _R({2, 7, 10, 11}, router_out)
    s = sorted(chain10 & S)
    d = sorted(chain10 & D)
    trace.append({'rule': 'business_closure_10th_csl',
                  'citation': CIT['business_closure'],
                  'detail': 'POLARITY INVERTED (YES = close it): 10th CSL '
                            '%s (agent %s) chain %s -> end-of-business '
                            '[1,5,9] hit %s, thriving [2,7,10,11] hit %s'
                            % (sub10, agent10, sorted(chain10), s, d)})
    verdict, reason = _binary_verdict_d1(s, d, trace, modifiers,
                                         'business_closure',
                                         levels=_chain_levels(_levels_planet(sub10, agent10), reading) if agent10 else None)
    if not s and not d:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    # 7th CSL gain-check: diagnostic confirm only, never verdict-changing.
    cusp7 = _rotated(7, router_out)
    sub7, agent7, chain7, _ = _csl_chain(cusp7, reading)
    g7 = sorted(chain7 & _R({2, 10, 11}, router_out))
    trace.append({'rule': 'business_closure_7th_confirm',
                  'citation': CIT['business_closure'],
                  'detail': '7th CSL %s (agent %s) -> gain houses [2,10,11] '
                            'hit %s (diagnostic only)' % (sub7, agent7, g7)})
    sup = sorted(chain10 & _R({8, 12}, router_out))
    if sup:
        trace.append({'rule': 'business_closure_loss_support',
                      'citation': CIT['business_closure'],
                      'detail': '8/12 hit %s supports the loss/closure '
                                'reading (Ex.159; diagnostic)' % sup})
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, d


def _financial_help_procedure(reading, router_out, trace, modifiers,
                             success, denial):
    """USER RULING 2026-10-04 ("do what the book says"): 11th CSL -> 2-6-11
    = YES (Bosmia Ex.192 true pp.466-468, outcome-confirmed: 11th CSL ->
    2-6-11 + the 8th as the helper's money; Rout ezine true p.388: 8th
    CSL -> 2-6-11, outcome-confirmed; Naik K.P. Dynamics true p.111:
    8,2,6,11). The 3 must come WITH 2/6/11 -- "If 3-9 HS operates, then
    talk between two parties only": talk without money is not help
    received. 8th DROPPED from denial per user ruling: the library tally
    shows NO book treats the 8th as denial for RECEIVING help (positive
    or channel-neutral everywhere; denial-flavored 8th only in
    recovery/loss contexts). Denial = [5,12]. BOSMIA EXCEPTION: the
    decider is the 11th CSL -> mixed -> NO.
    """
    cusp11 = _rotated(11, router_out)
    sub11, agent11, chain11, _ = _csl_chain(cusp11, reading)
    Smain = _R({2, 6, 11}, router_out)
    s3 = sorted(chain11 & _R({3}, router_out))
    s_main = sorted(chain11 & Smain)
    d = sorted(chain11 & _R({5, 12}, router_out))
    trace.append({'rule': 'financial_help_11th_csl',
                  'citation': CIT['financial_help'],
                  'detail': '11th CSL %s (agent %s) chain %s -> [2,6,11] '
                            'hit %s, [3] hit %s, denial [5,12] hit %s '
                            '(8th dropped from denial per user ruling '
                            '2026-10-04: helper\'s money, never denial for '
                            'receiving)'
                            % (sub11, agent11, sorted(chain11), s_main, s3,
                               d)})
    if s3 and not s_main:
        trace.append({'rule': 'help_talk_without_money',
                      'citation': CIT['financial_help'],
                      'detail': '3rd-house talk/approach without 2/6/11 -> '
                                '"talk between two parties only", not help '
                                'received -> v9 default binary'})
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    s_hit = sorted(set(s_main) | set(s3))
    # M1 (v9.6, user ruling 2026-10-05): the Bosmia exception no longer
    # fires here -- on help questions it rejected Bosmia's own
    # outcome-verified YES (Ex.192, re-run 2026-10-05). Mixed ->
    # YES+DELAYS per the general doctrine.
    verdict, reason = _binary_verdict_d1(s_hit, d, trace, modifiers,
                                            'financial_help',
                                            levels=_chain_levels(_levels_planet(sub11, agent11), reading) if agent11 else None)
    _delay_decor(reading, Smain, verdict, trace, modifiers)
    _moon_diagnostic(reading, Smain, trace, modifiers)
    return verdict, modifiers, trace, s_hit, d


def _financial_crisis_procedure(reading, router_out, trace, modifiers,
                               success, denial):
    """Bosmia Ex.13 true pp.73-74: 2nd CSL -> 2-6-11 = YES (relief comes,
    "during the joint period of 2-6-11"); the denial array [1,8,9,12] is
    book-given ("Positive bhava are 2-6 and negative bhava are 1-9-8-12")
    = NO (the crunch persists). Mixed -> YES + DELAYS (decider is the 2nd
    CSL: general doctrine).
    """
    cusp2 = _rotated(2, router_out)
    sub2, agent2, chain2, _ = _csl_chain(cusp2, reading)
    S = _R({2, 6, 11}, router_out)
    D = _R({1, 8, 9, 12}, router_out)
    s = sorted(chain2 & S)
    d = sorted(chain2 & D)
    trace.append({'rule': 'financial_crisis_2nd_csl',
                  'citation': CIT['financial_crisis'],
                  'detail': '2nd CSL %s (agent %s) chain %s -> 2-6-11 hit '
                            '%s, book-denial [1,8,9,12] hit %s'
                            % (sub2, agent2, sorted(chain2), s, d)})
    verdict, reason = _binary_verdict_d1(s, d, trace, modifiers,
                                         'financial_crisis',
                                         levels=_chain_levels(_levels_planet(sub2, agent2), reading) if agent2 else None)
    if not s and not d:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _eleventh_check(reading, router_out, S, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, d


def _thesis_submission_procedure(reading, router_out, trace, modifiers,
                                success, denial):
    """USER RULING 2026-10-04 ("do what the book says"): KSK Reader II
    true p.312 (verbatim: "The ninth house presides over research,
    invention, discovery, exploration, and submission of thesis"); Reader
    III true p.425: 9th-house significator also signifying 11 = pass /
    doctorate, signifying 12 = cannot come out successful; Hariharan true
    p.99: research/thesis judged on 9 and 12, with an 11th-significator
    needed for success; Bosmia Ex.129 true pp.324-325 (9th CSL -> 4-9-11
    = higher-education milestone assured). 9th CSL -> [4,9,11] = YES;
    -> [12] = NO. Decider is the 9th CSL: general mixed->YES+DELAYS
    doctrine (Bosmia 11th exception does not apply).
    """
    cusp9 = _rotated(9, router_out)
    sub9, agent9, chain9, _ = _csl_chain(cusp9, reading)
    S = _R({4, 9, 11}, router_out)
    D = _R({12}, router_out)
    s = sorted(chain9 & S)
    d = sorted(chain9 & D)
    trace.append({'rule': 'thesis_submission_9th_csl',
                  'citation': CIT['thesis_submission'],
                  'detail': '9th CSL %s (agent %s) chain %s -> [4,9,11] hit '
                            '%s, denial [12] hit %s'
                            % (sub9, agent9, sorted(chain9), s, d)})
    if not s and not d:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    verdict, reason = _binary_verdict_d1(s, d, trace, modifiers,
                                         'thesis_submission',
                                         levels=_chain_levels(_levels_planet(sub9, agent9), reading) if agent9 else None)
    _eleventh_check(reading, router_out, S, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s, d


def _desired_job_11th_test(reading, router_out, trace, modifiers):
    """Standalone 11th-CSL desired-post test (extracted from v9's D3 block).

    11th CSL -> 2-6-10-11 clean of denial admixture -> YES; else NO.
    Used by the known-job router and v9's desired_job path alike.
    """
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
                  'detail': '11th CSL %s (agent %s) chain %s -> 2-6-10-11 '
                            'hit %s, denial admixture %s'
                            % (sub11, agent11, sorted(chain11), s11, d11)})
    # E1 (v9.4): the user's Bosmia ruling — 11th CSL is the DECIDER here,
    # so mixed success+denial -> NO (not YES+DELAYS). Behavior matches
    # v9/v9.3's mixed->NO on this path; the trace now names the ruling.
    if s11 and not d11:
        verdict = 'YES'
    elif s11 and d11:
        verdict = 'NO'
        trace.append({'rule': 'BOSMIA_11TH_MIXED_NO',
                      'citation': CIT['bosmia_11th_mixed_no'],
                      'detail': '11th CSL %s -> 2-6-10-11 %s MIXED with '
                                'denial %s -> NO (11th-CSL decider; the '
                                'general mixed->YES+DELAYS ruling does not '
                                'apply here)' % (sub11, s11, d11)})
    else:
        verdict = 'NO'
        trace[-1]['detail'] += ' -> NO (desired post not promised)'
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(cusp11, reading)
        _career_floor_shadow([('11th CSL', levels)], S261011, verdict,
                             trace, modifiers)
    return verdict, s11, d11


def _job_get_2610_procedure(reading, router_out, trace, modifiers, success,
                            denial, question):
    """D11 (v9.3 round-2, REJECTED): Generic "will I get a job?" with the
    book-backed 2-6-10 promise set (no 11).

    TESTED AND REJECTED round-2: career 72.3% -> 63.6% (-8.7pp), FP 21 -> 34.
    The books (KSK Reader VI true pp.285-288; Bosmia 12x hint) say 2-6-10,
    but the measurement says v9's 2-6-10-11 works better. Kept in code as
    documentation of the tested variant; NOT called. Staged for the user.
    """
    q = (question or '').lower()
    aspirational = any(w in q for w in
                       ('better', 'higher', 'dream', 'desired', 'expectation',
                        'promotion', 'big', 'good job', 'great'))
    S = _R({2, 6, 10}, router_out)
    s_union = set()
    parts = []
    for c in (6, 10):
        rc = _rotated(c, router_out)
        sub, agent, chain, _ = _csl_chain(rc, reading)
        hit = sorted(chain & S)
        s_union |= set(hit)
        parts.append('%dth CSL %s (agent %s) -> 2/6/10 hit %s'
                     % (c, sub, agent, hit))
    s_union = sorted(s_union)
    trace.append({'rule': 'job_get_2610_procedure',
                  'citation': 'KSK Reader VI true pp.285-288 (2,6,10 for '
                              'employment); Bosmia 12x hint (6th/10th CSL -> '
                              '2-6-10)',
                  'detail': '6th/10th CSLs vs [2,6,10]: ' + '; '.join(parts)
                            + '; aspirational=%s' % aspirational})
    if s_union:
        verdict = 'YES'
        trace.append({'rule': 'job_get_2610_promised',
                      'citation': 'Bosmia hint (6th/10th CSL significator of '
                                  '2-6-10 -> service promised)',
                      'detail': '2/6/10 signified %s -> YES' % s_union})
        if aspirational:
            # Bosmia Ex 173: better-job desire -> 11th CSL must also confirm
            v11, s11, d11 = _desired_job_11th_test(reading, router_out,
                                                   trace, modifiers)
            trace.append({'rule': 'job_get_aspirational_11th',
                          'citation': 'Bosmia Ex 173 true p.423 (better job '
                                      '-> consider the 11th cusp also)',
                          'detail': 'aspirational question: 11th CSL test -> '
                                    '%s (s=%s, d=%s)' % (v11, s11, d11)})
            # The 11th confirms but does not veto: if it denies, the base
            # promise stands with DELAYS (per the ruling, mixed -> YES).
            if v11 == 'NO' and 'DELAYS' not in modifiers:
                modifiers.append('DELAYS')
    else:
        # book silent -> v9's default binary, not OTHER
        return _v9_default_binary(reading, router_out, success,
                                  denial, trace, modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s_union, []


def _unknown_job_procedure(reading, router_out, trace, modifiers, job_text):
    """THE USER'S JOB RULE, branch (b) (2026-10-03): the querent names a
    specific job the bot does NOT know -> one simple rule: judge the 11th
    cusp sub-lord AND the 11th lord, plus the standard promise rules.

    11th CSL clean (2-6-10-11, no denial admixture) -> YES.
    11th CSL denial-only -> NO.
    Mixed -> YES + DELAYS per the standing ruling.

    D10 (v9.3): the 11th LORD is demoted from verdict-tiebreaker to
    QUALIFIER. The 11th-doctrine mining found NO book makes the 11th lord
    a verdict decider ("the CSL is the decider; the lord is a contributor:
    timing, fallback signification, or a qualifier on how smoothly
    fulfillment comes" — KSK Reader VI true p.287: planets in 11th + its
    owner indicate whether desire is fulfilled EARLY or not; Prabhakar true
    p.125: lord of 11th in 8th = hindrance/impediment). The lord no longer
    flips verdicts; an afflicted lord (denial houses in its chain) adds
    DELAYS/FRICTION, a well-placed lord adds SMOOTH_FULFILLMENT. Doctrine
    call, logged for the user's overrule.
    """
    cusp11 = _rotated(11, router_out)
    sub11, agent11, chain11, _ = _csl_chain(cusp11, reading)
    S = _R({2, 6, 10, 11}, router_out)
    D = _R({1, 5, 8, 9, 12}, router_out)
    s11 = sorted(chain11 & S)
    d11 = sorted(chain11 & D)
    cusp_facts = reading.get('cusp_facts') or []
    lord11 = (cusp_facts[cusp11 - 1] or {}).get('sign_lord') \
        if 1 <= cusp11 <= len(cusp_facts) else None
    lord_chain = _chain_of(lord11, reading) if lord11 else set()
    s_lord = sorted(lord_chain & S)
    d_lord = sorted(lord_chain & D)
    trace.append({'rule': 'unknown_job_11th_test',
                  'citation': CIT['unknown_job'],
                  'detail': 'named job "%s" not in knowledge table: 11th '
                            'CSL %s (agent %s) chain %s -> 2-6-10-11 hit %s, '
                            'denial %s; 11th lord %s chain %s -> success %s, '
                            'denial %s (lord = qualifier only, D10)'
                            % (job_text, sub11, agent11, sorted(chain11),
                               s11, d11, lord11, sorted(lord_chain),
                               s_lord, d_lord)})
    if s11 and not d11:
        verdict = 'YES'
        trace.append({'rule': 'unknown_job_11th_promises',
                      'citation': CIT['unknown_job'],
                      'detail': '11th CSL clean 2-6-10-11 -> YES'})
    elif d11 and not s11:
        verdict = 'NO'
        trace.append({'rule': 'unknown_job_11th_denies',
                      'citation': CIT['unknown_job'],
                      'detail': '11th CSL denial-only -> NO'})
    elif s11 and d11:
        # E1 (v9.4): the user's Bosmia ruling — the 11th CSL is the DECIDER
        # on this path, so mixed success+denial -> NO (not YES+DELAYS).
        # (v9.3 said YES+DELAYS here; the ruling overrides it, narrowly.)
        verdict = 'NO'
        trace.append({'rule': 'BOSMIA_11TH_MIXED_NO',
                      'citation': CIT['bosmia_11th_mixed_no'],
                      'detail': '11th CSL %s -> 2-6-10-11 %s MIXED with '
                                'denial %s -> NO (11th-CSL decider; the '
                                'general mixed->YES+DELAYS ruling does not '
                                'apply here)' % (sub11, s11, d11)})
    else:
        # neutral (neither success nor denial) -> YES + DELAYS per the
        # standing general ruling (the Bosmia exception covers MIXED only).
        verdict = 'YES'
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        trace.append({'rule': 'unknown_job_neutral',
                      'citation': CIT['mixed_delays_flag'],
                      'detail': '11th CSL neutral (no 2-6-10-11, no denial) '
                                '-> YES + DELAYS per the general ruling '
                                '(lord is qualifier only)'})
    # D10: 11th lord as qualifier (timing/smoothness), not decider.
    if lord11:
        lord_afflicted = bool(d_lord)
        if lord_afflicted and verdict == 'YES':
            if 'FRICTION' not in modifiers:
                modifiers.append('FRICTION')
            trace.append({'rule': 'unknown_job_lord_qualifier',
                          'citation': 'KSK Reader VI true p.287; Prabhakar '
                                      'true p.125 (lord of 11th in 8th = '
                                      'hindrance)',
                          'detail': '11th lord %s -> denial %s -> FRICTION '
                                    'qualifier (lord judged, verdict '
                                    'unchanged)' % (lord11, d_lord)})
        elif s_lord and not d_lord and verdict == 'YES':
            trace.append({'rule': 'unknown_job_lord_smooth',
                          'citation': 'KSK Reader VI true p.287',
                          'detail': '11th lord %s -> success %s, well-placed '
                                    '-> smooth fulfillment (qualifier only)'
                                    % (lord11, s_lord)})
    if verdict == 'YES':
        _, _, levels, _ = _csl_chain_levels(cusp11, reading)
        _career_floor_shadow([('11th CSL', levels)], S, verdict, trace,
                             modifiers)
    _delay_decor(reading, S, verdict, trace, modifiers)
    _moon_diagnostic(reading, S, trace, modifiers)
    return verdict, modifiers, trace, s11, d11


def _known_job_route(reading, router_out, trace, modifiers, job_key,
                     mapping, flags, success, denial):
    """THE USER'S JOB RULE, branch (a): the job IS in the knowledge table ->
    that job's specific cusp procedure."""
    proc = (mapping or {}).get('procedure', 'desired_job_11th')
    trace.append({'rule': 'known_job_route',
                  'citation': CIT['known_job'],
                  'detail': 'named job "%s" in knowledge table (%s) -> '
                            'procedure %s'
                            % (job_key, (mapping or {}).get('citation',
                                                            'no citation'),
                               proc)})
    if proc == 'government_test':
        cusp10 = _rotated(10, router_out)
        sub, agent, chain, note = _csl_chain(cusp10, reading)
        S2610 = _R({2, 6, 10}, router_out)
        s_hit = sorted(chain & S2610)
        has10 = _rotated(10, router_out) in chain
        trace.append({'rule': 'government_test',
                      'citation': CIT['government_test'],
                      'detail': 'known job "%s" -> government procedure: '
                                '10th CSL %s (agent %s) chain %s -> 2-6-10 '
                                'hit %s, 10th connected=%s'
                                % (job_key, sub, agent, sorted(chain),
                                   s_hit, has10)})
        verdict = 'YES' if (s_hit and has10) else 'NO'
        if verdict == 'YES':
            _, _, levels, _ = _csl_chain_levels(cusp10, reading)
            _career_floor_shadow([('10th CSL', levels)], S2610, verdict,
                                 trace, modifiers)
        _delay_decor(reading, S2610, verdict, trace, modifiers)
        _moon_diagnostic(reading, S2610, trace, modifiers)
        return verdict, modifiers, trace, s_hit, []
    if proc == 'business_start':
        return _business_start_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
    if proc == 'promotion_11th':
        return _promotion_procedure(reading, router_out, trace, modifiers,
                                    success, denial)
    # default known-job procedure: the 11th-CSL desired-post test
    verdict, s11, d11 = _desired_job_11th_test(reading, router_out, trace,
                                               modifiers)
    _delay_decor(reading, _R({2, 6, 10, 11}, router_out), verdict, trace,
                 modifiers)
    _moon_diagnostic(reading, _R({2, 6, 10, 11}, router_out), trace,
                     modifiers)
    return verdict, modifiers, trace, s11, d11


# ---------------------------------------------------------------------------
# v9.2 dispatch
# ---------------------------------------------------------------------------

def _exam_no_third_bar(reading, router_out, trace, modifiers, success, denial,
                       event, question):
    """v10.2 exam handler: clean binary verdicts WITHOUT the D2 3rd-bar.

    - exam_competitive: Asc CSL + 11th CSL joint deciders -> 4-6-9-11
      (Bosmia Ex.169 + UPSC, outcome-verified x2). Gives the only principled
      competitive NO path.
    - education_higher: 9th CSL -> 4-9-11 (Bosmia Ex.168, Joshi p.57).
    - exam_pass_general, education_general: standard success/denial binary.
    """
    # 2026-10-14 (Gemini 4 audit): the D2 3rd-house bar was removed 2026-10-05
    # (user ruling), but Layer 2's 12th-from CANDIDATE_NEGATION fallback
    # ([3,8,10]) sneaks houses 3 and 10 back into denial. Strip them: 3 is
    # the banned bar, 10 is merit/rank (not denial for exams).
    denial = [h for h in (denial or []) if h not in (3, 10)]
    if event == 'exam_competitive':
        cusp1 = _rotated(1, router_out)
        # Use 4-level chain for exam (tuned on L1-L4; L5/L6/L7 create noise).
        # Relationship uses full 7-level chain (books use sub-lord levels).
        sub1, agent1, chain1, _ = _csl_chain_4level(cusp1, reading)
        cusp11 = _rotated(11, router_out)
        sub11, agent11, chain11, _ = _csl_chain_4level(cusp11, reading)
        S = _R({4, 6, 9, 11}, router_out)
        s1 = sorted(chain1 & S)
        s11 = sorted(chain11 & S)
        # Joint deciders: both Asc and 11th must promise
        s_joint = sorted(set(s1) | set(s11))
        d = sorted((chain1 | chain11) & _R(set(denial), router_out))
        trace.append({'rule': 'exam_competitive_asc_11th',
                      'citation': 'Bosmia Ex.169 + UPSC (outcome-verified x2)',
                      'detail': 'Asc CSL %s -> %s; 11th CSL %s -> %s; joint '
                                '4-6-9-11 hit %s, denial %s'
                                % (sub1, s1, sub11, s11, s_joint, d)})
        if set(s_joint) == S and not d:
            verdict = 'YES'
        elif not s_joint:
            verdict = 'OTHER'
        else:
            # Partial joint promise -> use binary verdict
            verdict, _ = _binary_verdict_d1(s_joint, d, trace, modifiers,
                                            'exam_competitive', S,
                                            denial_meta=router_out.get('denial_meta'))
        return verdict, modifiers, trace, s_joint, d
    if event == 'education_higher':
        # v10.3: admissions to prestigious/desired institutions -> competitive
        # procedure (Taneja Prasana p.1156: "Admission to good course or
        # prestigious institutions is regulated through competitive
        # examinations... 6,11 or 4,9,11").
        q_low = (question or '').lower()
        is_prestigious_admission = (
            'admission' in q_low and
            any(kw in q_low for kw in [
                'desired', 'prestigious', 'bits', 'iit', 'iim',
                'good course', 'top college', 'best college',
            ]))
        # v10.3 (user ruling 2026-10-06): CA/professional exam distinction
        # STAGED. "will i clear my ca final" -> competitive (Bosmia);
        # "is ca study suitable" -> higher-ed. Routing logic works but the
        # competitive procedure gives false YES on W157 — needs chart-level
        # analysis, not just routing. Reverted 2026-10-06.
        if is_prestigious_admission:
            trace.append({'rule': 'admission_prestigious_competitive',
                          'citation': 'Taneja Prasana p.1156',
                          'detail': 'admission to prestigious/desired '
                                    'institution -> competitive procedure '
                                    '(Asc+11th -> 4-6-9-11)'})
            # Run competitive logic inline (block is earlier in function)
            cusp1 = _rotated(1, router_out)
            sub1, agent1, chain1, _ = _csl_chain_4level(cusp1, reading)
            cusp11 = _rotated(11, router_out)
            sub11, agent11, chain11, _ = _csl_chain_4level(cusp11, reading)
            S = _R({4, 6, 9, 11}, router_out)
            s1 = sorted(chain1 & S)
            s11 = sorted(chain11 & S)
            s_joint = sorted(set(s1) | set(s11))
            d = sorted((chain1 | chain11) & _R(set(denial), router_out))
            trace.append({'rule': 'exam_competitive_asc_11th',
                          'citation': 'Bosmia Ex.169 + UPSC',
                          'detail': 'Asc CSL %s -> %s; 11th CSL %s -> %s; '
                                    'joint 4-6-9-11 hit %s, denial %s'
                                    % (sub1, s1, sub11, s11, s_joint, d)})
            if set(s_joint) == S and not d:
                verdict = 'YES'
            elif not s_joint:
                verdict = 'OTHER'
            else:
                verdict, _ = _binary_verdict_d1(s_joint, d, trace, modifiers,
                                                'exam_competitive', S,
                                                denial_meta=router_out.get('denial_meta'))
            return verdict, modifiers, trace, s_joint, d
        cusp9 = _rotated(9, router_out)
        sub9, agent9, chain9, _ = _csl_chain_4level(cusp9, reading)
        S = _R({4, 9, 11}, router_out)
        s9 = sorted(chain9 & S)
        d9 = sorted(chain9 & _R(set(denial), router_out))
        trace.append({'rule': 'education_higher_9th',
                      'citation': 'Bosmia Ex.168; Joshi p.57',
                      'detail': '9th CSL %s -> 4-9-11 hit %s, denial %s'
                                % (sub9, s9, d9)})
        verdict, _ = _binary_verdict_d1(s9, d9, trace, modifiers,
                                        'education_higher', S,
                                        denial_meta=router_out.get('denial_meta'))
        return verdict, modifiers, trace, s9, d9
    # exam_pass_general, education_general: 4th CSL (education house) decider
    # v10.2 fix: was using weak generic _signified_set -> mostly OTHER.
    # Book: 4th = basic education; use 4-6-9-11 (pass) / 4-9-11 (general).
    # S5 (partial+denial->OTHER) stays ON: accuracy guard. Coverage is lower
    # but the verdicts are trustworthy. (2026-10-05: loosening S5 gave 81%
    # coverage at 54% accuracy -- not worth it.)
    # Use strong-only chain (exam tuned on 4-level; L5/L6/L7 weak hits = noise)
    cusp4 = _rotated(4, router_out)
    sub4, agent4, chain4, _ = _csl_chain_4level(cusp4, reading)
    if event == 'exam_pass_general':
        # 2026-10-14 (Gemini 4 audit): non-competitive exams don't require
        # the 6th house (competition); a single 4th-CSL chain can't reliably
        # hit all 4 of {4,6,9,11}. Book set is {4,9,11}.
        S = _R({4, 9, 11}, router_out)
    else:  # education_general
        S = _R({4, 9, 11}, router_out)
    s4 = sorted(chain4 & S)
    d4 = sorted(chain4 & _R(set(denial), router_out))
    trace.append({'rule': 'exam_4th_csl',
                  'citation': 'v10.2: 4th CSL decider (4th = education)',
                  'detail': '%s: 4th CSL %s -> %s hit %s, denial %s'
                            % (event, sub4, sorted(S), s4, d4)})
    verdict, _ = _binary_verdict_d1(s4, d4, trace, modifiers,
                                    event, S,
                                    denial_meta=router_out.get('denial_meta'))
    return verdict, modifiers, trace, s4, d4


def _is_rank_question(question):
    """Detect rank/distinction questions (vs pass/fail)."""
    q = (question or '').lower()
    return any(kw in q for kw in [
        'rank', 'distinction', 'first class', 'topper', 'top 10', 'top ten',
        'merit list', 'position in', 'how many marks', 'percentage',
        'mention bien', 'mention tres bien', 'with honors', 'with honours',
        'cum laude', 'summa', 'magna', 'grade a', 'a grade',
    ])


def _exam_rank_procedure(reading, router_out, trace, modifiers):
    """v10.2: rank/distinction (E1-6). Book: 1st+4th CSL -> [3,6,10] with 6
    as veto. Both 1st and 4th must promise; 6 vetoes (6 = defeat/competition
    loss in this context). Uses 4-level chain (exam tuned on L1-L4)."""
    cusp1 = _rotated(1, router_out)
    sub1, agent1, chain1, _ = _csl_chain_4level(cusp1, reading)
    cusp4 = _rotated(4, router_out)
    sub4, agent4, chain4, _ = _csl_chain_4level(cusp4, reading)
    S = _R({3, 6, 10}, router_out)
    s1 = sorted(chain1 & S)
    s4 = sorted(chain4 & S)
    s_joint = sorted(set(s1) | set(s4))
    r6 = _rotated(6, router_out)
    has6_veto = r6 in chain1 or r6 in chain4
    trace.append({'rule': 'exam_rank_1st_4th',
                  'citation': 'EXAM_MISS_COVERAGE_REPORT.md E1-6 (book)',
                  'detail': '1st CSL %s -> %s; 4th CSL %s -> %s; joint '
                            '[3,6,10] hit %s; 6 veto=%s'
                            % (sub1, s1, sub4, s4, s_joint, has6_veto)})
    if has6_veto:
        verdict = 'NO'
        trace.append({'rule': 'exam_rank_6_veto',
                      'detail': '6 in chain -> veto -> NO (rank not achieved)'})
    elif set(s_joint) == S:
        verdict = 'YES'
    elif not s_joint:
        verdict = 'OTHER'
    else:
        verdict, _ = _binary_verdict_d1(s_joint, [], trace, modifiers,
                                        'exam_distinction_rank', S)
    return verdict, modifiers, trace, s_joint, []


# ---------------------------------------------------------------------------
# v10.3 marriage procedures (RELATIONSHIP_ABLATION_REPORT 2026-10-05)
# ---------------------------------------------------------------------------

_LOVE_KEYWORDS = [
    'love marriage', 'man i love', 'girl i love', 'woman i love',
    'boy i love', 'my lover', 'with my lover', 'i am in love',
    'in love with', 'boyfriend', 'girlfriend',
]


def _is_love_question(question):
    q = (question or '').lower()
    return any(kw in q for kw in _LOVE_KEYWORDS)


def _marriage_procedure(reading, router_out, trace, modifiers, success,
                        denial, question):
    """v10.3 marriage: 7th CSL decider (vR7, Reader IV p.108-109).
    S5 OFF: single-CSL deciders use legacy mixed->YES+DELAYS (vR1's 13 breaks
    proved S5 incompatible here).
    Love-marriage intercept (AS Part 3 p.23): 7th CSL -> [2,7,11] AND 5th
    connection -> YES; [2,7,11] without 5th -> NO (not a love marriage).
    Proposal carve-out (user ruling 2026-10-06, Taneja p.145): proposals with
    partial [2,7,11] (scattered, not clearly signified) -> NO, not YES+DELAYS.
    2026-10-14: retrograde-CSL and D4 gates run BEFORE the love-marriage
    intercept -- "will I have a love marriage?" no longer bypasses them.
    """
    # NOTE: 7th CSL chain is computed first so the retro/D4 gates below run
    # for every marriage question, including love-marriage ones.
    # Proposal carve-out: partial -> NO (Taneja p.145)
    # NARROWED 2026-10-06 per miss analysis (H-R26): fire only when 7 is
    # absent from the 7th CSL chain. Book-verified proposal YESes (H-R26:
    # 7th CSL -> 3-4-5-7-9-11; R14, R20) succeed with partial [2,7,11] —
    # the common thread is the 7th house itself being signified.
    # Taneja p.145 is about DBA level, not CSL.
    q_low = (question or '').lower()
    is_proposal = any(kw in q_low for kw in [
        'proposal', 'propose', 'rishta', 'alliance',
        'compatibility', 'prospective match', 'perfect match',
    ])
    cusp7 = _rotated(7, router_out)
    _v = _B3_VARIANT
    _core7 = _R({7}, router_out)
    if _v in ('V1', 'V1C', 'V3'):
        sub7, agent7, chain7, _ = _csl_chain_strong(cusp7, reading)
    elif _v == 'V2':
        sub7, agent7, _c4, _n4 = _csl_chain_4level(cusp7, reading)
        _lv = _chain_levels(_levels_planet(sub7, agent7), reading) if agent7 else {}
        chain7 = set((_lv.get('L1') or set()) | (_lv.get('L2') or set()))
        _ = _n4
    else:
        sub7, agent7, chain7, _ = _csl_chain_7level(cusp7, reading)
    # 2026-10-13 (USER RULING): retrograde 7th CSL decider = hard NO for marriage.
    # Extends the romance retrograde-CSL rule. "Saturn on top of retrograde...
    # a retrograde is a hard no, specially if its CSL."
    _retro7 = _retro_map(reading)
    if bool(_retro7.get(sub7, False)) or bool(_retro7.get(agent7, False)):
        trace.append({'rule': 'marriage_retro_csl_no',
                      'citation': 'user ruling 2026-10-13: retrograde CSL '
                                  'decider = hard NO (relationship)',
                      'detail': '7th CSL %s (agent %s) is retrograde -> '
                                'marriage cannot materialise -> NO'
                                % (sub7, agent7)})
        return 'NO', modifiers, trace, [], []
    # D4: decider's star-lord retrograde -> denial (Reader VI pp.146-147)
    _dec7 = agent7 or sub7
    if _d4_star_retro_check(reading, _dec7, trace, 'marriage', sub_lord=sub7):
        return 'NO', modifiers, trace, [], []
    # Love-marriage intercept (AS Part 3 p.23): runs AFTER the retro/D4
    # gates so love-marriage questions cannot bypass them (2026-10-14 fix).
    if _is_love_question(question):
        # 2026-10-15 (review 1.4): run delay/moon decors — the procedure
        # returns early without them, so exam/marriage YES never got DELAYS.
        _res = _love_marriage_procedure(reading, router_out, trace,
                                        modifiers, success, denial)
        _delay_decor(reading, success, _res[0], trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return _res
    S = _R({2, 7, 11}, router_out)
    D = _R({1, 6, 10}, router_out)
    if _v in ('V1', 'V2') and not (chain7 & _core7):
        trace.append({'rule': 'b3_core_house_gate',
                      'citation': 'B3 lab variant ' + _v,
                      'detail': 'core house 7 not signified at variant level '
                                '-> no promise -> OTHER'})
        return 'OTHER', modifiers, trace, [], []
    s = sorted(chain7 & S)
    d = sorted(chain7 & D)
    trace.append({'rule': 'marriage_7th_csl',
                  'citation': 'Reader IV p.108-109 (vR7, S5 off)',
                  'detail': '7th CSL %s -> [2,7,11] hit %s, [1,6,10] hit %s'
                            % (sub7, s, d)})
    # Margin instrumentation (lab 2026-10-13): weighted S-D
    _lv = _chain_levels(_levels_planet(sub7, agent7), reading) if agent7 else {}
    def _w(houses):
        return round(sum(LEVEL_WEIGHTS.get(lv, 0) for lv, hs in _lv.items()
                         for h in houses if h in hs), 2)
    _Sw, _Dw = _w(S), _w(D)
    trace.append({'rule': 'marriage_margin',
                  'citation': 'lab instrumentation 2026-10-13',
                  'detail': 'S=%.2f D=%.2f margin=%.2f' % (_Sw, _Dw, _Sw - _Dw)})
    # 2026-10-14 FIX: the proposal carve-out + verdict logic below was
    # accidentally nested inside _log_weighted_margin (returned None).
    # Restored to _marriage_procedure.
    # 2026-10-15 (Claude review A3): chain7 holds NATIVE chart houses while the
    # doctrine sets are _R-rotated. The literal 7 missed third-party
    # (turned) questions — use the rotated _core7 instead.
    if is_proposal and s and not (set(chain7) & _core7):
        # NARROWED: only when 7 is absent from the 7th CSL chain.
        trace.append({'rule': 'proposal_partial_no',
                      'citation': 'Taneja p.145; user ruling 2026-10-06; '
                                  'narrowed 2026-10-06 (7-absent only)',
                      'detail': 'proposal/compatibility with 7 absent from '
                                '7th CSL chain %s -> NO (carve-out from '
                                'YES+DELAYS)' % s})
        return 'NO', modifiers, trace, s, d
    _fs = S if _B3_VARIANT in ('V0S5', 'V1', 'V2', 'V3') else None
    verdict, _ = _binary_verdict_d1(s, d, trace, modifiers, 'marriage', _fs,
                                    levels=_lv)
    return verdict, modifiers, trace, s, d


def _log_weighted_margin(agent, reading, S, D, trace, label):
    """Generic weighted-margin logger (lab instrumentation 2026-10-13).
    Computes weighted S/D/margin for any procedure's decider chain.
    S, D: sets of house numbers (already rotated). label: trace rule name.
    """
    _lv = _chain_levels(agent, reading) if agent else {}
    def _w(houses):
        return round(sum(LEVEL_WEIGHTS.get(lv, 0) for lv, hs in _lv.items()
                         for h in houses if h in hs), 2)
    _Sw, _Dw = _w(S), _w(D)
    trace.append({'rule': label,
                  'citation': 'lab instrumentation 2026-10-13',
                  'detail': 'S=%.2f D=%.2f margin=%.2f' % (_Sw, _Dw, _Sw - _Dw)})
    # 2026-10-14: removed misplaced marriage verdict logic (was accidentally
    # nested here; restored to _marriage_procedure above).


def _love_marriage_procedure(reading, router_out, trace, modifiers,
                             success, denial):
    """Love-marriage rule (AS Part 3 p.23):
    7th CSL -> [2,7,11] AND connected to 5th -> YES.
    7th CSL -> [2,7,11] but NO 5th connection -> NO (not a love marriage).
    """
    cusp7 = _rotated(7, router_out)
    sub7, agent7, chain7, _ = _csl_chain_7level(cusp7, reading)
    S = _R({2, 7, 11}, router_out)
    D = _R({1, 6, 10}, router_out)
    r5 = _rotated(5, router_out)
    s = sorted(chain7 & S)
    d = sorted(chain7 & D)
    has_5th = r5 in chain7
    # FIXED 2026-10-06 (W95, Bosmia Ex.102): if the 7th CSL IS the 5th CSL
    # (same planet), that counts as 5th connection. "7th and 5th sub lord
    # Moon ... thus love marriage."
    if not has_5th:
        cusp5 = _rotated(5, router_out)
        sub5, _, _, _ = _csl_chain_7level(cusp5, reading)
        if sub7 == sub5:
            has_5th = True
            trace.append({'rule': 'love_marriage_same_csl',
                          'citation': 'Bosmia Ex.102: 7th & 5th CSL both Moon',
                          'detail': '7th CSL %s == 5th CSL -> 5th connection '
                                    'satisfied' % sub7})
    trace.append({'rule': 'love_marriage_7th_5th',
                  'citation': 'AS Part 3 p.23',
                  'detail': '7th CSL %s -> [2,7,11] hit %s, [1,6,10] hit %s, '
                            '5th-house connection: %s'
                            % (sub7, s, d, has_5th)})
    if s and has_5th and not d:
        return 'YES', modifiers, trace, s, d
    if s and not has_5th:
        trace.append({'rule': 'love_marriage_no_5th',
                      'citation': 'AS Part 3 p.23',
                      'detail': 'marriage promised %s but no 5th connection '
                                '-> not a LOVE marriage -> NO' % s})
        return 'NO', modifiers, trace, s, d
    verdict, _ = _binary_verdict_d1(s, d, trace, modifiers, 'marriage', None,
                                    levels=_chain_levels(_levels_planet(sub7, agent7), reading) if agent7 else None)
    return verdict, modifiers, trace, s, d


def _divorce_procedure(reading, router_out, trace, modifiers, success, denial):
    """v10.3 divorce: 7th CSL decider (Reader IV, Taneja) - CONSERVATIVE.
    Book: "DIVORCE IS TO BE SEEN FROM HOUSES ONE SIX AND TEN."
    Only fires YES when BOTH [2,7,11] and [1,6,10] clearly present.
    Otherwise falls back to generic (does not force NO).
    """
    cusp7 = _rotated(7, router_out)
    sub7, agent7, chain7, _ = _csl_chain_7level(cusp7, reading)
    S = _R({2, 7, 11}, router_out)
    D = _R({1, 6, 10}, router_out)
    s = sorted(chain7 & S)
    d = sorted(chain7 & D)
    trace.append({'rule': 'divorce_7th_csl',
                  'citation': 'Reader IV; Taneja (1-6-10 = divorce)',
                  'detail': '7th CSL %s -> [2,7,11] hit %s, [1,6,10] hit %s'
                            % (sub7, s, d)})
    # Conservative: need BOTH for a divorce YES
    if s and d and len(s) >= 2 and len(d) >= 2:
        trace.append({'rule': 'divorce_mixed_signature',
                      'citation': 'Reader IV: mixed = separation then divorce',
                      'detail': 'strong [2,7,11] + [1,6,10] -> divorce YES'})
        if 'DELAYS' not in modifiers:
            modifiers.append('DELAYS')
        return 'YES', modifiers, trace, s, d
    # Not clear -> fall back to generic (don't force)
    # FIXED 2026-10-06 (W97): per Bosmia Ex.104, "1st alone does not work
    # alone" — if marriage houses present but 6-10 absent from the divorce
    # signature, return NO instead of None. Prevents generic mixed→YES+DELAYS
    # from manufacturing a divorce YES the book would never give.
    # 2026-10-15 (Claude review A3): d holds NATIVE chart houses (hits against
    # the _R-rotated D). The literal {6,10} missed third-party (turned)
    # questions — rotate it too.
    if s and not (set(d) & _R({6, 10}, router_out)):
        trace.append({'rule': 'divorce_no_6_10',
                      'citation': 'Bosmia Ex.104: 7th CSL must signify 6-10; '
                                  '"1st ... does not work alone"',
                      'detail': 'marriage houses %s present but 6-10 absent '
                                'from divorce signature %s -> NO' % (s, d)})
        return 'NO', modifiers, trace, s, d
    return None, modifiers, trace, s, d


def _spouse_return_procedure(reading, router_out, trace, modifiers, success,
                             denial):
    """v10.3 spouse return/reunion: 11th CSL decider (Bosmia Ex.196) -
    CONSERVATIVE three-tier.
    Book hint (Ex.196): "If the cuspal sub lord of the 11th be the
    significator of 2-7-11 reunion with spouse is promised."
    Taneja: "[1,6,10] negates reunion" -> hard NO.
    Otherwise -> None (fall back to generic, don't force).
    FIXED 2026-10-06 (W182): was 7th CSL, book uses 11th CSL.
    """
    cusp11 = _rotated(11, router_out)
    sub11, agent11, chain11, _ = _csl_chain_7level(cusp11, reading)
    D = _R({1, 6, 10}, router_out)
    s = sorted(chain11 & _R({2, 7, 11}, router_out))
    d = sorted(chain11 & D)
    # 2026-10-13 (USER RULING): retrograde 11th CSL = wife coming back = YES.
    # "If its a married wife coming back to his life then its a yes."
    # Retrograde = returning motion, favourable for return questions
    # (opposite of the hard-NO for new relationships).
    # 2026-10-14 (Gemini 4 audit): guard — don't fire YES when the chain
    # shows pure [1,6,10] divorce with zero [2,7,11]. Retrograde returning
    # motion can't overcome hard negation.
    _retro11 = _retro_map(reading)
    _retro_return = bool(_retro11.get(sub11, False)) or bool(_retro11.get(agent11, False))
    if _retro_return and not (d and len(d) >= 2 and not s):
        trace.append({'rule': 'spouse_return_retro_yes',
                      'citation': 'user ruling 2026-10-13: retrograde decider '
                                  '= returning = YES (spouse return)',
                      'detail': '11th CSL %s (agent %s) is retrograde -> '
                                'spouse is returning -> YES'
                                % (sub11, agent11)})
        return 'YES', modifiers, trace, s, d
    if _retro_return:
        trace.append({'rule': 'spouse_return_retro_blocked',
                      'citation': '2026-10-14: retrograde cannot overcome '
                                  '[1,6,10] negation',
                      'detail': '11th CSL retrograde but chain shows %s with '
                                'no [2,7,11] -> negation wins, fall through'
                                % d})
    trace.append({'rule': 'spouse_return_11th_csl',
                  'citation': 'Bosmia Ex.196 (11th CSL = reunion decider)',
                  'detail': '11th CSL %s -> [2,7,11] hit %s, [1,6,10] hit %s'
                            % (sub11, s, d)})
    # [1,6,10] negates reunion -> hard NO (only if strong)
    if d and len(d) >= 2:
        trace.append({'rule': 'spouse_return_negated',
                      'citation': 'Taneja: [1,6,10] negates reunion',
                      'detail': 'strong [1,6,10] -> reunion negated -> NO'})
        return 'NO', modifiers, trace, s, d
    # 2-7-11 on the 11th CSL -> YES (reunion promised)
    if s and len(s) >= 2:
        trace.append({'rule': 'spouse_return_promised',
                      'citation': 'Bosmia Ex.196: 11th CSL -> 2-7-11',
                      'detail': '11th CSL signifies %s -> reunion promised '
                                '-> YES' % s})
        return 'YES', modifiers, trace, s, d
    # Not clear -> fall back
    return None, modifiers, trace, s, d


def _romance_procedure(reading, router_out, trace, modifiers, success, denial,
                       event):
    """v10.3 romance: 5th CSL decider (Bosmia Ex.62) - CONSERVATIVE.
    Book: "If 5th cusp sub lord signifies 7 and 7th cusp sub lord signifies
    5, then only love marriage is promised."
    "If 5th cusp sub lord signifies 5-6-8-12 (10), termination of love affair."
    5th CSL must signify 7 for YES; 5-6-8-12 without 7 -> NO (termination).
    FIXED 2026-10-06 (W57): was [2,5,11] array, missed the book's 7-requirement
    and 8/12 termination houses.
    """
    cusp5 = _rotated(5, router_out)
    sub5, agent5, chain5, _ = _csl_chain_7level(cusp5, reading)
    # 2026-10-14 (Gemini 4 audit): romance_breakup is an ADVERSE event —
    # termination houses mean YES (breakup happens), 7+success means NO
    # (relationship endures). Invert the verdicts; do NOT apply the
    # retrograde hard-NO (that's for formation, not dissolution).
    _is_breakup = (event == 'romance_breakup')
    # 2026-10-13 (USER RULING): retrograde CSL decider = hard NO for relationship.
    # "Saturn on top of retrograde, for girlfriend and other relation to happen,
    # a retrograde is a hard no, specially if its CSL." Applies to the decider
    # planet itself being retrograde (distinct from D4: star-lord retrograde).
    # Skipped for breakup (dissolution, not formation).
    _retro = _retro_map(reading)
    if not _is_breakup and (bool(_retro.get(sub5, False)) or bool(_retro.get(agent5, False))):
        trace.append({'rule': 'romance_retro_csl_no',
                      'citation': 'user ruling 2026-10-13: retrograde CSL '
                                  'decider = hard NO (relationship)',
                      'detail': '5th CSL %s (agent %s) is retrograde -> '
                                'relationship cannot materialise -> NO'
                                % (sub5, agent5)})
        return 'NO', modifiers, trace, [], []
    # D4: decider's star-lord retrograde -> denial (Reader VI pp.146-147)
    # Skipped for breakup.
    _dec = agent5 or sub5
    if not _is_breakup and _d4_star_retro_check(reading, _dec, trace, 'romance',
                                                sub_lord=sub5):
        return 'NO', modifiers, trace, [], []
    S = _R({2, 5, 11}, router_out)
    # Termination array per Bosmia Ex.62: 5-6-8-12 (10). 2026-10-14
    # (3-AI adjudication, book-verified): 5 REMOVED from the termination set.
    # In Ex.62 the 5th CSL signified {11,12,7,1,2} and Bosmia judged
    # termination from the 12 -- the 5 is the topic prefix (the affair
    # itself), never separative. Bare-5 no longer counts as termination.
    D = _R({1, 6, 8, 10, 12}, router_out)
    s = sorted(chain5 & S)
    d = sorted(chain5 & D)
    r7 = _rotated(7, router_out)
    has_7th = r7 in chain5
    trace.append({'rule': 'romance_5th_csl',
                  'citation': 'Bosmia Ex.62: 5th CSL -> 7 required; 5-6-8-12 '
                              '= termination',
                  'detail': '%s: 5th CSL %s -> [2,5,11] hit %s, termination '
                            '[1,6,8,10,12] hit %s, 7th: %s'
                            % (event, sub5, s, d, has_7th)})
    # 5th CSL signifies 7 -> love promised.
    # For breakup: 7 + success = relationship endures -> NO (won't break up).
    # For formation: -> YES.
    if has_7th and s:
        _v = 'NO' if _is_breakup else 'YES'
        trace.append({'rule': 'romance_breakup_inverted' if _is_breakup else 'romance_promised',
                      'detail': '%s: 7th signified + %s -> %s' % (event, s, _v)})
        return _v, modifiers, trace, s, d
    # 5th CSL -> 6/8/12 without 7 -> termination.
    # For breakup: termination = YES (breakup happens).
    # For formation: -> NO (never generic YES)
    if d and not has_7th:
        _v = 'YES' if _is_breakup else 'NO'
        trace.append({'rule': 'romance_terminated',
                      'citation': 'Bosmia Ex.62: 5th CSL -> 5-6-8-12 = '
                                  'termination of love affair',
                      'detail': '5th CSL signifies %s without 7 -> %s'
                                % (d, 'breakup YES' if _is_breakup else 'affair terminates -> NO')})
        return _v, modifiers, trace, s, d
    return None, modifiers, trace, s, d


def _decide(reading, router_out, success, denial, primary, event, question):
    trace = []
    modifiers = []
    flags = _flags(question)

    # C1: second marriage -> 2nd CSL decider (cherry-pick; replaces v9's block)
    if event == 'second_marriage':
        return _second_marriage_procedure(reading, router_out, trace,
                                          modifiers, denial)

    # v10.3: marriage -> 7th CSL decider (vR7, RELATIONSHIP_ABLATION_REPORT).
    # Love-marriage questions intercept first (AS Part 3 p.23).
    # NOTE: marriage_love_specific removed 2026-10-06 (dead event, L1 never
    # routes here; love intercept in _marriage_procedure covers it).
    if event == 'marriage':
        # 2026-10-15 (review 1.4): delay/moon decors (see love intercept).
        _res = _marriage_procedure(reading, router_out, trace, modifiers,
                                   success, denial, question)
        _delay_decor(reading, success, _res[0], trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return _res

    # v10.3: divorce/spouse_return/romance - conservative, fall back to generic
    # if not confident (2026-10-06 rewrite after regressions)
    if event == 'divorce':
        result = _divorce_procedure(reading, router_out, trace, modifiers,
                                    success, denial)
        if result[0] is not None:  # confident -> use it
            # 2026-10-15 (review 1.4): delay/moon decors on confident path too.
            _delay_decor(reading, success, result[0], trace, modifiers)
            _moon_diagnostic(reading, success, trace, modifiers)
            return result
        # else fall through to generic below
    if event in ('spouse_return', 'spouse_return_estranged', 'reunion',
                   'romance_reunion'):
        result = _spouse_return_procedure(reading, router_out, trace,
                                          modifiers, success, denial)
        if result[0] is not None:
            # 2026-10-15 (review 1.4): delay/moon decors on confident path too.
            _delay_decor(reading, success, result[0], trace, modifiers)
            _moon_diagnostic(reading, success, trace, modifiers)
            return result
        # else fall through to generic below
    if event in ('romance_breakup', 'romance_materialise', 'romance_new_entry',
                 'friend_to_romance'):
        result = _romance_procedure(reading, router_out, trace, modifiers,
                                    success, denial, event)
        if result[0] is not None:
            # 2026-10-15 (review 1.4): delay/moon decors on confident path too.
            _delay_decor(reading, success, result[0], trace, modifiers)
            _moon_diagnostic(reading, success, trace, modifiers)
            return result
        # else fall through to generic below

    # C2: money_gain -> 2nd CSL procedure (cherry-pick)
    if event == 'money_gain':
        return _money_gain_procedure(reading, router_out, trace, modifiers,
                                     flags)

    # ---- v9.5: L1+2 funnel-repair new events (2026-10-03) ----
    # bonus_receive / business_expansion / job_abroad are ALREADY-COVERED-BY
    # existing procedures (l12_repair/layer3_procedures.json): dispatch only,
    # no new code.
    if event == 'bonus_receive':
        trace.append({'rule': 'bonus_receive_alias',
                      'citation': CIT['money_gain'],
                      'detail': 'bonus_receive is employment income -> routed '
                                'through _money_gain_procedure '
                                '(ALREADY-COVERED-BY:money_gain)'})
        return _money_gain_procedure(reading, router_out, trace, modifiers,
                                     flags)
    if event == 'business_expansion':
        trace.append({'rule': 'business_expansion_alias',
                      'citation': CIT['business_profit'],
                      'detail': 'business_expansion = business-gain ask -> '
                                'routed through _business_profit_procedure '
                                '(ALREADY-COVERED-BY:business_profit)'})
        return _business_profit_procedure(reading, router_out, trace,
                                          modifiers, success, denial)
    if event == 'job_abroad':
        trace.append({'rule': 'job_abroad_event',
                      'citation': CIT['job_abroad'],
                      'detail': 'job_abroad event -> _job_abroad_procedure '
                                '(ALREADY-COVERED-BY:job_get_service; same '
                                'path as the job_get_service abroad '
                                'detector)'})
        return _job_abroad_procedure(reading, router_out, trace,
                                     modifiers, success, denial)
    if event == 'job_continuity':
        return _job_continuity_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
    if event == 'business_partnership':
        return _business_partnership_procedure(reading, router_out, trace,
                                               modifiers, success, denial,
                                               question)
    if event == 'exam_appear':
        # 2026-10-15 (review 1.4): delay/moon decors like the other exam paths.
        _res = _exam_appear_procedure(reading, router_out, trace,
                                      modifiers, success, denial)
        _delay_decor(reading, success, _res[0], trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return _res
    # v10.2 (user ruling 2026-10-05, exam ablation): D2 3rd-bar FULLY REMOVED.
    # The old "any 3rd-house hit -> NO" is contradicted three ways (AS Part 5
    # p.82; CA-Inter pass with 3rd present; Bosmia Ex.169). Exam events now use
    # clean binary verdicts without the 3rd-bar.
    if event in EXAM_EVENTS:
        # v10.2: rank/distinction questions (E1-6) checked BEFORE the standard
        # exam procedure. Book: 1st+4th CSL -> [3,6,10]. Detected by rank
        # keywords; not a pass/fail question.
        # SCOPED 2026-10-06 (W160 fix): was outside this block, fired on
        # career "position in" questions.
        if _is_rank_question(question):
            # 2026-10-15 (review 1.4): delay/moon decors.
            _res = _exam_rank_procedure(reading, router_out, trace, modifiers)
            _delay_decor(reading, success, _res[0], trace, modifiers)
            _moon_diagnostic(reading, success, trace, modifiers)
            return _res
        # 2026-10-15 (review 1.4): delay/moon decors — fixes the open Q2
        # "should display DELAY" item (exam YES never got DELAYS attached).
        _res = _exam_no_third_bar(reading, router_out, trace, modifiers,
                                  success, denial, event, question)
        _delay_decor(reading, success, _res[0], trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return _res
    if event == 'scholarship':
        return _scholarship_procedure(reading, router_out, trace,
                                      modifiers, success, denial)
    if event == 'job_voluntary_exit':
        return _job_voluntary_exit_procedure(reading, router_out, trace,
                                             modifiers, success, denial)
    if event == 'job_relocation':
        return _job_relocation_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
    if event == 'money_lent_recovery':
        return _money_lent_recovery_procedure(reading, router_out, trace,
                                              modifiers, success, denial)
    if event == 'chitfund_kitty_receive':
        return _chitfund_kitty_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
    if event == 'business_closure_decision':
        return _business_closure_procedure(reading, router_out, trace,
                                           modifiers, success, denial)
    if event == 'financial_help_receive':
        return _financial_help_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
    if event == 'financial_crisis_relief':
        return _financial_crisis_procedure(reading, router_out, trace,
                                           modifiers, success, denial)
    if event == 'thesis_submission':
        return _thesis_submission_procedure(reading, router_out, trace,
                                            modifiers, success, denial)

    # ---- v9.7 money-batch-2 (2026-10-05) ----
    if event == 'lottery':
        return _lottery_procedure(reading, router_out, trace, modifiers,
                                  success, denial)
    if event == 'donation_receive':
        # 2026-10-15 (review 1.4): delay/moon decors.
        _res = _donation_receive_procedure(reading, router_out, trace,
                                           modifiers, success, denial)
        _delay_decor(reading, success, _res[0], trace, modifiers)
        _moon_diagnostic(reading, success, trace, modifiers)
        return _res
    # v10.1 (user-ordered 2026-10-05, MISS_ANALYSIS): vehicle_purchase requires
    # 4th CSL to signify 4 as a NECESSARY condition (the documented 5:1 YES-bias
    # came from skipping this). Without 4, no vehicle promise.
    if event == 'vehicle_purchase':
        cusp4 = _rotated(4, router_out)
        sub4, agent4, chain4, _ = _csl_chain(cusp4, reading)
        has4 = _rotated(4, router_out) in chain4
        s4 = sorted(chain4 & _R({4, 9, 10, 11}, router_out))
        trace.append({'rule': 'vehicle_purchase_4th_necessity',
                      'citation': 'MISS_ANALYSIS 2026-10-05 (4th-necessity)',
                      'detail': '4th CSL %s chain %s -> 4 present=%s, '
                                '[4,9,10,11] hit %s' % (sub4, sorted(chain4),
                                                        has4, s4)})
        if not has4:
            return 'OTHER', modifiers, trace, [], []
        return _v9_decide(reading, router_out, success, denial, primary,
                          event, question)
    if event == 'provident_fund_pension':
        return _provident_fund_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
    if event == 'loan_borrow_get':
        return _loan_borrow_procedure(reading, router_out, trace,
                                      modifiers, success, denial)
    if event == 'loan_repay_clear':
        return _loan_repay_procedure(reading, router_out, trace, modifiers)

    # ---- career-first module (C5-C11) ----
    if event in CAREER_EVENTS:
        # C10: interview — the interview round itself (tight detector)
        if _is_interview_question(question):
            trace.append({'rule': 'interview_detected',
                          'citation': CIT['interview'],
                          'detail': 'interview-centric question detected'})
            return _interview_procedure(reading, router_out, trace,
                                        modifiers, success, denial)
        # E4 (v9.4): foreign job / foreign assignment — narrow detector,
        # only for generic job-get questions (promotion/transfer/etc. have
        # their own procedures)
        if event == 'job_get_service' \
                and _is_abroad_job_question(question):
            trace.append({'rule': 'abroad_job_detected',
                          'citation': CIT['job_abroad'],
                          'detail': 'foreign-job question detected'})
            return _job_abroad_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
        # PLACE-CHANGE (2026-10-06, W25/Bosmia Ex.27): "job in <place>"
        # -> 3rd CSL transfer procedure, not generic job_get.
        # 2026-10-15 (Claude review A7): tightened via _place_change_hit —
        # bare 'job in '/'job at ' misrouted companies ("job at TCS").
        if event == 'job_get_service' and _place_change_hit(question):
            trace.append({'rule': 'place_change_detected',
                          'citation': 'Bosmia Ex.27: place-change = 3rd CSL',
                          'detail': '"job in <place>" detected -> 3rd CSL '
                                    'transfer procedure'})
            return _transfer_procedure(reading, router_out, trace,
                                       modifiers, success, denial)
        # C5: promotion -> 11th CSL (event procedures beat named-job:
        # "promoted to General Manager" is a promotion question, not a
        # job-naming question)
        if event == 'promotion':
            return _promotion_procedure(reading, router_out, trace,
                                        modifiers, success, denial)
        # C6: transfer -> 10th CSL 2-of-3
        if event == 'transfer_job':
            return _transfer_procedure(reading, router_out, trace,
                                       modifiers, success, denial)
        # C7/C8: business
        if event == 'business_start':
            return _business_start_procedure(reading, router_out, trace,
                                             modifiers, success, denial)
        if event == 'business_profit':
            return _business_profit_procedure(reading, router_out, trace,
                                              modifiers, success, denial)
        # D5 (v9.3): business loss / recovery — new dedicated procedure
        if event == 'business_loss':
            return _business_loss_procedure(reading, router_out, trace,
                                            modifiers, success, denial)
        # C9: dismissal / position loss
        if event == 'job_loss_dismissal':
            return _dismissal_procedure(reading, router_out, trace,
                                        modifiers, success, denial)
        # position_lose: Bosmia Ex.124 — 8th CSL -> {5,9,12} (BOOK 2026-10-06)
        if event == 'position_lose':
            # 2026-10-15 (review 1.4): delay/moon decors.
            _res = _position_lose_procedure(reading, router_out, trace,
                                            modifiers, success, denial)
            _delay_decor(reading, success, _res[0], trace, modifiers)
            _moon_diagnostic(reading, success, trace, modifiers)
            return _res
        # E2 (v9.4): reinstatement / regaining position
        if event == 'position_regain':
            return _reinstatement_procedure(reading, router_out, trace,
                                            modifiers, success, denial)
        # E3 (v9.4): retirement
        if event == 'retirement_decision':
            return _retirement_procedure(reading, router_out, trace,
                                         modifiers, success, denial)
        # C11: the user's job rule — named specific job (only when no
        # event procedure claimed it). Round-2 refinement: the routing is
        # event-aware. "Become a successful X" (career_suitability) is not
        # a job-getting question — the 11th-CSL desired-post test broke
        # W128/W129 there. Suitability uses the job's own cusp instead.
        if event in ('job_get_service', 'career_suitability'):
            job_hit = _detect_named_job(question, flags)
            if job_hit is not None:
                job_key, mapping = job_hit
                if mapping is not None:
                    if event == 'career_suitability':
                        return _suitability_procedure(
                            reading, router_out, trace, modifiers,
                            success, denial, job_key, mapping)
                    return _known_job_route(reading, router_out, trace,
                                            modifiers, job_key, mapping,
                                            flags, success, denial)
                trace.append({'rule': 'unknown_job_detected',
                              'citation': CIT['unknown_job'],
                              'detail': 'named job "%s" not in knowledge '
                                        'table -> 11th CSL + 11th lord rule'
                                        % job_key})
                return _unknown_job_procedure(reading, router_out, trace,
                                              modifiers, job_key)
            # D11 (v9.3 round-2, REVERTED): the 2-6-10 variant was tested
            # and REJECTED. Round-2 measurement: career 72.3% -> 63.6%
            # (-8.7pp), FP 21 -> 34. The books (KSK Reader VI true pp.285-288;
            # Bosmia 12x hint) say 2-6-10, but the data says v9's 2-6-10-11
            # works better. Honest finding: book doctrine and measurement
            # contradict here. Reverted to v9's path. Staged for the user.
        # everything else career -> v9's exact dispatch (government,
        # high_post, desired_job qualifiers, default binary path)
        return _v9_decide(reading, router_out, success, denial, primary,
                          event, question)

    # all other topics: v9 exact (plus C1/C2 above)
    return _v9_decide(reading, router_out, success, denial, primary,
                      event, question)


def _judge(router_out, city, horary_number, as_of=None, coords=None):
    _event_early = router_out.get('event_key') or 'unknown'
    # B2c (v9.7): loan_repay_clear runs the v9.7-native procedure (planet
    # modes + Saturn-aspect PARTIAL); the shared layer2b router is left
    # untouched for all other judges.
    if router_out.get('status') == 'exception' and _event_early != 'loan_repay_clear':
        out = L3T.judge(router_out, city, horary_number,
                        as_of=as_of, coords=coords)
        out['method'] = 'layer2b-exception (v9.7-native repay)'
        out['v9_5_trace'] = [{'rule': 'exception_delegate',
                              'citation': 'layer2b procedure (as v6)',
                              'detail': 'exception event: delegated to the '
                                        'registered Layer-2b procedure'}]
        return out
    _repay_native = (router_out.get('status') == 'exception'
                     and _event_early == 'loan_repay_clear')
    if router_out.get('status') != 'ok' and not _repay_native:
        return {'status': 'error',
                'reason': 'layer-2 did not produce a routable result',
                'router': router_out}

    success = set(router_out.get('success') or [])
    denial = set(router_out.get('denial') or [])
    # B2c (v9.7): exception router_outs (loan_repay_clear) carry no
    # primary_cusp; fall back to relative_house.
    primary = int(router_out.get('primary_cusp')
                  or router_out.get('relative_house') or 12)
    event = router_out.get('event_key') or 'unknown'
    question = router_out.get('question') or ''

    # v10.1 money cusp/array corrections MOVED to events.json 2026-10-14
    # (Gemini 4 audit): stock_speculation [2,5,6,11], inheritance_claim
    # cusp 9 / [2,11], property_sale cusp 10 / [3,5,10] now live in Layer 2
    # so rotation + denial generation happen cleanly in one place.

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
        'method': 'v9.7-money-batch-2',
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
        'v9_5_trace': trace,
        'timing_eligible': timing_eligible,
        'primary_cusp': primary,
        'rotated': bool(router_out.get('rotated')),
        'answerability': {
            'status': 'OK' if verdict in ('YES', 'NO', 'PARTIAL') else 'INSUFFICIENT',
        },
        'provenance': {
            'layer3': 'v9.7 money-batch-2 (citations in v9_5_trace)',
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
                'reason': 'v9.4 judgment failed: %s' % str(e)[:200]}
