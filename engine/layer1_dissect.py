"""v5 Layer 1 — question dissection.

Turns a raw question string into {subject_base, event_rel, window} using
book-anchored dictionaries. Deterministic first; Gemini free-tier fallback
only when the dictionaries cannot handle the phrasing; clarification (never
a guess) on any ambiguity.

Provenance:
  - subjects.json / events.json: BOOK (Krishnamurti's Readers, every entry cited).
  - EVENT_KEYWORDS below: OURS (engineering). The books give house groups, not
    English keyword lists; these lists were written for this layer and tuned
    against the 369-case corpus. They are the most likely thing to need edits.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# 2026-10-14: default local timezone for date resolution. The app's users
# are in India; resolving "by Oct 9" to 23:59 UTC (= 05:29 IST Oct 10) was
# wrong. Callers may pass an aware ref in any timezone -- its tzinfo wins.
_LOCAL_TZ = ZoneInfo('Asia/Kolkata')

_HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_HERE, 'subjects.json'), encoding='utf-8') as f:
    SUBJECTS = json.load(f)
with open(os.path.join(_HERE, 'events.json'), encoding='utf-8') as f:
    EVENTS = json.load(f)

# ---------------------------------------------------------------------------
# EVENT_KEYWORDS: OURS. English trigger phrases per event key.
# Sorted longest-first at match time so "younger brother"-style multiword
# hits win over bare words. Inflections are listed explicitly (debuggable).
# ---------------------------------------------------------------------------
EVENT_KEYWORDS = {
    'job_get_service': ['get a job', 'get job', 'new job', 'job offer', 'offer letter',
                        'appointment letter', 'naukri', 'sarkari naukri', 'government job',
                        'job', 'employment', 'employed', 'hire', 'hired', 'hiring',
                        'interview', 'recruit', 'recruitment', 'internship',
                        'selected', 'selection', 'shortlisted'],
    'promotion': ['promotion', 'promoted', 'promote', 'increment', 'higher post',
                  'higher position', 'elevation'],
    'transfer_job': ['transfer', 'transferred'],
    'job_loss_dismissal': ['fired', 'dismissed', 'dismissal', 'lose my job',
                           'losing my job', 'lost my job', 'layoff', 'laid off',
                           'sacked', 'terminate', 'terminated', 'termination',
                           'removed from service'],
    'reinstatement_regain_position': ['reinstate', 'reinstated', 'reinstatement',
                                      'get back my job', 'regain'],
    'suspension_from_service': ['suspend', 'suspended', 'suspension'],
    'business_start': ['start business', 'starting business', 'new business',
                       'startup', 'start-up', 'new venture', 'own business',
                       'start my own', 'business venture'],
    'business_profit': ['business profit', 'profit in business', 'profit from business',
                      'business doing well', 'profitable business', 'business profitable',
                      'earn profit', 'business gains', 'profit'],
    'business_loss': ['business loss', 'loss in business', 'losing money in business',
                      'business losses', 'loss making business', 'loss', 'losses'],
    'money_gain': ['money', 'wealth', 'wealthy', 'become rich', 'financial gain',
                   'financial condition', 'income'],
    'stock_speculation': ['stock market', 'stock', 'stocks', 'share market', 'shares',
                          'speculation', 'intraday', 'trading', 'nifty', 'sensex'],
    'inheritance_claim': ['inheritance', 'inherit', 'inherits', 'ancestral property',
                          'insurance claim', 'provident fund', 'pf claim', 'legacy'],
    'renting_live_in': ['rent a house', 'rented house', 'renting a house',
                        'take on rent', 'on rent', 'lease a house', 'rental'],
    'adoption': ['adopt a child', 'adoption', 'adopt'],
    'loan_borrow_get': ['loan', 'borrow', 'borrowing', 'lend me'],
    'loan_repay_clear': ['repay', 'repay the loan', 'repaying', 'clear debt',
                         'clear off', 'clear the loan', 'debt free',
                         'pay off debt', 'pay back the loan'],
    'marriage': ['marry', 'married', 'marrying', 'marriage', 'wedding', 'wedlock',
                 'shaadi', 'get married', 'bride', 'groom'],
    'second_marriage': ['second marriage', 'remarry', 'remarriage', 'marry again',
                        'second shaadi', 'marry a second time', 'marry second',
                        'second wedding', 'another marriage', 're-marry',
                        'second husband', 'second wife'],
    'divorce': ['divorce', 'divorced', 'divorcing'],
    'love_affair': ['love affair', 'affair', 'in love', 'romance', 'romantic',
                    'love life'],
    'childbirth': ['pregnant', 'pregnancy', 'conceive', 'conception', 'childbirth',
                   'give birth', 'expecting a child', 'have a baby', 'have a child',
                   'get a child', 'get a baby', 'become a mother', 'become a father',
                   'birth', 'born', 'delivery', 'deliver'],
    'disease_illness': ['sick', 'illness', 'disease', 'ailment', 'unwell',
                        'health issue', 'health problem', 'suffering from', 'diagnosed',
                        'unconscious', 'consciousness', 'hospital', 'hospitalized',
                        'admitted in hospital'],
    'recovery_cure': ['recover', 'recovered', 'recovering', 'recovery', 'cure',
                      'cured', 'heal', 'healed', 'healing', 'get well',
                      'become healthy', 'come out of illness'],
    'surgery': ['surgery', 'surgical', 'operation'],
    'longevity': ['how long will', 'longevity', 'lifespan', 'pass away',
                  'death', 'die', 'survive'],
    'property_purchase_readybuilt': ['buy house', 'buy a house', 'buy flat',
                                     'buy a flat', 'buy plot', 'buy land',
                                     'buy a plot', 'purchase house', 'purchase property',
                                     'buy property', 'new house', 'own house',
                                     'house purchase', 'bought', 'purchased',
                                     'buying'],
    'property_construct': ['construct', 'construction', 'build a house',
                           'building a house', 'construct a house'],
    'property_sale': ['sell house', 'sell my house', 'sell flat', 'sell land',
                      'sell property', 'sale of house', 'sell the house',
                      'sold', 'sell', 'sale'],
    'vehicle_purchase': ['buy car', 'buy a car', 'buy bike', 'buy a bike',
                         'buy vehicle', 'new car', 'new bike', 'purchase car',
                         'four wheeler', 'two wheeler', 'bought a car',
                         'purchased a car'],
    'exam_pass_general': ['pass the exam', 'pass exam', 'clear the exam',
                          'clear exam', 'exam result', 'pass in', 'qualify',
                          'succeed in the exam', 'marks', 'exam'],
    'exam_competitive': ['upsc', 'ias', 'ips', 'ifs', 'neet', 'jee', 'cat',
                         'competitive exam', 'civil services', 'sarkari exam'],
    'education_general': ['study', 'studies', 'studying', 'education',
                          'admission', 'college', 'university', 'degree',
                          'school', 'school admission'],
    'education_higher': ['higher education', 'phd', 'masters', "master's",
                         'm.tech', 'research scholar', 'doctorate'],
    'foreign_travel': ['go abroad', 'going abroad', 'abroad', 'foreign trip',
                       'travel abroad', 'settle abroad', 'onsite', 'foreign'],
    'visa': ['visa', 'immigration', 'immigrate', 'green card',
              'permanent residency', 'work permit'],
    'court_case_litigation_win': ['court', 'litigation', 'lawsuit', 'legal case',
                                  'court case', 'judgement', 'case in court',
                                  'legal battle', 'win the case', 'bail',
                                  'arrest', 'arrested'],
    'jail_release': ['release from jail', 'released from jail', 'jail release',
                     'prison release', 'come out of jail', 'jail', 'imprisonment'],
    'contest_win': ['win the contest', 'win competition', 'win the competition'],
    'election_win': ['election', 'mla', 'constituency', 'vote', 'voting',
                     'panchayat', 'councillor', 'corporator'],
    'missing_person_return': ['come back', 'coming back', 'return home',
                              'returned home', 'return to me', 'come back to me',
                              'leave me', 'leaving me', 'left home', 'missing',
                              'run away', 'ran away', 'where is my'],
    'missing_person_status': ['alive', 'dead or alive', 'is he alive',
                              'is she alive', 'survived'],
    'spouse_return_estranged': ['estranged', 'separated', 'separation', 'reunion',
                                'reconcile', 'get back together', 'patch up'],
    'stolen_property_recovery': ['stolen', 'robbery', 'theft of'],
    'misplaced_item_recovery': ['misplaced', 'cannot find', "can't find",
                                'where did i keep', 'lost my keys', 'lost my phone',
                                'lost my wallet', 'lost my ring', 'lost my documents',
                                'lost my bag'],
    'rumor_true': ['rumor', 'rumour', 'is it true', 'heard that', 'gossip'],
    'theft_identify_thief': ['who stole', 'identify the thief', 'catch the thief',
                             'thief caught', 'be caught', 'find the thief', 'caught the thief'],
    'fraud_deception': ['fraud', 'fraudulent', 'cheated', 'cheat', 'cheating',
                        'scam', 'scammed', 'deceived', 'deceive', 'deception',
                        'duped', 'duping', 'conspiracy', 'forgery', 'forged'],
}

# Phrases that make a 7th-house question RELATIONAL (about the bond itself,
# not the person's separate affairs) -> Layer 2 must NOT rotate the chart.
RELATIONAL_PHRASES = ['return to me', 'come back to me', 'come back',
                      'return home', 'returned home',
                      'marry me', 'divorce me', 'leave me', 'leaving me',
                      'separate from me', 'reunite', 'patch up', 'get back together']

SEVENTH_STACK = {'spouse_partner', 'competitor_enemy_open', 'thief', 'business_partner'}

MONTHS = {m: i + 1 for i, m in enumerate(
    ['january', 'february', 'march', 'april', 'may', 'june', 'july',
     'august', 'september', 'october', 'november', 'december'])}

# Abbreviated month names (3-letter) -> month number. Added 2026-10-06 for
# day-first date formats common in Indian English ("9 oct 2026", "10th oct").
MONTHS_ABBR = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

# Combined lookup: full name or abbreviation -> month number.
_MONTH_LOOKUP = dict(MONTHS)
_MONTH_LOOKUP.update(MONTHS_ABBR)
_MONTH_NAMES = '|'.join(sorted(_MONTH_LOOKUP.keys(), key=len, reverse=True))


# ---------------------------------------------------------------------------
# matching helpers
# ---------------------------------------------------------------------------
def _norm(text):
    text = (text or '').lower()
    text = re.sub(r"[^\w\s']", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _hit(text, phrase):
    """Word-boundary match; multiword phrases matched verbatim."""
    pat = r'\b' + re.escape(phrase) + r's?\b'
    return re.search(pat, text) is not None


def _match_subjects(text):
    """Returns {subject_key: [matched keywords]} for the raw question."""
    hits = {}
    for key, sub in SUBJECTS.items():
        kws = sorted(sub.get('keywords', []), key=len, reverse=True)
        matched = [kw for kw in kws if _hit(text, kw.lower())]
        if matched:
            hits[key] = matched
    return hits


def _match_events(text):
    hits = {}
    for key, kws in EVENT_KEYWORDS.items():
        kws = sorted(kws, key=len, reverse=True)
        matched = [kw for kw in kws if _hit(text, kw)]
        if matched:
            hits[key] = matched
    return hits


def _resolve_subjects(hits, text):
    """Apply disambiguation rules. Returns (resolved_keys, clarify_info).

    Rules (all OURS, documented):
    - 'self' is the default: dropped when any other subject matched.
    - elder-qualified ('older brother') suppresses bare 'brother'->younger.
    - bare 'brother/sister/sibling' alone -> clarify younger vs elder.
    - 2+ distinct 7th-house subjects -> clarify (the 7th-house trap).
    - 0 subjects -> clarify (who?).
    """
    keys = set(hits)
    # self-default: drop 'self' if anyone else is named
    if 'self' in keys and len(keys) > 1:
        keys.discard('self')

    younger_kw = {'younger brother', 'younger sister', 'younger sibling'}
    elder_kw = {'elder brother', 'elder sister', 'older brother', 'older sister',
                'elder sibling', 'older sibling'}
    y_hits = set(hits.get('younger_sibling', []))
    elder_qualified = bool(set(hits.get('elder_sibling', [])) & elder_kw)
    younger_qualified = bool(y_hits & younger_kw)
    younger_bare_only = 'younger_sibling' in keys and not younger_qualified

    if elder_qualified and younger_bare_only:
        # "my older brother" also contains "brother" -> keep elder only
        keys.discard('younger_sibling')
        younger_bare_only = False

    # childbirth guard: "will I have a baby" — the baby is the event,
    # not an existing child. (Decided without a ruling; documented.)
    # (applied after event matching; see dissect())

    stack = keys & SEVENTH_STACK
    clarify = None
    if younger_bare_only and 'elder_sibling' not in keys:
        clarify = {
            'field': 'subject',
            'question': "When you say 'brother/sister', do you mean your younger or elder sibling?",
            'options': [{'key': 'younger_sibling', 'label': 'Younger brother/sister'},
                        {'key': 'elder_sibling', 'label': 'Elder brother/sister'}],
        }
    elif len(stack) >= 2:
        labels = {'spouse_partner': 'Spouse / romantic partner',
                  'competitor_enemy_open': 'Competitor / opponent',
                  'thief': 'Thief',
                  'business_partner': 'Business partner'}
        clarify = {
            'field': 'subject',
            'question': 'Who exactly is this question about?',
            'options': [{'key': k, 'label': labels[k]} for k in sorted(stack)],
        }
    elif len(keys) == 0:
        clarify = {
            'field': 'subject',
            'question': 'Who is this question about?',
            'options': [{'key': 'self', 'label': 'Myself / my own matter'}],
        }
    elif len(keys) > 1:
        clarify = {
            'field': 'subject',
            'question': 'Who exactly is this question about?',
            'options': [{'key': k, 'label': k.replace('_', ' ').title()}
                        for k in sorted(keys)],
        }
    return sorted(keys), clarify


# ---------------------------------------------------------------------------
# time-window extraction. NEVER guesses: vague ('soon') or absent -> None.
# ---------------------------------------------------------------------------
def extract_window(text, ref=None):
    """Returns (window_end|None, matched_text|None). ref = aware datetime.
    2026-10-14: dates resolve in ref's timezone (or Asia/Kolkata default),
    not UTC. All outputs are tz-aware, so downstream comparisons stay correct.
    """
    # 2026-10-14: honor the caller's timezone; default to Asia/Kolkata
    # (was: naive assumed UTC, all dates 23:59 UTC).
    if ref is None:
        ref = datetime.now(_LOCAL_TZ)
    elif ref.tzinfo is None:
        ref = ref.replace(tzinfo=_LOCAL_TZ)
    _tz = ref.tzinfo
    t = _norm(text)

    # 2026-10-14 (Gemini 4 audit): collect ALL explicit-date matches via
    # finditer (not just the first via re.search). A past date as context
    # ("gave exam on 9 Oct") must not hide a future target date ("result
    # before 15 Nov"). Pick best future candidate: preposition-anchored
    # first, then latest future date.
    _cands = []  # (dt, matched_text, has_prep, rolled)

    def _add(dt, mtxt, mstart, rolled=False):
        before = t[max(0, mstart - 12):mstart]
        has_prep = bool(re.search(r'\b(by|before|till|until|within|in|on)\s*$', before))
        _cands.append((dt, mtxt, has_prep, rolled))

    # 1) YYYY-MM-DD ISO first (2026-10-09). _norm() turns '-' to space.
    for m in re.finditer(r'\b(\d{4})[\s/\-.](\d{1,2})[\s/\-.](\d{1,2})\b', t):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1900 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                dt = datetime(y, mo, d, 23, 59, tzinfo=_tz)
                if dt > ref:
                    _add(dt, m.group(0), m.start())
            except ValueError:
                pass
    # DD/MM/YYYY
    for m in re.finditer(r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b', t):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            dt = datetime(y, mo, d, 23, 59, tzinfo=_tz)
            if dt > ref:
                _add(dt, m.group(0), m.start())
        except ValueError:
            pass
    # Month-first: 'October 14th, 2026'
    for m in re.finditer(r'\b(' + '|'.join(MONTHS) + r')\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})?\b', t):
        mo = MONTHS[m.group(1)]
        d = int(m.group(2))
        y = int(m.group(3)) if m.group(3) else ref.year
        # 2026-10-15 (review 1.10): a yearless PAST date ("gave exam on 9 Oct")
        # rolls forward a year; mark it rolled so it never outranks a
        # naturally-future target date ("result before 15 Nov").
        rolled = False
        if not m.group(3) and (mo < ref.month or (mo == ref.month and d <= ref.day)):
            y += 1
            rolled = True
        try:
            dt = datetime(y, mo, d, 23, 59, tzinfo=_tz)
            if dt > ref:
                _add(dt, m.group(0), m.start(), rolled)
        except ValueError:
            pass
    # 1b) day-first: '9 oct 2026', '10th oct'
    for m in re.finditer(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + _MONTH_NAMES + r')\b(?:\s*,?\s*(\d{4}))?', t):
        d = int(m.group(1))
        mo = _MONTH_LOOKUP[m.group(2)]
        y = int(m.group(3)) if m.group(3) else ref.year
        rolled = False
        if not m.group(3) and (mo < ref.month or (mo == ref.month and d <= ref.day)):
            y += 1
            rolled = True
        try:
            dt = datetime(y, mo, d, 23, 59, tzinfo=_tz)
            if dt > ref:
                _add(dt, m.group(0), m.start(), rolled)
        except ValueError:
            pass
    if _cands:
        # preposition-anchored first, then non-rolled (naturally future),
        # then latest date.
        _cands.sort(key=lambda c: (c[2], not c[3], c[0]), reverse=True)
        return _cands[0][0], _cands[0][1]

    # 2) month name, optional year: 'by October', 'in October 2027'
    m = re.search(r'\b(by|in|before|till|until)\s+(' + '|'.join(MONTHS) + r')\b(?:\s+(\d{4}))?', t)
    if not m:
        m = re.search(r'\b(' + '|'.join(MONTHS) + r')\s+(\d{4})\b', t)
    if m:
        g = [x for x in m.groups() if x]
        moname = next(x for x in g if x in MONTHS)
        mo = MONTHS[moname]
        yr = next((int(x) for x in g if x.isdigit() and len(x) == 4), None)
        if yr is None:
            yr = ref.year if mo >= ref.month else ref.year + 1
        # end of that month
        nxt = datetime(yr + (mo == 12), (mo % 12) + 1, 1, tzinfo=_tz)
        dt = nxt - timedelta(seconds=1)
        if dt > ref:
            return dt, m.group(0)
    # 3) 'within|in N days|weeks|months|years'
    m = re.search(r'\b(?:within|in)\s+(\d+)\s*(day|week|month|year)s?\b', t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {'day': 1, 'week': 7, 'month': 30, 'year': 365}[unit] * n
        return ref + timedelta(days=days), m.group(0)
    # 4) this/today/tomorrow/next week|month|year
    if re.search(r'\btoday\b', t):
        return ref.replace(hour=23, minute=59, second=0, microsecond=0), 'today'
    if re.search(r'\btomorrow\b', t):
        d = (ref + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
        return d, 'tomorrow'
    m = re.search(r'\bthis\s+(week|month|year)\b', t)
    if m:
        unit = m.group(1)
        if unit == 'week':
            # end of week: upcoming Sunday
            days_ahead = (6 - ref.weekday()) % 7 or 7
            dt = (ref + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=0, microsecond=0)
        elif unit == 'month':
            nxt = datetime(ref.year + (ref.month == 12), (ref.month % 12) + 1, 1, tzinfo=_tz)
            dt = nxt - timedelta(seconds=1)
        else:
            dt = datetime(ref.year, 12, 31, 23, 59, tzinfo=_tz)
        return dt, m.group(0)
    m = re.search(r'\bnext\s+(week|month|year)\b', t)
    if m:
        unit = m.group(1)
        if unit == 'week':
            days_ahead = (6 - ref.weekday()) % 7 or 7
            dt = (ref + timedelta(days=days_ahead + 7)).replace(hour=23, minute=59, second=0, microsecond=0)
        elif unit == 'month':
            y2 = ref.year + (ref.month >= 11)
            m2 = ref.month + 2 if ref.month <= 10 else (ref.month + 2) % 12
            nxt = datetime(y2 + (m2 == 13), ((m2 - 1) % 12) + 1, 1, tzinfo=_tz)
            dt = nxt - timedelta(seconds=1)
        else:
            dt = datetime(ref.year + 1, 12, 31, 23, 59, tzinfo=_tz)
        return dt, m.group(0)
    # 'soon' and friends are deliberately NOT a window (ruling: never guess)
    return None, None


# ---------------------------------------------------------------------------
# Gemini fallback: strict JSON-only, parsed defensively.
# ---------------------------------------------------------------------------
_GEMINI_PROMPT = """You are a strict JSON extractor for KP horary astrology. Read the question and map it to ONE subject base house and ONE event relative house.

Subject base houses: self=1, younger sibling=3, mother=4, children=5, spouse/partner=7, competitor/opponent=7, thief=7, business partner=7, father=9, guru/teacher=9, stranger=9, boss/superior=10, elder sibling=11, friend=11, secret enemy=12.
Event relative houses: longevity=1, money gain=2, transfer=3, education/exam=4, property/vehicle=4, childbirth/love=5, job/service/disease/recovery/court/loan=6, marriage/divorce/business=7, surgery=8, higher education/competitive exam=9, promotion/reinstatement=10, contest/election win=11, foreign travel/visa=12.

Respond with ONLY one JSON object and no other text: {"subject_base": <integer 1-12>, "event_rel": <integer 1-12>}. If you cannot determine either, respond ONLY: {"unknown": true}."""


def _get_config():
    """Load config.py from this package directory without touching sys.path."""
    import importlib.util
    path = os.path.join(_HERE, 'config.py')
    spec = importlib.util.spec_from_file_location('v5_config', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gemini_fallback(question):
    """Returns (subject_base, event_rel) or None. Never raises, never guesses."""
    try:
        _cfg = _get_config()
        fallback_on = _cfg.GEMINI_FALLBACK
        model = _cfg.GEMINI_MODEL
        timeout = _cfg.GEMINI_TIMEOUT_S
    except Exception:
        return None
    if not fallback_on:
        return None
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return None
    try:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={api_key}")
        body = json.dumps({
            'contents': [{'parts': [{'text': _GEMINI_PROMPT + '\nQuestion: ' + question}]}],
            'generationConfig': {'temperature': 0},
        }).encode('utf-8')
        req = urllib.request.Request(url, data=body,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        text = payload['candidates'][0]['content']['parts'][0]['text']
        m = re.search(r'\{[^{}]*\}', text)
        if not m:
            return None
        obj = json.loads(m.group(0))
        if obj.get('unknown'):
            return None
        sb, er = int(obj['subject_base']), int(obj['event_rel'])
        if 1 <= sb <= 12 and 1 <= er <= 12:
            return sb, er
        return None
    except Exception:
        return None


def _resolve_gemini(base, rel):
    """Map a Gemini (base, rel) pair onto our tables. Unique hit or clarify."""
    sub_keys = [k for k, v in SUBJECTS.items() if v['base_house'] == base]
    ev_keys = [k for k, v in EVENTS.items()
               if v.get('relative_house') == rel and v.get('success')]
    if len(sub_keys) == 1 and len(ev_keys) == 1:
        return {'status': 'ok', 'subject_key': sub_keys[0], 'subject_base': base,
                'event_key': ev_keys[0], 'event_rel': rel,
                'provenance': 'gemini-fallback'}
    return None


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------
def dissect(question, ref=None, use_gemini=True):
    """Dissect a question. Returns a dict; never raises.

    status 'ok':      {subject_key, subject_base, event_key, event_rel,
                       window_end, window_text, relational_7, provenance}
    status 'clarify': {question, options:[{key,label}], field}
    """
    try:
        return _dissect(question, ref=ref, use_gemini=use_gemini)
    except Exception as e:  # never crash the chat on a weird question
        return {'status': 'clarify', 'field': 'event',
                'question': 'I could not understand that question. What is it about?',
                'options': [], 'error': str(e)[:120]}


def _dissect(question, ref=None, use_gemini=True):
    t = _norm(question)
    if not t:
        return {'status': 'clarify', 'field': 'event',
                'question': 'Please ask your question.',
                'options': []}

    sub_hits = _match_subjects(t)
    ev_hits = _match_events(t)

    # childbirth guard: the unborn baby is the event, not an existing child
    if 'childbirth' in ev_hits and 'children' in sub_hits:
        only_baby_words = all(
            kw in ('baby', 'child', 'children', 'kid')
            for kw in sub_hits['children'])
        if only_baby_words:
            del sub_hits['children']

    sub_keys, sub_clarify = _resolve_subjects(sub_hits, t)

    # Role-as-position: "selected for district judge" — the role is the prize,
    # not a person. A selection/appointment verb BEFORE a role noun suppresses
    # the boss_superior subject hit. (OURS; W29 fix, user-confirmed 2026-09-28.)
    _ROLE_NOUNS = ('judge', 'officer', 'manager', 'employer', 'boss',
                   'superior', 'master', 'clerk', 'collector')
    _sel = re.search(r'\b(select\w*|appoint\w*|recruit\w*|become|became|chosen|choose)\b', t)
    if _sel and 'boss_superior' in sub_hits:
        kept = [kw for kw in sub_hits['boss_superior']
                if not (t.find(kw) > _sel.start() and kw in _ROLE_NOUNS)]
        if kept:
            sub_hits['boss_superior'] = kept
        else:
            del sub_hits['boss_superior']
        sub_keys, sub_clarify = _resolve_subjects(sub_hits, t)

    # First-person lead: "Will I get the job (employer never called back)" —
    # background person mentions don't become the subject. (OURS; F9 fix.)
    if re.match(r'\s*(will|can|shall|do|am)\s+i\b', t) and 'boss_superior' in sub_hits:
        del sub_hits['boss_superior']
        sub_keys, sub_clarify = _resolve_subjects(sub_hits, t)

    ev_keys = sorted(ev_hits)
    # "second marriage" always contains "marriage" as a substring hit;
    # the specific event wins over the generic one (OURS, documented).
    if 'marriage' in ev_hits and 'second_marriage' in ev_hits:
        del ev_hits['marriage']
        ev_keys = sorted(ev_hits)
    # "clear off my loans" hits borrow's bare 'loan' keyword too;
    # the specific repay action wins over the generic loan mention (OURS).
    if 'loan_borrow_get' in ev_hits and 'loan_repay_clear' in ev_hits:
        del ev_hits['loan_borrow_get']
        ev_keys = sorted(ev_hits)
    # "birth chart / natal chart / kundli" is the natal chart, not childbirth (OURS; W35 fix).
    if 'childbirth' in ev_hits and re.search(r'birth\s+chart|natal\s+chart|kundli|horoscope', t):
        kws = [kw for kw in ev_hits['childbirth'] if kw != 'birth']
        if kws:
            ev_hits['childbirth'] = kws
        else:
            del ev_hits['childbirth']
            ev_keys = sorted(ev_hits)
    # "newly married, when will I get a child": the child is the question,
    # not the marriage (OURS; W53 fix, user-confirmed 2026-09-28).
    if 'marriage' in ev_hits and 'childbirth' in ev_hits:
        del ev_hits['marriage']
        ev_keys = sorted(ev_hits)
    # "fraud about registered marriage": the fraud is the question (OURS; W197).
    if 'marriage' in ev_hits and 'fraud_deception' in ev_hits:
        del ev_hits['marriage']
        ev_keys = sorted(ev_hits)
    # "medical school interview": education context beats job's 'interview'
    # keyword (OURS; W156 fix, user-confirmed 2026-09-28).
    _EDU_CTX = ('school', 'college', 'university', 'admission')
    if ('job_get_service' in ev_hits and 'education_general' in ev_hits
            and set(ev_hits['job_get_service']) <= {'interview'}
            and any(w in t for w in _EDU_CTX)):
        del ev_hits['job_get_service']
        ev_keys = sorted(ev_hits)
    # "lost the silver plate - is recovery possible": object-loss recovery is
    # not disease recovery (OURS; J103 fix).
    _DISEASE_CTX = ('sick', 'illness', 'disease', 'health', 'hospital', 'fever',
                    'cancer', 'treatment', 'doctor')
    if ('recovery_cure' in ev_hits
            and re.search(r'\blost\b|\bmisplaced\b', t)
            and not any(w in t for w in _DISEASE_CTX)):
        del ev_hits['recovery_cure']
        ev_hits['misplaced_item_recovery'] = ev_hits.get('misplaced_item_recovery', ['lost'])
        ev_keys = sorted(ev_hits)
    ev_clarify = None
    if len(ev_keys) == 0:
        ev_clarify = {
            'field': 'event',
            'question': 'What is this question about?',
            'options': [{'key': k, 'label': k.replace('_', ' ').title()}
                        for k in ['job_get_service', 'marriage', 'disease_illness',
                                  'money_gain', 'exam_pass_general', 'foreign_travel']],
        }
    elif len(ev_keys) > 1:
        ev_clarify = {
            'field': 'event',
            'question': 'Which of these is your question about?',
            'options': [{'key': k, 'label': k.replace('_', ' ').title()}
                        for k in ev_keys],
        }

    # Gemini fallback only for *misses*, never for genuine ambiguity
    if use_gemini and (sub_clarify or ev_clarify):
        fb = _gemini_fallback(question)
        if fb:
            resolved = _resolve_gemini(*fb)
            if resolved:
                wend, wtext = extract_window(t, ref)
                resolved.update({'window_end': wend, 'window_text': wtext,
                                 'relational_7': False})
                return resolved
        # fall through to clarification

    if sub_clarify and ev_clarify:
        return {'status': 'clarify', 'field': 'both',
                'question': sub_clarify['question'] + ' ' + ev_clarify['question'],
                'options': sub_clarify['options'] + ev_clarify['options']}
    if sub_clarify:
        return {'status': 'clarify', **sub_clarify}
    if ev_clarify:
        return {'status': 'clarify', **ev_clarify}

    subject_key = sub_keys[0]
    event_key = ev_keys[0]
    subject_base = SUBJECTS[subject_key]['base_house']
    event_rel = EVENTS[event_key].get('relative_house')

    relational_7 = (subject_base == 7
                    and any(p in t for p in RELATIONAL_PHRASES))

    # Estranged-spouse return: the relational phrases ('return to me', ...)
    # technically match missing_person_return, but when the subject is the
    # spouse the specific reunion event is the precise one (OURS, documented).
    if (event_key == 'missing_person_return' and relational_7
            and subject_key == 'spouse_partner'):
        event_key = 'spouse_return_estranged'
        event_rel = EVENTS[event_key]['relative_house']

    wend, wtext = extract_window(t, ref)
    return {'status': 'ok',
            'subject_key': subject_key, 'subject_base': subject_base,
            'event_key': event_key, 'event_rel': event_rel,
            'window_end': wend, 'window_text': wtext,
            'relational_7': relational_7,
            'provenance': 'dictionary'}
