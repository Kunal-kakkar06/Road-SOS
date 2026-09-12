"""
ai/feature_engine/nlp_service.py
================================
Deterministic, semantic NLP feature extractor for emergency text.

Replaces brittle exact-string matching with robust concept groups,
negation handling, and explicit boolean/numeric feature indicators.
"""

import logging
import re
from typing import Dict, Any, List

from ai.schemas.feature_schema import TextFeatures

logger = logging.getLogger("roadsos.ai.feature_engine.nlp_service")

# ── Concept Groups ─────────────────────────────────────────────

CONCEPT_GROUPS = {
    "CRITICAL": {
        "unconscious": ["unconscious", "unresponsive", "passed out", "knocked out", "not waking up", "comatose"],
        "not_breathing": ["not breathing", "stopped breathing", "no pulse", "cardiac arrest", "can't breathe", "cannot breathe", "choking", "asphyxiating", "apnea"],
    },
    "HIGH": {
        "bleeding": ["heavy bleeding", "severe bleeding", "major bleeding", "blood everywhere", "arterial bleed", "gushing blood", "hemorrhaging", "significant bleeding", "profuse bleeding"],
        "trapped": ["trapped", "stuck inside", "can't get out", "cannot get out", "pinned", "crushed"],
        "fire": ["fire", "burning", "on fire", "flames", "smoke", "explosion"],
        "chest_pain": ["chest pain", "heart attack", "heart hurts", "angina", "myocardial infarction", "tight chest"],
        "breathing_difficulty": [
            "difficulty breathing", "severe difficulty breathing", "trouble breathing",
            "having trouble breathing", "struggling to breathe", "cannot breathe",
            "can't breathe", "unable to breathe", "shortness of breath", "gasping",
            "gasping for air", "respiratory distress", "wheezing", "asthma attack"
        ],
        "trauma": ["massive collision", "severe accident", "major crash", "head injury", "severe trauma", "amputation", "paralyzed"],
    },
    "TRAUMA": {
        "accident": ["collision", "crash", "accident", "wreck", "hit by", "run over", "fell", "fall", "struck"],
        "injury": ["broken bone", "fracture", "deep cut", "deep wound", "stabbed", "shot", "gunshot", "laceration"],
    },
    "MODERATE": {
        "pain": ["severe pain", "intense pain", "lots of pain", "hurts a lot", "extreme pain", "bad pain"],
        "bleeding": ["bleeding", "cut", "scrape", "wound", "blood"],
        "other": ["vomiting", "dizzy", "dizziness", "fainted", "passed out", "nausea", "seizure", "stroke", "fever"],
    },
    "LOW": {
        "pain": ["mild pain", "minor pain", "headache", "ache", "sore", "tired", "discomfort", "slight pain"],
        "other": ["feel okay", "otherwise okay", "fine", "nothing serious", "minor"],
    },
    "URGENCY": {
        "urgent": ["immediately", "help now", "urgent", "emergency", "hurry", "fast as possible", "right now", "quick", "asap"],
    }
}

NEGATION_TERMS = {"no", "not", "without", "zero", "none", "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't", "didn't"}

def _is_negated(text: str, match_start: int) -> bool:
    """
    Check if a matched concept is preceded by a negation term.
    Looks at the 3 words preceding the match.
    """
    preceding_text = text[:match_start].strip()
    if not preceding_text:
        return False
    
    words = re.findall(r'\w+', preceding_text.lower())
    # Check the last 3 words before the match
    for word in words[-3:]:
        if word in NEGATION_TERMS:
            return True
    return False

def _detect_concepts(text: str, group_dict: Dict[str, List[str]]) -> float:
    """
    Detect concepts in the text for a given group.
    Returns a score 0.0 or 1.0 indicating if the concept is present and not negated.
    """
    text_lower = text.lower()
    for concept, keywords in group_dict.items():
        for keyword in keywords:
            # Find all occurrences of the keyword
            for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', text_lower):
                if not _is_negated(text_lower, match.start()):
                    return 1.0
    return 0.0

def _detect_specific_concept(text: str, keywords: List[str]) -> float:
    """Detect a specific concept list."""
    text_lower = text.lower()
    for keyword in keywords:
        for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', text_lower):
            if not _is_negated(text_lower, match.start()):
                return 1.0
    return 0.0

def extract_features(text: str) -> TextFeatures:
    """
    Convert raw text into structured emergency-related features.
    """
    if not text or text.strip() == "":
        return TextFeatures(raw_text_available=False, nlp_severity_score=0.4)
        
    t = text.lower()
    
    # 1. Detect Indicators
    # Critical
    unconscious_ind = _detect_specific_concept(t, CONCEPT_GROUPS["CRITICAL"]["unconscious"])
    not_breathing_ind = _detect_specific_concept(t, CONCEPT_GROUPS["CRITICAL"]["not_breathing"])
    
    # High / Serious
    major_bleeding = _detect_specific_concept(t, CONCEPT_GROUPS["HIGH"]["bleeding"])
    minor_bleeding = _detect_specific_concept(t, CONCEPT_GROUPS["MODERATE"]["bleeding"])
    bleeding_ind = max(major_bleeding, minor_bleeding * 0.5)
    
    trapped_ind = _detect_specific_concept(t, CONCEPT_GROUPS["HIGH"]["trapped"])
    fire_ind = _detect_specific_concept(t, CONCEPT_GROUPS["HIGH"]["fire"])
    chest_pain_ind = _detect_specific_concept(t, CONCEPT_GROUPS["HIGH"]["chest_pain"])
    breathing_diff_ind = max(not_breathing_ind, _detect_specific_concept(t, CONCEPT_GROUPS["HIGH"]["breathing_difficulty"]) * 0.5)
    
    # Trauma
    major_trauma = _detect_specific_concept(t, CONCEPT_GROUPS["HIGH"]["trauma"])
    accident = _detect_specific_concept(t, CONCEPT_GROUPS["TRAUMA"]["accident"])
    injury = _detect_specific_concept(t, CONCEPT_GROUPS["TRAUMA"]["injury"])
    trauma_ind = max(major_trauma, injury * 0.5)
    accident_ind = accident
    
    # Pain
    severe_pain = _detect_specific_concept(t, CONCEPT_GROUPS["MODERATE"]["pain"])
    mild_pain = _detect_specific_concept(t, CONCEPT_GROUPS["LOW"]["pain"])
    pain_ind = max(severe_pain, mild_pain * 0.5)
    
    # Urgency
    urgency_ind = _detect_specific_concept(t, CONCEPT_GROUPS["URGENCY"]["urgent"])
    
    # 2. Category Hits
    critical_hit = any([unconscious_ind, not_breathing_ind])
    high_hit = any([major_bleeding, trapped_ind, fire_ind, chest_pain_ind, breathing_diff_ind, major_trauma])
    trauma_hit = any([accident, injury])
    moderate_hit = any([minor_bleeding, severe_pain, _detect_concepts(t, {"other": CONCEPT_GROUPS["MODERATE"]["other"]})])
    low_hit = any([mild_pain, _detect_concepts(t, {"other": CONCEPT_GROUPS["LOW"]["other"]})])
    
    # 3. Calculate nlp_severity_score
    # Start at baseline 0.4
    score = 0.40
    
    if moderate_hit:
        score += 0.15  # 0.55
    if trauma_hit:
        score += 0.15  # 0.70 (or 0.55 if no moderate)
    if high_hit:
        score += 0.30  # 0.70 or 0.85
    if critical_hit:
        score += 0.45  # 0.85+
        
    if urgency_ind:
        score += 0.05
        
    # Cap at bounds
    score = min(max(score, 0.40), 1.0)
    
    # 4. Keyword Counts (approximations based on hits)
    words = [w for w in re.findall(r'\w+', t)]
    symptom_count = len(words) // 5 + 1 # rough heuristic
    
    return TextFeatures(
        raw_text_available=True,
        symptom_count=symptom_count,
        emergency_keyword_count=1 if critical_hit else 0,
        serious_keyword_count=1 if high_hit else 0,
        moderate_keyword_count=1 if moderate_hit else 0,
        nlp_severity_score=round(score, 4),
        bleeding_indicator=bleeding_ind,
        breathing_difficulty_indicator=breathing_diff_ind,
        unconsciousness_indicator=unconscious_ind,
        trauma_indicator=trauma_ind,
        fire_indicator=fire_ind,
        trapped_indicator=trapped_ind,
        chest_pain_indicator=chest_pain_ind,
        accident_indicator=accident_ind,
        pain_severity_indicator=pain_ind,
        urgency_indicator=urgency_ind
    )
