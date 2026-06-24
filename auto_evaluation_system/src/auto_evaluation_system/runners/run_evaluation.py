from auto_evaluation_system.bootstrap import setup_paths  # noqa: F401
"""RAG evaluation entry point. Runs full comparison suite."""
from auto_evaluation_system.runners.run_comparison import main

if __name__ == "__main__":
    main()
