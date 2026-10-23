from datetime import date
from pydantic import BaseModel, Field

class PredictionInput(BaseModel):
    prediction_date: date
    previous_day_kwh: float = Field(ge=0, le=100000)
    day_type: str = 'Weekday'
    temperature: float | None = None
    humidity: float | None = None

class PredictionOutput(BaseModel):
    id: int
    prediction_date: date
    day_type: str
    previous_day_kwh: float
    predicted_kwh: float
    actual_kwh: float | None = None

class SettingUpdate(BaseModel):
    theme: str = 'Dark'
    chart_style: str = 'Line & Bar'
    language: str = 'English'
    notifications: bool = True
