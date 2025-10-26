from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from .roi import scrape as scrape_roi
from .tierthree import scrape as scrape_tierthree
from .mbc import scrape as scrape_mbc

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

SCRAPED_CSV = DATA_DIR / "scraped_listings.csv"
APPRAISAL_CSV = DATA_DIR / "appraisal_dataset.csv"

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _to_df(rows):
    if not rows:
        return pd.DataFrame(columns=[
            "broker","title","url","province","asking_price","collections",
            "ebitda_or_sde","equipped_ops","sqft","appraised_value","scraped_at"
        ])
    df = pd.DataFrame(rows)
    if "scraped_at" not in df.columns:
        df["scraped_at"] = _now_iso()
    for col in ["broker","title","url","province","asking_price","collections",
                "ebitda_or_sde","equipped_ops","sqft","appraised_value","scraped_at"]:
        if col not in df.columns:
            df[col] = pd.NA
    return df

def run_all_scrapers():
    frames = []
    for name, fn in [("ROI", scrape_roi), ("TierThree", scrape_tierthree), ("MBC", scrape_mbc)]:
        try:
            rows = fn()
            frames.append(_to_df(rows))
        except Exception as e:
            print(f"[SCRAPER] {name} error: {e}")

    if not frames:
        return {"added": 0, "total": 0}

    big = pd.concat(frames, ignore_index=True)
    if "url" in big.columns:
        big = big.drop_duplicates(subset=["url"], keep="last")

    cols_order = ["broker","title","url","province","asking_price","collections",
                  "ebitda_or_sde","equipped_ops","sqft","scraped_at","appraised_value"]
    for c in cols_order:
        if c not in big.columns:
            big[c] = pd.NA
    big = big.loc[:, cols_order]
    big.to_csv(SCRAPED_CSV, index=False)

    keep_cols = [c for c in ["province","collections","ebitda_or_sde","equipped_ops","sqft","appraised_value"] if c in big.columns]
    use = big.loc[:, keep_cols].copy()

    for c in ["collections","ebitda_or_sde","equipped_ops","sqft","appraised_value"]:
        if c in use.columns:
            use[c] = pd.to_numeric(use[c], errors="coerce")

    if use.shape[0]:
        all_null = use.drop(columns=[c for c in ["province"] if c in use.columns])
        use = use.loc[~all_null.isna().all(axis=1)].copy()

    if APPRAISAL_CSV.exists():
        prev = pd.read_csv(APPRAISAL_CSV)
        for c in set(use.columns) - set(prev.columns):
            prev[c] = pd.NA
        for c in set(prev.columns) - set(use.columns):
            use[c] = pd.NA
        combined = pd.concat([prev[use.columns], use], ignore_index=True)
        dedup_keys = [k for k in ["province","collections","ebitda_or_sde","equipped_ops","sqft","appraised_value"] if k in combined.columns]
        if dedup_keys:
            combined = combined.drop_duplicates(subset=dedup_keys, keep="last")
        combined.to_csv(APPRAISAL_CSV, index=False)
        added = max(0, combined.shape[0] - prev.shape[0])
        total = combined.shape[0]
        return {"added": added, "total": total}
    else:
        use.to_csv(APPRAISAL_CSV, index=False)
        return {"added": use.shape[0], "total": use.shape[0]}
