# PowerPredict — Electricity Consumption Prediction

A responsive HTML/CSS/JavaScript dashboard with a FastAPI backend, MySQL storage, and a scikit-learn daily consumption forecasting model trained from the supplied household power dataset.

## Features
- Dashboard, Predict, Analytics, History, Insights and Settings pages.
- Prediction history saved to MySQL.
- Charts for forecast trends, day type and saved predictions.
- CSV export and history search/clear.
- Settings saved to MySQL; demo profile stored in the browser.
- Chunk-based training script for the large semicolon-separated dataset.
- FastAPI Swagger docs at `http://127.0.0.1:8000/docs`.

## Project structure
```text
powerpredict_project/
  frontend/
    index.html
    style.css
    app.js
  backend/
    app/
      main.py
      database.py
      models.py
      schemas.py
    data/                         # Put dataset here
    models/                       # Trained model saved here
    train_model.py
    requirements.txt
    .env.example
```

## 1. Install MySQL and create the database
Make sure MySQL Server is running. In MySQL Workbench, execute:
```sql
CREATE DATABASE powerpredict CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Remember your MySQL username and password.

## 2. Set up the backend (Windows / VS Code)
Open the `powerpredict_project` folder in VS Code. Open Terminal and run:
```powershell
cd backend
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```
Open `backend/.env` and replace `YOUR_MYSQL_PASSWORD` with your actual MySQL password. If your MySQL username isn't `root`, change it too. Do not commit `.env` to GitHub.

## 3. Put the dataset in the correct place
Copy the uploaded file `household_power_consumption(1).txt` to:
`backend/data/household_power_consumption.txt`

The file uses semicolon separators and `?` for missing values. The training script reads it in chunks, converts minute-level active power readings to daily kWh estimates, and makes a chronological holdout evaluation before refitting the final model on the available historical data.

## 4. Train the ML model
With the backend virtual environment activated and terminal in `backend/`:
```powershell
python train_model.py
```
The script saves:
- `models/consumption_model.joblib`
- `models/training_metrics.json`

The dataset is large, so training can take several minutes and needs enough free memory and disk space. Keep the terminal open until it says `Training complete`.

**Target/units note:** `Global_active_power` is recorded in kW at minute intervals. The script estimates daily kWh by summing valid minute readings and dividing by 60. Missing readings are ignored, so days with missing data may be underestimates. The provided dataset has no temperature, humidity or residential/commercial labels; those fields are not model inputs. Forecasts are estimates, not guaranteed real meter readings.

## 5. Start the FastAPI backend
From `backend/`:
```powershell
uvicorn app.main:app --reload
```
Visit `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/api/health`. The backend creates its MySQL tables on startup. If MySQL connection fails, check that the service is running, the database exists, and `.env` credentials are correct.

## 6. Start the frontend
Open a **second VS Code terminal** at the project root and run:
```powershell
cd frontend
py -m http.server 5500
```
Open `http://127.0.0.1:5500`. Keep both terminals running. The frontend calls `http://127.0.0.1:8000` by default. Chart.js and Google Fonts load from CDNs, so charts/fonts require internet access; core layout and forms are local.

Alternative: use the VS Code Live Server extension on `frontend/index.html`. If its port differs from 5500, add that origin to `CORS_ORIGINS` in `backend/.env` and restart FastAPI.

## 7. Verify the project
1. Check `/api/health` and confirm `model_trained` is `true` after training.
2. In the frontend, open Predict and create a forecast.
3. Confirm the result appears in Dashboard and History.
4. Open Analytics and Insights.
5. Change a preference in Settings and save it.
6. Export the history as CSV.

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API/model status |
| GET | `/api/dashboard` | Dashboard metrics and recent history |
| POST | `/api/predict` | Generate and save a forecast |
| GET | `/api/predictions?limit=100` | List saved predictions |
| DELETE | `/api/predictions` | Clear prediction history |
| PATCH | `/api/predictions/{id}/actual?actual_kwh=123` | Save an actual reading |
| GET | `/api/analytics` | Trend and day-type aggregates |
| GET | `/api/insights` | Insights from saved predictions |
| GET/PUT | `/api/settings` | Read/save app preferences |

## 8. GitHub (do not upload the raw dataset or secrets)
Create `backend/.gitignore` or use the root `.gitignore` below. Since the raw dataset is large and may have redistribution restrictions, keep it outside GitHub and place it locally for training. The trained model may also be excluded; teammates can run the training script on their own copy of the dataset.

```powershell
git init
git add .
git commit -m "Build PowerPredict electricity forecasting dashboard"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```
Replace the remote URL with your actual GitHub repository URL. Do not commit `.env`, `.venv`, the raw dataset, or private credentials.

## 9. Deployment overview
- Frontend: deploy `frontend/` as a static site (for example, GitHub Pages or a static hosting service). Set `API_BASE` in `frontend/app.js` to your deployed HTTPS backend URL before publishing.
- Backend: deploy the FastAPI app to a Python host that supports persistent environment variables and outbound database connections. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (adjust to the host's required port syntax).
- Database: use a hosted MySQL instance and set `DATABASE_URL` to its connection URL.
- Add your frontend URL to `CORS_ORIGINS` on the backend. Use HTTPS for both frontend and backend.
- Ensure `models/consumption_model.joblib` is deployed, or run `python train_model.py` during a suitable build/job step. Do not rely on an ephemeral filesystem for the database.

## Limitations
This is a college-project starter, not a production energy-management system. There is no login/authentication or multi-user isolation. The Settings profile is browser-local, while preferences and predictions are stored in MySQL. Forecast accuracy must be evaluated using the included holdout metrics; it is not represented as a fixed accuracy percentage. The fallback predictor is only used if the trained model file is missing.
