"""Detection & trajectory modeling — GDM, TRS, MIS."""

from auto_evaluation_system.detection.goal_drift import run_gdm_baseline
from auto_evaluation_system.detection.memory_integrity import run_mis_baseline
from auto_evaluation_system.detection.trajectory_risk import run_trs_baseline

__all__ = ["run_gdm_baseline", "run_mis_baseline", "run_trs_baseline"]
