"""Runtime schedulers package.

Houses long-running loop entry points for background worker processes.
These modules own process-level behavior (sleep intervals, restart logic) and
delegate all business logic to application-layer use cases.
"""

from dietary_guardian.runtime.schedulers.reminder_scheduler import (
    ReminderSchedulerRunResult,
    run_reminder_scheduler_loop,
    run_reminder_scheduler_once,
)

__all__ = [
    "ReminderSchedulerRunResult",
    "run_reminder_scheduler_loop",
    "run_reminder_scheduler_once",
]
