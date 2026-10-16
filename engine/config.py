"""v5 configuration flags. All rulings recorded here with their source."""

# Ruling (a), user 2026-09-28: follow the book (Reader VI L5198, L17750).
# The original 1-249 number is KEPT on clarification; only the chart moment
# (planetary positions) refreshes to the moment of clear understanding.
KEEP_NUMBER_ON_CLARIFICATION = True

# Ruling: the retrograde failsafe from the design PDF is KEPT for v5
# (retrograde deciding/ruling planet -> delay/friction, never a hard denial),
# but it is flagged for empirical cross-check once v5 runs on real outcomes.
# The absolute retro veto was killed by the user's own blind-100 ruling;
# v5 must never reintroduce a hard retro denial without new data.
RETRO_MODE = 'delay'   # 'delay' | (no other mode is currently authorized)

# Layer-1 fallback: when dictionary extraction cannot handle a question,
# call the Gemini free tier with a strict JSON-only prompt. Degrades
# gracefully to clarification when no GEMINI_API_KEY is configured.
GEMINI_FALLBACK = True
GEMINI_MODEL = 'gemini-flash-latest'
GEMINI_TIMEOUT_S = 25

# Time-window handling, ruling (b) user 2026-09-28: never guess the window.
# If the question states no window, the caller must ask "By when?" —
# timing_v5 refuses to run without one.
ASK_WINDOW_WHEN_ABSENT = False  # user ruling: open When? allowed

# Layer-2b exceptions: the book's loan-repay procedure (R6:L12420-12435)
# states a HARD retrograde denial ("if either is retrograde, one cannot
# repay"). The user's general ruling says retrograde = delay, never denial.
# Inside exceptions the book is kept VERBATIM while this flag is True —
# that is what exceptions are for: book-specific procedures the general
# rules do not reach. Set False to soften to YES-with-delay inside
# exceptions too. Either way the tension is documented in V5_BUILD_NOTES.md.
EXCEPTION_RETRO_BOOK_VERBATIM = False  # user ruling: retro=delay, not denial

# ---------------------------------------------------------------------------
# Layer-4 overrides (2026-09-28). All four are OURS: empirically validated on
# the 369-case corpus (night experiments), NOT Krishnamurti doctrine. They sit
# OUTSIDE the traditional core (layer3_traditional is untouched logic) as
# labeled, switch-off-able verdict flips. Precedence:
#   love_retro_veto > return_override > toxicity > occupancy_rescue
# At most one fires per reading; the rest are recorded as considered_not_applied.

# Return/recovery override: on return/reunion/missing/misplaced questions,
# never deny on a bad chart. NIGHT_REPORT 4a: 20 return cases, 16 reality-YES
# (80%); flipping v3-NO->YES fixed 13, broke 1 (+12 net).
RETURN_OVERRIDE = False

# Occupancy rescue: deciding planet occupies a success house (occupation
# levels) while owning none (ownership levels) -> YES instead of OTHER/NO.
# NIGHT_REPORT 4b: 31 situations, 22 reality-YES (71%, +13 net).
OCCUPANCY_RESCUE = False

# Toxicity: mixed/OTHER signification touching fatal houses {8,12} -> NO.
# Friction-only mixed stays OTHER. engine_v3 TEST_RESULTS: +3.5 on full 369.
TOXICITY = False

# Love retro veto (ROMANCE EVENTS ONLY — pooled retro-denial is 38%, so this
# must never generalize): Rule A — deciding planet retrograde -> NO; Rule B —
# deciding planet direct but its star-lord retrograde -> NO. VARIANT_UB: 4/4.
# romance_materialise/breakup/reunion, friend_to_romance only.
LOVE_RETRO_VETO = False

# Second-marriage dual-sign/Mercury gate (BOOK, R6 p.165 / R6:9029-9044):
# the 7th-cusp sub-lord must be Mercury, or be deposited in a dual sign
# (Gemini/Virgo/Sagittarius/Pisces), or be in the constellation of a planet
# that is in or owns a dual sign. Failing the gate -> NO before judgment.
SECOND_MARRIAGE_GATE = False  # 2026-10-06: disabled per miss analysis — Bosmia Ex.111 explicitly records the dual test failing ("not connected with Mercury or dual sign") and still predicts YES. L3's procedure already matches the books.

# Layer 2.5 Moon genuineness gate (user ruling 2026-10-01; OVERRULES the
# 2026-09-25 reported-signal-only design for the v5 lab pipeline).
# 'hard': FAIL blocks Layer 3 -> verdict OTHER + MOON_GENUINENESS_FAIL
#         ("the chart is not valid and should not be judged").
# 'flag': the result is recorded as modifiers/notes; Layer 3 always runs.
# Measure block-rate and blocked-vs-passed accuracy on the 369 corpus before
# trusting the gate — every hard gate tested so far has needed data.
MOON_GATE_ENABLED = False  # user ruling: moon gate report-only
MOON_GATE_MODE = 'flag'  # user ruling: never hard   # 'hard' | 'flag'

ENGINE_V5_VERSION = '0.2.0-experimental'

# Overlap policy (UNDECIDED, default False = current behavior): the OURS
# 12th-from denial fallback can put a house in BOTH lists (e.g. job success
# [2,6,10,11] -> denial [1,5,9,10]: house 10 is on both sides, so the frozen
# engine counts significators of 10 for and against simultaneously).
# Corpus evidence 2026-09-28: W74 looked like an overlap victim (v5 denial
# [1,5,9,10] vs old hand [1,5,8,12] flipped YES->NO). Direct test showed the
# overlap was NOT the culprit: dedup->[1,5,9] still gives NO; the whole OURS
# fallback denial differs from the hand denial. Full-corpus experiment:
# dedup changed ZERO verdicts (369 cases). Policy still open, not urgent.
# Awaiting user ruling.
DENIAL_DEDUP_OVERLAP = True

# LEAN TIER — FIXED 2026-09-28, DO NOT TUNE.
# |kp_score| <= 2 verdicts measured 48.6% on the corpus (coin flip); the rule
# converts them to OTHER (lean) instead of YES/NO. It invents nothing: it only
# abstains. Threshold was set once from that bucket analysis and must not be
# re-tuned on the same corpus. Exceptions (layer2b procedures) are untouched.
LEAN_THRESHOLD = 2

# 2026-09-28 blind re-test on 369 corpus (merged brain): overrides HURT v5.
# toxicity 28/57=49.1%, occupancy_rescue 0/5, return_override 0/1,
# love_retro_veto 0 fires. All default OFF per keep-if-works/remove-if-not.
# Flags remain for future live-data testing only.

# Layer-3 judge selection (2026-10-07): v10.2 is the finished judge.
# Set False to fall back to the weighted-evidence judge.
L3_V10_2 = True

# Layer-3 judge selection (2026-09-30): True = weighted-evidence judge
# (layer3_weighted: hierarchical evidence, score-based verdict, stability
# test, answerability reasons). False = legacy flat set-intersection judge
# (layer3_traditional). Weighted is the active development path.
L3_WEIGHTED = True
