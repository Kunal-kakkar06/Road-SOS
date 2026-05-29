"""
nlp_triage.py — Voice/NLP triage scorer.

Pipeline:
  1. Whisper (speech → text)
  2. Keyword heuristic → severity score  (primary scorer)
  3. ClinicalBERT refinement             (secondary, optional; skipped if import fails)
"""

import logging
import os
import tempfile
from typing import Dict

logger = logging.getLogger("roadsos.nlp_triage")

# ── Lazy singletons ────────────────────────────────────────────
_whisper_model  = None
_bert_pipeline  = None


def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            _whisper_model = whisper.load_model("base")
            logger.info("[NLPTriage] Whisper base loaded")
        except Exception as exc:
            logger.error("[NLPTriage] Could not load Whisper: %s", exc)
            _whisper_model = None
    return _whisper_model


def get_bert_pipeline():
    """
    Load ClinicalBERT as a text-classification pipeline.

    Disabled by default — opt in by setting ENABLE_CLINICAL_BERT=true in .env.
    Keyword-only scoring is accurate enough for the prototype and avoids a
    multi-second CPU inference on every cold start.
    """
    global _bert_pipeline
    import os
    if _bert_pipeline is False:
        return None
    # Check opt-in env var
    if os.getenv("ENABLE_CLINICAL_BERT", "false").lower() != "true":
        _bert_pipeline = False
        return None
    if _bert_pipeline is None:
        try:
            from transformers import pipeline
            _bert_pipeline = pipeline(
                "text-classification",
                model="medicalai/ClinicalBERT",
                device=-1,               # CPU
                top_k=None,
            )
            logger.info("[NLPTriage] ClinicalBERT pipeline loaded")
        except Exception as exc:
            logger.warning(
                "[NLPTriage] ClinicalBERT not available (%s) — "
                "falling back to keyword-only scoring.", exc
            )
            _bert_pipeline = False
    return _bert_pipeline if _bert_pipeline is not False else None


# ── Keyword severity lexicons ──────────────────────────────────

_CRITICAL = [
    "unconscious", "not breathing", "no pulse", "massive bleeding",
    "blood everywhere", "can't breathe", "cannot breathe", "chest pain",
    "paralyzed", "severe head injury", "seizure", "cardiac arrest",
    "heart attack", "stroke", "unresponsive",
]
_SERIOUS = [
    "heavy bleeding", "broken bone", "can't move", "cannot move",
    "dizziness", "vomiting blood", "deep wound", "can't feel", "cannot feel",
    "blurry vision", "severe pain", "neck injury", "back injury",
    "fractured", "dislocated",
]
_MODERATE = [
    "bleeding", "pain", "bruise", "sprain", "conscious", "awake",
    "responding", "cut", "scrape", "mild pain", "dizzy", "nausea",
]


def _keyword_score(text: str) -> tuple[str, float]:
    t = text.lower()
    critical = sum(1 for k in _CRITICAL if k in t)
    serious  = sum(1 for k in _SERIOUS  if k in t)
    moderate = sum(1 for k in _MODERATE if k in t)

    if critical >= 1:
        return "P1", 0.85
    if serious >= 1:
        return "P2", 0.70
    if moderate >= 1:
        return "P3", 0.55
    return "P4", 0.40


def _bert_refine(text: str, base_score: float) -> float:
    """
    Use ClinicalBERT output label text to nudge the keyword score.
    ClinicalBERT outputs ICD/clinical labels — we map them heuristically.
    Returns adjusted score.
    """
    pipe = get_bert_pipeline()
    if pipe is None or len(text.split()) < 3:
        return base_score
    try:
        results = pipe(text[:512])
        top = max(results[0], key=lambda x: x["score"])
        label = top["label"].lower()
        if any(w in label for w in ["severe", "critical", "emergency", "acute"]):
            return max(base_score, 0.80)
        if any(w in label for w in ["moderate", "significant"]):
            return max(base_score, 0.60)
        if any(w in label for w in ["mild", "minor", "stable"]):
            return min(base_score, 0.50)
    except Exception as exc:
        logger.debug("[ClinicalBERT] Refinement skipped: %s", exc)
    return base_score


# ── Public API ─────────────────────────────────────────────────

def transcribe_audio(audio_bytes: bytes, audio_format: str = "wav") -> str:
    """Convert speech bytes → transcript string using Whisper."""
    model = get_whisper()
    if model is None:
        return ""
    try:
        with tempfile.NamedTemporaryFile(
            suffix=f".{audio_format}", delete=False
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        result   = model.transcribe(tmp_path, language="en")
        os.unlink(tmp_path)
        return result["text"].strip()
    except Exception as exc:
        logger.error("[Whisper] Transcription error: %s", exc)
        return ""


def extract_severity_from_text(text: str) -> Dict:
    """
    Keyword + optional ClinicalBERT severity scoring from free text.

    Returns:
        severity     : "P1" | "P2" | "P3" | "P4"
        score        : float 0.0–1.0
        transcript   : the input text (echoed)
        keywords_hit : number of severity keywords detected
    """
    if not text.strip():
        return {"severity": "P3", "score": 0.50, "transcript": "", "keywords_hit": 0}

    t = text.lower()
    severity, score = _keyword_score(text)
    keywords_hit    = sum(
        1 for k in (_CRITICAL + _SERIOUS + _MODERATE) if k in t
    )

    # Optional ClinicalBERT refinement
    score = _bert_refine(text, score)

    return {
        "severity":     severity,
        "score":        round(score, 4),
        "transcript":   text,
        "keywords_hit": keywords_hit,
    }


def score_voice_input(audio_bytes: bytes, audio_format: str = "wav") -> Dict:
    """Full pipeline: raw audio bytes → transcript → severity dict."""
    transcript = transcribe_audio(audio_bytes, audio_format)
    if not transcript:
        return {
            "severity":   "P3",
            "score":      0.50,
            "transcript": "",
            "error":      "Could not transcribe audio",
        }
    return extract_severity_from_text(transcript)
