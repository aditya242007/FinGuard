"""FinGuard — UPI Fraud Ring & Merchant Risk Intelligence."""
import sys, pathlib
# Ensure project root is on sys.path for absolute imports
_project_root = pathlib.Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.append(str(_project_root))
