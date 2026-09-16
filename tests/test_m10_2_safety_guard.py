"""
tests/test_m10_2_safety_guard.py
─────────────────────────────────
M10.2 — FinGuard AI Safety Guard Unit Tests

Tests the deterministic post-generation safety validation layer implemented
in src/m9_agent/safety_guard.py.

Coverage matrix (as specified in M10.2 requirements):
  a. "CLU00604 is confirmed fraud"              -> BLOCK
  b. "CLU00604 is definitely fraud"             -> BLOCK
  c. "The fraud probability is 85%"             -> BLOCK
  d. "CLU00604 is an elevated-risk investigation candidate." -> ALLOW
  e. "This does not prove fraud."               -> ALLOW
  f. "The dataset has no ground-truth fraud labels." -> ALLOW

Additional coverage:
  g. Negation-prefix exemptions for each major forbidden term
  h. validate_response returns SAFE_FALLBACK on violation without callback
  i. validate_response uses regeneration callback when provided
  j. validate_response uses SAFE_FALLBACK when callback also violates
  k. is_safe() convenience predicate
  l. Case-insensitivity of forbidden patterns
"""

import pytest
from src.m9_agent.safety_guard import is_safe, validate_response, SAFE_FALLBACK


# ──────────────────────────────────────────────────────────────────────────────
# Required M10.2 tests (a–f)
# ──────────────────────────────────────────────────────────────────────────────

class TestM102Required:
    """Exact test cases specified in the M10.2 requirements."""

    def test_a_confirmed_fraud_blocked(self):
        """(a) 'CLU00604 is confirmed fraud' must be BLOCKED."""
        assert not is_safe("CLU00604 is confirmed fraud"), (
            "Phrase 'confirmed fraud' should be blocked"
        )

    def test_b_definitely_fraud_blocked(self):
        """(b) 'CLU00604 is definitely fraud' must be BLOCKED."""
        assert not is_safe("CLU00604 is definitely fraud"), (
            "Phrase 'definitely fraud' should be blocked"
        )

    def test_c_fraud_probability_blocked(self):
        """(c) 'The fraud probability is 85%' must be BLOCKED."""
        assert not is_safe("The fraud probability is 85%."), (
            "Phrase 'fraud probability' should be blocked"
        )

    def test_d_elevated_risk_investigation_candidate_allowed(self):
        """(d) 'CLU00604 is an elevated-risk investigation candidate.' must be ALLOWED."""
        assert is_safe("CLU00604 is an elevated-risk investigation candidate."), (
            "Legitimate FinGuard terminology must pass the safety guard"
        )

    def test_e_does_not_prove_fraud_allowed(self):
        """(e) 'This does not prove fraud.' must be ALLOWED."""
        assert is_safe("This does not prove fraud."), (
            "Negated fraud claim should pass the safety guard"
        )

    def test_f_no_ground_truth_labels_allowed(self):
        """(f) 'The dataset has no ground-truth fraud labels.' must be ALLOWED."""
        assert is_safe("The dataset has no ground-truth fraud labels."), (
            "Statement about data limitations should pass the safety guard"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Extended blocking tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBlockedPhrases:
    """Additional phrases that must be blocked."""

    @pytest.mark.parametrize("text", [
        "This transaction was fraudulent.",
        "The merchant is guilty.",
        "Guilty of fraud.",
        "100% fraud detected.",
        "This is proven fraud.",
        "CLU00604 is fraudulent activity.",
        "These transactions are fraudulent.",
        "CLU00604 is fraud.",
        "CLU00604 is a fraudulent transaction.",
        "CLU00604 constitutes fraud.",
        "CLU00604 committed fraud.",
        "CLU00604 is certainly fraudulent.",
        "There is no doubt that CLU00604 is fraudulent.",
        "CLU00604 has been established as fraudulent.",
        "CLU00604 is unquestionably fraud.",
        "CLU00604 is conclusively fraudulent.",
        "CLU00604 is definitely a fraud case.",
    ])
    def test_blocked(self, text):
        assert not is_safe(text), f"Expected BLOCK for: {text!r}"


# ──────────────────────────────────────────────────────────────────────────────
# Extended allow tests (negation-prefix exemptions)
# ──────────────────────────────────────────────────────────────────────────────

class TestAllowedNegatedPhrases:
    """Negated fraud claims that must NOT be blocked (false-positive prevention)."""

    @pytest.mark.parametrize("text", [
        "This does not prove fraud.",
        "The available data cannot establish fraud.",
        "No ground truth fraud labels are available.",
        "This is an investigation candidate, not confirmed fraud.",
        "We cannot confirm fraud.",
        "There is no confirmed fraud here.",
        "These signals do not establish fraud.",
        "Cannot prove fraud with available evidence.",
    ])
    def test_allowed(self, text):
        assert is_safe(text), f"Expected ALLOW (false positive avoided) for: {text!r}"


# ──────────────────────────────────────────────────────────────────────────────
# FinGuard-approved terminology allow tests
# ──────────────────────────────────────────────────────────────────────────────

class TestApprovedTerminology:
    """Responses using FinGuard-approved terminology must pass."""

    @pytest.mark.parametrize("text", [
        "CLU00604 is an elevated-risk investigation candidate.",
        "This entity presents observable evidence of suspicious activity.",
        "The risk signal indicates further review is warranted.",
        "Investigation candidate based on observed behavioral patterns.",
        "Data limitations prevent a definitive conclusion.",
        "Due to data limitations no fraud determination can be made.",
        "This is an investigation candidate, not a confirmed fraud finding.",
    ])
    def test_approved_terminology_allowed(self, text):
        assert is_safe(text), f"Approved terminology should pass: {text!r}"


# ──────────────────────────────────────────────────────────────────────────────
# Case-insensitivity
# ──────────────────────────────────────────────────────────────────────────────

class TestCaseInsensitivity:
    """Forbidden patterns must be caught regardless of case."""

    @pytest.mark.parametrize("text", [
        "CLU00604 IS CONFIRMED FRAUD",
        "Confirmed Fraud detected.",
        "FRAUD PROBABILITY = 0.9",
        "Definitely Fraud.",
        "PROVEN FRAUD in this cluster.",
    ])
    def test_blocked_case_insensitive(self, text):
        assert not is_safe(text), f"Expected BLOCK (case-insensitive) for: {text!r}"


# ──────────────────────────────────────────────────────────────────────────────
# validate_response integration
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateResponse:
    """Behavioural tests for validate_response()."""

    def test_safe_response_returned_unchanged(self):
        safe_text = "CLU00604 is an elevated-risk investigation candidate."
        result = validate_response(safe_text)
        assert result == safe_text

    def test_unsafe_without_callback_returns_fallback(self):
        unsafe_text = "CLU00604 is confirmed fraud."
        result = validate_response(unsafe_text)
        assert result == SAFE_FALLBACK

    def test_unsafe_with_safe_callback_returns_regenerated(self):
        unsafe_text = "This is confirmed fraud."
        safe_regen = "This entity is an elevated-risk investigation candidate."
        result = validate_response(unsafe_text, regeneration_callback=lambda: safe_regen)
        assert result == safe_regen

    def test_unsafe_with_unsafe_callback_returns_fallback(self):
        unsafe_text = "Confirmed fraud detected."
        also_unsafe_regen = "Definitely fraud, definitely."
        result = validate_response(
            unsafe_text,
            regeneration_callback=lambda: also_unsafe_regen
        )
        assert result == SAFE_FALLBACK

    def test_unsafe_with_throwing_callback_returns_fallback(self):
        unsafe_text = "Proven fraud in this cluster."

        def _throwing_callback():
            raise RuntimeError("LLM timeout")

        result = validate_response(unsafe_text, regeneration_callback=_throwing_callback)
        assert result == SAFE_FALLBACK

    def test_safe_fallback_itself_is_safe(self):
        """SAFE_FALLBACK must itself pass the safety policy (sanity check)."""
        assert is_safe(SAFE_FALLBACK), "SAFE_FALLBACK text must itself be policy-compliant"


# ──────────────────────────────────────────────────────────────────────────────
# Adversarial Negation Bypass tests
# ──────────────────────────────────────────────────────────────────────────────

class TestAdversarialNegationBypass:
    """Tests ensuring that unrelated negations do not exempt later unsafe statements."""

    @pytest.mark.parametrize("text", [
        "The dataset does not prove fraud. However, CLU00604 is confirmed fraud.",
        "This analysis cannot establish fraud. Therefore, CLU00604 is definitely fraud.",
        "We cannot confirm fraud for other entities, but CLU00604 is fraud.",
        "There is no evidence of money laundering.\nCLU00604 is confirmed fraud.",
        "We did not find anything here; CLU00604 is definitely fraud.",
        "They are not clean| CLU00604 is proven fraud.",
        "• This does not prove fraud.\n• CLU00604 is confirmed fraud.",
        "I cannot say for sure. CLU00604 is fraudulent.",
        "It is not okay. Thus, it is 100% fraud.",
        "There's no problem with user A. User B is guilty of fraud.",
        "CLU00604 is not only high risk but is confirmed fraud.",
        "CLU00604 is not merely suspicious but is confirmed fraud.",
        "CLU00604 is not just risky; it is fraudulent.",
        "This is not merely a risk assessment. CLU00604 is definitely fraud.",
        "The data does not prove fraud, but CLU00604 is confirmed fraud.",
        "The dataset cannot establish fraud; nevertheless, CLU00604 is fraudulent.",
        "* We found no issues here.\n* CLU00604 is confirmed fraud.",
        "# No immediate concerns\n## CLU00604 is definitely fraud",
        "> This does not prove anything.\n> CLU00604 is proven fraud.",
        "There is no evidence. **CLU00604 is fraud.**",
        "1. No issues.\n2. CLU00604 is fraud.",
        "It is not okay.\n\nCLU00604 is fraudulent.",
    ])
    def test_cross_boundary_negation_blocked(self, text):
        assert not is_safe(text), f"Expected BLOCK (bypassing negation) for: {text!r}"


# ──────────────────────────────────────────────────────────────────────────────
# is_safe predicate
# ──────────────────────────────────────────────────────────────────────────────

class TestIsSafePredicate:
    def test_is_safe_true_for_clean_text(self):
        assert is_safe("This entity requires investigation based on risk signals.")

    def test_is_safe_false_for_forbidden(self):
        assert not is_safe("The fraud probability is 100%.")

    def test_is_safe_empty_string(self):
        assert is_safe("")

    def test_is_safe_only_whitespace(self):
        assert is_safe("   \n\t  ")
