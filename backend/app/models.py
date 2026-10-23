from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Boolean, func
from .database import Base

class Prediction(Base):
    __tablename__ = 'predictions'
    id = Column(Integer, primary_key=True, index=True)
    prediction_date = Column(Date, nullable=False, index=True)
    day_type = Column(String(20), nullable=False, default='Weekday')
    previous_day_kwh = Column(Float, nullable=False, default=0)
    predicted_kwh = Column(Float, nullable=False)
    actual_kwh = Column(Float, nullable=True)
    model_version = Column(String(40), default='RandomForest daily forecast')
    created_at = Column(DateTime, server_default=func.now())

class AppSetting(Base):
    __tablename__ = 'app_settings'
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(80), unique=True, nullable=False)
    setting_value = Column(String(255), nullable=False)
