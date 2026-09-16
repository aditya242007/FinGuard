"""
src/m9_agent/safety_guard.py
────────────────────────────
M10.2 — FinGuard AI Deterministic Post-Generation Safety Guard

This module is the **only** place that decides whether an LLM-generated
response is safe to return to the caller.  It is intentionally kept
dependency-free (stdlib + re) so it can be unit-tested without any LLM
or network access.

Design principles
─────────────────
1. All pattern matching is case-insensitive.
2. Negation detection: if any negation word (not, no, never, cannot, …)
   appears in the 80-character window BEFORE the forbidden match AND is
   not itself negated, the match is exempted as a false-positive.
3. Only EXACT substring matches count – no fuzzy matching – to keep the
   false-positive rate near zero.
4. On a violation the guard either allows one controlled regeneration (when
   a regeneration callback is supplied) or returns the deterministic
   SAFE_FALLBACK string.  It never returns an unsafe response.
"""

import re
from typing import Optional, Callable

# ──────────────────────────────────────────────────────────────────────────────
# Forbidden patterns (case-insensitive substring match)
# ──────────────────────────────────────────────────────────────────────────────

_FORBIDDEN_SUBSTRINGS = [
    "confirmed fraud",
    "definitely fraud",
    "is fraud",          # e.g. "CLU00604 is fraud"
    "was fraudulent",
    "fraud probability",
    "100% fraud",
    "proven fraud",
    "is fraudulent",
    "are fraudulent",
    "guilty of fraud",
    "fraudulent transaction",
    "constitutes fraud",
    "committed fraud",
    "certainly fraudulent",
    "established as fraudulent",
    "unquestionably fraud",
    "conclusively fraudulent",
    "definitely a fraud",
    # " guilty" handled specially via word-boundary below
]

# "guilty" on its own is forbidden unless negated; use word boundary pattern
_GUILTY_PATTERN = re.compile(r"\bguilty\b", re.IGNORECASE)

# ──────────────────────────────────────────────────────────────────────────────
# Negation detection — looks for any negation word/phrase in the local clause
# before the match. Boundaries like periods, contrastive conjunctions (but, however),
# and newlines break the negation context.
# ──────────────────────────────────────────────────────────────────────────────

# Boundaries that break a negation context
_CLAUSE_BOUNDARY_PATTERN = re.compile(
    r"(?:\.|\?|!|;|\n|\||•|\*|#|>|\bhowever\b|\bbut\b|\balthough\b|\btherefore\b|\bthus\b|\bnevertheless\b)",
    re.IGNORECASE
)

# Any of these words/phrases appearing in the local clause trigger exemption.
# Uses negative lookahead so 'no doubt' and 'without doubt' aren't treated as negations.
_NEGATION_PATTERN = re.compile(
    r"\b(not|no(?!\s+doubt)|never|cannot|can't|couldn't|doesn't|didn't|don't|"
    r"without(?!\s+(?:a\s+)?doubt)|absence|non|neither|nor)\b",
    re.IGNORECASE,
)


def _is_negated(text_lower: str, match_start: int) -> bool:
    """Return True if a negation word appears in the same clause before the match."""
    # Look back up to 150 chars to be safe (long sentences).
    window_start = max(0, match_start - 150)
    preceding = text_lower[window_start:match_start]
    
    # Find the local clause immediately preceding the match
    pieces = _CLAUSE_BOUNDARY_PATTERN.split(preceding)
    local_clause = pieces[-1] if pieces else preceding
    
    return bool(_NEGATION_PATTERN.search(local_clause))


def _check_response(text: str):
    """Return (is_safe: bool, violated_pattern: str | None).

    A response is safe if none of its forbidden substrings are present
    (after accounting for negation-prefix exemptions).
    """
    text_lower = text.lower()

    # Check substring patterns
    for pattern in _FORBIDDEN_SUBSTRINGS:
        pat_lower = pattern.lower()
        search_start = 0
        while True:
            idx = text_lower.find(pat_lower, search_start)
            if idx == -1:
                break
            if not _is_negated(text_lower, idx):
                return False, pattern  # un-negated hit -> unsafe
            search_start = idx + len(pat_lower)

    # Check "guilty" separately with word boundary
    for m in _GUILTY_PATTERN.finditer(text):
        if not _is_negated(text_lower, m.start()):
            return False, "guilty"

    return True, None


# ──────────────────────────────────────────────────────────────────────────────
# Safe deterministic fallback
# ──────────────────────────────────────────────────────────────────────────────

SAFE_FALLBACK = (
    "### Investigation Summary\n"
    "The FinGuard AI system was unable to produce a safe, policy-compliant "
    "response for this query.\n\n"
    "### Data Limitations\n"
    "The available dataset contains no ground-truth fraud labels. "
    "Consequently, no fraud-certainty claim can be made.\n\n"
    "### Analyst Conclusion\n"
    "Based on the observable evidence and risk signals retrieved from the "
    "M3-M8 analytical layers, the entity under investigation may qualify as "
    "an elevated-risk investigation candidate. "
    "This designation reflects observed risk signals only and is "
    "not a fraud-certainty statement. "
    "Further investigation by a qualified analyst is recommended."
)

# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def validate_response(response_text: str, *, regeneration_callback=None) -> str:
    """Validate *response_text* against the FinGuard safety policy.

    Parameters
    ----------
    response_text : str
        The raw text produced by the LLM.
    regeneration_callback : callable | None
        Optional zero-argument callable that returns a new candidate response
        string.  Called AT MOST ONCE.  If omitted, SAFE_FALLBACK is used
        directly on violation.

    Returns
    -------
    str
        A policy-compliant response (original, regenerated, or SAFE_FALLBACK).

    Notes
    -----
    * This function never returns an unsafe string.
    * It never raises; it always returns a safe string or SAFE_FALLBACK.
    """
    is_safe_flag, _violated = _check_response(response_text)

    if is_safe_flag:
        return response_text

    # ── First violation: attempt controlled regeneration ──────────────────────
    if regeneration_callback is not None:
        try:
            regenerated_text = regeneration_callback()
        except Exception:
            return SAFE_FALLBACK

        regen_safe, _ = _check_response(regenerated_text)
        if regen_safe:
            return regenerated_text
        # Regenerated response also violated -> use deterministic fallback
        return SAFE_FALLBACK

    # ── No regeneration callback: use deterministic fallback directly ─────────
    return SAFE_FALLBACK


def is_safe(response_text: str) -> bool:
    """Convenience predicate: True if *response_text* passes the safety policy.

    Primarily used in unit tests.
    """
    safe, _ = _check_response(response_text)
    return safe
