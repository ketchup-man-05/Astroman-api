"""v5 Layer 2b — exception router.

Some events cannot be judged by house arrays at all: the books prescribe a
*procedure* instead (e.g. loan repayment = 12th-cusp + retrograde test).
These events carry an "exception" descriptor in events.json:

    "exception": {"procedure": "loan_repay",
                  "provenance": "BOOK:R6:L12420-12435",
                  "params": {"cusp": 12}}

Design rule: exceptions are DATA, not code. This module's router
(run_exception) contains no event-specific logic — it reads the descriptor
and dispatches to a registered procedure in PROCEDURES. Adding a new
exception = one events.json entry + one @procedure function. Nothing else
changes.

Procedures receive the CAST CHART (the frozen engine's reading dict:
cusp_facts + planet_facts, read-only) and return a verdict dict:
    {"verdict": "YES"/"NO"/"UNCLEAR", "detail": "...",
     "modifiers": [...], "procedure": name, "provenance": ...}
instead of house arrays. They never raise; UNCLEAR is always preferred
over a guess.

RETROGRADE TENSION (documented, user-visible): the book's loan procedure
states a HARD retrograde denial ("if either is retrograde, one cannot
repay"). The user's general ruling says retrograde = delay, never denial.
Inside exceptions the book is kept verbatim (that is what exceptions are
for: book-specific procedures the general rules do not reach) UNLESS
config.EXCEPTION_RETRO_BOOK_VERBATIM is set False, in which case the
denial softens to YES-with-delay. See V5_BUILD_NOTES.md.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

PROCEDURES = {}


def procedure(name):
    """Register a procedure function under `name`."""
    def deco(fn):
        PROCEDURES[name] = fn
        return fn
    return deco


def _get_config():
    import importlib.util
    path = os.path.join(_HERE, 'config.py')
    spec = importlib.util.spec_from_file_location('v5_config_l2b', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cusp_map(reading):
    return {f['house']: f for f in (reading.get('cusp_facts') or [])}


def _planet_map(reading):
    return {f['planet']: f for f in (reading.get('planet_facts') or [])}


def _shift(base, cusp):
    """Bhavat Bhavam: the person's `cusp`, counted from their own house."""
    return ((int(base) - 1) + (int(cusp) - 1)) % 12 + 1


def _verdict(verdict, detail, modifiers, name, provenance):
    return {'verdict': verdict, 'detail': detail,
            'modifiers': list(modifiers), 'procedure': name,
            'provenance': provenance}


def run_exception(descriptor, reading):
    """Dispatch an L2 'exception' descriptor against a cast chart.

    descriptor: {'procedure', 'params', 'subject_base', ...} from L2.
    reading:    frozen-engine reading dict (cusp_facts, planet_facts).
    Never raises.
    """
    try:
        name = descriptor.get('procedure')
        fn = PROCEDURES.get(name)
        if fn is None:
            return _verdict('UNCLEAR', f'no procedure registered for {name!r}',
                            [], name, 'OURS')
        return fn(descriptor, reading or {})
    except Exception as e:
        return _verdict('UNCLEAR', f'procedure error: {e}'[:160], [],
                        descriptor.get('procedure'), 'OURS')


# --------------------------------------------------------------------------
# loan_repay — BOOK (R6:L12420-12435)
# "judge the 12th cusp and find out whether the lord of the sub of the 12th
# cusp is either retrograde or deposited in a constellation whose lord is
# retrograde. If either is retrograde, one cannot either invest or repay
# loan. If the sub lord and the lord of the constellation ... is in direct
# motion, then one will invest or repay loan. If it is Saturn, then there
# will be delay and some obstacles to repay. If it is Mercury, one will
# correspond, send agent and repay in instalments. If it is Jupiter, by
# lawful means all the legitimate amount will be repayed. If Mars is the
# sub lord, the lender threatens and then [repays]."
# --------------------------------------------------------------------------
@procedure('loan_repay')
def _loan_repay(descriptor, reading):
    name = 'loan_repay'
    prov = descriptor.get('provenance', {}).get('tables', 'BOOK:R6:L12420-12435')
    base = int(descriptor.get('subject_base') or 1)
    cusp = _shift(base, int(descriptor.get('params', {}).get('cusp', 12)))
    cm, pm = _cusp_map(reading), _planet_map(reading)
    cf = cm.get(cusp)
    if cf is None:
        return _verdict('UNCLEAR', f'{cusp}th cusp facts missing from chart',
                        [], name, prov)
    csl = cf['sub_lord']
    cslf = pm.get(csl, {})
    star = cslf.get('star_lord')
    csl_retro = bool(cslf.get('is_retrograde'))
    star_retro = bool(pm.get(star, {}).get('is_retrograde'))
    # Frozen engine marks nodes is_retrograde=False (always retrograde in
    # motion, but not a retro *flag* in KP judgment) — no false trigger.

    cfg = _get_config()
    book_verbatim = bool(getattr(cfg, 'EXCEPTION_RETRO_BOOK_VERBATIM', True))

    mods = []
    if csl == 'Saturn':
        mods.append('delay and some obstacles to repay (book: Saturn sub-lord)')
    elif csl == 'Mercury':
        mods.append('repay in instalments; correspond / send agent (book)')
    elif csl == 'Jupiter':
        mods.append('lawful means; full legitimate amount repaid (book)')
    elif csl == 'Mars':
        mods.append('lender threatens first, then repayment (book)')

    if csl_retro or star_retro:
        who = csl if csl_retro else f"star lord {star} of {csl}"
        detail = (f'BOOK R6:L12420: {who} is retrograde -> '
                  f'"one cannot either invest or repay loan" ({cusp}th cusp)')
        if not book_verbatim:
            return _verdict('YES', detail + ' [softened: config says delay-only]',
                            mods + ['retrograde read as delay, per config'], name, prov)
        return _verdict('NO', detail, [], name, prov)
    return _verdict(
        'YES',
        (f'BOOK R6:L12420: {cusp}th cusp sub-lord {csl} and its star lord '
         f'{star} both direct -> will repay the loan'),
        mods, name, prov)


# --------------------------------------------------------------------------
# missing_person_status — OURS
# Simplified from the book's note (R6:L8695-8710: take the relationship
# house - 9th for strangers/father; its CSL in maraka/badhaka constellations
# -> dead, in that house's own constellations -> alive). v5's simplification:
# 9th CSL; its star lord owning 2 or 7 (marakas) -> not alive; owning 9 ->
# alive; anything else -> UNCLEAR. The full counted-from-that-house badhaka
# refinement is NOT implemented (documented simplification).
# --------------------------------------------------------------------------
@procedure('missing_person_status')
def _missing_person_status(descriptor, reading):
    name = 'missing_person_status'
    prov = descriptor.get('provenance', {}).get('tables', 'OURS')
    # 2026-10-14 (Gemini 4 audit, KSK Reader VI L8695-8710): maraka houses
    # are RELATIVE to the missing person's ascendant, not fixed 2/7.
    base = int(descriptor.get('subject_base') or 1)
    person_asc = base if base != 1 else 9
    # 2026-10-15 (review 1.9): judge the PERSON's ascendant cusp, not the
    # hardcoded params cusp 9. (person_asc is 9 when base==1, preserving
    # the old stranger/self behavior.)
    cusp = person_asc
    maraka = {_shift(person_asc, 2), _shift(person_asc, 7)}
    cm, pm = _cusp_map(reading), _planet_map(reading)
    cf = cm.get(cusp)
    if cf is None:
        return _verdict('UNCLEAR', f'{cusp}th cusp facts missing from chart',
                        [], name, prov)
    csl = cf['sub_lord']
    star = pm.get(csl, {}).get('star_lord')
    owned = set(pm.get(star, {}).get('owns_houses', []) or [])
    if owned & maraka:
        return _verdict('NO', (f'OURS: {cusp}th CSL {csl}\'s star lord {star} '
                               f'owns maraka houses {sorted(owned & maraka)} (from person house {person_asc}) '
                               f'-> not alive'),
                        [], name, prov)
    if person_asc in owned:
        return _verdict('YES', (f'OURS: {cusp}th CSL {csl}\'s star lord {star} '
                                f'owns the {person_asc}th (person\'s ascendant) -> alive'),
                        [], name, prov)
    return _verdict('UNCLEAR', (f'OURS: {csl}\'s star lord {star} owns '
                                f'{sorted(owned) or "nothing relevant"} - '
                                f'neither maraka nor {person_asc}th; will not guess'),
                    [], name, prov)


# --------------------------------------------------------------------------
# infidelity_detect — OURS (2026-09-29)
# "Is my partner cheating on me" asks whether something is TRUE RIGHT NOW —
# a present-fact detection like rumor_true, not a future-outcome array.
# Method adapted from Phase-2 youtube_research/extra/partner_fidelity.md
# Video 1 (KP natal walkthrough): 5+8 = scandalous/illegal love affair,
# read from the 5th CSL (primary) with the 8th CSL as secondary check.
# NO prashna-case walkthrough was found in the research, so this is an
# honest adaptation: YES only on the clean 5+8 pattern, NO when neither
# 5 nor 8 is signified, UNCLEAR otherwise. Never guessed.
# Tone: the caller flags this as an accusatory question about a real
# relationship — the reading must stay gentle regardless of verdict.
# --------------------------------------------------------------------------
@procedure('infidelity_detect')
def _infidelity_detect(descriptor, reading):
    name = 'infidelity_detect'
    prov = descriptor.get('provenance', {}).get('tables', 'OURS')
    # 2026-10-14 (Gemini 4 audit): INVARIANT to subject_base. "Is he cheating?"
    # (base=1) and "Is my husband cheating?" (base=7) must judge the same
    # cusps. Always use unrotated 5th (romance) and 8th (secrecy) from lagna.
    # (OURS adaptation — no prashna book source; keep consistent.)
    cusp5, cusp8 = 5, 8
    cm, pm = _cusp_map(reading), _planet_map(reading)
    tone = ('tone:sensitive — accusatory question about a real relationship; '
            'keep the reading gentle')

    def _signified(cusp):
        cf = cm.get(cusp)
        if cf is None:
            return None
        csl = cf['sub_lord']
        cslf = pm.get(csl, {})
        star = cslf.get('star_lord')
        starf = pm.get(star, {})
        houses = set()
        for h in (cslf.get('house_occupied'), starf.get('house_occupied')):
            if h:
                houses.add(h)
        houses |= set(cslf.get('owns_houses') or [])
        houses |= set(starf.get('owns_houses') or [])
        return csl, star, houses

    r5 = _signified(cusp5)
    if r5 is None:
        return _verdict('UNCLEAR', f'{cusp5}th cusp facts missing from chart',
                        [tone], name, prov)
    csl5, star5, h5 = r5
    r8 = _signified(cusp8)
    h8 = r8[2] if r8 else set()

    pat5 = ({5, 8} <= h5)
    pat8 = ({5, 8} <= h8)
    if pat5 or pat8:
        which = f'{cusp5}th' if pat5 else f'{cusp8}th'
        return _verdict(
            'YES',
            (f'OURS (Phase-2 Video 1: 5+8 = affair pattern): {which} CSL '
             f'{csl5 if pat5 else r8[0]} signifies both 5 and 8 '
             f'(via star lord {star5 if pat5 else r8[1]}) -> affair indicated'),
            [tone], name, prov)
    if not ({5, 8} & h5) and not ({5, 8} & h8):
        return _verdict(
            'NO',
            (f'OURS: neither the {cusp5}th nor the {cusp8}th CSL signifies '
             f'5 or 8 -> no affair pattern'),
            [tone], name, prov)
    return _verdict(
        'UNCLEAR',
        (f'OURS: partial pattern only ({cusp5}th CSL {csl5} signifies '
         f'{sorted(h5 & {5, 8}) or "neither 5 nor 8"}) — will not guess'),
        [tone], name, prov)


# --------------------------------------------------------------------------
# rumor_true — OURS
# 3rd house = rumours/messages (verified in Readers house lists). The planet
# rule (Jupiter=true; Saturn/Mars/Rahu/Ketu=false) is practitioner lore,
# NOT found in the Readers. Any other planet -> UNCLEAR, never guessed.
# --------------------------------------------------------------------------
@procedure('rumor_true')
def _rumor_true(descriptor, reading):
    name = 'rumor_true'
    prov = descriptor.get('provenance', {}).get('tables', 'OURS')
    # 2026-10-14 (Gemini 4 audit, KSK Reader VI pp.146, 155-159): rumor is
    # ALWAYS the querent's unrotated 3rd cusp (news reaching the querent),
    # regardless of who the rumor is about. Never _shift by subject_base.
    cusp = 3
    cm = _cusp_map(reading)
    cf = cm.get(cusp)
    if cf is None:
        return _verdict('UNCLEAR', f'{cusp}th cusp facts missing from chart',
                        [], name, prov)
    csl = cf['sub_lord']
    if csl == 'Jupiter':
        return _verdict('YES', (f'OURS: {cusp}th CSL is Jupiter -> news is true'),
                        [], name, prov)
    if csl in ('Saturn', 'Mars', 'Rahu', 'Ketu'):
        return _verdict('NO', (f'OURS: {cusp}th CSL is {csl} -> news false or '
                               f'maliciously exaggerated'),
                        [], name, prov)
    return _verdict('UNCLEAR', (f'OURS: {cusp}th CSL is {csl} - no verified rule '
                                f'for this planet; will not guess'),
                    [], name, prov)
