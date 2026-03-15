"""
Run the reminder scheduler loop.

This entrypoint executes the scheduling loop used to enqueue reminder
notifications on a cadence.
"""

import asyncio

from care_pilot.platform.scheduling import run_reminder_scheduler_loop


def main() -> None:
    asyncio.run(run_reminder_scheduler_loop())


if __name__ == "__main__":
    main()
