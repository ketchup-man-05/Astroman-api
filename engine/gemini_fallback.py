"""Gemini fallback + learning loop for Layer 1 (2026-10-06, v10.4).

Design (from 2026-09-29 ai_filter.py, user-approved):
  - Rules core first (fast, free, auditable). This module ONLY fires when
    rules return NO_EVENT (never on out_of_scope, never overriding a match).
  - Gemini (free tier) maps the question to ONE EXISTING event and names
    the new keyword(s) that signal it. It can NEVER invent a new event.
  - Learned keywords go to learned_vocabulary.json as reviewed=false.
  - Unreviewed words work at low weight (flagged ai_suggested, can't
    override strong rule matches — they only fire at the NO_EVENT point).
  - Reviewed words (user-approved via review_learned_words.py) work at
    full weight, like normal keywords.
  - Fail safe: no key, API error, bad parse -> return None, log, never raise.

No import of layer1_stage1 here (it imports this module). Everything the
fallback needs (candidate events, existing keywords) is passed as params.
"""

import json
import os
import re
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_LEARNED_PATH = os.path.join(_HERE, "learned_vocabulary.json")
_LOG_PATH = os.path.join(_HERE, "gemini_fallback.log")

# Words too generic to ever be "unknown" -- skip them silently.
# (From 2026-09-29 ai_filter.py.)
_STOP = set("""
will i my me be is are was were do does did have has had get got getting
the a an of to in on for with and or but if then than so as at by from
when where what which who whom whose how why whether will would should
could can may might must shall this that these those it its it s he she
they them his her their our your you we us our ours your yours their theirs
mein kya kab kaise hoga hogi honge meri mera mere apna apni apne ko ke ki
ka se mein main ne par per tak bhi aur ya hai hain tha thi the ho raha
rahi rahe gaya gayi gaye liya liye wala wali wale
""".split())

# Collision stoplist: everyday English words that must NEVER become event
# keywords. Lesson 2026-09-29 (AGENTS.md): a Hindi gloss key 'the'->'were'
# once rewrote the English article in every sentence. Check every learned
# phrase against this AND all existing EVENT_PHRASES keywords before saving.
_COLLISION_STOP = set("""
the a an of to in on for with and or but if then than so as at by from
will would should could can may might must shall will i my me be is are
was were do does did have has had get got getting this that these those
it its he she they them his her their our your you we us when where what
which who whom whose how why whether when what where who how why if or
not no yes very much more most less least all any some every each other
another such own same than too also just only even still already yet now
today tomorrow yesterday here there then when while after before during
up down out off over under again once twice my me mine your yours his her
hers its our ours their theirs this that these those am is are was were
be been being have has had having do does did doing will would shall
should may might must can could ought need dare used
""".split())

_CONFIDENCE_THRESHOLD = 0.6
_MAX_KEYWORDS = 5


def _qhash(question):
    """Short non-reversible hash for logs. 2026-10-15 (Claude review A9):
    the old code logged raw question text (personal questions) in plaintext.
    Logs now carry only hashes."""
    import hashlib
    return hashlib.sha256((question or '').encode('utf-8')).hexdigest()[:12]


def _log(msg):
    try:
        with open(_LOG_PATH, "a") as f:
            f.write("[%s] %s\n" % (date.today(), msg))
    except OSError:
        pass


def _load_learned():
    try:
        with open(_LEARNED_PATH) as f:
            return json.load(f).get("_entries", {})
    except (OSError, ValueError):
        return {}


# 2026-10-15 (Claude review A9): cap total entries so the file cannot grow
# without bound from hostile inputs. Reviewed entries are never evicted.
_MAX_LEARNED_ENTRIES = 1000


def _save_learned(entries):
    # Evict oldest unreviewed first if over cap.
    if len(entries) > _MAX_LEARNED_ENTRIES:
        scored = sorted(entries.items(),
                        key=lambda kv: (bool(kv[1].get('reviewed')),
                                        kv[1].get('date_added') or ''))
        entries = dict(scored[len(entries) - _MAX_LEARNED_ENTRIES:])
    # 2026-10-15 (Claude review A9): atomic write. The old open("w") could
    # be interleaved by concurrent sessions -> half-written file -> the
    # ValueError path in _load_learned returned {} and wiped reviewed entries.
    tmp = _LEARNED_PATH + '.tmp'
    with open(tmp, "w") as f:
        json.dump({"_schema": "phrase -> {event, confidence, source, "
                              "date_added, reviewed}. Only the AI filter "
                              "writes here; humans review.",
                   "_entries": entries}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, _LEARNED_PATH)


def get_learned_triggers():
    """Return [(phrase, event, reviewed_bool)] for _dissect to check.

    Reviewed -> full weight (treated like a normal keyword).
    Unreviewed -> low weight (only fires at NO_EVENT, flagged ai_suggested).
    Never raises.
    """
    try:
        out = []
        for phrase, rec in _load_learned().items():
            if rec.get("event"):
                out.append((phrase, rec["event"], bool(rec.get("reviewed"))))
        return out
    except Exception:
        return []


def find_unknown_words(norm_text, known_vocab):
    """Content words in the question that no vocabulary knows."""
    words = [w for w in re.findall(r"[a-z']+", norm_text.lower())
             if w not in _STOP]
    return sorted({w for w in words if w not in known_vocab})


def check_collision(phrase, existing_keywords):
    """True if the phrase is safe to learn, False on collision.

    Rejects: (a) common English words (b) any existing EVENT_PHRASES
    keyword (c) empty/whitespace. Logs rejections.
    """
    p = (phrase or "").strip().lower()
    if not p:
        return False
    # Single common words are never safe as keywords.
    if " " not in p and p in _COLLISION_STOP:
        _log("COLLISION-REJECT (common word): %r" % phrase)
        return False
    # Must not duplicate an existing keyword.
    if p in existing_keywords:
        _log("COLLISION-REJECT (existing keyword): %r" % phrase)
        return False
    return True


def call_gemini_for_event(question, candidate_events):
    """Ask Gemini to map a question to ONE existing event.

    Returns {'event', 'keywords', 'confidence'} or None.
    NEVER returns an event outside candidate_events. Never raises.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    # 2026-10-15 (Claude review A9): model/timeout from engine config, not
    # hardcoded; API key via header (not URL query).
    try:
        from engine import config as _cfg
        _model = getattr(_cfg, 'GEMINI_MODEL', 'gemini-flash-latest')
        _timeout = int(getattr(_cfg, 'GEMINI_TIMEOUT_S', 25))
    except Exception:
        _model, _timeout = 'gemini-flash-latest', 25
    try:
        import urllib.request
        prompt = (
            "You are a classifier for a KP astrology question router. "
            "Map the user's question to exactly ONE of these event labels, "
            "or reply NONE if it fits none of them. Do NOT invent a new label.\n"
            + ", ".join(sorted(candidate_events)) +
            "\n\nQuestion: " + question +
            "\n\nReply ONLY as JSON: "
            '{"event": "<label or NONE>", "keywords": ["<new signaling '
            'words or phrases from the question>"], "confidence": 0.0-1.0}'
        )
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "%s:generateContent" % _model,
            data=body, headers={"Content-Type": "application/json",
                                "x-goog-api-key": api_key})
        with urllib.request.urlopen(req, timeout=_timeout) as resp:
            data = json.load(resp)
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            _log("PARSE-FAIL: no JSON in response for q=%s" % _qhash(question))
            return None
        out = json.loads(m.group(0))
        event = out.get("event")
        # HARD GUARD: never invent an event.
        if event not in candidate_events:
            _log("REJECT: event %r not in candidate set" % (event,))
            return None
        conf = out.get("confidence", 0)
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0
        if conf < _CONFIDENCE_THRESHOLD:
            _log("LOW-CONF (%.2f): q=%s -> %s" % (conf, _qhash(question), event))
            return None
        keywords = [k.strip().lower() for k in out.get("keywords", [])
                    if isinstance(k, str) and k.strip()][: _MAX_KEYWORDS]
        return {"event": event, "keywords": keywords, "confidence": conf}
    except Exception as e:
        _log("API-FAIL: %s for q=%s" % (type(e).__name__, _qhash(question)))
        return None


def save_learned(keywords, event, confidence, existing_keywords, question=None):
    """Save learned keywords as unreviewed (after collision + domain check).

    Returns the list of phrases actually saved. Never raises.

    2026-10-14 (Gemini 4 audit): domain-anchor quarantine. A phrase must
    contain at least one domain-anchor stem (job, exam, money, marriage...)
    and not be pure generic words ("good news", "settle down"). Prevents
    silent hijacking of unrelated questions.
    2026-10-15 (review 3.2): a keyword is only saved if it actually appears
    in the question (substring of question.lower()) — a prompt-injected
    keyword like "job offer" for a divorce question is dropped.
    """
    saved = []
    try:
        entries = _load_learned()
        q_low = (question or '').lower()
        for kw in keywords:
            kw = (kw or "").strip().lower()
            if not kw or kw in entries:
                continue
            if q_low and kw not in q_low:
                _log("DROPPED (not in question): '%s' -> %s" % (kw, event))
                continue
            if not check_collision(kw, existing_keywords):
                continue
            if not is_safe_learned_phrase(kw):
                _log("QUARANTINED: '%s' -> %s (no domain anchor)" % (kw, event))
                continue
            entries[kw] = {"event": event,
                           "confidence": confidence,
                           "source": "gemini-fallback",
                           "date_added": str(date.today()),
                           "reviewed": False}
            saved.append(kw)
        if saved:
            _save_learned(entries)
            _log("LEARNED: %s -> %s (unreviewed)" % (saved, event))
    except Exception as e:
        _log("SAVE-FAIL: %s" % type(e).__name__)
    return saved


# 2026-10-14: domain-anchor stems that prove a phrase belongs to a concrete
# horary domain. Auto-learned phrases MUST contain at least one.
_DOMAIN_ANCHORS = {
    # Career
    "job", "naukri", "employ", "hir", "recruit", "interview", "offer",
    "promot", "transfer", "resign", "sack", "terminat", "retir", "boss",
    "busi", "startup", "contract",
    # Exam & Education
    "exam", "test", "paper", "upsc", "ibps", "ssc", "neet", "jee", "gate",
    "admit", "cutoff", "merit", "qualifi", "pass", "degre", "colleg",
    "univers", "board", "rank",
    # Money, Property & Legal
    "money", "rupe", "lakh", "crore", "loan", "debt", "emi", "repay",
    "lent", "stock", "share", "lotteri", "inherit", "properti", "flat",
    "plot", "court", "case", "bail", "jail", "alimon", "theft", "stolen",
    "fraud", "scam",
    # Relationship & Family
    "marri", "shaadi", "wed", "bride", "groom", "engag", "divorc",
    "affair", "cheat", "boyfriend", "girlfriend", "breakup", "reunion",
    "pregnant", "conceiv", "childbirth", "adopt",
    # Health & Travel
    "ill", "sick", "diseas", "recover", "cure", "surgeri", "oper",
    "hospit", "icu", "visa", "abroad", "foreign", "passport",
}

# Generic words that alone prove nothing — a phrase of only these is poison.
_GENERIC_POISON = {
    "good", "bad", "news", "favour", "favor", "work", "thing", "things",
    "happen", "soon", "future", "life", "luck", "fate", "destiny",
    "success", "result", "outcome", "next", "final", "stage", "round",
    "step", "list", "chance", "hope", "wish", "dream", "problem",
    "issue", "settle", "clear", "approve",
}

def _simple_stem(w):
    """Minimal stemmer for quarantine check (no imports from stage1)."""
    w = w.lower()
    if len(w) <= 3:
        return w
    for suf in ("ing", "ed", "ies", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            if suf == "ies":
                return w[:-3] + "y"
            return w[:-len(suf)]
    return w

def is_safe_learned_phrase(phrase):
    """True if a learned phrase is safe to auto-save. Never raises."""
    try:
        toks = [t.lower() for t in re.findall(r"[a-zA-Z]+", phrase)]
        if not (2 <= len(toks) <= 4):
            return False
        stems = {_simple_stem(t) for t in toks}
        if not (stems & _DOMAIN_ANCHORS):
            return False
        non_generic = [t for t in toks
                       if t not in _GENERIC_POISON and t not in _STOP]
        if not non_generic:
            return False
        return True
    except Exception:
        return False


def fallback_for_question(question, norm_text, known_vocab, candidate_events,
                          existing_keywords):
    """Main entry: called at the NO_EVENT point when use_gemini is on.

    Returns (event_or_None, saved_keywords_list). Always safe to call.
    """
    unknown = find_unknown_words(norm_text, known_vocab)
    result = call_gemini_for_event(question, candidate_events)
    if not result:
        _log("NO-MAP: q=%s (unknown: %s)" % (_qhash(question), unknown[:8]))
        return None, []
    saved = save_learned(result["keywords"], result["event"],
                         result["confidence"], existing_keywords,
                         question=question)
    return result["event"], saved
