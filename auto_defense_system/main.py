import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))

if __name__ == "__main__":
    import runpy
    runpy.run_path(str(_ROOT / "apps" / "cli.py"), run_name="__main__")
