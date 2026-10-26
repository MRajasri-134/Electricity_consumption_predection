from datetime import date, timedelta
from pathlib import Path
import os
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .database import Base, engine, get_db
from .models import Prediction, AppSetting
from .schemas import PredictionInput, SettingUpdate

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / 'models' / 'consumption_model.joblib'
app = FastAPI(title='PowerPredict API', version='1.0.0', description='Electricity consumption forecasting and analytics API')
origins = os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:8000').split(',')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        defaults = {'theme':'Dark','chart_style':'Line & Bar','language':'English','notifications':'true'}
        for key, value in defaults.items():
            if not db.scalar(select(AppSetting).where(AppSetting.setting_key == key)):
                db.add(AppSetting(setting_key=key, setting_value=value))
        db.commit()

def model_bundle():
    if MODEL_PATH.exists():
        try: return joblib.load(MODEL_PATH)
        except Exception: pass
    return None

def predict_kwh(day: date, previous: float, db: Session) -> float:
    bundle = model_bundle()
    dow, month = day.weekday(), day.month
    recent = db.scalars(select(Prediction).where(Prediction.prediction_date < day).order_by(Prediction.prediction_date.desc()).limit(7)).all()
    recent_values = [x.predicted_kwh for x in recent]
    rolling = float(np.mean(recent_values)) if recent_values else previous
    features = pd.DataFrame([{'day_of_week':dow,'month':month,'day_of_month':day.day,'previous_day_kwh':previous,'rolling_7day_kwh':rolling}])
    if bundle and 'model' in bundle:
        result = float(bundle['model'].predict(features)[0])
    else:
        # Clearly marked fallback until the provided dataset has been used to train the model.
        result = previous * (1.04 if dow in (4,5) else 0.98)
    return round(max(0.0, result), 2)

def row_dict(row):
    return {'id':row.id,'prediction_date':row.prediction_date.isoformat(),'day_type':row.day_type,'previous_day_kwh':round(row.previous_day_kwh,2),'predicted_kwh':round(row.predicted_kwh,2),'actual_kwh':round(row.actual_kwh,2) if row.actual_kwh is not None else None,'created_at':row.created_at.isoformat() if row.created_at else None}

@app.get('/')
def root(): return {'name':'PowerPredict API','status':'online','docs':'/docs'}
@app.get('/api/health')
def health(): return {'status':'ok','model_trained':MODEL_PATH.exists(),'model_path':str(MODEL_PATH)}

@app.post('/api/predict')
def create_prediction(payload: PredictionInput, db: Session = Depends(get_db)):
    predicted = predict_kwh(payload.prediction_date, payload.previous_day_kwh, db)
    row = Prediction(prediction_date=payload.prediction_date, day_type=payload.day_type, previous_day_kwh=payload.previous_day_kwh, predicted_kwh=predicted)
    db.add(row); db.commit(); db.refresh(row)
    return {**row_dict(row), 'model_trained':MODEL_PATH.exists(), 'note': 'Temperature and humidity are accepted for the form but are not model features because they are absent from the supplied dataset.'}

@app.get('/api/predictions')
def list_predictions(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.scalars(select(Prediction).order_by(Prediction.prediction_date.desc(), Prediction.id.desc()).limit(min(max(limit,1),500))).all()
    return [row_dict(x) for x in rows]

@app.delete('/api/predictions')
def clear_predictions(db: Session = Depends(get_db)):
    db.query(Prediction).delete(); db.commit(); return {'message':'Prediction history cleared'}

@app.patch('/api/predictions/{prediction_id}/actual')
def add_actual(prediction_id: int, actual_kwh: float, db: Session = Depends(get_db)):
    row = db.get(Prediction, prediction_id)
    if not row: raise HTTPException(404, 'Prediction not found')
    if actual_kwh < 0: raise HTTPException(400, 'Actual consumption cannot be negative')
    row.actual_kwh = actual_kwh; db.commit(); db.refresh(row); return row_dict(row)

@app.get('/api/dashboard')
def dashboard(db: Session = Depends(get_db)):
    rows = db.scalars(select(Prediction).order_by(Prediction.prediction_date.desc()).limit(30)).all()
    all_count = db.scalar(select(func.count(Prediction.id))) or 0
    avg = db.scalar(select(func.avg(Prediction.predicted_kwh))) or 0
    latest = rows[0].predicted_kwh if rows else 0
    return {'total_predictions':all_count,'average_prediction_kwh':round(float(avg),2),'latest_prediction_kwh':round(float(latest),2),'model_trained':MODEL_PATH.exists(),'history':[row_dict(r) for r in reversed(rows)]}

@app.get('/api/analytics')
def analytics(db: Session = Depends(get_db)):
    rows = db.scalars(select(Prediction).order_by(Prediction.prediction_date.asc()).limit(500)).all()
    return {'trend':[{'date':r.prediction_date.isoformat(),'predicted_kwh':r.predicted_kwh,'actual_kwh':r.actual_kwh} for r in rows], 'by_day_type':[{'day_type':name,'count':sum(1 for r in rows if r.day_type==name),'average_kwh':round(float(np.mean([r.predicted_kwh for r in rows if r.day_type==name])),2) if any(r.day_type==name for r in rows) else 0} for name in ['Weekday','Weekend']], 'count':len(rows)}

@app.get('/api/insights')
def insights(db: Session = Depends(get_db)):
    rows = db.scalars(select(Prediction).order_by(Prediction.prediction_date.desc()).limit(30)).all()
    if not rows: return {'items':[{'title':'Start with a prediction','detail':'Run your first forecast to begin building personalized consumption insights.','kind':'info'}]}
    values=[r.predicted_kwh for r in rows]
    newest=values[0]; avg=float(np.mean(values)); high=max(rows,key=lambda r:r.predicted_kwh)
    return {'items':[{'title':'Latest forecast','detail':f'Your latest prediction is {newest:.2f} kWh.','kind':'success' if newest<=avg else 'warning'},{'title':'Highest predicted day','detail':f'{high.prediction_date.isoformat()} has the highest saved prediction at {high.predicted_kwh:.2f} kWh.','kind':'warning'},{'title':'Recent average','detail':f'The average of the latest {len(values)} saved forecasts is {avg:.2f} kWh.','kind':'info'}]}

@app.get('/api/settings')
def get_settings(db: Session = Depends(get_db)):
    return {r.setting_key:(r.setting_value.lower()=='true' if r.setting_key=='notifications' else r.setting_value) for r in db.scalars(select(AppSetting)).all()}

@app.put('/api/settings')
def save_settings(payload: SettingUpdate, db: Session = Depends(get_db)):
    values={'theme':payload.theme,'chart_style':payload.chart_style,'language':payload.language,'notifications':str(payload.notifications).lower()}
    for key,value in values.items():
        row=db.scalar(select(AppSetting).where(AppSetting.setting_key==key))
        if row: row.setting_value=str(value)
        else: db.add(AppSetting(setting_key=key,setting_value=str(value)))
    db.commit(); return get_settings(db)
