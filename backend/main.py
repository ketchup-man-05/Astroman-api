"""Astroman AI backend API.

Thin FastAPI wrapper around the KP engine (engine/pipeline.py).
The engine code is untouched — this just gives it an HTTP door.

Endpoints:
  GET  /health  — uptime check (for UptimeRobot)
  POST /ask     — ask a question, get a verdict + narration
"""

import os
import sys
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Engine import ---
# Local dev: engine lives in ~/workspace/astroman_v2
# Render deploy: engine/ is copied next to this file (see build script)
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.expanduser("~/workspace/astroman_v2")):
    if _p not in sys.path and os.path.isdir(os.path.join(_p, "engine")):
        sys.path.insert(0, _p)

from engine import pipeline  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))

app = FastAPI(title="Astroman AI API", version="1.0.0")

# Allow the JS frontend (any origin for now; lock down later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    city: str = Field(default="Shimla", max_length=100)
    horary_number: int = Field(..., ge=1, le=249)


class FollowupRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    verdict: str = Field(..., min_length=1, max_length=100)
    narration: str = Field(default="", max_length=4000)
    timing: str = Field(default="", max_length=2000)
    followup: str = Field(..., min_length=3, max_length=500)


class AskResponse(BaseModel):
    verdict: str
    modifiers: list = []
    narration: str = ""
    question: str
    city: str
    number: int
    cast_at: str
    # Full engine result for the frontend to use as needed
    result: dict = {}


def _gemini_key():
    return os.environ.get("GEMINI_API_KEY") or None


def _bedrock_config():
    """Bedrock credentials from env. Returns None if not configured."""
    key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not (key_id and secret):
        return None
    return {
        "key_id": key_id,
        "secret": secret,
        "region": os.environ.get("AWS_REGION") or "ap-south-1",
        "model": os.environ.get("BEDROCK_MODEL_ID") or "amazon.nova-lite-v1:0",
    }


def _bedrock_narrate(question: str, verdict_line: str, template_notes: str) -> str:
    """Rewrite the engine's template narration via Bedrock. Never raises.

    The verdict is decided by the engine and passed in fixed — Bedrock only
    rewords it. Any failure returns "" so the caller falls back to the
    template narration silently.
    """
    cfg = _bedrock_config()
    if not cfg:
        return ""
    try:
        import boto3
        client = boto3.client(
            "bedrock-runtime",
            region_name=cfg["region"],
            aws_access_key_id=cfg["key_id"],
            aws_secret_access_key=cfg["secret"],
        )
        prompt = (
            "You are the narrator for Astroman.AI, a KP horary astrology app. "
            "The astrology engine has already decided the verdict below. NEVER change, "
            "soften, or question the verdict. Your only job is to say it in warm, plain, "
            "simple English for a young person who knows nothing about astrology.\n\n"
            f"Question: {question}\n"
            f"Verdict: {verdict_line}\n"
            f"Engine notes: {template_notes}\n\n"
            "Rules: 3-5 short sentences. No astrology jargon. No remedies, gemstones, "
            "or rituals. No exaggeration and no guarantees beyond what the verdict says. "
            "Start with the verdict in plain words. "
            "IMPORTANT: if the verdict is OTHER or UNANSWERABLE, the chart gave no clear "
            "answer. Say that honestly and warmly in plain words — never turn it into a yes "
            "or a no. Suggest asking again another time or speaking to a human reader."
        )
        resp = client.converse(
            modelId=cfg["model"],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 300, "temperature": 0.7},
        )
        parts = resp.get("output", {}).get("message", {}).get("content", [])
        text = "".join(
            p.get("text", "") for p in parts if isinstance(p, dict)
        ).strip()
        return text
    except Exception:
        return ""


def _bedrock_followup(question: str, verdict_line: str, narration: str,
                      timing: str, followup: str) -> str:
    """Answer a follow-up about an EXISTING reading via Bedrock. Never raises.

    The verdict is fixed by the engine and has already been shown to the
    user. This only explains/discusses that reading — it must never give a
    new verdict. Any failure returns "" so the caller can answer honestly
    that follow-ups are unavailable right now.
    """
    cfg = _bedrock_config()
    if not cfg:
        return ""
    try:
        import boto3
        client = boto3.client(
            "bedrock-runtime",
            region_name=cfg["region"],
            aws_access_key_id=cfg["key_id"],
            aws_secret_access_key=cfg["secret"],
        )
        prompt = (
            "You are the follow-up voice for Astroman.AI, a KP horary astrology "
            "app. A reading has already been given and is FIXED below. The user "
            "is asking a follow-up question about THAT reading.\n\n"
            f"Original question: {question}\n"
            f"Verdict (fixed, already shown): {verdict_line}\n"
            f"Reading given to the user: {narration}\n"
            f"Timing from the reading: {timing or '(none given)'}\n\n"
            f"User follow-up: {followup}\n\n"
            "Rules:\n"
            "- Answer ONLY about this reading: explain the verdict, the reading, "
            "or its timing in warm, plain, simple English for a young person who "
            "knows nothing about astrology.\n"
            "- NEVER change, soften, reverse, or question the verdict. NEVER give "
            "a new verdict or a yes/no answer to a new question.\n"
            "- If the follow-up is actually a NEW question about a different "
            "matter (not about this reading), reply briefly and warmly starting "
            "with 'That needs its own chart.' and explain that a new question "
            "needs a fresh number and chart, so they should use the Ask a New "
            "Question button. Do not answer the new question.\n"
            "- Use ONLY the facts in the reading above. No astrology jargon, no "
            "invented planetary reasons, no remedies, gemstones, or rituals, no "
            "guarantees. If the reading does not say something, say that honestly "
            "instead of inventing it.\n"
            "- Keep it short: 2-4 short sentences."
        )
        resp = client.converse(
            modelId=cfg["model"],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 300, "temperature": 0.7},
        )
        parts = resp.get("output", {}).get("message", {}).get("content", [])
        text = "".join(
            p.get("text", "") for p in parts if isinstance(p, dict)
        ).strip()
        return text
    except Exception:
        return ""


def _narration_text(result: dict) -> str:
    """Build a human-readable narration from the engine result.

    The engine's verdict + modifiers are the core. The full narration
    (Gemini or template) lives in result['notes'] when available.
    """
    notes = result.get("notes") or ""
    if isinstance(notes, list):
        notes = " ".join(str(n) for n in notes)
    return str(notes)


def _display_verdict(result: dict) -> str:
    """User-facing verdict line, e.g. 'YES — with delays'."""
    verdict = (result.get("verdict") or "UNANSWERABLE").upper()
    modifiers = result.get("modifiers") or []
    if verdict == "YES" and any("DELAY" in str(m).upper() for m in modifiers):
        return "YES — with delays"
    if verdict == "YES" and "PARTIAL" in [str(m).upper() for m in modifiers]:
        return "YES — partially"
    return verdict


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(IST).isoformat()}


@app.get("/")
def root():
    return {
        "name": "Astroman AI API",
        "version": "1.0.0",
        "endpoints": ["/health", "/ask", "/followup"],
    }


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    key = _gemini_key()
    if key and not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = key

    try:
        result = pipeline.answer(
            req.question.strip(),
            req.city.strip() or "Shimla",
            int(req.horary_number),
            use_gemini=bool(key),
        )
    except Exception as e:
        # pipeline.answer never raises, but be safe
        result = {"verdict": "UNANSWERABLE", "modifiers": [],
                  "notes": f"Engine error: {e}"}

    if not result or not result.get("verdict"):
        result = {"verdict": "UNANSWERABLE", "modifiers": [],
                  "notes": "The chart could not be cast for that city."}

    narration = _narration_text(result)

    # Bedrock narration (optional): rewords the template notes, never the verdict.
    # Used only when Bedrock is configured AND no Gemini key is set (Gemini keeps
    # priority if the user ever adds a fresh key). Any failure falls back to the
    # template silently — verdicts never depend on narration.
    if _bedrock_config() and not key:
        improved = _bedrock_narrate(
            req.question.strip(),
            _display_verdict(result),
            narration,
        )
        if improved:
            narration = improved

    # Make the result JSON-safe (engine may include non-serializable objects)
    safe_result = {}
    for k, v in result.items():
        try:
            import json
            json.dumps(v)
            safe_result[k] = v
        except (TypeError, ValueError):
            safe_result[k] = str(v)

    return AskResponse(
        verdict=_display_verdict(result),
        modifiers=result.get("modifiers") or [],
        narration=narration,
        question=req.question.strip(),
        city=req.city.strip() or "Shimla",
        number=int(req.horary_number),
        cast_at=datetime.now(IST).strftime("%-d %b %Y, %-I:%M %p IST"),
        result=safe_result,
    )


@app.post("/followup")
def followup(req: FollowupRequest):
    """Follow-up about an existing reading. Explains the reading only —
    never casts a chart and never gives a new verdict. Follow-ups are part
    of the reading the user already got, so no quota is involved here (the
    frontend quota counts full questions only)."""
    answer = _bedrock_followup(
        req.question.strip(),
        req.verdict.strip(),
        req.narration.strip(),
        req.timing.strip(),
        req.followup.strip(),
    )
    if not answer:
        return {"answer": "", "available": False}
    return {"answer": answer, "available": True}
