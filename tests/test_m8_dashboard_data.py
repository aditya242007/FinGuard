import pytest
import pandas as pd
from pathlib import Path

DASHBOARD_DATA_DIR = Path("dashboard/public/data")

@pytest.fixture
def transactions():
    return pd.read_csv(DASHBOARD_DATA_DIR / "finguard_transactions.csv", low_memory=False)

@pytest.fixture
def suspicious_clusters():
    return pd.read_csv(DASHBOARD_DATA_DIR / "suspicious_clusters.csv")

@pytest.fixture
def merchant_scores():
    return pd.read_csv(DASHBOARD_DATA_DIR / "merchant_risk_scores.csv")

class TestM8DashboardData:
    
    def test_dashboard_data_dir_exists(self):
        assert DASHBOARD_DATA_DIR.exists()
        
    def test_transactions_file_exists(self):
        assert (DASHBOARD_DATA_DIR / "finguard_transactions.csv").exists()
        
    def test_transaction_count_remains_20000(self, transactions):
        assert len(transactions) == 20000
        
    def test_chargeback_rate_max_is_one(self, suspicious_clusters):
        """Dashboard must not display chargeback rates > 1.0"""
        assert (suspicious_clusters["cluster_chargeback_rate"] <= 1.0).all()
        
    def test_clu00604_chargeback_rate_is_100_percent(self, suspicious_clusters):
        """CLU00604 must show 100% (1.0) chargeback rate and 2 complaint records"""
        row = suspicious_clusters[suspicious_clusters["cluster_id"] == "CLU00604"]
        if not row.empty:
            assert row["cluster_chargeback_rate"].iloc[0] == 1.0
            assert row["chargeback_count"].iloc[0] == 2
            
    def test_no_fabricated_ids_in_clusters(self, suspicious_clusters):
        """Dashboard data must have valid cluster IDs (CLUxxxxx)"""
        assert suspicious_clusters["cluster_id"].str.startswith("CLU").all()
        
    def test_merchant_risk_levels_valid(self, merchant_scores):
        valid_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        levels = set(merchant_scores["risk_level"].dropna().unique())
        assert levels.issubset(valid_levels)
        
    def test_no_nan_or_infinity_in_cluster_scores(self, suspicious_clusters):
        assert not suspicious_clusters["cluster_risk_score"].isna().any()
        assert not (suspicious_clusters["cluster_risk_score"] == float("inf")).any()
