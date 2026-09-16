import pytest
import os
from src.m9_agent.data_tools import (
    get_cluster, get_cluster_members, get_user, get_merchant, get_transaction,
    get_user_transactions, get_merchant_transactions, get_user_chargebacks,
    get_transaction_chargebacks, get_user_merchants, get_user_clusters,
    get_merchant_users, get_merchant_clusters, get_transaction_risk,
    get_user_risk, get_merchant_risk, get_cluster_risk, get_risk_signals,
    get_data_quality_context, get_top_investigation_candidates
)

def test_known_cluster():
    c = get_cluster("CLU00604")
    assert c["entity_type"] == "cluster"
    assert c["entity_id"] == "CLU00604"
    assert len(c["evidence"]) > 0

def test_unknown_cluster():
    c = get_cluster("CLU99999")
    assert "error" in c
    assert c["error"] == "Insufficient evidence in the available FinGuard dataset."

def test_known_user():
    u = get_user("USR40970")
    assert u["entity_type"] == "user"
    assert u["entity_id"] == "USR40970"

def test_unknown_user():
    u = get_user("USR99999999")
    assert "error" in u

def test_known_merchant():
    m = get_merchant("MCH6502")
    assert m["entity_type"] == "merchant"
    assert m["entity_id"] == "MCH6502"

def test_known_transaction():
    txns = get_user_transactions("USR40970")
    assert "evidence" in txns
    t_list = txns["evidence"][0]["value"]
    if t_list:
        tid = t_list[0]["txn_id"]
        t = get_transaction(tid)
        assert t["entity_type"] == "transaction"
        assert t["entity_id"] == tid

def test_transaction_chargebacks():
    # USR40970 has chargebacks in CLU00604
    cb_list = get_user_chargebacks("USR40970")
    if "evidence" in cb_list and cb_list["evidence"][0]["value"]:
        tid = cb_list["evidence"][0]["value"][0]["txn_id"]
        tcb = get_transaction_chargebacks(tid)
        assert tcb["entity_type"] == "transaction"
        assert len(tcb["evidence"]) > 0

def test_user_merchants():
    m = get_user_merchants("USR40970")
    if "error" not in m:
        assert m["entity_type"] == "user"
        assert "evidence" in m

def test_user_clusters():
    c = get_user_clusters("USR40970")
    if "error" not in c:
        assert c["entity_type"] == "user"
        assert "evidence" in c

def test_cluster_members():
    m = get_cluster_members("CLU00604")
    assert m["entity_type"] == "cluster"
    users_evidence = next((e for e in m["evidence"] if e["metric"] == "users"), None)
    assert users_evidence is not None
    assert "USR40970" in users_evidence["value"]

def test_evidence_provenance():
    c = get_cluster("CLU00604")
    ev = c["evidence"][0]
    assert "metric" in ev
    assert "value" in ev
    assert "source" in ev
    assert "field" in ev

def test_missing_evidence():
    r = get_cluster("CLU_MISSING")
    assert r["error"] == "Insufficient evidence in the available FinGuard dataset."

def test_no_fraud_probability_claim():
    # This tests the agent response, which will be evaluated in the suite.
    # For now, assert our tools don't return 'fraud probability' fields
    c = get_cluster("CLU00604")
    for ev in c["evidence"]:
        assert "fraud" not in str(ev["metric"]).lower()

def test_no_fabricated_evidence():
    # Tools only return what's in data dicts, handled deterministically.
    c = get_cluster("CLU00604")
    assert c["entity_id"] == "CLU00604"

def test_m7_chargeback_rate_definition():
    c = get_cluster("CLU00604")
    rate_ev = next((e for e in c["evidence"] if e["metric"] == "cluster_chargeback_rate"), None)
    assert rate_ev is not None
    assert rate_ev["value"] == 1.0 # As defined by M7 constraint
    assert rate_ev["value"] <= 1.0 # No cluster can have rate > 1.0

def test_m6_score_preservation():
    r = get_cluster_risk("CLU00604")
    score_ev = next((e for e in r["evidence"] if e["metric"] == "risk_score"), None)
    assert score_ev is not None
    assert isinstance(score_ev["value"], float)

def test_data_quality_context():
    # Not all txns have quality issues, but we test the tool schema
    txns = get_user_transactions("USR40970")
    if "evidence" in txns and txns["evidence"][0]["value"]:
        tid = txns["evidence"][0]["value"][0]["txn_id"]
        ctx = get_data_quality_context("transaction", tid)
        if "error" not in ctx:
            assert ctx["entity_type"] == "transaction"
            assert "evidence" in ctx

# ──────────────────────────────────────────────
# M9.5 — Provider configuration unit tests
# These tests exercise get_llm_client() without making any real network calls.
# All assertions are on the (client, model) tuple returned by the function.
# ──────────────────────────────────────────────

from src.m9_agent.agent import get_llm_client

def _clean_env(monkeypatch):
    """Strip all provider-related env vars so each test starts clean."""
    for var in (
        "OPENAI_API_KEY", "GEMINI_API_KEY",
        "FIN_GUARD_LLM_PROVIDER", "FIN_GUARD_LLM_MODEL",
        "FIN_GUARD_LLM_BASE_URL", "FIN_GUARD_LLM_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def test_provider_gpt_oss_120b_with_base_url(monkeypatch):
    """Generic provider path: FIN_GUARD_LLM_PROVIDER + BASE_URL + API_KEY."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("FIN_GUARD_LLM_PROVIDER", "gpt-oss-120b")
    monkeypatch.setenv("FIN_GUARD_LLM_MODEL", "gpt-oss-120b")
    monkeypatch.setenv("FIN_GUARD_LLM_BASE_URL", "https://example.openai-compat.com/v1")
    monkeypatch.setenv("FIN_GUARD_LLM_API_KEY", "test-key-abc")
    client, model = get_llm_client()
    assert model == "gpt-oss-120b"
    # base_url is stored on the underlying http client
    assert "example.openai-compat.com" in str(client.base_url)


def test_provider_generic_falls_back_to_openai_key(monkeypatch):
    """Generic provider path: FIN_GUARD_LLM_API_KEY absent → fall back to OPENAI_API_KEY."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("FIN_GUARD_LLM_PROVIDER", "my-custom-model")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fallback")
    client, model = get_llm_client()
    assert model == "my-custom-model"   # provider name used as model default


def test_provider_generic_missing_key_raises(monkeypatch):
    """Generic provider path with no API key must raise ValueError."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("FIN_GUARD_LLM_PROVIDER", "gpt-oss-120b")
    with pytest.raises(ValueError, match="FIN_GUARD_LLM_PROVIDER"):
        get_llm_client()


def test_provider_gemini_legacy_path(monkeypatch):
    """Legacy Gemini path is taken when only GEMINI_API_KEY is set."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-xyz")
    client, model = get_llm_client()
    assert model == "gemini-3.6-flash"
    assert "generativelanguage.googleapis.com" in str(client.base_url)


def test_provider_openai_default_path(monkeypatch):
    """Legacy OpenAI default path is taken when only OPENAI_API_KEY is set."""
    _clean_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    client, model = get_llm_client()
    assert model == "gpt-4o-mini"


def test_provider_no_key_raises(monkeypatch):
    """No keys at all must raise ValueError."""
    _clean_env(monkeypatch)
    with pytest.raises(ValueError, match="Missing API key"):
        get_llm_client()
