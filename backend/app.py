from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from model import Inputs, baseline_estimate, load_benchmarks

ROOT = Path(__file__).parent

app = FastAPI(title="Rooted.ai API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

class PredictIn(BaseModel):
    province: Optional[str] = "ON"
    collections: Optional[float] = 0
    ebitda_or_sde: Optional[float] = 0
    equipped_ops: Optional[float] = 0
    sqft: Optional[float] = 0

@app.get("/api/health")
def health():
    return {"ok": True, "version": "1.0"}

@app.post("/api/predict")
def predict(body: PredictIn):
    x = Inputs(
        province=(body.province or "ON").upper(),
        collections=body.collections or 0,
        ebitda_or_sde=body.ebitda_or_sde or 0,
        equipped_ops=body.equipped_ops or 0,
        sqft=body.sqft or 0,
    )
    return baseline_estimate(x)

@app.get("/api/benchmarks")
def benchmarks(province: Optional[str] = None):
    df = load_benchmarks()
    if province:
        df = df[df["province"] == province.upper()]
    return {"rows": df.to_dict(orient="records")}

# ===== Scheduler & Scraper Integration =====
import os
from apscheduler.schedulers.background import BackgroundScheduler
from scrapers import run_all_scrapers

scheduler: BackgroundScheduler = None

def start_scheduler():
    global scheduler
    if scheduler: return
    scheduler = BackgroundScheduler(timezone="UTC")
    # Run every day at 02:00 UTC
    scheduler.add_job(run_all_scrapers, "cron", hour=2, minute=0, id="daily-scrape", replace_existing=True)
    scheduler.start()
    print("[SCHEDULER] Started daily broker scraping.")

@app.on_event("startup")
def _maybe_start_scheduler():
    # Guard so dev auto-reload doesn't start multiple schedulers
    if os.getenv("RUN_SCHEDULER", "0") == "1":
        start_scheduler()

@app.get("/api/scraped")
def scraped():
    import pandas as pd
    from pathlib import Path
    path = Path(__file__).parent / "data" / "scraped_listings.csv"
    if not path.exists():
        return {"rows": []}
    df = pd.read_csv(path)
    return {"rows": df.tail(200).to_dict(orient="records")}  # last 200 for brevity
