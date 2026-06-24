"""Out-of-band telemetry — trajectory capture decoupled from execution."""

from auto_evaluation_system.telemetry.emitter import TelemetryStepEmitter
from auto_evaluation_system.telemetry.recorder import TrajectoryRecorder

__all__ = [
    "TelemetryStepEmitter",
    "TrajectoryRecorder",
]
