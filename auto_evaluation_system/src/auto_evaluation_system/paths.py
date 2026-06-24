"""Shared data paths for evaluation scripts."""
from pathlib import Path

SYSTEM_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = SYSTEM_ROOT / "auto_evaluation_system"
DATA_DIR = PROJECT_ROOT / "data"
BENCHMARK_DIR = DATA_DIR / "benchmarks"
POISON_PDFS_DIR = DATA_DIR / "poison" / "pdfs"
POISON_RESULTS_DIR = DATA_DIR / "poison" / "results"
EXPERIMENTS_DIR = DATA_DIR / "experiments"
DATASETS_DIR = DATA_DIR / "datasets"
REPORTS_DIR = PROJECT_ROOT / "reports"
ASSETS_PDFS_DIR = PROJECT_ROOT / "assets" / "pdfs"
