# data_collection.py
"""
Nepal Economic Dashboard - Data Collection Pipeline
Fetches 6 key indicators for Nepal from the World Bank API via wbgapi,
cleans the data with Pandas, and saves clean CSVs to the /data folder.

Run:  python data_collection.py
"""

import os
import sys
import json
import warnings
from datetime import datetime, timezone

import pandas as pd
import wbgapi as wb

# Suppress DeprecationWarnings from wbgapi
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ── Configuration ──────────────────────────────────────────────────────────────
COUNTRY_CODE = "NPL"
START_YEAR   = 2000
END_YEAR     = 2023
DATA_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": {
        "name": "GDP Growth Rate",
        "unit": "% per year",
        "filename": "gdp_growth.csv",
    },
    "FP.CPI.TOTL.ZG": {
        "name": "Inflation (CPI)",
        "unit": "% per year",
        "filename": "inflation_cpi.csv",
    },
    "BX.TRF.PWKR.DT.GD.ZS": {
        "name": "Remittances",
        "unit": "% of GDP",
        "filename": "remittances.csv",
    },
    "NE.EXP.GNFS.ZS": {
        "name": "Exports of Goods & Services",
        "unit": "% of GDP",
        "filename": "exports.csv",
    },
    "NE.IMP.GNFS.ZS": {
        "name": "Imports of Goods & Services",
        "unit": "% of GDP",
        "filename": "imports.csv",
    },
    "SL.UEM.TOTL.ZS": {
        "name": "Unemployment Rate",
        "unit": "% of total labour force",
        "filename": "unemployment.csv",
    },
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def utcnow_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[OK] Data directory ready: {DATA_DIR}")


def fetch_indicator(code, meta):
    print(f"\n[->] Fetching: {meta['name']} ({code})")
    try:
        raw = wb.data.DataFrame(
            code,
            economy=COUNTRY_CODE,
            time=range(START_YEAR, END_YEAR + 1),
        )
    except Exception as exc:
        print(f"    [!] API error for {code}: {exc}")
        return None

    if raw is None or raw.empty:
        print(f"    [!] No data returned for {code}.")
        return None

    year_cols = [c for c in raw.columns if str(c).startswith("YR") and str(c)[2:].isdigit()]
    if not year_cols:
        print(f"    [!] Unexpected columns: {raw.columns.tolist()}")
        return None

    raw = raw.reset_index()
    df = raw.melt(
        id_vars=["economy"],
        value_vars=year_cols,
        var_name="year_str",
        value_name="value",
    )

    df["year"] = df["year_str"].str[2:].astype(int)
    df = df[["year", "value"]].copy()

    before  = len(df)
    df      = df.dropna(subset=["value"])
    dropped = before - len(df)
    if dropped:
        print(f"    [i] Dropped {dropped} row(s) with missing values.")

    df = df.sort_values("year").reset_index(drop=True)

    df["indicator_code"] = code
    df["indicator_name"] = meta["name"]
    df["unit"]           = meta["unit"]
    df["country"]        = "Nepal"
    df["source"]         = "World Bank"
    df["fetched_at"]     = utcnow_str()

    print(f"    [OK] {len(df)} year(s) of data ({int(df['year'].min())}-{int(df['year'].max())})")
    return df


def save_csv(df, filename):
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)
    print(f"    [SAVED] {filename}")


def save_combined(all_dfs):
    combined = pd.concat(all_dfs, ignore_index=True)
    path = os.path.join(DATA_DIR, "all_indicators.csv")
    combined.to_csv(path, index=False)
    print(f"\n[OK] Combined CSV saved.")
    return combined


def save_metadata():
    meta = {
        "last_updated": utcnow_str(),
        "source": "World Bank Open Data (wbgapi)",
        "country": "Nepal (NPL)",
        "year_range": f"{START_YEAR}-{END_YEAR}",
        "indicators": [
            {"code": code, "name": m["name"], "unit": m["unit"]}
            for code, m in INDICATORS.items()
        ],
    }
    path = os.path.join(DATA_DIR, "metadata.json")
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[OK] Metadata saved.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Nepal Economic Dashboard - Data Collection")
    print("=" * 60)

    ensure_data_dir()

    all_dfs = []
    failed  = []

    for code, meta in INDICATORS.items():
        df = fetch_indicator(code, meta)
        if df is not None:
            save_csv(df, meta["filename"])
            all_dfs.append(df)
        else:
            failed.append(meta["name"])

    if all_dfs:
        save_combined(all_dfs)
        save_metadata()

    print("\n" + "=" * 60)
    print(f"  Done. {len(all_dfs)}/{len(INDICATORS)} indicators fetched.")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print("=" * 60)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
