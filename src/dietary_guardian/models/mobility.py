from pydantic import BaseModel


class MobilityReminderSettings(BaseModel):
    user_id: str
    enabled: bool = False
    interval_minutes: int = 120
    active_start_time: str = "08:00"
    active_end_time: str = "20:00"
    updated_at: str | None = None
