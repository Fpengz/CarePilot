import asyncio

from dietary_guardian.infrastructure.schedulers.reminder_scheduler import run_reminder_scheduler_loop


def main() -> None:
    asyncio.run(run_reminder_scheduler_loop())


if __name__ == "__main__":
    main()
