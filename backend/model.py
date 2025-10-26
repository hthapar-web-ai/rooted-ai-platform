from __future__ import annotations
from dataclasses import dataclass
import math
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
BENCHMARKS_CSV = DATA_DIR / "benchmarks.csv"
APPRAISALS_CSV = DATA_DIR / "appraisal_dataset.csv"  # optional

@dataclass
class Inputs:
    province: str = "ON"
    collections: float = 0.0
    ebitda_or_sde: float = 0.0
    equipped_ops: float = 0.0
    sqft: float = 0.0

def _f(v, default=0.0):
    try:
        x = float(v)
        if math.isinf(x) or math.isnan(x):
            return default
        return x
    except:
        return default

def load_benchmarks() -> pd.DataFrame:
    df = pd.read_csv(BENCHMARKS_CSV)
    df["province"] = df["province"].astype(str).str.upper()
    return df

def baseline_estimate(x: Inputs) -> dict:
    # Inputs with safe defaults
    c = _f(x.collections)
    e = _f(x.ebitda_or_sde)
    if e <= 0 and c > 0:
        e = 0.25 * c  # assume 25% margin if not provided

    ops = max(_f(x.equipped_ops), 1.0)
    sqft = max(_f(x.sqft), 1.0)

    # Core blend: revenue & EBITDA approaches
    base = max(0.80 * c, 3.8 * e)

    # Capacity premium (above 4 ops)
    over_ops = max(0.0, ops - 4.0)
    cap_adj = min(0.12, 0.015 * over_ops)

    # Space efficiency
    sqft_per_op = sqft / ops
    if sqft_per_op < 260:
        space_adj = +0.03
    elif sqft_per_op > 330:
        space_adj = -0.03
    else:
        space_adj = 0.0

    est = base * (1.0 + cap_adj + space_adj)

    # Provincial multiple blend (pulls toward bench multiple * EBITDA)
    try:
        bm = load_benchmarks()
        row = bm[bm["province"] == x.province.upper()].head(1)
        if not row.empty and e > 0:
            prov_mult = float(row["ebitda_multiple"].iloc[0])
            prov_est = prov_mult * e
            est = 0.7 * est + 0.3 * prov_est
    except Exception:
        pass

    # Uncertainty shrinks as more fields filled
    filled = sum([c > 0, e > 0, ops > 0, sqft > 0])
    err = {1: 0.28, 2: 0.22, 3: 0.16, 4: 0.12}.get(filled, 0.30)

    lo68, hi68 = est * (1 - err/2), est * (1 + err/2)
    lo95, hi95 = est * (1 - err),   est * (1 + err)

    return {
        "estimate": round(est),
        "range_68": [round(lo68), round(hi68)],
        "range_95": [round(lo95), round(hi95)],
        "details": {
            "collections": c,
            "ebitda_or_sde": e,
            "equipped_ops": ops,
            "sqft": sqft,
            "sqft_per_op": round(sqft_per_op, 1),
            "capacity_adj": round(cap_adj, 4),
            "space_adj": round(space_adj, 4),
        },
    }
