import pytest
from src.m9_agent.data_tools import (
    get_cluster, get_cluster_members, get_user, get_merchant, get_transaction,
    get_user_transactions, get_merchant_transactions, get_user_chargebacks,
    get_top_investigation_candidates
)

def test_get_cluster():
    c = get_cluster("CLU00604")
    assert c["cluster_id"] == "CLU00604"
    assert c["cluster_chargeback_rate"] == 1.0
    assert c["chargeback_count"] == 2
    assert "_provenance" in c
    
def test_unknown_cluster():
    c = get_cluster("CLU99999")
    assert "error" in c

def test_get_cluster_members():
    m = get_cluster_members("CLU00604")
    assert "USR40970" in m["users"]
    assert "MCH6502" in m["merchants"]

def test_get_user():
    u = get_user("USR40970")
    assert u["user_id"] == "USR40970"
    
def test_get_merchant():
    m = get_merchant("MCH6502")
    assert m["merchant_id"] == "MCH6502"
    
def test_get_transaction():
    txns = get_user_transactions("USR40970")
    assert len(txns["transactions"]) > 0
    tid = txns["transactions"][0]["txn_id"]
    t = get_transaction(tid)
    assert t["txn_id"] == tid

def test_get_top_investigation_candidates():
    res = get_top_investigation_candidates("cluster", 3)
    assert len(res["candidates"]) == 3
    assert res["entity_type"] == "cluster"
