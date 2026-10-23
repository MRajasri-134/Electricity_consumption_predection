"""Train a daily household-consumption forecasting model from the supplied semicolon TXT file.
Processes the large file in chunks and saves a scikit-learn model plus evaluation metrics.
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE = Path(__file__).resolve().parent
FEATURES = ['day_of_week','month','day_of_month','previous_day_kwh','rolling_7day_kwh']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data', default=str(BASE/'data'/'household_power_consumption.txt'))
    parser.add_argument('--chunksize',type=int,default=100_000)
    args=parser.parse_args(); path=Path(args.data)
    if not path.exists(): raise SystemExit(f'Dataset not found: {path}\nCopy household_power_consumption(1).txt into backend/data/household_power_consumption.txt')
    daily_parts=[]
    print(f'Reading {path} in chunks...')
    for i,chunk in enumerate(pd.read_csv(path,sep=';',na_values=['?'],chunksize=args.chunksize,low_memory=False)):
        chunk['Global_active_power']=pd.to_numeric(chunk['Global_active_power'],errors='coerce')
        chunk['Date']=pd.to_datetime(chunk['Date'],format='%d/%m/%Y',errors='coerce')
        chunk=chunk.dropna(subset=['Date','Global_active_power'])
        # The power reading is in kW at one-minute intervals; sum kW readings / 60 = daily kWh.
        part=chunk.groupby('Date')['Global_active_power'].agg(['sum','count']).reset_index()
        part['energy_kwh']=part['sum']/60.0
        daily_parts.append(part[['Date','energy_kwh','count']])
        if (i+1)%5==0: print(f'  processed {i+1} chunks')
    if not daily_parts: raise SystemExit('No valid rows were found in the dataset.')
    combined=pd.concat(daily_parts,ignore_index=True).groupby('Date').agg({'energy_kwh':'sum','count':'sum'}).sort_index().reset_index()
    # The file may split a day across chunks. Summing each chunk's daily energy correctly handles this.
    combined['day_of_week']=combined['Date'].dt.dayofweek
    combined['month']=combined['Date'].dt.month
    combined['day_of_month']=combined['Date'].dt.day
    combined['previous_day_kwh']=combined['energy_kwh'].shift(1)
    combined['rolling_7day_kwh']=combined['energy_kwh'].shift(1).rolling(7,min_periods=1).mean()
    data=combined.dropna(subset=FEATURES+['energy_kwh']).copy()
    if len(data)<30: raise SystemExit(f'Only {len(data)} usable daily records; need at least 30.')
    split=max(int(len(data)*0.8),1)
    train,test=data.iloc[:split],data.iloc[split:]
    model=RandomForestRegressor(n_estimators=180,max_depth=12,min_samples_leaf=2,random_state=42,n_jobs=-1)
    model.fit(train[FEATURES],train['energy_kwh'])
    if len(test):
        pred=model.predict(test[FEATURES]); metrics={'mae_kwh':float(mean_absolute_error(test['energy_kwh'],pred)),'rmse_kwh':float(np.sqrt(mean_squared_error(test['energy_kwh'],pred))),'r2':float(r2_score(test['energy_kwh'],pred)) if len(test)>1 else None,'test_days':int(len(test))}
    else: metrics={'mae_kwh':None,'rmse_kwh':None,'r2':None,'test_days':0}
    # Refit on all valid historical records for the deployed model after time-ordered evaluation.
    model.fit(data[FEATURES],data['energy_kwh'])
    model_dir=BASE/'models'; model_dir.mkdir(exist_ok=True)
    joblib.dump({'model':model,'features':FEATURES,'metrics':metrics,'training_days':int(len(data)),'date_start':str(data['Date'].min().date()),'date_end':str(data['Date'].max().date()),'target':'daily kWh estimated from Global_active_power'},model_dir/'consumption_model.joblib')
    (model_dir/'training_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(f"Training complete: {len(data)} days ({data['Date'].min().date()} to {data['Date'].max().date()})")
    print('Evaluation (chronological holdout):',json.dumps(metrics,indent=2))
    print('Saved model:',model_dir/'consumption_model.joblib')
if __name__=='__main__': main()
