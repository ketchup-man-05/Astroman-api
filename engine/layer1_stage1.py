"""Stage-1 deterministic router (lab, 2026-09-28; upgraded 2026-09-29). OURS engineering.

Upgrades over layer1_dissect (which is kept untouched for comparison):
- Phrase dictionary, longest-first, incl. Hinglish/transliterated terms.
- Form detection: yes_no / when / status / identification / advice / compound.
- Polarity detection: seek_gain / adverse / neutral, + explicit-negation flip,
  + negative-framing verdict inversion (2026-09-29), + ambiguous-polarity clarify.
- Span output: every routing decision carries the triggering text span.
- Token matching (2026-09-29): hand-rolled stemmer + unordered token-set
  intersection within a 12-token window. Replaces literal substring matching,
  so "purchase a new luxury car" hits the "purchase car" trigger. No NLP
  downloads (deploy-safe: zero new packages).
- Collision guards (2026-09-29): ambiguous single-word triggers ("transfer",
  "dismissed", "cheat") require co-occurring topic words and are vetoed by
  competing-topic words.
- Possessive-ownership rule (2026-09-29): event-noun carrying my/our/mine with
  no kin-word elsewhere -> subject=self (authority actors never become subject).
- Default-self (2026-09-29): no third party named -> the chart is the querent's.
- Intent hierarchy (2026-09-29): event roles outcome|context; exactly one
  outcome-event among matches wins over any number of context-events.
- Compound relatives (2026-09-29): in-laws derived by Bhavat Bhavam
  (father-in-law = 9th from 7th = 3rd, etc.); grandparents ask maternal/paternal.
- Gap fills (detected, never force-fit): "win the election/match/title",
  "should I", pets, journeys, exam phrasings.
- Multi-event / multi-subject conflicts -> clarify (stage-2 handoff), never guess.

CONSTRAINTS (protocol 2026-09-28): house arrays FROZEN — only keyword maps
changed. Built from question text + blind hand labels (routing, not outcomes).
Never consulted expected verdicts.
"""
import re

from engine import layer1_dissect as OLD  # reuse: window extraction, relational phrases
# 2026-10-14: canonical bond-event set lives in layer2_router (single source).
# Layer 1 uses it for bond_no_rotate; Layer 2 for the relational guard.
from engine.layer2_router import BOND_EVENTS as _BOND_EVENTS

# events.json metadata (success_is_desired): the polarity inverter may only
# flip verdicts for events whose success array is the DESIRED outcome.
# Unknown/absent -> False (safe direction: never flip unless explicit).
import json as _json
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
with open(_os.path.join(_HERE, 'events.json'), encoding='utf-8') as _f:
    _EVENTS_META = _json.load(_f)


# v10.4 Gemini fallback + learning loop (2026-10-06, user-approved).
# Rules core first; Gemini ONLY fires at the NO_EVENT point (never on
# out_of_scope, never overriding a rule match). Learned keywords go to
# learned_vocabulary.json as reviewed=false; reviewed ones are injected
# into EVENT_PHRASES below at full weight.
# 2026-10-15 (Claude review A1): the old double-try used `engine_v5` (which
# does not exist) and a bare `import gemini_fallback` that only resolved if
# engine/ happened to be on sys.path (a layer2_5_moon side effect that runs
# AFTER this import). In production _GF was silently None, disabling the
# Gemini fallback and learned-vocabulary promotion. Package-qualified import
# works in every context (app, lab, bare).
try:
    from engine import gemini_fallback as _GF
except ImportError:
    _GF = None


def _event_desired(key):
    return bool(_EVENTS_META.get(key, {}).get('success_is_desired', False))

# ---------------------------------------------------------------------------
# subject phrases: book keywords + Hinglish/transliterated additions (OURS)
# ---------------------------------------------------------------------------
SUBJECT_PHRASES = {
    'self': ['myself', 'my own', 'i ', ' me ', ' my ', 'querist', 'querent'],
    'spouse_partner': ['my wife', 'my husband', 'wife', 'husband', 'spouse',
                       'patni', 'pati', 'my partner', 'partner',
                       # 2026-10-06 Phase 3 (A50): third-person spouse
                       'his wife', 'her husband', 'his husband', 'her wife'],
    # Rule 2 bucket split (USER-RULING 2026-09-28): romance/pre-legal -> 5th.
    # 'lover' moved here from spouse_partner.
    'romantic_partner': ['my girlfriend', 'my boyfriend', 'girlfriend',
                        'boyfriend', 'my crush', 'crush', 'lover',
                        'my lover', 'affair partner', 'my date', 'girlfriends',
                        'boyfriends', 'sweetheart', 'my sweetheart'],
    'children': ['my son', 'my daughter', 'my child', 'my children', 'son',
                 'daughter', 'beta', 'beti', 'my kid'],
    'father': ['my father', 'father', 'dad', 'papa', 'pitaji'],
    'mother': ['my mother', 'mother', 'mom', 'mum', 'maa'],
    'elder_sibling': ['elder brother', 'older brother', 'elder sister',
                      'older sister', 'elder sibling', 'older sibling',
                      'bade bhai', 'badi behen'],
    'younger_sibling': ['younger brother', 'younger sister', 'younger sibling',
                        'chhota bhai', 'chhoti behen', 'brother', 'sister',
                        'sibling', 'bhai', 'behen'],
    'boss_superior': ['my boss', 'boss', 'senior officer', 'superior',
                      'my manager', 'manager'],
    'business_partner': ['business partner', 'my partner in business'],
    'friend': ['my friend', 'friend', 'best friend', 'dost'],
    'guru_teacher': ['my teacher', 'teacher', 'guru', 'my guru', 'professor'],
    'competitor_enemy_open': ['opponent', 'competitor', 'rival', 'enemy'],
    'secret_enemy': ['secret enemy', 'hidden enemy'],
    'stranger_unknown': ['stranger', 'unknown person'],
    'thief': ['thief', 'robber', 'burglar', 'chor'],
    # compound relatives (OURS 2026-09-29, Bhavat-Bhavam derivation; the old
    # code forced all of these to stranger_unknown, which misjudged every
    # house downstream — e.g. father-in-law's disease read from the 9th).
    'father_in_law': ['father in law', 'father-in-law', 'sasur'],
    'mother_in_law': ['mother in law', 'mother-in-law', 'saas'],
    'brother_in_law': ['brother in law', 'brother-in-law', 'sala', 'jija'],
    'sister_in_law': ['sister in law', 'sister-in-law', 'bhabhi', 'sali'],
    'son_in_law': ['son in law', 'son-in-law', 'damaad'],
    'daughter_in_law': ['daughter in law', 'daughter-in-law', 'bahu'],
    # grandparents: lineage matters in KP, so Layer 1 asks maternal/paternal
    # and maps to grandfather_paternal (5th) / grandfather_maternal (12th) /
    # grandmother_paternal (12th) / grandmother_maternal (7th).
    # 2026-10-14: Hinglish kinship terms already encode lineage — dada/dadaji
    # = paternal, nana/nanaji = maternal. Route them directly, no clarify.
    # Only bare English grandfather/grandmother triggers the clarify.
    'grandfather': ['grandfather', 'grandpa'],
    'grandmother': ['grandmother', 'grandma'],
    'grandfather_paternal': ['dada', 'dadaji', 'paternal grandfather'],
    'grandfather_maternal': ['nana', 'nanaji', 'maternal grandfather'],
    'grandmother_paternal': ['dadi', 'dadiji', 'paternal grandmother'],
    'grandmother_maternal': ['nani', 'naniji', 'maternal grandmother'],
}

# Named third parties ("will X win?") resolve here when no relation matches.
PROPER_NOUN_SUBJECT = 'stranger_unknown'

PET_WORDS = ['cat', 'dog', 'pet', 'kitten', 'puppy', 'parrot', 'parrots',
             'rabbit', 'fish tank', 'my cat', 'my dog',
             # breed/common-animal expansion (OURS 2026-09-29): the old list
             # missed "retriever" and routed a missing dog as a missing human.
             'retriever', 'labrador', 'german shepherd', 'beagle', 'pug',
             'bulldog', 'poodle', 'indie dog', 'persian cat', 'siamese',
             'budgie', 'budgerigar', 'cockatiel', 'lovebird', 'hamster',
             'guinea pig', 'turtle', 'tortoise', 'pup', 'kitty']
JOURNEY_WORDS = ['journey', 'flight', 'train journey', 'my trip', 'road trip']

# Inanimate objects: a missing laptop is not a missing person. When these
# appear with a missing/lost event, route to misplaced/stolen item recovery.
OBJECT_WORDS = ['laptop', 'bag', 'phone', 'mobile', 'wallet', 'keys', 'key',
                'ring', 'watch', 'gold', 'jewellery', 'jewelry', 'documents',
                'document', 'passport', 'file', 'car', 'bike', 'bicycle',
                'cycle', 'luggage', 'suitcase', 'purse', 'camera', 'tablet',
                'headphone', 'headphones', 'charger', 'umbrella',
                'spectacles', 'glasses', 'cycle']
THEFT_WORDS = ['stolen', 'theft', 'robbed', 'robbery', 'snatched', 'chori']

# Kin words: flip the chart's subject. Authority/institutional actors
# (boss, bank, court, builder, landlord, police) NEVER appear here — they are
# the mechanism of the querent's matter, not the subject (OURS 2026-09-29).
KIN_WORDS = {'wife', 'husband', 'spouse', 'son', 'daughter', 'child',
             'children', 'father', 'mother', 'brother', 'sister',
             'sibling', 'friend', 'partner', 'uncle', 'aunt',
             'nephew', 'niece', 'cousin', 'grandfather', 'grandmother',
             'grandpa', 'grandma', 'dada', 'dadaji', 'nana', 'nanaji',
             'dadi', 'dadiji', 'nani', 'naniji',
             'father in law', 'mother in law',
             'brother in law', 'sister in law', 'son in law',
             'daughter in law', 'in-law', 'inlaw', 'sasur', 'saas',
             'bahu', 'damaad', 'beta', 'beti', 'bhai', 'behen'}
# Authority/institutional actors (OURS 2026-09-29): commonly the MECHANISM
# of the matter (the boss approves, the bank lends), not its subject. When
# they are the only subject candidates and a possessive attaches to the
# event noun ("my promotion"), the querent owns the matter.
AUTHORITY_ACTORS = {'boss_superior', 'guru_teacher'}
# Offices/titles: third parties even without a name ("will the prime
# minister win") — must not fall through to default-self.
OFFICE_WORDS = ['prime minister', 'chief minister', 'president', 'minister',
                'mla', 'mp ', 'mayor', 'governor', 'king', 'cm ', 'pm ']

# ---------------------------------------------------------------------------
# event phrases: old keyword table + gap fills + Hinglish (OURS)
# ---------------------------------------------------------------------------
EVENT_PHRASES = {
    'job_get_service': ['get a job', 'get job', 'new job', 'job offer',
                        'offer letter', 'appointment letter', 'naukri',
                        'sarkari naukri', 'government job', 'govt job',
                        'employment', 'employed', 'hire', 'hired',
                        'hiring', 'interview', 'recruit', 'recruitment',
                        'internship', 'selected', 'selection', 'shortlisted',
                        'joining', 'join the company', 'permanent role',
                        'secure a job', 'secure good job', 'full-time job',
                        'full time job', 'next job', 'company job',
                        'take up a job', 'take up job', 'campus placement',
                        'placement offer', 'placement',
                        # 2026-10-06 Phase 3 (W16, H-C13): for the job/project
                        'for the job', 'new project', 'find project',
                        'get project'],
    'promotion': ['promotion', 'promoted', 'promote', 'increment',
                  'higher post', 'higher position', 'elevation', 'padonnati'],
    'transfer_job': ['transfer', 'transferred', 'posting',
                     # 2026-10-06 Phase 3 (A12): "change in the present job"
                     'change in the present job', 'change in present job'],
    'job_loss_dismissal': ['fired', 'dismissed', 'dismissal', 'lose my job',
                           'losing my job', 'losing current job',
                           'lost my job', 'layoff', 'laid off', 'sacked',
                           'terminate', 'terminated', 'termination',
                           'removed from service', 'asked to resign',
                           'lose the job', 'losing the job'],
    'job_change': ['job change', 'change of job', 'change in job',
                   'change my job', 'switch job', 'switching job',
                   'change job', 'job switching'],
    'reinstatement_regain_position': ['reinstate', 'reinstated',
                                      'reinstatement', 'get back my job',
                                      'regain'],
    # 2026-10-14: keep/continue-in-job triggers moved here from
    # reinstatement_regain_position -- "will I keep my job?" is continuity
    # (6th CSL, BOOK [2,6,10]/[1,5,9,12]), not reinstatement.
    'job_continuity': ['keep my job', 'keep his job',
                       'keep her job', 'keep the job',
                       'retain my job',
                       'continue in my current job',
                       'continue in the job',
                       'continue my job',
                       'continue in current job'],
    'suspension_from_service': ['suspend', 'suspended', 'suspension'],
    'business_start': ['start business', 'starting business', 'new business',
                       'startup', 'start-up', 'new venture', 'own business',
                       'start my own', 'business venture', 'dhandha',
                       'for business', 'into business',
                       # 2026-10-06 Phase 3: franchise/open/establish/stall
                       'franchise', 'franchisees',
                       'establish business', 'set up business',
                       'open business', 'open an office', 'open office',
                       'educational institute', 'independent business',
                       'new stall',
                       # 2026-10-06: mining lease -> business_start
                       # (Shanmugam: mines/mining = independent business)
                       'lease license', 'mining lease', 'mine license',
                       'mines license'],
    # ADDED 2026-10-06 (W88/Bosmia Ex.94): partnership questions need their
    # own event. L3's _business_partnership_procedure exists but L1 never
    # routed to it; "buying/repairing damaged cars" fell through to property.
    # NOTE: bare 'partnership' alone is too broad (Ex30: money partnership).
    # Require business context.
    'business_partnership': ['business partner', 'partner in business',
                             'partner for business', 'joint venture partner',
                             'business partnership',
                             # 2026-10-06 Phase 3 (NEW-BosmiaPrashna-Ex30)
                             'partnership be continued',
                             'partnership continued',
                             'continue partnership',
                             # 2026-10-06 Phase 3 (A31): "partnership in the
                             # industrial set-up" — business context
                             'partnership in the industrial',
                             'industrial set-up'],
    # 2026-10-06: new events from book research (BOOK_RULINGS_NEW_EVENTS.md)
    # User adopted 2026-10-06. property_retain/property_rent_out LEFT OUT
    # per user ruling (no book support).
    'retirement_decision': ['retire', 'retirement', 'voluntary retirement',
                            'VRS', 'superannuation', 'retire from'],
    'position_lose': ['lose power', 'step down', 'lose position', 'ousted',
                      'removed from power', 'lose his power',
                      'lose her power'],
    'career_suitability': ['become an actor', 'become a successful',
                           'successful astrologer', 'successful in political',
                           'aptitude for', 'suitable for', 'become a',
                           'success as a', 'career suitable'],
    'money_lent_recovery': ['amount lent', 'get back the amount',
                            'lent money', 'recover lent', 'money lent',
                            'amount I lent', 'get back my money'],
    'business_profit': ['business profit', 'profit in business',
                        'profit from business', 'business doing well',
                        'profitable business', 'business profitable',
                        'earn profit', 'business gains', 'profit',
                        # 2026-10-06 Phase 3: box office/dividends/deal
                        # NOTE: 'business be successful' removed — token matcher
                        # false-positives on "business partner...be successful"
                        # (EzineFeb2023-landlit). 'successful business' is safer.
                        'box office', 'rich dividends', 'dividends',
                        'successful business',
                        'benefited in the deal'],
    'business_loss': ['business loss', 'loss in business',
                      'losing money in business', 'business losses',
                      'loss making business', 'business in losses',
                      'loss', 'losses', 'nuksan', 'wind up'],
    'money_gain': ['money', 'wealth', 'wealthy', 'become rich',
                   'financial gain', 'financial condition', 'income',
                   'financial help', 'earn',
                   # 2026-10-06 Phase 3: draft/crunch/treasure/bonus/payment
                   'bank draft', 'financial crunch', 'treasure', 'bonus',
                   'help me financially', 'help financially',
                   'release my payment', 'release payment',
                   'salary increase', 'increased salary', 'arrears',
                   'financial position'],
    'stock_speculation': ['stock market', 'stock', 'stocks', 'share market',
                          'shares', 'speculation', 'intraday', 'trading',
                          'nifty', 'sensex', 'short nifty'],
    # v9.7 money-batch-2 (2026-10-05): lottery / donation / PF events.
    'lottery': ['lottery', 'lottery ticket', 'win lottery', 'win the lottery',
                'prize bond', 'lucky draw', 'jackpot', 'win a prize'],
    'donation_receive': ['donation', 'get donation', 'receive donation',
                         'get a donation'],
    'provident_fund_pension': ['provident fund', 'pf money', 'pf withdrawal',
                               'pension', 'gratuity', 'retirement benefit',
                               'pension money'],
    'inheritance_claim': ['inheritance', 'inherit', 'inherits',
                          'ancestral property', 'insurance claim',
                          'legacy', 'inherited property'],
                          # v9.7: 'provident fund'/'pf claim' moved to the
                          # specific provident_fund_pension event.
    'renting_live_in': ['rent a house', 'rented house', 'renting a house',
                        'take on rent', 'on rent', 'lease a house', 'rental',
                        'change house', 'shifting house', 'move house'],
    'adoption': ['adopt a child', 'adoption', 'adopt'],
    'loan_borrow_get': ['loan', 'borrow', 'borrowing', 'lend me', 'karz'],
    'loan_repay_clear': ['repay', 'repay the loan', 'repaying', 'clear debt',
                         'clear off', 'clear the loan', 'debt free',
                         'pay off debt', 'pay back the loan', 'clear my loans',
                         'credit card debt', 'clear debts', 'repay debts',
                         'debt repayment'],
    'marriage': ['marry', 'married', 'marrying', 'marriage', 'wedding',
                 'wedlock', 'shaadi', 'shadi', 'vivah', 'get married',
                 'bride', 'groom', 'love marriage', 'arranged marriage',
                 'engaged', 'engagement', 'get engaged', 'sagai',
                 # 2026-10-06 Phase 3 (D5, NEW-077): marital bliss/good match
                 'marital bliss', 'marital', 'good match'],
    'second_marriage': ['second marriage', 'remarry', 'remarriage',
                        'marry again', 'second shaadi', 'marry a second time',
                        'marry second', 'second wedding', 'another marriage',
                        're-marry', 'second husband', 'second wife',
                        'married again'],
    'divorce': ['divorce', 'divorced', 'divorcing', 'talaq',
                # 2026-10-14: "will my marriage end" / "end my marriage" is
                # divorce, not romance_breakup (marriage removed from its guard).
                'marriage end', 'end my marriage', 'end the marriage',
                'end our marriage'],
    # alimony/maintenance: the ex-spouse's money coming to the querent.
    # 2nd from 7th = radical 8th (same Bhavat-Bhavam technique as Rout's
    # verified boss-money case, third_party.md). OURS 2026-09-29.
    'alimony_settlement': ['alimony', 'maintenance amount', 'monthly maintenance',
                           'divorce settlement', 'settlement amount',
                           'lump sum alimony', 'spousal support'],
    # infidelity detection: "is my partner cheating on me" asks whether
    # something is TRUE RIGHT NOW — a present-fact detection like rumor_true,
    # not a future-outcome array event. Layer-2b exception procedure
    # infidelity_detect (OURS; Phase-2 partner_fidelity.md Video 1: 5+8
    # pattern via 5th/8th CSL, natal method adapted — no prashna walkthrough
    # found, so UNCLEAR unless the pattern is clean).
    'infidelity_detect': ['cheating on me', 'cheat on me', 'having an affair',
                          'is my husband cheating', 'is my wife cheating',
                          'is he cheating', 'is she cheating',
                          'unfaithful', 'extra marital affair',
                          'extramarital affair', 'sleeping with someone',
                          'seeing someone else'],
    # relationship events (Rules 2-3, 2026-09-28). 'love affair'/'affair'
    # moved here from love_affair so they route to a judged event.
    'romance_materialise': ['love affair materialize', 'love affair materialise',
                            'affair materialize', 'affair materialise',
                            'love affair', 'having an affair',
                            'will we get together', 'get together',
                            'be together', 'start a relationship',
                            'start dating', 'accept my proposal',
                            'accept my love', 'say yes to me',
                            # 2026-10-13: "will i get a girlfriend" (friend Q4)
                            'get a girlfriend', 'get a boyfriend',
                            'find a girlfriend', 'find a boyfriend',
                            'have a girlfriend', 'have a boyfriend'],
    'romance_breakup': ['break up', 'breakup', 'break-up', 'breaks up with me',
                        'end the affair', 'end my love affair', 'will it end',
                        'finally end', 'leave my boyfriend',
                        'leave my girlfriend', 'dumped me', 'dump me'],
    'romance_reunion': ['ex boyfriend', 'ex girlfriend', 'ex boyfriends',
                        'ex girlfriends', 'my ex come back',
                        'ex come back to me', 'get my love back',
                        # 2026-10-06 Phase 3 (H-R18): re-union/blocked
                        're-union', 'reunion', 'blocked communication'],
    'friend_to_romance': ['friend and i date', 'date my friend',
                          'dating my friend', 'my friend become',
                          'fall for my friend', 'love with my friend',
                          'friend be my girlfriend', 'friend be my boyfriend'],
    'love_affair': ['in love', 'romance', 'romantic', 'love life',
                    'affair rumor', 'affair rumour',
                    # 2026-10-06 Phase 3 (NEW-073): "does the boy loves me"
                    'loves me', 'love me'],
    'childbirth': ['pregnant', 'pregnancy', 'conceive', 'conception',
                   'childbirth', 'give birth', 'expecting a child',
                   'have a baby', 'have a child', 'get a child', 'get a baby',
                   'become a mother', 'become a father', 'birth', 'born',
                   'delivery', 'deliver', 'conceive and', 'childless',
                   'issueless', 'to-be-born'],
    'disease_illness': ['sick', 'illness', 'disease', 'ailment', 'unwell',
                        'health issue', 'health problem', 'suffering from',
                        'diagnosed', 'unconscious', 'consciousness',
                        'hospital', 'hospitalized', 'admitted in hospital',
                        'bimari', 'suffering'],
    'recovery_cure': ['recover', 'recovered', 'recovering', 'recovery',
                      'cure', 'cured', 'heal', 'healed', 'healing',
                      'get well', 'become healthy', 'come out of illness',
                      'gain consciousness', 'discharged from hospital',
                      'be discharged'],
    'surgery': ['surgery', 'surgical', 'operation'],
    'longevity': ['how long will', 'longevity', 'lifespan', 'pass away',
                  'death', 'die', 'survive', 'survival', 'assassinated',
                  'assassinate'],
    'property_purchase_readybuilt': ['buy house', 'buy a house', 'buy flat',
                                     'buy a flat', 'buy plot', 'buy land',
                                     'buy a plot', 'purchase house',
                                     'purchase property', 'buy property',
                                     'new house', 'own house',
                                     'house purchase', 'bought', 'purchased',
                                     'buying', 'buying a plot', 'possession',
                                     'hand over possession', 'flat possession',
                                     'get possession', 'handover',
                                     'new house', 'own house',
                                     'house purchase', 'bought', 'purchased',
                                     'buying', 'buying a plot',
                                     # 2026-10-06 Phase 3 (EzineDec2021-land)
                                     'purchase land'],
    'property_construct': ['construct', 'construction', 'build a house',
                           'building a house', 'construct a house'],
    'property_sale': ['sell house', 'sell my house', 'sell flat', 'sell land',
                      'sell property', 'sale of house', 'sell the house',
                      'sold', 'sell', 'sale', 'sell off'],
    'vehicle_purchase': ['buy car', 'buy a car', 'buy bike', 'buy a bike',
                         'buy vehicle', 'new car', 'new bike', 'purchase car',
                         'four wheeler', 'two wheeler', 'bought a car',
                         'purchased a car', 'buy an old car', 'gaadi',
                         # 2026-10-06 Phase 3 (Ex84, Pa-111): bus/bike/motorbike
                         'purchase bus', 'buy bus', 'purchase bike',
                         'purchase motorbike', 'motorbike'],
    'vehicle_sale': ['sell my car', 'sell the car', 'sell car',
                     'dispose my vehicle', 'dispose the vehicle',
                     'sell my vehicle', 'sell bike'],
    # 2026-10-13: exam_appear (KSK VI p.198 lagna-deposition test).
    # "attend/appear for exam" = will I be able to make the attempt?
    # Distinct from exam_pass_general (will I clear/pass?).
    'exam_appear': ['attend the exam', 'attend exam', 'attend my exam',
                    'appear for the exam', 'appear for exam', 'appear for',
                    'appear in the exam', 'appear in exam',
                    'be able to give the exam', 'be able to give my exam',
                    'be able to give exam', 'able to attend',
                    'able to give exam', 'able to appear',
                    # 2026-10-14: moved from exam_pass_general — "give/appear/
                    # sit for" is about attendance (Indian English), not passing.
                    'give my exam', 'give the exam', 'give exam',
                    'sit for the exam', 'sit for exam'],
    'exam_pass_general': ['pass the exam', 'pass exam', 'clear the exam',
                          'clear exam', 'exam result', 'pass in', 'qualify',
                          'succeed in the exam', 'marks', 'pass my',
                          'baccalaureat', 'board exam', 'high school',
                          # 2026-10-14: "will I fail/not fail the exam" needs
                          # the event to fire; XOR framing handles polarity.
                          'fail the exam', 'fail in exam', 'fail my exam',
                          # 2026-10-06: "give my exam" = appear/take exam
                          # (Indian English). "able to give" = will I sit for it.
                          # 2026-10-14: moved to exam_appear (dedicated event).
                          'take my exam',
                          # 2026-10-02: bare 'examination' (E2-4, A3, W45-48).
                          # Ported from rebuild/event_classifier.py which already
                          # carries ('examination', 1.5) with a comment noting
                          # v5 lacked it. All 12 'examin*' hits in the 369 are
                          # exam questions; no non-exam use observed.
                          'examination',
                          # 2026-10-06 Phase 3 (H-H4): written test
                          'written test', 'clear the written test'],
    'exam_competitive': ['upsc', 'ias', 'ips', 'ifs', 'neet', 'jee', 'cat',
                         'competitive exam', 'civil services', 'sarkari exam',
                         'high court exam', 'entrance exam',
                         # 2026-10-14 (Gemini 4 audit): banking, SSC, defense,
                         # teaching, police, fellowship/recruitment exams are
                         # competitive selections (6th house), not school exams.
                         'ibps', 'sbi po', 'sbi clerk', 'bank po',
                         'bank clerk', 'banking exam', 'rbi grade', 'nabard',
                         'ssc', 'cgl', 'chsl', 'mts', 'rrb', 'ntpc',
                         'nda', 'cds', 'afcat', 'gate', 'clat',
                         'ugc net', 'csir net', 'ctet', 'tet', 'tgt', 'pgt',
                         'psc', 'pcs', 'patwari', 'constable'],
    'education_general': ['study', 'studies', 'studying', 'education',
                          'admission', 'degree', 'school', 'school admission',
                          'courses', 'attending classes', 'padhai',
                          'continue his studies', 'go back to school',
                          # 2026-10-06 (E4-1): vocational courses are general
                          # education, not higher. Moved 'ultrasound course'
                          # here from education_higher.
                          'ultrasound course', 'diploma course',
                          'certificate course', 'vocational',
                          'training course', 'internship in',
                          'computer course', 'learn astrology'],
    'education_higher': ['higher education', 'phd', 'masters', "master's",
                         'm.tech', 'research scholar', 'doctorate',
                         'synopsis presentation',
                         'college', 'university', 'engineering college',
                         'medical college', 'bits', 'iit', 'programme',
                         # 2026-10-06 (W156): professional schools are higher ed.
                         # 'ultrasound course' moved to education_general (E4-1).
                         'medical school', 'law school', 'business school',
                         'dental school'],
    # 2026-10-14: scholarship moved to its own event -- a dedicated
    # scholarship procedure exists in Layer 3 but was unreachable.
    'scholarship': ['scholarship', 'research scholarship'],
    'foreign_travel': ['go abroad', 'going abroad', 'abroad', 'foreign trip',
                       'travel abroad', 'settle abroad', 'onsite', 'foreign',
                       'videsh'],
    'visa': ['visa', 'immigration', 'immigrate', 'green card',
             'permanent residency', 'work permit', 'passport'],
    'court_case_litigation_win': ['court', 'litigation', 'lawsuit',
                                  'legal case', 'court case', 'judgement',
                                  'case in court', 'legal battle',
                                  'win the case', 'found guilty',
                                  'criminal charges', 'hearing in court',
                                  'mukadma', 'mukadama'],
    'jail_release': ['release from jail', 'released from jail',
                     'jail release', 'prison release', 'come out of jail',
                     'get bail', 'bail', 'jail'],
    'imprisonment': ['imprisonment', 'imprisoned', 'sent to jail',
                     'go to jail', 'jail punishment', 'punished with',
                     'is there any jail'],
    'contest_win': ['win the contest', 'win competition',
                    'win the competition', 'win the match', 'win match',
                    'win the title', 'win title', 'win the trophy',
                    'win big brother', 'master chef'],
    'election_win': ['win the election', 'win election', 'elections',
                     'election', 'mla', 'constituency', 'vote', 'voting',
                     'panchayat', 'councillor', 'corporator',
                     'become cm', 'chief minister', 'prime minister',
                     'president of india', 'come to power',
                     'win delhi', 'assembly election'],
    'missing_person_return': ['come back', 'coming back', 'return home',
                              'returned home', 'return to me',
                              'come back to me', 'left home', 'missing',
                              'run away', 'ran away', 'where is my',
                              'will she return', 'will he return',
                              'relieved from'],
    'missing_person_status': ['alive', 'dead or alive', 'is he alive',
                              'is she alive', 'survived', 'is she alive?'],
    'spouse_return_estranged': ['estranged', 'separated', 'separation',
                                'reunion', 'reconcile', 'get back together',
                                'patch up', 'left me', 'ex-wife', 'ex-husband',
                                'normal relations', 'relations with my',
                                # 2026-10-06 Phase 3 (W99, NEW-069, NEW-013)
                                'return back', 'husband return',
                                'wife return', 'go back to my husband',
                                'go back to husband', 'back to my husband',
                                'return to my husband',
                                'living with my wife', 'live with my wife'],
    'stolen_property_recovery': ['stolen', 'robbery', 'theft of', 'chori'],
    'misplaced_item_recovery': ['misplaced', 'cannot find', "can't find",
                                'where did i keep', 'lost the', 'lost my keys',
                                'lost my phone', 'lost my wallet',
                                'lost my ring', 'lost my documents',
                                'lost my bag', 'lost the',
                                'find my'],
    'rumor_true': ['rumor', 'rumour', 'is it true', 'heard that', 'gossip',
                   'news true', 'heard news', 'news about'],
    'theft_identify_thief': ['who stole', 'identify the thief',
                             'catch the thief', 'thief caught', 'be caught',
                             'find the thief', 'caught the thief'],
    'fraud_deception': ['fraud', 'fraudulent', 'cheated', 'cheat',
                        'cheating', 'scam', 'scammed', 'deceived', 'deceive',
                        'deception', 'duped', 'duping', 'conspiracy',
                        'forgery', 'forged'],
}

# v10.4 learning loop: reviewed learned keywords are promoted to full
# weight here (treated exactly like hand-written keywords). Unreviewed
# ones are NOT injected — they only fire at the NO_EVENT point via
# _learned_fallback(), flagged ai_suggested. Source of truth is
# learned_vocabulary.json (reviewed=true).
if _GF is not None:
    try:
        for _phrase, _event, _reviewed in _GF.get_learned_triggers():
            if _reviewed and _event in EVENT_PHRASES:
                if _phrase not in EVENT_PHRASES[_event]:
                    EVENT_PHRASES[_event] = (list(EVENT_PHRASES[_event])
                                             + [_phrase])
    except Exception:
        pass

# NEW OURS events added by stage-1 (keyword level only; arrays in events.json
# are FROZEN — these route to clarify/unsupported until arrays are ruled on).
# They are detected so the gap is named, never force-fit.
STAGE1_ONLY_EVENTS = {'vehicle_sale', 'imprisonment'}  # job_change unblocked 2026-10-06 (book: Bhatnagar p.79, Taneja p.108, Joshi p.54)

# phrases where YES = the feared outcome (polarity adverse)
ADVERSE_CORES = ['lose', 'losing', 'lost', 'die', 'death', 'fail', 'failed',
                 'failure', 'denied', 'rejected', 'arrest', 'arrested',
                 'imprisonment', 'imprisoned', 'jail', 'divorce', 'divorced',
                 'assassinat', 'fired', 'dismissed', 'sacked',
                 'asked to resign', 'evict', 'guilty', 'fraud',
                 'lose power', 'wind up', 'lose the case']

FORM_PATTERNS = [
    ('when', [r'\bwhen\b', r'\bhow long\b', r'\bhow soon\b',
              r'\bin which period\b', r'\bby when\b', r'\bwhat time\b']),
    ('advice', [r'\bshould i\b', r'\badvisable\b', r'\bright decision\b',
                r'\bright time to\b', r'\bwhat is good for me\b',
                r'\bwhether i should\b', r'\bcan i take up\b']),
    ('identification', [r'\bwho\b', r'\bwhich\b', r'\bsex of\b',
                        r'\bboy or girl\b', r'\blove or arranged\b',
                        r'\bor an arranged\b']),
    ('status', [r'\bis .{0,20}alive\b', r'\bis .{0,20}well\b',
                r'\bwhat is the position of\b', r'\bwhere is\b']),
]

NEGATION = re.compile(
    r'\b(will|shall|can|could|do|does|is|are|am)\b[^?.]{0,25}(?<!or )not\b|\bn\'t\b',
    re.I)


# ---------------------------------------------------------------------------
# Hand-rolled stemmer + unordered token matcher (OURS 2026-09-29).
# Deliberately NOT nltk/spaCy: both need a first-run download (wordnet /
# model weights) that fails silently under Streamlit Cloud's network
# restrictions — the exact deploy-fragility class this project keeps hitting.
# Twelve lines, zero packages, zero network.
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[a-zA-Z]+")  # apostrophes split: "daughter's" ->
# ["daughter", "s"], so possessives still match ("my daughter")


# 2026-10-14 (Gemini 4 audit): upgraded stemmer. The old version left
# words <= 4 chars untouched and didn't handle -ied->-y, doubled
# consonants, or silent -e, causing "hir" != "hire" mismatches.
_IRREGULAR_STEMS = {
    "lost": "lose", "losing": "lose", "paid": "pay", "lent": "lend",
    "left": "leave", "leaving": "leave", "spoken": "speak", "broke": "break",
    "broken": "break", "chosen": "choose", "frozen": "freeze", "stole": "steal",
    "stolen": "steal", "met": "meet", "kept": "keep", "built": "build",
    "sold": "sell", "told": "tell", "won": "win", "winning": "win",
    "got": "get", "gotten": "get", "getting": "get", "gave": "give",
    "given": "give", "giving": "give", "took": "take", "taken": "take",
    "taking": "take", "made": "make", "making": "make", "came": "come",
    "coming": "come", "gone": "go", "went": "go", "dies": "die", "died": "die",
    "dying": "die", "tied": "tie", "owes": "owe", "owed": "owe",
}

def _stem(w):
    w = w.lower()
    if w in _IRREGULAR_STEMS:
        return _IRREGULAR_STEMS[w]
    if len(w) <= 3:
        return w
    if w.endswith("ied") and len(w) > 4:
        return w[:-3] + "y"           # married -> marry
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"           # dies -> die (if not in irregular)
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            base = w[:-len(suf)]
            # Collapse doubled final consonants: transferr -> transfer
            if len(base) >= 4 and base[-1] == base[-2] and base[-1] not in "lsz":
                base = base[:-1]
            # Don't strip 's' from words ending in 'ss' (business, pass)
            if suf == "s" and base.endswith("s"):
                return w
            if suf == "es" and w.endswith("sses"):
                return w
            return base
    # Strip trailing silent 'e' so 'hire' -> 'hir' matches 'hiring' -> 'hir'
    if w.endswith("e") and len(w) >= 4 and not w.endswith(("ee", "oe", "ye")):
        return w[:-1]
    return w


def _hit(text, phrase):
    pat = r'\b' + re.escape(phrase.strip()) + r's?\b'
    return re.search(pat, text) is not None


def _tokenize(text):
    return [(m.group(0), m.start(), m.end())
            for m in _TOKEN_RE.finditer(text.lower())]


def _match(phrases, text, regex=None, subsume=False):
    """Token-set phrase match (2026-09-29). Returns [(key, phrase, span)].

    Every trigger phrase is reduced to stemmed tokens; a phrase hits when ALL
    its tokens appear anywhere in the question within a 12-token window, in
    any order. "purchase a new luxury car" -> {purchase, car} hits the
    "purchase car" trigger. One span per key: most tokens wins, ties broken
    by tightest window. With subsume=True, a hit whose character span lies
    strictly inside another hit's span is dropped ("brother in law" keeps
    brother_in_law and drops the "brother" younger_sibling hit).
    """
    toks = _tokenize(text)
    stems = [_stem(w) for w, _, _ in toks]
    out = []
    for key, kws in phrases.items():
        best = None
        for kw in kws:
            kw = kw.strip().lower()
            if not kw:
                continue
            kws_stems = [_stem(w) for w in _TOKEN_RE.findall(kw)]
            if not kws_stems:
                continue
            pos, used, ok = [], set(), True
            for ks in kws_stems:
                found = None
                for i, s in enumerate(stems):
                    if s == ks and i not in used:
                        found = i
                        break
                if found is None:
                    ok = False
                    break
                used.add(found)
                pos.append(found)
            if ok:
                lo, hi = min(pos), max(pos)
                if hi - lo <= 12:
                    c0, c1 = toks[lo][1], toks[hi][2]
                    cand = (len(kws_stems), -(c1 - c0), key, kw,
                            text[c0:c1], frozenset(used))
                    if best is None or cand[:2] > best[:2]:
                        best = cand
        if best:
            out.append(best[2:])   # (key, kw, span, used_indices)
    for key, pats in (regex or {}).items():
        if any(k == key for k, _, _, _ in out):
            continue
        for p in pats:
            m = re.search(p, text)
            if m:
                out.append((key, p, m.group(0), frozenset()))
                break
    if subsume and len(out) > 1:
        # token-overlap subsumption (2026-09-29): two subject hits sharing a
        # token index ("my father" vs "father in law" share "father") keep
        # the longer one. Disjoint hits ("my father and my mother") both stay.
        keep = []
        for i, (ki, kwi, spi, ui) in enumerate(out):
            swallowed = any(
                j != i and (ui & uj) and len(uj) > len(ui)
                for j, (kj, kwj, spj, uj) in enumerate(out))
            if not swallowed:
                keep.append((ki, kwi, spi))
        return keep
    return [(k, kw, sp) for k, kw, sp, _ in out]


def _stem_set(text):
    """Stemmed token set of a text, for guard checks."""
    return {_stem(w) for w in _TOKEN_RE.findall(text.lower())}


# ---------------------------------------------------------------------------
# Collision guards (OURS 2026-09-29). Ambiguous single-word triggers are the
# only silent-wrong-answer bug class: they must prove their topic with a
# co-occurring word, and competing-topic words veto them outright.
#   transfer  -> needs a job-word nearby; IVF/embryo/pregnancy vetoes it
#   dismissed/dismissal -> court/case/defamation words veto the job reading
#   cheat-family (fraud_deception) -> spouse/partner/affair words veto it
#                (infidelity_detect owns the relationship reading)
# ---------------------------------------------------------------------------
TRIGGER_GUARDS = {
    'transfer_job': {
        # Bare 'transfer' is almost always a job transfer in Indian service
        # context ("Is my transfer possible?" A7). The IVF/embryo sense is
        # the dangerous one — veto it (and property/money transfers), but
        # don't demand a job word (that missed A7/J63).
        # 2026-10-14: removed 'bank', 'pregnant', 'pregnancy', 'baby'.
        # Bank employees ask about transfers; pregnant women ask for
        # hometown transfers. Only medical IVF terms stay vetoed.
        'transfer': {'exclude_any': ['embryo', 'ivf',
                                    'uterus', 'fertility',
                                    'egg', 'frozen', 'property', 'money',
                                    'funds', 'shares']},
        # Passive 'transferred' ("get transferred to Chennai") is never the
        # IVF sense — no job-word requirement, just the IVF veto.
        'transferred': {'exclude_any': ['embryo', 'ivf',
                                       'uterus',
                                       'fertility', 'egg']},
        'posting': {'exclude_any': ['embryo', 'ivf',
                                    'uterus', 'egg']},
    },
    'job_loss_dismissal': {
        # 2026-10-14: unless_any — departmental charges/FIR in a JOB context
        # ("dismissed from service") must not kill job_loss_dismissal.
        'dismissed': {'exclude_any': ['court', 'case', 'lawsuit',
                                      'litigation', 'defamation', 'charges',
                                      'fir', 'mukadma', 'mukadama',
                                      'hearing', 'trial'],
                      'unless_any': ['job', 'service', 'duty', 'work',
                                     'office', 'post', 'employee',
                                     'department', 'departmental']},
        'dismissal': {'exclude_any': ['court', 'case', 'lawsuit',
                                      'litigation', 'defamation', 'charges',
                                      'fir', 'mukadma', 'mukadama',
                                      'hearing', 'trial'],
                      'unless_any': ['job', 'service', 'duty', 'work',
                                     'office', 'post', 'employee',
                                     'department', 'departmental']},
    },
    'fraud_deception': {
        # 2026-10-14: removed 'partner' and 'marriage' from exclude_any.
        # "Is my business partner cheating me?" is fraud, not romance.
        # Only pure romance words block fraud now.
        'cheat': {'exclude_any': ['wife', 'husband', 'boyfriend',
                                  'girlfriend', 'spouse',
                                  'affair', 'relationship']},
        'cheating': {'exclude_any': ['wife', 'husband', 'boyfriend',
                                     'girlfriend', 'spouse',
                                     'affair', 'relationship']},
        'cheated': {'exclude_any': ['wife', 'husband', 'boyfriend',
                                    'girlfriend', 'spouse',
                                    'affair', 'relationship']},
    },
    # 2026-10-14: infidelity_detect guard REMOVED entirely. "I heard my
    # husband talking at 2 AM" is a real infidelity question. Rely on
    # ('rumor_true', 'infidelity_detect') precedence for true rumors.
    'romance_breakup': {
        # "will it end" / "finally end" are generic — "will the suffering
        # end", "will the rain end" are not breakups. Require romance proof.
        # Guard key is the single token 'end' (present in all three
        # end-phrases); 'end the affair' carries its own proof.
        # 2026-10-14: added dating/fiance/crush/lover; removed 'marriage'
        # ("will my marriage end" → divorce, not breakup).
        'end': {'require_any': ['love', 'affair', 'relationship',
                               'boyfriend', 'girlfriend', 'breakup',
                               'break up', 'partner', 'dating', 'date',
                               'crush', 'fiance', 'fiancee', 'lover',
                               'engaged', 'together']},
    },
    'friend_to_romance': {
        # "my friend become normal towards me" is reconciliation, not
        # romance. Require a romance word near 'become'.
        'become': {'require_any': ['girlfriend', 'boyfriend', 'date',
                                  'dating', 'love', 'romance', 'romantic',
                                  'marry', 'marriage']},
    },
    'recovery_cure': {
        # "recover" is generic: "recover my stolen bike" / "recover the
        # 10 lakh rupees lent" are not health recoveries. Block the
        # money/property/theft contexts; health context needs no proof
        # ("the victim recovered" has none of these words).
        # 2026-10-14: unless_any — health words override the money veto.
        # "spent 8 lakhs in hospital, will father recover" must stay health.
        'recover': {'exclude_any': ['money', 'rupees', 'lakh', 'lent',
                                   'loan', 'debt', 'stolen', 'dues',
                                   'emi', 'crore'],
                    'unless_any': ['hospital', 'icu', 'ill', 'illness',
                                   'sick', 'disease', 'surgery', 'operation',
                                   'doctor', 'treatment', 'cancer', 'coma',
                                   'patient', 'health', 'fever', 'accident',
                                   'ventilator', 'admitted']},
        'recovered': {'exclude_any': ['money', 'rupees', 'lakh', 'lent',
                                      'loan', 'debt', 'stolen', 'dues',
                                      'emi', 'crore'],
                      'unless_any': ['hospital', 'icu', 'ill', 'illness',
                                     'sick', 'disease', 'surgery', 'operation',
                                     'doctor', 'treatment', 'cancer', 'coma',
                                     'patient', 'health', 'fever', 'accident',
                                     'ventilator', 'admitted']},
        'recovering': {'exclude_any': ['money', 'rupees', 'lakh', 'lent',
                                       'loan', 'debt', 'stolen', 'dues',
                                       'emi', 'crore'],
                       'unless_any': ['hospital', 'icu', 'ill', 'illness',
                                      'sick', 'disease', 'surgery', 'operation',
                                      'doctor', 'treatment', 'cancer', 'coma',
                                      'patient', 'health', 'fever', 'accident',
                                      'ventilator', 'admitted']},
        'recovery': {'exclude_any': ['money', 'rupees', 'lakh', 'lent',
                                     'loan', 'debt', 'stolen', 'dues',
                                     'emi', 'crore'],
                     'unless_any': ['hospital', 'icu', 'ill', 'illness',
                                    'sick', 'disease', 'surgery', 'operation',
                                    'doctor', 'treatment', 'cancer', 'coma',
                                    'patient', 'health', 'fever', 'accident',
                                    'ventilator', 'admitted']},
    },
    'education_higher': {
        # "my college friend" is not higher education. 'college' needs
        # an education word nearby.
        'college': {'require_any': ['admission', 'degree', 'studies',
                                   'study', 'exam', 'course', 'university',
                                   'phd', 'masters', 'scholar',
                                   'presentation']},
        # "Master Chef" is a cooking show, not a master's degree (stemmer
        # strips the trailing 's': masters -> master).
        'masters': {'exclude_any': ['chef', 'cook', 'masterchef', 'kitchen']},
    },
    'misplaced_item_recovery': {
        # "find a suitable rental accommodation" / "find a groom" are not
        # lost items. Block the rental/matchmaking contexts.
        'find': {'exclude_any': ['rental', 'accommodation', 'rent', 'job',
                                'groom', 'bride', 'alliance', 'match']},
    },
    'business_loss': {
        # bare "loss/losses" is generic ("car's total loss accident claim").
        # Require a business word; the multi-word phrases ('business loss',
        # 'loss in business'...) carry their own proof.
        'loss': {'require_any': ['business', 'shop', 'firm', 'company',
                                'trade', 'startup', 'factory', 'nuksan',
                                'office', 'branch', 'outlet']},
        'losses': {'require_any': ['business', 'shop', 'firm', 'company',
                                  'trade', 'startup', 'factory', 'nuksan',
                                  'office', 'branch', 'outlet']},
    },
    # 2026-10-14: bare "court" in "high court exam" is a competitive exam,
    # not litigation. Matched as a PHRASE (see _apply_trigger_guards).
    'court_case_litigation_win': {
        'court': {'exclude_phrases': ['high court exam']},
    },
}


def _apply_trigger_guards(ev_hits, text):
    """Drop event hits whose trigger word fails its collision guard.

    Returns (kept, vetoed): vetoed hits were killed by a competing-topic
    word. A vetoed AMBIGUOUS-polarity word (dismissed/settled/overturned/
    contested in a court context) must still trigger the polarity clarify
    downstream — dropping it silently would fake a "no event" result.
    """
    toks = _stem_set(text)
    kept, vetoed = [], []
    for key, kw, span in ev_hits:
        guards = TRIGGER_GUARDS.get(key, {})
        # the guard word may sit inside a multi-word phrase ("cheating on
        # me"): match on any guard word contained in the phrase's tokens
        kw_toks = {_stem(w) for w in _TOKEN_RE.findall(kw.lower())}
        g = None
        for gw, gd in guards.items():
            if _stem(gw) in kw_toks:
                g = gd
                break
        if not g:
            kept.append((key, kw, span))
            continue
        excl = {_stem(w) for w in g.get('exclude_any', [])}
        # 2026-10-14: unless_any — if any of these words are present, the
        # exclude_any veto does NOT apply (e.g. health words protect
        # recovery_cure from money-word vetoes).
        unless = {_stem(w) for w in g.get('unless_any', [])}
        # 2026-10-14: exclude_phrases — multi-word phrases matched literally
        # against the text (not word-stemmed). "high court exam" vetoes bare
        # "court" but "court case on the SSC exam" still fires.
        excl_phrases = g.get('exclude_phrases', [])
        _phrase_hit = any(ph.lower() in text.lower() for ph in excl_phrases)
        if (toks & excl or _phrase_hit) and not (toks & unless):
            vetoed.append((key, kw, span))  # competing topic wins: vetoed
            continue
        req = {_stem(w) for w in g.get('require_any', [])}
        if req and not (toks & req):
            continue                      # ambiguous word, no proof: dropped
        kept.append((key, kw, span))
    return kept, vetoed


# ---------------------------------------------------------------------------
# Event roles for the intent hierarchy (OURS 2026-09-29). Two word classes,
# not a pairwise table: outcome verbs (recover, heal, win, pass, approve,
# grant, clear) beat context/precondition nouns (surgery, theft, attempt,
# procedure) whenever both appear. Rule: if exactly ONE outcome-event is
# among the matches it wins regardless of context-events; two or more
# outcome-events is a genuine multi-event (clarify); zero outcome-events
# falls back to the old pairwise precedence.
# ---------------------------------------------------------------------------
EVENT_ROLES = {
    # context / precondition — background, never the main ask on their own
    'surgery': 'context',
    'disease_illness': 'context',
    'theft_identify_thief': 'context',
    'suspension_from_service': 'context',
}
# every other event defaults to 'outcome'


def _apply_intent_hierarchy(ev_hits):
    """Returns (ev_hits, clarified). Single outcome-event wins over contexts."""
    keys = list(dict.fromkeys(k for k, _, _ in ev_hits))
    if len(keys) <= 1:
        return ev_hits, False
    outcomes = [k for k in keys
                if EVENT_ROLES.get(k, 'outcome') == 'outcome']
    if len(outcomes) == 1:
        winner = outcomes[0]
        return [(k, kw, sp) for k, kw, sp in ev_hits if k == winner], False
    return ev_hits, False   # 0 or 2+ outcomes: caller falls back to precedence


# ---------------------------------------------------------------------------
# Polarity framing (OURS 2026-09-29). "Will my visa get rejected?" — the
# chart's YES means the visa is GRANTED, but the user asked about rejection,
# so the presented verdict must be flipped. The flip applies ONLY to events
# whose success array is the DESIRED outcome (see success_is_desired in
# events.json). Events already framed as the feared outcome (job_loss,
# divorce, fraud_deception, disease_illness, business_loss, surgery) are
# SKIPPED — flipping them would double-invert the answer.
# Unambiguous negatives flip silently; genuinely ambiguous ones
# (dismissed/settled/overturned/contested — good or bad depends on which
# side the querent is on) trigger a one-tap clarify instead of a guess.
# ---------------------------------------------------------------------------
NEGATIVE_UNAMBIG = ['reject', 'cancel', 'denied', 'deny', 'revoke',
                    'fail', 'collapse']
AMBIGUOUS_POLARITY = ['dismissed', 'dismissal', 'dropped', 'withdrawn',
                      'contested', 'overturned']
AMBIGUOUS_POLARITY_EVENTS = {'court_case_litigation_win'}

EVENT_PRE_NEGATIVE = {'job_loss_dismissal', 'divorce', 'imprisonment',
                      'fraud_deception', 'business_loss', 'disease_illness',
                      'surgery', 'suspension_from_service',
                      'romance_breakup', 'loan_repay_clear',
                      'missing_person_status', 'rumor_true',
                      'infidelity_detect'}


def _detect_framing(text, event_key):
    """Negative / ambiguous / positive framing of the question as asked.

    2026-10-14 (Gemini 4 audit): XOR parity rule. Grammatical negation
    ("not", "n't", "never") XOR negative lexeme ("fail", "reject") determines
    framing. "Will I not pass?" (True^False) = negative. "Will I not fail?"
    (True^True) = positive (double negation). Old code missed the first case
    entirely (giving the OPPOSITE answer) and double-inverted the second.
    """
    toks = _stem_set(text)
    neg = {_stem(w) for w in NEGATIVE_UNAMBIG}
    amb = {_stem(w) for w in AMBIGUOUS_POLARITY}
    if event_key in AMBIGUOUS_POLARITY_EVENTS and (toks & amb):
        return 'ambiguous'
    # Grammatical negation: check raw text for not/n't/never/no chance
    # within a 3-token window before the event verb
    has_gram_neg = bool(re.search(
        r"\b(not|never|n't|no chance|without)\b", text.lower()))
    has_neg_lexeme = bool(toks & neg)
    # XOR: exactly one of (grammatical neg, negative lexeme) = negative framing
    if has_gram_neg ^ has_neg_lexeme:
        return 'negative'
    return 'positive'


def _detect_form(text):
    found = []
    for form, pats in FORM_PATTERNS:
        for p in pats:
            if re.search(p, text):
                found.append(form)
                break
    nq = text.count('?')
    if len(found) >= 2 or (nq >= 2 and len(found) >= 1):
        return 'compound'
    return found[0] if found else 'yes_no'


def _detect_polarity(text, event, form=None, subject=None):
    t = ' ' + text + ' '
    # advice questions ('should I', 'what is good for me') are neutral —
    # the querent asks for guidance, not for a gain (blind-label agreement)
    if form == 'advice':
        return 'neutral'
    # asking for information, or about a third party's win, is neutral —
    # the querent has no personal stake either way
    if form == 'identification':
        return 'neutral'
    if subject == 'stranger_unknown' and event in ('election_win', 'contest_win'):
        return 'neutral'
    if NEGATION.search(t):
        base = 'adverse'
    else:
        base = 'seek_gain'
    adverse_events = {'job_loss_dismissal', 'divorce', 'imprisonment',
                      'fraud_deception'}
    if event in adverse_events:
        return 'adverse'
    if event == 'longevity' and any(w in t for w in ['die', 'death', 'assassinat', 'pass away']):
        return 'adverse'
    if event == 'court_case_litigation_win' and 'guilty' in t:
        return 'adverse'
    if event == 'job_change':
        return 'neutral'
    if any(w in t for w in ADVERSE_CORES) and event in (
            'court_case_litigation_win', 'business_loss', 'property_sale'):
        return 'adverse'
    return base


def _proper_noun_subject(text):
    """'Will X win ...?' / 'Will X or Y ...?' with capitalized names -> stranger."""
    stop = {'i', 'we', 'my', 'the', 'this', 'that', 'it', 'he', 'she',
            'they', 'you', 'a', 'an', 'be', 'is', 'are', 'was', 'were',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'can', 'could', 'will', 'would', 'shall', 'should', 'may',
            'might', 'must', 'mr', 'mrs', 'ms', 'dr'}
    for pat in (r'\b[Ww]ill\s+([A-Z][a-z]+(?:\s+or\s+[A-Z][a-z]+)?)\b',
                r'\bbetween\s+([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\b',
                r'\b([A-Z][a-z]+)\s+or\s+([A-Z][a-z]+)\b'):
        m = re.search(pat, text)  # case-SENSITIVE: 'buying' must not match
        if m:
            names = [g for g in m.groups() if g and g.lower() not in stop]
            if names:
                return ' or '.join(names)
    return None


# regex-based event triggers for patterns phrases can't cover (OURS)
REGEX_EVENTS = {
    'misplaced_item_recovery': [
        r"\blost\s+(?:my|his|her|their|the)\s+(?!job\b)\w+",   # lost his wallet
        r"\bcannot\s+trace\s+(?:my|his|her|their)\b",
    ],
    'business_start': [
        r"\bbuy\b.{0,120}\bprofitable\b",   # buy equipment; will it be profitable
    ],
    'job_get_service': [
        r"\bfull.?time\b.{0,25}\bjob\b",   # full time & stable job
        r"\bget\s+(?:a\s+|the\s+|this\s+|that\s+|new\s+)?job\b(?!\s+back\b)",  # get the job (not 'get my job back' = reinstatement)
    ],
    'rumor_true': [
        r"\bis\s+it\s+(?:also\s+)?true\s+that\b",
    ],
    'election_win': [
        r"\bwin\s+(?:the\s+)?(?:election|elections|polls?)\b",
        r"\b(?:become|as)\s+(?:the\s+|a\s+)?(?:cm|pm|chief minister|prime minister|president|minister)\b",
        r"\bcome\s+to\s+power\b",   # 'come to power again in the elections'
    ],
    'contest_win': [
        r"\bwin\s+(?:the\s+)?(?:\w+\s+){0,2}(?:match|title|trophy|cup|tournament|game)\b",
    ],
    # 2026-10-14: "Is Rahul cheating?" — named person + cheating = infidelity,
    # not financial fraud. Matches "is X cheating" where X is not a pronoun
    # or common word (text is lowercased by now, so use exclusion list).
    'infidelity_detect': [
        r"\bis\s+(?!(he|she|it|this|that|my|the|a|an)\b)([a-z]+)\s+cheating\b",
    ],
}

INLAW_WORDS = ['father in law', 'mother in law', 'son in law',
               'daughter in law', 'brother in law', 'sister in law']
GRANDCHILD_WORDS = ['grandson', 'granddaughter', 'grandchild',
                    'grandchildren']
RELATION_WORDS = {'wife', 'husband', 'spouse', 'son', 'daughter', 'child',
                  'children', 'father', 'mother', 'brother', 'sister',
                  'sibling', 'friend', 'partner', 'uncle', 'aunt',
                  'nephew', 'niece', 'cousin'}
THIRD_POSSESSIVE = re.compile(
    r'\b(his|her|their)\s+(' + '|'.join(sorted(RELATION_WORDS | {'marriage', 'wedding'})) + r')\b')
POSSESSIVE_CHAIN = re.compile(
    r'\b(my\s+)?(' + '|'.join(sorted(RELATION_WORDS)) + r")'s\s+"
    r'(?:\w+\s+)?(' + '|'.join(sorted(RELATION_WORDS)) + r')\b')
TITLE_NOUN = re.compile(
    r'\b(?:[Mm][Rr]|[Mm][Rr][Ss]|[Mm][Ss]|[Dd][Rr]|[Ss][Rr][Ii]|[Ss][Mm][Tt])'
    r'\.?\s+([A-Z][a-z.]+(?:\s+[A-Z][a-z.]+)?)\b')
FIRST_PERSON = re.compile(r"\b(i|me|my|myself|we|our)\b")
STRONG_FIRST = re.compile(r"\b(i|we|myself)\b")  # subject-position self
# Rule 4 ex-trap (USER-RULING 2026-09-28)
EX_SPOUSE = re.compile(r"\bex[-\s]?(wife|wives|husband|husbands|spouse)\b")
EX_ROMANCE = re.compile(r"\bex[-\s]?(girlfriend|girlfriends|boyfriend|boyfriends)\b")
EX_AMBIG = re.compile(r"\bex[-\s]?(partner|partners|lover|lovers|fiance|fiancee|fianc\u00e9|fianc\u00e9e)\b")
# default-to-stranger (USER-RULING 2026-09-28): about someone else, relation
# not mentioned -> stranger_unknown, no follow-up question.
THIRD_PERSON_REF = re.compile(r"\b(that|this)\s+(person|man|woman|boy|girl|guy|lady|fellow)\b")
# definite but unnamed third party: "the lady", "the victim", "the road-
# accident victim" — a real person the text never names. Book: unnamed
# person = 9th (stranger). "The lady" is not the querent (policy 2026-09-29:
# default-self only when NO third party is referenced at all).
DEFINITE_THIRD = re.compile(
    r"\bthe\s+(?:\w+\s+){0,2}(lady|victim|victims|gentleman)\b")
DANGLING_PRONOUN = re.compile(r"\b(he|she|they|him|her|them|his|hers|their)\b")

MONEY_EVENTS = {'money_gain', 'inheritance_claim'}

# When two events fire, the question's main clause wins. OURS, documented.
EVENT_PRECEDENCE = [
    ('recovery_cure', 'disease_illness'),
    ('recovery_cure', 'missing_person_return'),
    ('job_get_service', 'job_loss_dismissal'),
    ('stolen_property_recovery', 'money_gain'),
    ('fraud_deception', 'money_gain'),
    ('fraud_deception', 'marriage'),
    ('rumor_true', 'money_gain'),
    ('rumor_true', 'fraud_deception'),
    ('misplaced_item_recovery', 'job_loss_dismissal'),
    ('misplaced_item_recovery', 'recovery_cure'),
    ('second_marriage', 'marriage'),
    ('second_marriage', 'divorce'),
    ('divorce', 'marriage'),
    ('childbirth', 'marriage'),
    ('disease_illness', 'longevity'),
    ('business_loss', 'disease_illness'),
    ('exam_pass_general', 'education_general'),
    ('exam_competitive', 'exam_pass_general'),
    ('education_higher', 'education_general'),
    ('stock_speculation', 'business_profit'),
    # 2026-10-14: flipped — property_sale is more specific than bare "money".
    # "Will I get good money from my property sale?" must route to property_sale.
    ('property_sale', 'money_gain'),
    ('job_loss_dismissal', 'job_change'),
    ('election_win', 'job_get_service'),
    ('election_win', 'rumor_true'),
    ('missing_person_status', 'missing_person_return'),
    ('jail_release', 'court_case_litigation_win'),
    # 2026-10-14: flipped — imprisonment is STAGE1_ONLY (unsupported dead-end).
    # A supported outcome (jail_release, court win) must never be killed by it.
    ('jail_release', 'imprisonment'),
    ('court_case_litigation_win', 'imprisonment'),
    ('business_start', 'business_profit'),
    # 2026-10-14: REMOVED ('exam_competitive', 'court_case_litigation_win').
    # "high court exam" no longer triggers court_case (phrase guard); a real
    # "court case on the SSC exam" must keep court_case.
    ('court_case_litigation_win', 'exam_competitive'),
    ('stock_speculation', 'property_purchase_readybuilt'),
    ('stock_speculation', 'property_sale'),
    # relationship routing (2026-09-28): rumor about an affair is a rumor
    # question (W33); an explicit ending beats a vague affair mention (W56);
    # an ex coming back is a reunion, not a missing person (Rule 3).
    ('rumor_true', 'romance_materialise'),
    ('rumor_true', 'romance_breakup'),
    ('rumor_true', 'love_affair'),
    ('rumor_true', 'infidelity_detect'),
    ('romance_breakup', 'romance_materialise'),
    ('romance_breakup', 'love_affair'),
    # 2026-09-29: alimony is about the money, not the divorce itself;
    # a cheating question is infidelity detection, not fraud or romance odds.
    ('alimony_settlement', 'divorce'),
    ('alimony_settlement', 'money_gain'),
    ('infidelity_detect', 'fraud_deception'),
    ('infidelity_detect', 'romance_materialise'),
    ('infidelity_detect', 'love_affair'),
    ('romance_reunion', 'missing_person_return'),
    ('romance_reunion', 'romance_materialise'),
    ('spouse_return_estranged', 'missing_person_return'),
    ('friend_to_romance', 'marriage'),
    # "interviewed for promotion": the interview is background, the
    # promotion is the question (D12).
    ('promotion', 'job_get_service'),
    # 2026-10-14 (Gemini 4 audit): transitive closure edges. The single-pass
    # loop can't follow A>B>C chains, so add the direct A>C edges:
    ('recovery_cure', 'longevity'),
    ('recovery_cure', 'missing_person_status'),
    ('job_get_service', 'job_change'),
    ('exam_competitive', 'education_general'),
    ('exam_appear', 'exam_pass_general'),
    # 2026-10-14 (Batch 1 fixes): "get a transfer in my bank job" fires both
    # job_get_service and transfer_job — the specific transfer wins.
    ('transfer_job', 'job_get_service'),
    # "I am pregnant, will my transfer get approved" — transfer is the ask,
    # pregnancy is background context.
    ('transfer_job', 'childbirth'),
    # "Will my ex-wife get married?" — explicit marriage beats the implicit
    # ex->return assumption.
    ('marriage', 'spouse_return_estranged'),
    # 2026-10-14: "Is my business partner cheating me?" — fraud is the ask,
    # not the partnership itself.
    ('fraud_deception', 'business_partnership'),
    # 2026-10-14: "will my marriage end" → divorce, not romance_breakup.
    ('divorce', 'romance_breakup'),
    # "Will my marriage survive?" — survive refers to the marriage, not lifespan.
    ('marriage', 'longevity'),
    # "Will I get my money back?" — specific recovery beats bare "money".
    ('money_lent_recovery', 'money_gain'),
]


def dissect(question, ref=None, use_gemini=True):
    """Stage-1 dissect. Same contract as layer1_dissect.dissect.

    status 'ok': {subject_key, event_key, form, polarity, spans, window_...}
    status 'clarify': {field, question, options, guess}
    status 'out_of_scope': {topic, question, reason, handoff, spans}
        (v10.4 Phase 4: clearly outside the 4 topics or content-free ->
        human_chat handoff, not a dead-end clarify)
    v10.4 Gemini fallback (user-approved 2026-10-06): when use_gemini is
    True and rules return NO_EVENT (not out_of_scope), Gemini maps the
    question to an existing event; learned keywords are saved unreviewed.
    use_gemini=False reproduces the exact pre-fallback behavior.
    """
    try:
        return _dissect(question, ref=ref, use_gemini=use_gemini)
    except Exception as e:
        return {'status': 'clarify', 'field': 'event',
                'question': 'I could not understand that question. What is it about?',
                'options': [], 'error': str(e)[:120]}


# v10.4 Phase 4: out-of-scope detection. Conservative by design — only fires
# when the question is clearly outside the 4 product topics (career, exam,
# relationship, money) or is content-free. Called at the NO_EVENT point in
# _dissect (AFTER event matching), so in-scope questions whose events matched
# never reach here. When in doubt, returns None -> existing clarify path.
_OUT_OF_SCOPE_POLITICS = [
    'parliament', 'lok sabha', 'rajya sabha', 'jan lokpal', 'lokpal',
    'legislative assembly', 'vidhan sabha',
]
_OUT_OF_SCOPE_INSURANCE = [
    'insurance', 'mediclaim', 'medi claim', 'sum insured', 'sum assured',
]
_OUT_OF_SCOPE_CAREER_WORDS = [
    'working', 'company', 'project', 'employer', 'colleague', 'office',
    'boss', 'negotiation',
]
_OUT_OF_SCOPE_QUESTION_WORDS = {
    # Interrogatives + modals that mark a real question. Be/do verbs
    # ('is','are','do'...) excluded — they appear in statements too
    # ("This is my personal query...").
    'will', 'would', 'can', 'could', 'shall', 'should', 'may', 'might',
    'when', 'what', 'where', 'who', 'whom', 'how', 'why', 'whether',
    'if', 'chance', 'chances',
}
_OUT_OF_SCOPE_PERSON_WORDS = (
    'girl|boy|man|woman|person|lady|guy|fellow|caller'
)


def _detect_out_of_scope(t, spans):
    """Return {'topic', 'reason'} if clearly out of scope, else None.

    t: normalized full question text. Only called when no event matched.
    """
    # 1. Politics / legislative (W93: Jan Lokpal bill in parliament).
    # election_win questions never reach here (their event matched).
    if any(_hit(t, w) for w in _OUT_OF_SCOPE_POLITICS):
        return {'topic': 'politics',
                'reason': 'political/legislative matter — outside the 4 '
                          'topics (career, exam, relationship, money)'}
    if (_hit(t, 'bill') or _hit(t, 'act of parliament')) and any(
            _hit(t, w) for w in ('government', 'upa', 'nda', 'passed by',
                                 'passage of', 'parliament')):
        return {'topic': 'politics',
                'reason': 'government bill/legislation — outside the 4 topics'}
    # 2. Insurance (NEW-Unknown-087: mediclaim). 'policy' alone is ambiguous
    # (government policy), so it needs an insurance anchor.
    if any(_hit(t, w) for w in _OUT_OF_SCOPE_INSURANCE):
        return {'topic': 'insurance',
                'reason': 'insurance matter — outside the 4 topics'}
    if _hit(t, 'policy') and any(_hit(t, w) for w in (
            'premium', 'cover', 'insured', 'claim', 'maturity')):
        return {'topic': 'insurance',
                'reason': 'insurance matter — outside the 4 topics'}
    # 3. Caller-identity question (NEW-KPSublordSpeaksPa-112:
    # "is it the girl I am in league with?") — asks WHO, not what will
    # happen. Not a standard outcome question. Checked before the
    # content-free rule (it has no question-markers, so that would fire).
    # Note: _norm strips '?', so markers (not punctuation) are the signal.
    if re.search(r'\bis it (the|a|this)\s+(?:' + _OUT_OF_SCOPE_PERSON_WORDS
                 + r')\b', t):
        return {'topic': 'relationship',
                'reason': 'caller-identity question — unclear what outcome '
                          'is being asked'}
    # 4. Content-free: no interrogative/modal markers at all, very short
    # (H-C10: "This is my personal query regarding the job." — no question).
    words = t.split()
    if (len(words) < 25
            and not any(_hit(t, w) for w in _OUT_OF_SCOPE_QUESTION_WORDS)):
        return {'topic': None,
                'reason': 'no clear question asked — too vague to route'}
    # 5. Ruled-out property events (user ruling 2026-10-06: property_retain
    # and property_rent_out left out — no event exists by design).
    if ((_hit(t, 'stay with me') or _hit(t, 'remain with me'))
            and any(_hit(t, w) for w in ('land', 'property', 'plot', 'house'))):
        return {'topic': 'property',
                'reason': 'property retention — not a reading we do yet'}
    if re.search(r'\b(get|find|getting|need)\s+a\s+tenant\b', t):
        return {'topic': 'property',
                'reason': 'renting out property — not a reading we do yet'}
    # 6. Likely career but unroutable (H-C13: matcher window limitation).
    # Narrow: needs career-signal words AND real question-markers, so pure
    # keyword-gap cases stay NO_EVENT for Phase 3 to fix.
    if (any(_hit(t, w) for w in _OUT_OF_SCOPE_QUESTION_WORDS)
            and any(_hit(t, w) for w in _OUT_OF_SCOPE_CAREER_WORDS)):
        return {'topic': 'career',
                'reason': 'looks career-related but no event matched '
                          'confidently — needs human judgment'}
    return None


# v10.4 Gemini fallback helpers (user-approved 2026-10-06).
# These ONLY run at the NO_EVENT point inside _dissect — after rules found
# nothing and _detect_out_of_scope returned None. They never override a
# rule match and never fire for out_of_scope questions.

def _check_learned_triggers(t):
    """Return (phrase, event, reviewed) for the first learned trigger in t.

    Reviewed triggers were already injected into EVENT_PHRASES at import,
    so in practice only unreviewed (low-weight) ones reach here. Returns
    None if no learned phrase matches. Never raises.
    """
    if _GF is None:
        return None
    try:
        for phrase, event, reviewed in _GF.get_learned_triggers():
            if _hit(t, phrase):
                return (phrase, event, reviewed)
    except Exception:
        pass
    return None


def _fallback_subject(spans):
    """Subject for the AI-fallback paths, from the word-boundary-matched
    subject spans (2026-10-15, review 1.8). The old substring loop matched
    'son' inside 'person'/'soon'/'reason' and 'mom' inside 'moment',
    mis-resolving subjects to children/mother. The main path's _match()
    already resolved subjects correctly, so reuse its result."""
    _hit0 = (spans.get('subject') or [None])[0]
    if _hit0:
        _sk = _hit0[0]
        try:
            return _sk, OLD.SUBJECTS[_sk]['base_house']
        except (KeyError, AttributeError, TypeError):
            return _sk, 1
    return 'self', 1


def _gemini_fallback(question, t):
    """Ask Gemini to map the question to an existing event.

    Returns the event key or None. Learned keywords are saved as
    unreviewed (collision-checked). STAGE1_ONLY_EVENTS are excluded from
    candidates (no L3 arrays). Never raises.
    """
    if _GF is None:
        return None
    try:
        candidate_events = {k for k in EVENT_PHRASES
                            if k not in STAGE1_ONLY_EVENTS}
        known_vocab = set()
        for phrases in EVENT_PHRASES.values():
            for p in phrases:
                known_vocab.update(p.lower().split())
        existing_keywords = {p.lower() for phrases in EVENT_PHRASES.values()
                             for p in phrases}
        event, _saved = _GF.fallback_for_question(
            question, t, known_vocab, candidate_events, existing_keywords)
        return event
    except Exception:
        return None


def _dissect(question, ref=None, use_gemini=True):    # Two views of the question (all blind to outcomes):
    # - t_ev:   full text, parens kept (F8: 'work permit' lived in parens)
    # - t_subj: commentator parentheticals stripped (J87: '(querist, ...; father'
    #           is background, not the question's subject).
    # Window extraction still uses the full original question.
    t_ev = OLD._norm(question or '')
    t_subj = OLD._norm(re.sub(r'\([^)]*\)', ' ', question or ''))
    t = t_ev  # legacy alias: event/guards below use the full view
    if not t:
        return {'status': 'clarify', 'field': 'event',
                'question': 'Please ask your question.', 'options': []}

    # 'querist/querent' in background parens still anchors the self (J87)
    querist_self = bool(re.search(r'\bquerist\b|\bquerent\b', t))
    spans = {}
    # subsume=True for subjects: "brother in law" must not also fire "brother"
    sub_hits = _match(SUBJECT_PHRASES, t_subj, subsume=True)
    # in-law ownership (2026-09-29): "my father-in-law" is the querent's;
    # "the consultant's father-in-law" / "his father-in-law" belongs to
    # someone else -> not the querent's in-law (would rotate to the wrong
    # house). Exception: the possessor is the querent's own kin ("my
    # husband's father-in-law" IS the querent's father-in-law).
    _INLAW_KEYS = {'father_in_law', 'mother_in_law', 'brother_in_law',
                   'sister_in_law', 'son_in_law', 'daughter_in_law'}
    _THIRD_POSS = re.compile(r"\b\w+'s\b|\b(his|her|hers|their|theirs)\b")
    _KIN_SINGLE = {'wife', 'husband', 'spouse', 'son', 'daughter', 'father',
                   'mother', 'brother', 'sister', 'sibling'}
    third_party_inlaw = False
    kept_sub = []
    for key, kw, span in sub_hits:
        if key in _INLAW_KEYS:
            idx = t_subj.find(span)
            before = t_subj[max(0, idx - 30):idx] if idx >= 0 else ''
            before_np = re.sub(r"\b(my|our|mine|ours)\b", ' ', before)
            m = _THIRD_POSS.search(before_np)
            if m:
                raw = m.group(0).lower()
                # "consultant's" -> possessor "consultant";
                # "his"/"her"/"their" -> the pronoun itself
                possessor = raw[:-2] if raw.endswith("'s") else raw
                # "my husband's father-in-law": possessor is querent's kin
                if possessor in _KIN_SINGLE and re.search(
                        r'\b(my|our)\b\s+' + re.escape(possessor), before):
                    kept_sub.append((key, kw, span))
                    continue
                third_party_inlaw = True
                continue  # someone else's in-law: not the querent's
        kept_sub.append((key, kw, span))
    sub_hits = kept_sub
    ev_hits = _match(EVENT_PHRASES, t, REGEX_EVENTS)
    for key, kw, span in sub_hits:
        spans.setdefault('subject', []).append((key, span))
    for key, kw, span in ev_hits:
        spans.setdefault('event', []).append((key, span))

    # birth-chart guard: 'birth chart'/'natal chart' is not childbirth (W35)
    if any(_hit(t, w) for w in ['birth chart', 'natal chart', 'janma kundli']):
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits if k != 'childbirth']

    # trap: loan repay beats bare 'loan' borrow
    if 'loan_repay_clear' in [k for k, _, _ in ev_hits]:
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                   if not (k == 'loan_borrow_get' and kw.strip() == 'loan')]

    # collision guards (2026-09-29): ambiguous single-word triggers
    # ("transfer", "dismissed", "cheat") must prove their topic; a
    # competing-topic word vetoes them outright. Silent-wrong-answer class.
    ev_hits, vetoed_hits = _apply_trigger_guards(ev_hits, t)
    spans['event'] = [(k, sp) for k, kw, sp in ev_hits]
    # vetoed ambiguous-legal word (dismissed/settled/overturned/contested in
    # a court context): the question IS understood — it's a court case whose
    # polarity is ambiguous. Ask which side the querent is on (user ruling).
    if not ev_hits and vetoed_hits:
        amb = {_stem(w) for w in AMBIGUOUS_POLARITY}
        vetoed_toks = set()
        for _, kw, _ in vetoed_hits:
            vetoed_toks |= {_stem(w) for w in _TOKEN_RE.findall(kw.lower())}
        if vetoed_toks & amb:
            return {'status': 'clarify', 'field': 'polarity',
                    'question': 'Are you hoping the case continues, or that it ends?',
                    'options': [{'key': 'END', 'label': 'I want the case to end'},
                                {'key': 'CONTINUE',
                                 'label': 'I want to continue / fight the case'}],
                    'guess': None, 'spans': spans,
                    'polarity_hint': 'END inverts the verdict at presentation'}

    # vague job change ('any change in the present job', A12): name the gap,
    # do not force-fit job_get_service
    if (not ev_hits and 'change' in t
            and any(_hit(t, w) for w in
                    ['job', 'naukri', 'service', 'posting', 'employment'])):
        ev_hits = [('job_change', 'change (unspecified)', 'change')]
        spans.setdefault('event', []).append(
            ('job_change', 'change (unspecified)'))

    # animate/inanimate pre-prune (2026-09-29): "my missing laptop" — an
    # object can never be a missing PERSON. Drop missing_person_return when
    # an object word is present, before precedence/clarify sees it, so a
    # laptop can't force a fake multi-event choice. Pets never reach here:
    # the pet clarify above already returned.
    if any(_hit(t, w) for w in OBJECT_WORDS):
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                   if k != 'missing_person_return']
        spans['event'] = [(k, sp) for k, kw, sp in ev_hits]

    # FIXED 2026-10-06 (W88): bare 'buying' must not match property purchase
    # in business/partnership contexts ("buying/repairing damaged cars").
    if any(k == 'business_partnership' for k, _, _ in ev_hits):
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                   if not (k.startswith('property_') and kw == 'buying')]
    ev_keys = [k for k, _, _ in ev_hits]
    ev_set = set(ev_keys)
    if 'childbirth' in ev_set and 'marriage' in t:
        # Check if childbirth was triggered only by 'born' (existing child)
        # vs actual pregnancy/birth keywords
        childbirth_kws = [kw for k, kw, sp in ev_hits if k == 'childbirth']
        if all('born' in kw for kw in childbirth_kws):
            ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                       if k != 'childbirth']
    # directional court/imprisonment rule (W191 vs W193): the verdict question
    # ('found guilty') is a court case; the punishment question
    # ('get imprisonment') is imprisonment.
    if 'court_case_litigation_win' in ev_set and 'imprisonment' in ev_set:
        if 'found guilty' in t:
            ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                       if k != 'imprisonment']
        elif 'get imprisonment' in t or 'imprisonment punishment' in t:
            ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                       if k != 'court_case_litigation_win']
    ev_keys = [k for k, _, _ in ev_hits]
    ev_set = set(ev_keys)
    for winner, loser in EVENT_PRECEDENCE:
        if winner in ev_set and loser in ev_set:
            # 2026-10-14: an unsupported (STAGE1_ONLY) event must never prune
            # a supported event. Skip the pair instead of killing the outcome.
            if winner in STAGE1_ONLY_EVENTS and loser not in STAGE1_ONLY_EVENTS:
                continue
            if winner == 'disease_illness' and loser == 'longevity':
                # A3.3 (2026-10-02): survival is the ask, illness is context.
                # 'will he survive the illness' -> longevity. The old
                # precedence only stands when the longevity hit is the
                # duration sense ('how long will', 'lifespan'), not a
                # survival/death verb.
                lon_kws = [kw for k, kw, sp in ev_hits if k == 'longevity']
                if any(re.search(r'surviv|\bdie\b|\bdeath\b|\bdead\b|'
                                 r'pass away|assassinat', kw)
                       for kw in lon_kws):
                    ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                               if k != winner]
                    ev_set = set(k for k, _, _ in ev_hits)
                    continue
            if winner == 'job_get_service' and loser == 'job_loss_dismissal':
                # bare 'job' is context; 'asked to resign' is the ask (W69).
                # A substantive job_get phrase ('new job','get a job') wins back.
                get_spans = [sp for k, kw, sp in ev_hits if k == winner]
                if all(sp.strip() == 'job' for sp in get_spans):
                    ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                               if k != winner]
                    continue
                # 2026-10-14: "will I get fired from my new job?" — the LOSS
                # is the question (future/interrogative), not background.
                # Only let job_get win when the loss is past-tense/background.
                # Check the FULL text (spans are just the trigger words).
                _future_loss = bool(re.search(
                    r'\b(will|shall|can|could|would|may|might)\b[^.]{0,40}'
                    r'\b(fir|fired|lose|losing|lost|terminat|sack|lay.?off|'
                    r'retrench|dismiss)\b', t, re.I))
                if _future_loss:
                    # loss is the ask: kill job_get instead
                    ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                               if k != winner]
                    ev_set.discard(winner)
                    continue
            ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits if k != loser]
    ev_keys = [k for k, _, _ in ev_hits]
    # intent hierarchy (2026-09-29): exactly one outcome-event among the
    # matches beats any number of context-events ("recover" is the ask;
    # "surgery"/"stolen" is background). Zero or 2+ outcome-events falls
    # through to the old clarify below.
    ev_hits = _apply_intent_hierarchy(ev_hits)[0]
    ev_keys = [k for k, _, _ in ev_hits]
    spans['event'] = [(k, sp) for k, kw, sp in ev_hits]
    if 'childbirth' in ev_keys:
        baby_only = all(kw in ('baby', 'child', 'children', 'kid', 'son',
                               'daughter', 'beta', 'beti')
                        for k, kw, _ in sub_hits if k == 'children')
        if baby_only:
            sub_hits = [(k, kw, sp) for k, kw, sp in sub_hits
                        if k != 'children']

    # pets: detected, named, not force-fit ('my'->self must not block it)
    real_sub_hits = [(k, kw, sp) for k, kw, sp in sub_hits if k != 'self']
    if any(_hit(t, w) for w in PET_WORDS) and not real_sub_hits:
        return {'status': 'clarify', 'field': 'subject',
                'question': 'Is this about your pet? I read for people, not '
                            'pets yet — but tell me whose pet and I will note it.',
                'options': [{'key': 'self', 'label': 'My pet'}],
                'guess': None, 'gap': 'pets'}

    # journeys without abroad: detected, named, not force-fit
    if (any(_hit(t, w) for w in JOURNEY_WORDS)
            and 'foreign_travel' not in ev_keys):
        return {'status': 'clarify', 'field': 'event',
                'question': 'Is this a journey within the country? I cover '
                            'foreign travel and visas so far — say more.',
                'options': [], 'guess': None, 'gap': 'journey'}

    # subject guards (OURS, all blind-to-outcome): relations that are one step
    # removed from the querent have no table entry -> stranger_unknown.
    # In-laws are NOT forced here anymore (2026-09-29): father/mother/
    # brother/sister/son/daughter-in-law are derived by Bhavat Bhavam
    # (9th/4th/3rd from 7th etc.) via SUBJECT_PHRASES.
    def _force_stranger(reason_span):
        return [PROPER_NOUN_SUBJECT]

    forced = None
    _kin_childbirth_redirect = False
    if any(_hit(t_subj, w) for w in GRANDCHILD_WORDS):
        forced = 'grandchild (no table entry)'
    elif POSSESSIVE_CHAIN.search(t_subj):
        # "my sister's husband", "friend's elder sister"
        forced = 'possessive chain'
    elif THIRD_POSSESSIVE.search(t_subj):
        # "his wife", "her son" — someone else's relative
        forced = 'third-person possessive'

    # named third party with no relation matched -> stranger_unknown
    sub_keys = [k for k, _, _ in sub_hits]
    # 2026-10-14 (Gemini 4 audit): "[kin]'s wife" + childbirth → route to the
    # KIN, not the wife. 5th from brother (3rd) = 7th house (correct); 5th from
    # sister_in_law (9th) = 1st house (double-rotation distortion).
    _kin_childbirth_redirect = False
    if ev_keys and ev_keys[0] == 'childbirth' and re.search(
            r"\bmy\s+(brother|sister|son|daughter)'s\s+(wife|husband)\b", t_subj):
        _kin = re.search(r"\bmy\s+(brother|sister|son|daughter)'s\s+", t_subj).group(1)
        _kin_map = {'brother': 'younger_sibling', 'sister': 'younger_sibling',
                    'son': 'children', 'daughter': 'children'}
        sub_keys = [_kin_map.get(_kin, 'younger_sibling')]
        spans['subject'] = [(sub_keys[0], "kin-of-couple (childbirth)")]
        _kin_childbirth_redirect = True
    name = _proper_noun_subject(question or '')
    tm = TITLE_NOUN.search(question or '')
    if not name and tm:
        name = tm.group(1)
    # anonymized/all-caps subjects: 'Will BJP+ win ...', 'When will XYZ receive ...'
    if not name:
        m = re.search(r'\b(?:will|shall|can)\s+([A-Z]{2,}\+?)(?![A-Za-z])',
                      question or '')
        if m:
            name = m.group(1)
    # election/contest about a named public figure not adjacent to 'will':
    # 'incumbent CM Narendra Modi ...' (W141). Uses the provisional event —
    # full event resolution (with its guards) runs just below.
    prov_event = ev_keys[0] if ev_keys else None
    if not name and prov_event in ('election_win', 'contest_win'):
        m = re.search(r'(?<!^)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
                      question or '')
        if m:
            name = m.group(1)
    # any other event about a named person mid-sentence ('... Barack Obama ...
    # Beyonce ...', W33): a named third party with no relation matched.
    if not name and ev_keys and not sub_keys:
        m = re.search(r'(?<!^)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
                      question or '')
        if m and not FIRST_PERSON.search(t_subj):
            name = m.group(1)
    self_kws = [kw.strip() for k, kw, _ in sub_hits if k == 'self']
    weak_self_only = (sub_keys == ['self'] and bool(self_kws) and all(
        kw in ('me', 'my', 'myself') for kw in self_kws))
    if forced and not _kin_childbirth_redirect:
        sub_keys = _force_stranger(forced)
        spans['subject'] = [(PROPER_NOUN_SUBJECT, forced)]
    elif name and (not sub_keys or weak_self_only):
        # 'Will Mr. A.V. ever marry me?' is about Mr. A.V., not the querent
        sub_keys = [PROPER_NOUN_SUBJECT]
        spans['subject'] = [(PROPER_NOUN_SUBJECT, name)]
    else:
        # default-to-stranger (USER-RULING 2026-09-28): the question is about
        # someone else and the relation is not mentioned -> stranger_unknown,
        # no follow-up question. 'that person', 'this man', 'the lady',
        # 'the victim', or a dangling he/she/they with no strong self
        # anchor and no real subject.
        # A real subject ('will that person harm my son?') is never
        # overridden.
        third_ref = THIRD_PERSON_REF.search(t_subj) or DEFINITE_THIRD.search(t_subj)
        dangling = (bool(DANGLING_PRONOUN.search(t_subj))
                    and not STRONG_FIRST.search(t_subj))
        if (third_ref or dangling) and (not sub_keys or weak_self_only):
            who = (third_ref.group(0) if third_ref
                   else 'unnamed third person')
            sub_keys = [PROPER_NOUN_SUBJECT]
            spans['subject'] = [(PROPER_NOUN_SUBJECT, who)]

    # Rule 4 ex-trap (USER-RULING): resolve the bucket before event resolution.
    # ex-wife/husband -> 7th bucket; ex-girlfriend/boyfriend -> 5th bucket;
    # ex-partner/lover/fiance -> halt and ask which bucket.
    ex_spouse = bool(EX_SPOUSE.search(t_subj))
    ex_romance = bool(EX_ROMANCE.search(t_subj))
    if EX_AMBIG.search(t_subj) and not (ex_spouse or ex_romance):
        return {'status': 'clarify', 'field': 'subject',
                'question': 'To calculate the exact coordinates, please '
                            'clarify your relationship with this person. '
                            'Were you legally married/engaged, or were you '
                            'dating?',
                'options': [{'key': 'spouse_partner',
                             'label': 'Legally married / engaged'},
                            {'key': 'romantic_partner',
                             'label': 'We were dating'}],
                'guess': None, 'gap': 'ex-bucket', 'spans': spans}
    if ex_spouse:
        sub_keys = ['spouse_partner']
        spans['subject'] = [('spouse_partner', 'ex-spouse')]
        # the spouse bucket owns "come back": drop the dating-bucket event so
        # unordered matching ("my ex come back" ~ "my ex-wife ... come back")
        # can't force a fake multi-event clarify
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                   if k != 'romance_reunion']
        spans['event'] = [(k, sp) for k, kw, sp in ev_hits]
    elif ex_romance:
        sub_keys = ['romantic_partner']
        spans['subject'] = [('romantic_partner', 'ex-romance')]
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                   if k != 'spouse_return_estranged']
        spans['event'] = [(k, sp) for k, kw, sp in ev_hits]
    # the trap pruned a competing bucket event -> recompute keys so the
    # multi-event clarify below sees the pruned list, not the stale one
    if ex_spouse or ex_romance:
        ev_keys = [k for k, _, _ in ev_hits]

    # v9.7 specificity (2026-10-05): a specific money event beats bare
    # money_gain when both fire on the same question.
    # v10.4 (2026-10-06, Phase 2): added loan_borrow_get, loan_repay_clear,
    # stock_speculation — "borrow the money as a loan" (A24), "borrow from
    # relatives" (NEW-NewDimensionsofK-153) are loans, not generic gains.
    _SPECIFIC_BEATS_MONEY = {'provident_fund_pension', 'donation_receive',
                             'lottery', 'loan_borrow_get', 'loan_repay_clear',
                             'stock_speculation'}
    if 'money_gain' in ev_keys and any(k in ev_keys
                                       for k in _SPECIFIC_BEATS_MONEY):
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits
                   if k != 'money_gain']
        spans['event'] = [(k, sp) for k, kw, sp in ev_hits]
        ev_keys = [k for k, _, _ in ev_hits]

    # v10.4 precedence guards (2026-10-06, Phase 2): resolve false
    # multi-event clarifies where the question is really about one matter.
    # Each guard prunes the losing event from ev_hits before the multi-event
    # clarify below. Only fires on a clear distinguishing signal; genuinely
    # ambiguous pairs are left to clarify.
    def _prune(loser):
        nonlocal ev_hits, ev_keys
        ev_hits = [(k, kw, sp) for k, kw, sp in ev_hits if k != loser]
        spans['event'] = [(k, sp) for k, kw, sp in ev_hits]
        ev_keys = [k for k, _, _ in ev_hits]

    _t = t  # normalized question text
    # 2026-10-06 Phase 3 (A12): "change in the present job" is a transfer,
    # not the vague job_change fallback. Prune the fallback job_change.
    if 'transfer_job' in ev_keys and 'job_change' in ev_keys:
        if _hit(_t, 'change in the present job') or _hit(_t, 'change in present job'):
            _prune('job_change')
    # 2026-10-06 Phase 3 (W183, H-R16): "reunion with my wife/husband" —
    # spouse words mean spouse_return_estranged, not romance_reunion.
    if 'spouse_return_estranged' in ev_keys and 'romance_reunion' in ev_keys:
        if any(_hit(_t, w) for w in ('my wife', 'my husband', 'with my wife',
                                      'with my husband')):
            _prune('romance_reunion')
    # 2026-10-06 Phase 3 (H-R21): negated return ("did not return",
    # "never return") is NOT a spouse-return question. Prune the false hit.
    if 'spouse_return_estranged' in ev_keys:
        if any(_hit(_t, w) for w in ('did not return', 'didnt return',
                                      'never return', 'not return',
                                      'no return', "n't return")):
            _prune('spouse_return_estranged')
    # 2026-10-06 Phase 3 (A31): business partnership "break up"/"separation"
    # is not romance_breakup NOR spouse_return. Business context wins.
    if 'romance_breakup' in ev_keys or 'spouse_return_estranged' in ev_keys:
        if any(_hit(_t, w) for w in ('business partner', 'partnership',
                                      'industrial', 'units')):
            if 'romance_breakup' in ev_keys:
                _prune('romance_breakup')
            if 'spouse_return_estranged' in ev_keys:
                _prune('spouse_return_estranged')
    # job_get_service beats job_change when the framing is about GETTING
    # (A47 "get a change of job to the new company", W72 "get a chance to
    # change job", H-C27 "get the job change he wishes for"). Pure "should I
    # change my job" (no get/new/next) keeps job_change.
    if 'job_get_service' in ev_keys and 'job_change' in ev_keys:
        get_kw = [kw for k, kw, _ in ev_hits
                  if k == 'job_get_service' and kw in (
                      'get a job', 'get job', 'new job', 'next job',
                      'secure a job', 'secure good job')]
        # 2026-10-06 (W161): "get next job change" — explicit "job change"
        # phrase means job_change wins; don't let "next job" hijack it.
        if _hit(_t, 'job change'):
            _prune('job_get_service')
        elif get_kw or _hit(_t, 'get a change') or _hit(_t, 'get the job change'):
            _prune('job_change')
    # Education interview/selection beats job_get_service: "medical school
    # interview" (W156), "admission interview for MPhil" (H-H7), "go to
    # another school; will I get selected" (H-H14), "internship in the
    # Ultrasound course" (E4-1). Distinguisher: education-context words.
    if 'job_get_service' in ev_keys and any(
            k in ev_keys for k in ('education_general', 'education_higher')):
        if any(_hit(_t, w) for w in (
                'school', 'college', 'university', 'course', 'admission',
                'medical', 'mphil', 'phd', 'mba', 'student')):
            _prune('job_get_service')
    # Civils/UPSC interview is a JOB interview, not an exam: "cleared the
    # civils written exam; interview on 24.02.2023" (H-C1) -> job_get_service
    # beats exam_pass_general.
    if 'job_get_service' in ev_keys and 'exam_pass_general' in ev_keys:
        if any(_hit(_t, w) for w in ('civils', 'upsc', 'ias', 'ips')):
            _prune('exam_pass_general')
    # Revaluation/subjects/marks -> the exam itself, not higher education:
    # "revaluation of her university exam marks" (A30), "pass the essential
    # examination" (H-H2) -> exam_pass_general beats education_higher.
    if 'exam_pass_general' in ev_keys and 'education_higher' in ev_keys:
        if any(_hit(_t, w) for w in ('revaluation', 'revaluation of',
                                     'subjects', 'marks')) or (
                _hit(_t, 'pass') and _hit(_t, 'examination')):
            _prune('education_higher')
    # Competitive entrance -> exam_competitive: "qualify in the IIT-JEE
    # entrance test" (H-H11) -> exam_competitive beats education_higher.
    if 'exam_competitive' in ev_keys and 'education_higher' in ev_keys:
        if any(_hit(_t, w) for w in ('iit-jee', 'iit jee', 'jee', 'neet',
                                     'entrance test', 'qualify in')):
            _prune('education_higher')
    # Explicit "lottery" beats property_purchase ("purchased a lottery
    # ticket" — Ex31, EzineAug2021-lottery).
    if 'lottery' in ev_keys and 'property_purchase_readybuilt' in ev_keys:
        if _hit(_t, 'lottery'):
            _prune('property_purchase_readybuilt')
    # "Getting a new job" beats transfer when the question asks about getting:
    # "will I get a new job" (W67, gold job_get_service) even with "transfer
    # order put on hold" in the background. But "company is transferring
    # him; will he continue" (H-C4) is about the transfer itself.
    if 'job_get_service' in ev_keys and 'transfer_job' in ev_keys:
        if any(_hit(_t, w) for w in ('get a new job', 'get a job',
                                     'get job', 'new job', 'applied for',
                                     'will i be selected', 'call me for an '
                                     'interview')):
            _prune('transfer_job')
        elif _hit(_t, 'transferring') and _hit(_t, 'continue'):
            _prune('job_get_service')
    # "Job in India or abroad" is about the JOB, location secondary
    # (easywaykphoraryt-009) -> job_get_service beats foreign_travel.
    if 'job_get_service' in ev_keys and 'foreign_travel' in ev_keys:
        if _hit(_t, 'job') and _hit(_t, 'abroad'):
            _prune('foreign_travel')
    # Loan words beat recovery_cure: "clear off the loans... free from
    # debts" (A11) -> loan_repay_clear.
    if 'loan_repay_clear' in ev_keys and 'recovery_cure' in ev_keys:
        if any(_hit(_t, w) for w in ('loan', 'loans', 'debt', 'debts')):
            _prune('recovery_cure')
    # Market words beat recovery_cure: "profit... on GMRINF option shares"
    # (E5-6) -> stock_speculation.
    if 'stock_speculation' in ev_keys and 'recovery_cure' in ev_keys:
        if any(_hit(_t, w) for w in ('shares', 'options', 'option',
                                     'profit', 'trading', 'break-even',
                                     'breakeven')):
            _prune('recovery_cure')
    # "Lost job" = lost employment, not a lost item: "when will I leave the
    # present job, and will I get the next job" (W66, gold job_get_service)
    # -> job_get_service beats misplaced_item_recovery.
    if 'job_get_service' in ev_keys and 'misplaced_item_recovery' in ev_keys:
        if _hit(_t, 'job'):
            _prune('misplaced_item_recovery')
    # Stolen articles are item recovery, not reinstatement: "regain the
    # articles lost by theft (gold ring, watch...)" (AstrologyforBeginn-103)
    # -> misplaced_item_recovery beats reinstatement_regain_position.
    if ('misplaced_item_recovery' in ev_keys
            and 'reinstatement_regain_position' in ev_keys):
        if any(_hit(_t, w) for w in ('theft', 'stolen', 'articles',
                                      'gold ring', 'watch')):
            _prune('reinstatement_regain_position')
    # Explicit litigation beats partnership: "litigation with my business
    # partner regarding the land issue" (EzineFeb2023-landlit).
    if ('court_case_litigation_win' in ev_keys
            and 'business_partnership' in ev_keys):
        if _hit(_t, 'litigation'):
            _prune('business_partnership')
    # 2026-10-06 Phase 3: litigation also beats business_profit (landlit's
    # "business partner...be successful" false-fires business_profit).
    if ('court_case_litigation_win' in ev_keys
            and 'business_profit' in ev_keys):
        if _hit(_t, 'litigation'):
            _prune('business_profit')
    # Settlement negotiation beats litigation: "one-time divorce settlement...
    # will she agree" (KPEzineMar2021-167) -> alimony_settlement.
    if ('alimony_settlement' in ev_keys
            and 'court_case_litigation_win' in ev_keys):
        if any(_hit(_t, w) for w in ('settlement', 'agree', 'one-time')):
            _prune('court_case_litigation_win')
    # Decided second marriage beats background court: "have got the divorce
    # orders... now I want to marry. Is there second marriage" (H-R3).
    if 'second_marriage' in ev_keys and 'court_case_litigation_win' in ev_keys:
        if _hit(_t, 'second marriage') or _hit(_t, 'want to marry'):
            _prune('court_case_litigation_win')
    # Explicit marriage question beats background construction business:
    # "Marriage when? (construction business)" (H-R4).
    if 'marriage' in ev_keys and 'property_construct' in ev_keys:
        if _hit(_t, 'marriage'):
            _prune('property_construct')
    # "Get bank loan" is about the loan, home is the purpose: "when will I
    # get bank loan for constructing home" (H-M7) -> loan_borrow_get.
    if 'loan_borrow_get' in ev_keys and 'property_construct' in ev_keys:
        if _hit(_t, 'loan'):
            _prune('property_construct')
    # Higher vs general education: "medical school interview" (W156, gold
    # education_higher) vs "internship in the Ultrasound course" (E4-1, gold
    # education_general). Degree words -> higher; bare course/training ->
    # general.
    if 'education_higher' in ev_keys and 'education_general' in ev_keys:
        if any(_hit(_t, w) for w in ('medical school', 'university',
                                      'college', 'phd', 'mphil', 'mba',
                                      'degree', 'iit-jee', 'iit jee')):
            _prune('education_general')
        elif any(_hit(_t, w) for w in ('course', 'training', 'coaching',
                                       'diploma')):
            _prune('education_higher')

    # event resolution
    if not ev_keys:
        # v10.4 Phase 4: clean out-of-scope handoff instead of a dead-end
        # clarify — but only when clearly outside the 4 topics or
        # content-free. Keyword gaps stay NO_EVENT for Phase 3.
        _oos = _detect_out_of_scope(t, spans)
        if _oos:
            return {'status': 'out_of_scope',
                    'topic': _oos.get('topic'),
                    'question': question,  # original text preserved
                    'reason': _oos['reason'],
                    'handoff': 'human_chat',
                    'spans': spans}
        # v10.4 Gemini fallback + learning loop (user-approved 2026-10-06).
        # ONLY fires here: rules found nothing and it's not out_of_scope.
        # Never overrides a rule match. Unreviewed learned keywords fire
        # at low weight (flagged ai_suggested); reviewed ones were already
        # injected into EVENT_PHRASES at import.
        if _GF is not None:
            _learned_hit = _check_learned_triggers(t)
            if _learned_hit:
                _phrase, _event, _reviewed = _learned_hit
                # 2026-10-14: resolve subject from text (not hardcoded 'self').
                # 2026-10-15 (review 1.8): via word-boundary spans, not the
                # old substring loop ('son' in 'person' false-fired).
                _fb_subj, _fb_base = _fallback_subject(spans)
                # 2026-10-14 (learned-vocab gate): UNREVIEWED AI-suggested
                # triggers never return 'ok' -- the user must confirm the
                # interpretation first. Only human-reviewed entries route.
                if not _reviewed:
                    return {'status': 'clarify', 'field': 'event',
                            'question': 'I think this is about %s -- is that right?' % _event.replace('_', ' '),
                            'options': [{'key': _event, 'label': _event.replace('_', ' ').title()}],
                            'guess': _event,
                            'spans': {'event': [(_event, _phrase)],
                                      'subject': [(_fb_subj, 'learned-detect')]},
                            'ai_suggested': True,
                            'ai_confidence': 'low',
                            'ai_phrase': _phrase}
                # 2026-10-15 (review 1.8): the old dict omitted 'event_rel',
                # so Layer 2 rejected it as unsupported. Mirror the normal
                # ok-contract keys.
                return {'status': 'ok',
                        'subject_key': _fb_subj,
                        'subject_base': _fb_base,
                        'event_key': _event,
                        'event_rel': OLD.EVENTS.get(_event, {}).get('relative_house'),
                        'form': 'yes_no',
                        'polarity': 'seek_gain',
                        'invert_verdict': False,
                        'window_end': None,
                        'bond_no_rotate': False,
                        'spans': {'event': [(_event, _phrase)],
                                  'subject': [(_fb_subj, 'learned-detect')]},
                        'ai_suggested': True,
                        'ai_confidence': 'full',
                        'ai_phrase': _phrase}
            if use_gemini:
                _g_event = _gemini_fallback(question, t)
                if _g_event:
                    # 2026-10-14: don't hardcode 'self' — resolve subject from
                    # text first. "Will my father's operation succeed?" must
                    # keep father (9th house), not silently become self.
                    # 2026-10-15 (review 1.8): via word-boundary spans.
                    _fb_subj, _fb_base = _fallback_subject(spans)
                    # 2026-10-14 (learned-vocab gate): Gemini fallback never
                    # returns 'ok' -- the user confirms the guess first.
                    # AI suggests, human decides; Python judges.
                    return {'status': 'clarify', 'field': 'event',
                            'question': 'I think this is about %s -- is that right?' % _g_event.replace('_', ' '),
                            'options': [{'key': _g_event, 'label': _g_event.replace('_', ' ').title()}],
                            'guess': _g_event,
                            'spans': {'event': [(_g_event, 'gemini-fallback')],
                                      'subject': [(_fb_subj, 'fallback-detect')]},
                            'ai_suggested': True,
                            'ai_confidence': 'low',
                            'ai_phrase': 'gemini-fallback'}
        return {'status': 'clarify', 'field': 'event',
                'question': 'What is your question about?',
                'options': [], 'guess': None, 'spans': spans}
    if len(set(ev_keys)) > 1:
        # multi-event: do not guess — stage 2 asks
        return {'status': 'clarify', 'field': 'event',
                'question': 'Your question touches more than one matter — '
                            'which one should I read?',
                'options': [{'key': k, 'label': k.replace('_', ' ').title()}
                            for k in sorted(set(ev_keys))],
                'guess': ev_keys[0], 'spans': spans}

    event = ev_keys[0]
    # ambiguous polarity (2026-09-29): "dismissed / dropped / overturned"
    # is good news or bad news depending on which side the querent is on —
    # ask, never guess. Guessing wrong here inverts the whole reading.
    if _detect_framing(t, event) == 'ambiguous':
        return {'status': 'clarify', 'field': 'polarity',
                'question': 'Are you hoping the case continues, or that it ends?',
                'options': [{'key': 'END', 'label': 'I want the case to end'},
                            {'key': 'CONTINUE',
                             'label': 'I want to continue / fight the case'}],
                'guess': None, 'spans': spans,
                'polarity_hint': 'END inverts the verdict at presentation'}
    if event in STAGE1_ONLY_EVENTS:
        return {'status': 'clarify', 'field': 'event',
                'question': f'I understand this is about '
                            f'"{event.replace("_", " ")}" — that is not a '
                            f'reading I do yet.',
                'options': [], 'guess': None, 'gap': event, 'spans': spans}

    # 'job or own business' asks two things (W83) -> stage 2, not a guess
    if re.search(r'\bjob\s+or\b', t) and event in ('business_start',):
        return {'status': 'clarify', 'field': 'event',
                'question': 'Your question is about a job and a business — '
                            'which one should I read?',
                'options': [{'key': 'job_get_service', 'label': 'Job'},
                            {'key': 'business_start', 'label': 'Own business'}],
                'guess': None, 'spans': spans}

    # election ticket/nomination is not winning (A1)
    if event == 'election_win' and 'ticket' in t:
        return {'status': 'clarify', 'field': 'event',
                'question': 'Is this about getting the election ticket '
                            '(nomination)? That is a different reading from '
                            'winning.',
                'options': [], 'guess': None, 'gap': 'election ticket',
                'spans': spans}

    # 'will there be an election' asks occurrence, not victory (W28)
    if event == 'election_win' and not any(
            w in t for w in ['win', 'victory', 'elected', 'selected',
                             'become', 'defeat', 'come to power',
                             'be the next']):
        return {'status': 'clarify', 'field': 'event',
                'question': 'Are you asking whether the election will happen '
                            'at all, or whether someone will win it?',
                'options': [{'key': 'election_win', 'label': 'Who will win'},
                            {'key': 'NONE', 'label': 'Will it happen'}],
                'guess': 'election_win', 'spans': spans}

    # possessive-ownership rule (2026-09-29): "my promotion", "our loan" —
    # the possessive DIRECTLY attaches to the event noun ("my" is the last
    # token before the event span). "My boss approves my promotion" -> self
    # (boss_superior is an AUTHORITY_ACTOR: the mechanism, not the subject);
    # "will my girlfriend come back" does NOT fire ("my" attaches to
    # "girlfriend", not to "come back"). Fires only when self is already
    # among the candidates, no candidates exist, or the only candidates are
    # authority actors — never against an explicit non-self claim (ex-trap,
    # pet, election, kin). A kin-word present anywhere ("will my son get my
    # property") means the kin is the recipient — the rule does not fire.
    _cands = set(sub_keys)
    if ('self' in _cands or not _cands or _cands <= AUTHORITY_ACTORS) \
            and not any(_hit(t_subj, w) for w in KIN_WORDS):
        for k, kw, sp in ev_hits:
            if k != event:
                continue
            idx = t.find(sp)
            before = t[max(0, idx - 30):idx] if idx >= 0 else ''
            last_tok = _TOKEN_RE.findall(before.lower())
            if last_tok and last_tok[-1] in ('my', 'our', 'mine'):
                sub_keys = ['self']
                spans['subject'] = [('self', '(possessive: %s)' % sp)]
                break

    # self default — after event resolution, so election name-fallbacks above
    # can still claim the subject; querist/querent in background parens
    # also anchors self
    if not sub_keys:
        if FIRST_PERSON.search(t_subj) or querist_self:
            sub_keys = ['self']
            spans.setdefault('subject', [('self', '(default)')])
        elif any(_hit(t_subj, w) for w in OFFICE_WORDS):
            # "will the prime minister win" — a third party, not the querent
            sub_keys = [PROPER_NOUN_SUBJECT]
            spans['subject'] = [(PROPER_NOUN_SUBJECT, '(office)')]
        else:
            # default-self (2026-09-29): nobody named, no kin-word, no
            # office — the chart belongs to the asker. Never ask "who?".
            # Exception: a dropped in-law means someone ELSE's relative was
            # named ("the consultant's father-in-law") -> stranger, not self.
            if third_party_inlaw:
                sub_keys = ['stranger_unknown']
                spans.setdefault(
                    'subject',
                    [('stranger_unknown', "(someone else's relative)")])
            else:
                sub_keys = ['self']
            spans.setdefault('subject', [('self', '(default-self)')])

    # subject resolution
    if len(set(sub_keys)) > 1:
        # drop self-default when someone else is named
        others = [k for k in sub_keys if k != 'self']
        if others and 'self' in sub_keys:
            sub_keys = others
    # v10.4 (2026-10-06, Phase 2): explicit "business partner" beats the
    # bare "partner" (which also fires spouse_partner). "litigation with my
    # business partner" (EzineFeb2023-landlit) is about the business partner.
    if 'business_partner' in sub_keys and 'spouse_partner' in sub_keys:
        if _hit(t, 'business partner'):
            sub_keys = [k for k in sub_keys if k != 'spouse_partner']
            spans['subject'] = [(k, sp) for k, sp in spans.get('subject', [])
                                if k != 'spouse_partner']
    # grandparent lineage (2026-09-29): KP differentiates paternal
    # (father's father -> 5th) from maternal (mother's father -> 12th).
    # Runs after the self-drop above, so "my grandfather" reaches here as
    # ['grandfather'], not ['self', 'grandfather'].
    if sub_keys == ['grandfather']:
        return {'status': 'clarify', 'field': 'subject',
                'question': "Is this your paternal grandfather (father's "
                            "father) or maternal grandfather (mother's father)?",
                'options': [{'key': 'grandfather_paternal',
                             'label': "Paternal (father's father)"},
                            {'key': 'grandfather_maternal',
                             'label': "Maternal (mother's father)"}],
                'guess': None, 'spans': spans}
    if sub_keys == ['grandmother']:
        return {'status': 'clarify', 'field': 'subject',
                'question': "Is this your paternal grandmother (father's "
                            "mother) or maternal grandmother (mother's mother)?",
                'options': [{'key': 'grandmother_paternal',
                             'label': "Paternal (father's mother)"},
                            {'key': 'grandmother_maternal',
                             'label': "Maternal (mother's mother)"}],
                'guess': None, 'spans': spans}
    # bare brother/sister alone -> CLARIFY (was: default younger_sibling).
    # 2026-10-14 (Gemini 4 audit): guessing younger vs elder corrupts the
    # ENTIRE chart rotation (8 houses off) 50% of the time. A 2-button clarify
    # is cheaper than a wrong reading. v10.4's default was UX-driven; this
    # is correctness-driven.
    bare_sib = ('younger_sibling' in sub_keys and 'elder_sibling' not in sub_keys
                and not _kin_childbirth_redirect
                and not any(_hit(t, q) for q in
                            ['younger', 'elder', 'older', 'chhota', 'chhoti',
                             'bade', 'badi', 'chota']))
    if bare_sib:
        return {'status': 'clarify', 'field': 'subject',
                'question': 'Is this about your elder or younger sibling?',
                'options': [{'key': 'elder_sibling',
                             'label': 'Elder brother / sister'},
                            {'key': 'younger_sibling',
                             'label': 'Younger brother / sister'}],
                'guess': None, 'spans': spans}
    if len(set(sub_keys)) > 1:
        return {'status': 'clarify', 'field': 'subject',
                'question': 'Who exactly is this question about?',
                'options': [{'key': k, 'label': k.replace('_', ' ').title()}
                            for k in sorted(set(sub_keys))],
                'guess': sub_keys[0], 'spans': spans}
    subject = sub_keys[0]

    # spouse_return_estranged is only for spouses (W181: friend reconciliation
    # is a different, unsupported matter). A dating partner reconciling is a
    # romance reunion (Rule 3), not a spousal one.
    if event == 'spouse_return_estranged' and subject == 'romantic_partner':
        event = 'romance_reunion'
        event_rel = OLD.EVENTS[event]['relative_house']
    elif event == 'spouse_return_estranged' and subject != 'spouse_partner':
        # 2026-10-06 (A50): "his wife return home" — third-person spouse
        # return. The event keywords ('wife return'/'husband return') already
        # fired; "his" just means a turned chart, not an unknown subject.
        # Don't block — let it through as spouse return.
        _spouse_return_kw = any(kw in t for kw in
                                ['wife return', 'husband return',
                                 'wife come back', 'husband come back'])
        if not _spouse_return_kw:
            return {'status': 'clarify', 'field': 'event',
                    'question': 'I understand this is about making up after a '
                                'fight — who with?',
                    'options': [], 'guess': None, 'gap': 'reconciliation',
                    'spans': spans}
        # Third-person spouse return: default subject to spouse_partner
        # (chart rotation handles the "his" via turned houses).
        subject = 'spouse_partner'

    # money inflow with a named giver ('my partner') is about the querent (W178)
    if subject == 'spouse_partner' and FIRST_PERSON.search(t):
        pspans = [sp for k, kw, sp in sub_hits if k == 'spouse_partner']
        # event is resolved above; money events re-anchor to the querent
        if pspans and 'partner' in pspans[0].lower() and event in MONEY_EVENTS:
            subject = 'self'
            spans['subject'] = [('self', '(money recipient)')]

    # fraud is always experienced by the querent: 'fraud ... by Mr. X' is
    # about me, the (potential) victim (W197)
    if (event == 'fraud_deception' and subject == 'stranger_unknown'
            and FIRST_PERSON.search(t_subj)):
        subject = 'self'
        spans['subject'] = [('self', '(fraud victim)')]

    form = _detect_form(t)
    # polarity on the sanitized view (parens stripped): matches the labeling
    # protocol, so outcome leaks like '(lost)' can't flip it
    polarity = _detect_polarity(t_subj, event, form, subject)
    # verdict inversion (2026-09-29): "will my visa get rejected?" — the
    # chart's YES means the visa is GRANTED, so presentation must flip it.
    # Only for desired-outcome events; already-negative events
    # (job_loss, divorce, fraud, disease...) are skipped — flipping them
    # would double-invert the answer.
    framing = _detect_framing(t, event)
    invert_verdict = (framing == 'negative' and _event_desired(event))

    subject_base = OLD.SUBJECTS[subject]['base_house']
    event_rel = OLD.EVENTS[event].get('relative_house')
    relational_7 = (subject_base == 7
                    and any(p in t for p in OLD.RELATIONAL_PHRASES))
    # Estranged-spouse return: relational phrases match missing_person_return,
    # but with a spouse subject the reunion event is the precise one.
    if (event == 'missing_person_return' and relational_7
            and subject == 'spouse_partner'):
        event = 'spouse_return_estranged'
        event_rel = OLD.EVENTS[event]['relative_house']
    # Romance reunion: an ex / departed boyfriend-girlfriend coming back is a
    # romance reunion (Rule 3), not a missing-person case.
    if (event == 'missing_person_return' and subject == 'romantic_partner'):
        event = 'romance_reunion'
        event_rel = OLD.EVENTS[event]['relative_house']

    window_end, window_text = OLD.extract_window(question, ref=ref)

    # Rule 1 no-rotation guard (USER-RULING): the querent's OWN bond is judged
    # straight from lagna. Bystanders still rotate ('will my brother get a
    # divorce' -> his 7th). The querent is a party when the subject is
    # self/spouse/romantic, or when a defaulted stranger event carries a
    # first-person reference ('will that girl accept my proposal').
    # 2026-10-14: _BOND_EVENTS is now the canonical set imported from
    # layer2_router (single source) -- no local copy.
    # 2026-10-14 (Gemini 4 audit, Leak 2): the first-person token must be the
    # OBJECT of the bond (marry me, my proposal, love me), not a possessive
    # on the subject ("my colleague" must not trigger no-rotation).
    _bond_self_anchor = re.compile(
        r'\b(marry me|marry again|to me|with me|love me|my proposal|'
        r'my boyfriend|my girlfriend|my husband|my wife|my partner|'
        r'between us|with each other|\bus\b)\b')
    bond_no_rotate = (
        (subject in ('spouse_partner', 'romantic_partner')
         and event in _BOND_EVENTS)
        or (event in _BOND_EVENTS
            and subject in ('self', 'stranger_unknown')
            and bool(_bond_self_anchor.search(t_subj)))
        or event == 'friend_to_romance')
    # 2026-10-14 (Gemini 4 audit): "Will my ex get married?" asks about the
    # ex marrying SOMEONE ELSE — a third-party event on the ex's chart.
    # Only keep no-rotation when there's a self-anchor ("to me", "with me",
    # "us", "marry me", "again"). Otherwise rotate to the ex.
    _is_ex_subject = False
    try:
        _is_ex_subject = bool(ex_spouse or ex_romance)
    except NameError:
        pass
    if _is_ex_subject and event in ('marriage', 'second_marriage'):
        _self_anchor = bool(re.search(
            r'\b(to me|with me|marry me|marry again|with each other'
            r'|\bus\b|again with me)\b', t_subj))
        if not _self_anchor:
            bond_no_rotate = False

    out = {'status': 'ok', 'subject_key': subject, 'subject_base': subject_base,
           'event_key': event, 'event_rel': event_rel,
           'form': form, 'polarity': polarity,
           'framing': framing, 'invert_verdict': invert_verdict,
           'spans': spans,
           'window_end': window_end, 'window_text': window_text,
           'relational_7': relational_7, 'bond_no_rotate': bond_no_rotate,
           'provenance': {'layer1': 'stage1-deterministic'}}
    # Election/contest handoff (OURS, not BOOK): the Readers are silent on
    # third-party election routing in one chart. Layer 2 must NOT silently
    # rotate through stranger->9th as doctrine; it must use the explicit
    # OURS election rule or ask for a separate number per candidate.
    if event in ('election_win', 'contest_win') and subject == 'stranger_unknown':
        out['election_handoff'] = True
        out['provenance']['election'] = 'OURS-handoff'
    return out
