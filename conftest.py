"""Test configuration to ensure src package is importable."""
import sys, pathlib
_repo_root = pathlib.Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.append(str(_repo_root))
