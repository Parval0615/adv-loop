import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Streamlit entry: streamlit run app.py (re-exports apps/web.py)
from apps.web import *  # noqa: F401, F403
