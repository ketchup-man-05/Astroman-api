"""v5 Layer 4 — flag-only diagnostic modifiers (all OURS). [v5.1]

REVIEW CHANGE 2026-09-30 (compendium review, priority 2):
automatic verdict reversals REMOVED. No Layer 4 rule may reverse a clear
YES or NO anymore. Each former override now emits a diagnostic FLAG
(modifier) on the reading; the verdict is byte-untouched.

  return_override  -> RETURN_EVENT_CONFLICT        (was NO->YES flip)
  love_retro_veto  -> RETROGRADE_FRICTION_OR_REVIEW (was ->NO flip)
  toxicity         -> HEAVY_OBSTRUCTION_OR_RISK_SIGNAL (was OTHER->NO flip)
  occupancy_rescue -> OCCUPANCY_SUPPORT             (was OTHER/NO->YES flip)

Rationale (review): 16/20 and 4/4 development-slice results do not justify
unconditional reversals; OTHER-touching-8/12->NO was an absolute 8/12 veto
in disguise (a rejected rule); occupancy must not defeat a negative
stellar chain by itself.

Policy going forward:
  - flags may add modifiers; flags may refine OTHER into a more informative
    OTHER subtype note; flags NEVER change the verdict;
  - verdict-changing behavior requires fresh, prospective evidence AND
    evaluation against a frozen control (not the development corpus).

The config flags (default OFF since the 2026-09-28 blind-test ruling) now
gate flag EMISSION. Even with a flag forced on, no flip is possible.

Each flag function takes (judge_out, ctx) and returns None (no fire) or
{'name': ..., 'modifier': ..., 'why': ..., 'label': 'OURS'}.
"""

from engine import config as _cfg

FATAL_HOUSES = {8, 12}

# Romance events only. Pooled retro-denial across all topics measured 38%
# (VARIANT_UB) — the love flag must NEVER generalize beyond this set.
ROMANCE_EVENTS = {'romance_materialise', 'romance_breakup',
                  'romance_reunion', 'friend_to_romance'}

# Substrings matching return/recovery-type events.
RETURN_KEYS = ('return', 'reunion', 'missing_person', 'misplaced_item')


def return_override(judge_out, ctx):
    """OURS flag. Return/reunion/missing/misplaced question whose chart
    denies (NO, or OTHER with denial-hits-only): keep the verdict, flag the
    conflict. "Return" is not a reason a denial becomes a promise; the
    follow-up outcome should be RECORDED, not assumed."""
    key = (ctx.get('event_key') or '')
    if not any(k in key for k in RETURN_KEYS):
        return None
    v = judge_out.get('verdict_class')
    fires = (v == 'NO') or (v == 'OTHER' and judge_out.get('denial_hit')
                            and not judge_out.get('success_hit'))
    if not fires:
        return None
    return {'name': 'return_override', 'label': 'OURS',
            'modifier': 'RETURN_EVENT_CONFLICT',
            'why': ('Return-type question with a denying/denial-only chart '
                    f'(verdict kept: {v}). Returns are often reality-YES '
                    '(NIGHT_REPORT 4a: 16/20 on a dev slice) — record the '
                    'follow-up outcome; do not flip the verdict.')}


def occupancy_rescue(judge_out, ctx):
    """OURS flag. Deciding planet OCCUPIES a success house (occupation
    levels) while OWNING none -> OCCUPANCY_SUPPORT. Occupancy may
    strengthen an existing promise or reduce abstention ONLY after separate
    validation; it never converts NO to YES by itself."""
    v = judge_out.get('verdict_class')
    if v not in ('OTHER', 'NO'):
        return None
    levels = judge_out.get('levels') or {}
    success = set(ctx.get('success') or [])
    occ = {levels.get('step_1_house'), levels.get('step_2_house')}
    occ.discard(0)
    occ.discard(None)
    own = set(levels.get('step_3_houses') or []) | \
        set(levels.get('step_4_houses') or [])
    if (occ & success) and not (own & success):
        return {'name': 'occupancy_rescue', 'label': 'OURS',
                'modifier': 'OCCUPANCY_SUPPORT',
                'why': (f"Deciding planet occupies success house(s) "
                        f"{sorted(occ & success)} but owns none "
                        f"(verdict kept: {v}). NIGHT_REPORT 4b: 71% "
                        f"reality-YES on a dev slice — supportive signal "
                        f"only, not a verdict changer.")}
    return None


def toxicity(judge_out, ctx):
    """OURS flag. OTHER verdict whose signified houses touch fatal houses
    {8,12} -> HEAVY_OBSTRUCTION_OR_RISK_SIGNAL. The old OTHER->NO flip was
    an absolute 8/12 veto in disguise (a rejected rule); contact with 8/12
    on an abstention must not manufacture a definite NO."""
    v = judge_out.get('verdict_class')
    if v != 'OTHER':
        return None
    fatal = set(judge_out.get('signified_houses') or []) & FATAL_HOUSES
    if fatal:
        return {'name': 'toxicity', 'label': 'OURS',
                'modifier': 'HEAVY_OBSTRUCTION_OR_RISK_SIGNAL',
                'why': (f'Mixed/empty signification touching fatal house(s) '
                        f'{sorted(fatal)} (verdict kept: OTHER). Heavy '
                        f'obstruction/risk signal — not a denial without an '
                        f'event-specific verified rule.')}
    return None


def love_retro_veto(judge_out, ctx):
    """OURS flag, ROMANCE EVENTS ONLY. Deciding planet retrograde (rule A)
    or its star-lord retrograde (rule B) -> RETROGRADE_FRICTION_OR_REVIEW.
    VARIANT_UB went 4/4 on the love slice but pooled retro-denial is 38%,
    so this stays an experimental romance-only flag, never an auto-NO."""
    if (ctx.get('event_key') or '') not in ROMANCE_EVENTS:
        return None
    v = judge_out.get('verdict_class')
    if v == 'NO':
        return None  # already denied; nothing to add
    retro = judge_out.get('planet_retro') or {}
    dp = judge_out.get('deciding_planet')
    sl = judge_out.get('star_lord')
    if dp and retro.get(dp):
        return {'name': 'love_retro_veto', 'label': 'OURS',
                'modifier': 'RETROGRADE_FRICTION_OR_REVIEW',
                'why': (f'Rule A (VARIANT_UB, experimental): deciding planet '
                        f'{dp} retrograde on a romance question '
                        f'(verdict kept: {v}). Friction/review, not denial.')}
    if sl and retro.get(sl):
        return {'name': 'love_retro_veto', 'label': 'OURS',
                'modifier': 'RETROGRADE_FRICTION_OR_REVIEW',
                'why': (f'Rule B (VARIANT_UB, experimental): deciding planet '
                        f'{dp} direct but star-lord {sl} retrograde '
                        f'(verdict kept: {v}). Friction/review, not denial.')}
    return None


_FLAG_FNS = (
    ('LOVE_RETRO_VETO', love_retro_veto),
    ('RETURN_OVERRIDE', return_override),
    ('TOXICITY', toxicity),
    ('OCCUPANCY_RESCUE', occupancy_rescue),
)


def apply_overrides(judge_out, ctx):
    """Evaluate all enabled Layer-4 flags. Returns (flags, []) where flags
    is a list of flag dicts (possibly empty). The verdict is NEVER changed
    here — the pipeline appends flag modifiers to the reading's modifiers.

    Flags never run on exception-procedure verdicts (no signification
    arrays there) and never touch a BOOK gate (the pipeline short-circuits
    gates before this is called).
    """
    if not judge_out or judge_out.get('status') != 'ok':
        return [], []
    if judge_out.get('exception'):
        return [], []
    flags = []
    for cfg_flag, fn in _FLAG_FNS:
        if not getattr(_cfg, cfg_flag, False):
            continue
        try:
            hit = fn(judge_out, ctx)
        except Exception:
            hit = None
        if hit:
            flags.append(hit)
    return flags, []
