import os
import shutil
from pathlib import Path

def main():
    print("Preparing data for M8 Dashboard...")
    
    # Source paths
    base_dir = Path("data/processed")
    src_files = [
        base_dir / "finguard_transactions.csv",
        base_dir / "users_analytics.csv",
        base_dir / "merchants_analytics.csv",
        base_dir / "chargebacks_aggregated.csv",
        base_dir / "features" / "transaction_risk_features.csv",
        base_dir / "features" / "user_risk_features.csv",
        base_dir / "features" / "merchant_risk_features.csv",
        base_dir / "features" / "chargeback_risk_features.csv",
        base_dir / "risk" / "transaction_risk_scores.csv",
        base_dir / "risk" / "user_risk_scores.csv",
        base_dir / "risk" / "merchant_risk_scores.csv",
        base_dir / "graph" / "suspicious_clusters.csv",
        base_dir / "graph" / "cluster_members.csv",
        base_dir / "graph" / "user_merchant_relationships.csv"
    ]
    
    # Destination path
    dest_dir = Path("dashboard/public/data")
    os.makedirs(dest_dir, exist_ok=True)
    
    for f in src_files:
        if f.exists():
            dest_file = dest_dir / f.name
            shutil.copy2(f, dest_file)
            print(f"Copied {f.name} to {dest_dir}/")
        else:
            print(f"WARNING: Source file not found: {f}")
            
    print("Dashboard data preparation complete.")

if __name__ == "__main__":
    main()
