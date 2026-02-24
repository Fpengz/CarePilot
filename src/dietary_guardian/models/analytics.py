from pydantic import BaseModel


class EngagementMetrics(BaseModel):
    reminders_sent: int
    meal_confirmed_yes: int
    meal_confirmed_no: int
    meal_confirmation_rate: float
