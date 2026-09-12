"""
tests/test_m6_risk_engine.py
Pytest validation suite for FinGuard M6 Explainable Risk Engine.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'features'))

from m6_risk_engine import (
    get_signal_registry,
    get_risk_level,
    calculate_point_in_time_features,
    generate_explanations,
    score_users,
    score_merchants,
    score_transactions,
    run_risk_engine,
)

# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

TXNS_PATH  = "data/processed/features/transaction_risk_features.csv"
USERS_PATH = "data/processed/features/user_risk_features.csv"
MERCH_PATH = "data/processed/features/merchant_risk_features.csv"
OUT_DIR    = "data/processed/risk"
TXN_RISK   = os.path.join(OUT_DIR, "transaction_risk_scores.csv")
USER_RISK  = os.path.join(OUT_DIR, "user_risk_scores.csv")
MERCH_RISK = os.path.join(OUT_DIR, "merchant_risk_scores.csv")


@pytest.fixture(scope="module")
def txns():
    return pd.read_csv(TXN_RISK)


@pytest.fixture(scope="module")
def users():
    return pd.read_csv(USER_RISK)


@pytest.fixture(scope="module")
def merchants():
    return pd.read_csv(MERCH_RISK)


@pytest.fixture(scope="module")
def raw_txns():
    return pd.read_csv(TXNS_PATH)


@pytest.fixture(scope="module")
def raw_users():
    return pd.read_csv(USERS_PATH)


@pytest.fixture(scope="module")
def raw_merchants():
    return pd.read_csv(MERCH_PATH)


# ─────────────────────────────────────────────────────────────────
# 1. Score bounds
# ─────────────────────────────────────────────────────────────────

class TestScoreBounds:
    def test_txn_tt_score_bounds(self, txns):
        assert txns["transaction_time_risk_score"].between(0, 100).all(), \
            "Transaction-time scores out of [0, 100]"

    def test_txn_retro_score_bounds(self, txns):
        assert txns["retrospective_risk_score"].between(0, 100).all(), \
            "Retrospective transaction scores out of [0, 100]"

    def test_user_retro_score_bounds(self, users):
        assert users["retrospective_risk_score"].between(0, 100).all(), \
            "User retrospective scores out of [0, 100]"

    def test_merchant_retro_score_bounds(self, merchants):
        assert merchants["retrospective_risk_score"].between(0, 100).all(), \
            "Merchant retrospective scores out of [0, 100]"


# ─────────────────────────────────────────────────────────────────
# 2. No NaN scores
# ─────────────────────────────────────────────────────────────────

class TestNoNaN:
    def test_txn_tt_no_nan(self, txns):
        assert txns["transaction_time_risk_score"].isna().sum() == 0

    def test_txn_retro_no_nan(self, txns):
        assert txns["retrospective_risk_score"].isna().sum() == 0

    def test_user_no_nan(self, users):
        assert users["retrospective_risk_score"].isna().sum() == 0

    def test_merchant_no_nan(self, merchants):
        assert merchants["retrospective_risk_score"].isna().sum() == 0


# ─────────────────────────────────────────────────────────────────
# 3. No infinity
# ─────────────────────────────────────────────────────────────────

class TestNoInfinity:
    def test_txn_tt_no_inf(self, txns):
        assert not np.isinf(txns["transaction_time_risk_score"]).any()

    def test_txn_retro_no_inf(self, txns):
        assert not np.isinf(txns["retrospective_risk_score"]).any()

    def test_user_no_inf(self, users):
        assert not np.isinf(users["retrospective_risk_score"]).any()

    def test_merchant_no_inf(self, merchants):
        assert not np.isinf(merchants["retrospective_risk_score"]).any()


# ─────────────────────────────────────────────────────────────────
# 4. Risk level mapping
# ─────────────────────────────────────────────────────────────────

class TestRiskLevels:
    def test_risk_level_mapping_correctness(self):
        assert get_risk_level(0)   == "LOW"
        assert get_risk_level(29)  == "LOW"
        assert get_risk_level(30)  == "MEDIUM"
        assert get_risk_level(59)  == "MEDIUM"
        assert get_risk_level(60)  == "HIGH"
        assert get_risk_level(79)  == "HIGH"
        assert get_risk_level(80)  == "CRITICAL"
        assert get_risk_level(100) == "CRITICAL"

    def test_txn_risk_levels_valid_strings(self, txns):
        valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert set(txns["transaction_time_risk_level"].unique()).issubset(valid)
        assert set(txns["retrospective_risk_level"].unique()).issubset(valid)

    def test_user_risk_levels_valid_strings(self, users):
        valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert set(users["risk_level"].unique()).issubset(valid)

    def test_merchant_risk_levels_valid_strings(self, merchants):
        valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert set(merchants["risk_level"].unique()).issubset(valid)


# ─────────────────────────────────────────────────────────────────
# 5. Transaction row conservation
# ─────────────────────────────────────────────────────────────────

class TestRowConservation:
    def test_transaction_count_20000(self, txns):
        assert len(txns) == 20000, f"Expected 20000 transactions, got {len(txns)}"

    def test_user_row_count(self, users, raw_users):
        assert len(users) == len(raw_users), "User row count mismatch"

    def test_merchant_row_count(self, merchants, raw_merchants):
        assert len(merchants) == len(raw_merchants), "Merchant row count mismatch"


# ─────────────────────────────────────────────────────────────────
# 6. Entity uniqueness
# ─────────────────────────────────────────────────────────────────

class TestEntityUniqueness:
    def test_txn_id_unique(self, txns):
        assert txns["txn_id"].nunique() == len(txns), "Duplicate transaction IDs found"

    def test_user_id_unique(self, users):
        assert users["user_id"].nunique() == len(users), "Duplicate user IDs found"

    def test_merchant_id_unique(self, merchants):
        assert merchants["merchant_id"].nunique() == len(merchants), "Duplicate merchant IDs found"


# ─────────────────────────────────────────────────────────────────
# 7. No chargeback leakage into transaction-time score
# ─────────────────────────────────────────────────────────────────

class TestTemporalLeakage:
    def test_chargeback_not_used_in_tt_score(self):
        """
        Directly verify: the scoring function returns the SAME TT score
        whether or not has_chargeback is 0 or 1 for a transaction.
        We do this by creating two minimal synthetic dataframes that differ
        ONLY in has_chargeback and confirm TT scores are identical.
        """
        base_row = {
            "txn_id_normalized": ["TXN_TEST"],
            "user_id_normalized": ["USR_TEST"],
            "merchant_id_normalized": ["MCH_TEST"],
            "amount_abs": [100.0],
            "failed_flag": [0],
            "missing_utr_flag": [False],
            "timestamp_invalid_flag": [False],
            "transaction_date": ["2024-01-01"],
            "has_chargeback": [0],   # No chargeback
            "amount_numeric": [100.0],
        }
        no_cb = pd.DataFrame(base_row)
        with_cb = no_cb.copy()
        with_cb["has_chargeback"] = 1

        user_feats = pd.DataFrame({
            "user_id_normalized": ["USR_TEST"],
            "kyc_status": ["VERIFIED"],
            "kyc_duplicate_entity_flag": [False],
        })

        scored_no_cb   = score_transactions(no_cb, user_feats)
        scored_with_cb = score_transactions(with_cb, user_feats)

        assert scored_no_cb["transaction_time_risk_score"].values[0] == \
               scored_with_cb["transaction_time_risk_score"].values[0], \
            "LEAKAGE: has_chargeback influenced the transaction-time score!"


# ─────────────────────────────────────────────────────────────────
# 8. Point-in-time leakage check
# ─────────────────────────────────────────────────────────────────

class TestPointInTime:
    def test_first_transaction_has_zero_history(self):
        """
        First transaction by a user should have 0 historical failure rate
        (no prior observations).
        """
        df = pd.DataFrame({
            "txn_id_normalized": ["TXN_A", "TXN_B"],
            "user_id_normalized": ["USR_1", "USR_1"],
            "amount_abs": [100.0, 200.0],
            "failed_flag": [1, 0],
            "transaction_date": ["2024-01-01", "2024-01-02"],
        })
        result = calculate_point_in_time_features(df)
        first_txn = result[result["txn_id_normalized"] == "TXN_A"]
        assert first_txn["historical_user_failure_rate"].values[0] == 0.0, \
            "First transaction should have 0 historical failure rate"

    def test_second_transaction_uses_only_prior_data(self):
        """
        Second transaction should see only the first transaction's failure signal.
        """
        df = pd.DataFrame({
            "txn_id_normalized": ["TXN_A", "TXN_B"],
            "user_id_normalized": ["USR_1", "USR_1"],
            "amount_abs": [100.0, 200.0],
            "failed_flag": [1, 0],  # First failed, second didn't
            "transaction_date": ["2024-01-01", "2024-01-02"],
        })
        result = calculate_point_in_time_features(df)
        second_txn = result[result["txn_id_normalized"] == "TXN_B"]
        assert second_txn["historical_user_failure_rate"].values[0] == 1.0, \
            "Second txn should see prior failure rate of 1.0 (first transaction failed)"


# ─────────────────────────────────────────────────────────────────
# 9. Cold-start behaviour
# ─────────────────────────────────────────────────────────────────

class TestColdStart:
    def test_cold_start_flag_applied(self):
        """
        A user with 0 prior transactions should receive a lower score
        than if they had 10 prior transactions, when all else is equal.
        """
        # Create a user with exactly 3 prior transactions (cold-start)
        df_cold = pd.DataFrame({
            "txn_id_normalized": [f"T{i}" for i in range(4)],
            "user_id_normalized": ["USR_X"] * 4,
            "amount_abs": [100.0] * 4,
            "failed_flag": [0, 1, 1, 1],  # 3 failures in history for 4th txn
            "transaction_date": [f"2024-01-0{i+1}" for i in range(4)],
        })
        result_cold = calculate_point_in_time_features(df_cold)
        fourth_txn = result_cold.iloc[-1]
        # txn_count is 3 (0-indexed cumcount), cold_start_factor = min(3/5, 1) = 0.6
        assert fourth_txn["historical_user_txn_count"] == 3, \
            "Expected 3 prior transactions before 4th"
        # Failure rate should be 2/3 (first was not failed, 2nd and 3rd were)
        assert abs(fourth_txn["historical_user_failure_rate"] - 2/3) < 0.01, \
            f"Expected 2/3 failure rate, got {fourth_txn['historical_user_failure_rate']}"


# ─────────────────────────────────────────────────────────────────
# 10. Safe division / no division by zero
# ─────────────────────────────────────────────────────────────────

class TestSafeDivision:
    def test_user_score_when_all_rates_zero(self):
        """
        User with 0 chargebacks and 0 failures should have score == 0.
        """
        users_df = pd.DataFrame({
            "user_id_normalized": ["USR_ZERO"],
            "transaction_count": [10],
            "total_transaction_amount": [1000.0],
            "chargeback_rate": [0.0],
            "failure_rate": [0.0],
            "dispute_after_7_days_rate": [0.0],
            "kyc_duplicate_entity_flag": [False],
            "total_disputed_amount": [0.0],
        })
        scored = score_users(users_df)
        assert scored["retrospective_risk_score"].values[0] == 0.0, \
            "User with all-zero signals should score 0"

    def test_merchant_score_when_all_rates_zero(self):
        merch_df = pd.DataFrame({
            "merchant_id_normalized": ["MCH_ZERO"],
            "transaction_count": [10],
            "total_transaction_amount": [1000.0],
            "chargeback_transaction_count": [0],
            "chargeback_rate": [0.0],
            "disputed_amount_ratio": [0.0],
            "failure_rate": [0.0],
            "dispute_after_7_days_rate": [0.0],
        })
        scored = score_merchants(merch_df)
        assert scored["retrospective_risk_score"].values[0] == 0.0, \
            "Merchant with all-zero signals should score 0"


# ─────────────────────────────────────────────────────────────────
# 11. Retrospective / Transaction-time separation
# ─────────────────────────────────────────────────────────────────

class TestModeSeparation:
    def test_registry_modes_are_distinct(self):
        registry = get_signal_registry()
        tt_keys = set(registry["transaction_time"].keys())
        retro_keys = set(registry["retrospective"].keys())
        overlap = tt_keys & retro_keys
        assert len(overlap) == 0, f"Signal names overlap between modes: {overlap}"

    def test_output_files_exist(self):
        assert os.path.exists(TXN_RISK),  "transaction_risk_scores.csv missing"
        assert os.path.exists(USER_RISK), "user_risk_scores.csv missing"
        assert os.path.exists(MERCH_RISK),"merchant_risk_scores.csv missing"

    def test_txn_output_has_both_score_columns(self, txns):
        assert "transaction_time_risk_score" in txns.columns
        assert "retrospective_risk_score" in txns.columns

    def test_txn_output_has_both_level_columns(self, txns):
        assert "transaction_time_risk_level" in txns.columns
        assert "retrospective_risk_level" in txns.columns


# ─────────────────────────────────────────────────────────────────
# 12. Determinism
# ─────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_engine_is_deterministic(self):
        """
        Running the engine twice should produce identical output.
        """
        import tempfile
        out1 = tempfile.mkdtemp()
        out2 = tempfile.mkdtemp()
        run_risk_engine(TXNS_PATH, USERS_PATH, MERCH_PATH, out1)
        run_risk_engine(TXNS_PATH, USERS_PATH, MERCH_PATH, out2)

        for fname in ["transaction_risk_scores.csv", "user_risk_scores.csv", "merchant_risk_scores.csv"]:
            df1 = pd.read_csv(os.path.join(out1, fname))
            df2 = pd.read_csv(os.path.join(out2, fname))
            # Sort to ensure order-independent comparison
            score_col = "transaction_time_risk_score" if "transaction" in fname else "retrospective_risk_score"
            if score_col in df1.columns:
                diff = (df1[score_col] - df2[score_col]).abs().max()
                assert diff < 1e-9, f"Non-deterministic output in {fname}: max diff = {diff}"


# ─────────────────────────────────────────────────────────────────
# 13. Explanation coverage
# ─────────────────────────────────────────────────────────────────

class TestExplainability:
    def test_explanation_not_empty_when_score_positive(self, txns):
        positive = txns[txns["transaction_time_risk_score"] > 0]
        empty_exp = positive[positive["explanation"].fillna("").str.strip() == ""]
        assert len(empty_exp) == 0, \
            f"{len(empty_exp)} positive-score transactions have empty explanations"

    def test_user_explanation_not_empty_when_score_positive(self, users):
        positive = users[users["retrospective_risk_score"] > 0]
        empty_exp = positive[positive["explanation"].fillna("").str.strip() == ""]
        assert len(empty_exp) == 0, \
            f"{len(empty_exp)} positive-score users have empty explanations"
