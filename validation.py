# validation.py
"""
Nepal Economic Dashboard - Data Validation Script
Runs quality checks on all cleaned CSVs in /data and prints a clear report.

Checks performed:
  1. File existence
  2. Missing values
  3. Duplicate years
  4. Year range coverage (flags sparse datasets)
  5. Outlier detection (IQR method, 3x fence)
  6. Unit consistency (checks unit column is uniform per file)

Run:  python validation.py
"""

import os
import json
import sys
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EXPECTED_MIN_YEARS   = 10       # flag if fewer than this many data points
OUTLIER_IQR_MULTIPLIER = 3.0    # conservative - only flags extreme outliers

INDICATOR_FILES = {
    "GDP Growth Rate":              "gdp_growth.csv",
    "Inflation (CPI)":              "inflation_cpi.csv",
    "Remittances":                  "remittances.csv",
    "Exports of Goods & Services":  "exports.csv",
    "Imports of Goods & Services":  "imports.csv",
    "Unemployment Rate":            "unemployment.csv",
}

SEP  = "-" * 62
TICK = "  [OK]  "
WARN = "  [WARN]"
FAIL = "  [FAIL]"


def header(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def check_file_exists(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        print(f"{FAIL} FILE NOT FOUND: {filename}")
        return False
    print(f"{TICK} File found: {filename}")
    return True


def load(filename):
    try:
        return pd.read_csv(os.path.join(DATA_DIR, filename))
    except Exception as exc:
        print(f"{FAIL} Could not read {filename}: {exc}")
        return None


def check_missing_values(df, name):
    n_missing = df["value"].isna().sum()
    if n_missing == 0:
        print(f"{TICK} No missing values in 'value' column.")
    else:
        years = sorted(df.loc[df["value"].isna(), "year"].tolist())
        print(f"{WARN} {n_missing} missing value(s) in 'value' column - years: {years}")
    return n_missing


def check_duplicates(df, name):
    dupes = df[df.duplicated(subset=["year"], keep=False)]
    n_dupes = len(dupes)
    if n_dupes == 0:
        print(f"{TICK} No duplicate years.")
    else:
        print(f"{WARN} {n_dupes} duplicate year row(s): {sorted(dupes['year'].unique().tolist())}")
    return n_dupes


def check_year_coverage(df, name):
    n      = len(df)
    yr_min = int(df["year"].min())
    yr_max = int(df["year"].max())
    gaps   = sorted(set(range(yr_min, yr_max + 1)) - set(df["year"].tolist()))
    warnings_found = 0
    if n < EXPECTED_MIN_YEARS:
        print(f"{WARN} Only {n} data points - dataset is sparse.")
        warnings_found += 1
    else:
        print(f"{TICK} {n} data points covering {yr_min}-{yr_max}.")
    if gaps:
        print(f"{WARN} Missing years in sequence: {gaps}")
        warnings_found += 1
    else:
        print(f"{TICK} No gaps in year sequence.")
    return warnings_found


def check_outliers(df, name):
    vals = df["value"].dropna()
    if len(vals) < 4:
        print(f"{WARN} Too few values for outlier detection.")
        return []
    q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
    iqr     = q3 - q1
    lo      = q1 - OUTLIER_IQR_MULTIPLIER * iqr
    hi      = q3 + OUTLIER_IQR_MULTIPLIER * iqr
    outliers = df[(df["value"] < lo) | (df["value"] > hi)][["year", "value"]]
    if outliers.empty:
        print(f"{TICK} No extreme outliers (IQR x{OUTLIER_IQR_MULTIPLIER} fence: [{lo:.2f}, {hi:.2f}]).")
    else:
        print(f"{WARN} Potential outliers (review manually):")
        for _, row in outliers.iterrows():
            print(f"         Year {int(row['year'])}: {row['value']:.4f}")
    return outliers["year"].tolist()


def check_unit_consistency(df, name):
    if "unit" not in df.columns:
        print(f"{WARN} No 'unit' column found.")
        return 1
    unique_units = df["unit"].unique()
    if len(unique_units) == 1:
        print(f"{TICK} Unit consistent: '{unique_units[0]}'")
        return 0
    else:
        print(f"{WARN} Mixed units detected: {unique_units.tolist()}")
        return 1


def check_value_range(df, name):
    vals = df["value"].dropna()
    print(f"         Range  : {vals.min():.4f}  to  {vals.max():.4f}")
    print(f"         Mean   : {vals.mean():.4f}")
    print(f"         Std Dev: {vals.std():.4f}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 62)
    print("   Nepal Economic Dashboard - Data Validation Report")
    print("=" * 62)

    meta_path = os.path.join(DATA_DIR, "metadata.json")
    if os.path.isfile(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        print(f"\n  Last updated : {meta.get('last_updated', 'unknown')}")
        print(f"  Country      : {meta.get('country', 'unknown')}")
        print(f"  Year range   : {meta.get('year_range', 'unknown')}")
    else:
        print(f"\n{WARN} metadata.json not found - run data_collection.py first.")

    total_errors = 0
    total_warnings = 0

    for indicator_name, filename in INDICATOR_FILES.items():
        header(f"Indicator: {indicator_name}  ({filename})")

        if not check_file_exists(filename):
            total_errors += 1
            continue

        df = load(filename)
        if df is None:
            total_errors += 1
            continue

        total_errors += check_missing_values(df, indicator_name)
        total_errors += check_duplicates(df, indicator_name)
        total_warnings += check_year_coverage(df, indicator_name)
        total_warnings += check_unit_consistency(df, indicator_name)
        check_value_range(df, indicator_name)
        outlier_years = check_outliers(df, indicator_name)
        if outlier_years:
            total_warnings += len(outlier_years)

    print(f"\n{'=' * 62}")
    if total_errors == 0:
        if total_warnings == 0:
            print("  ALL CHECKS PASSED. Data looks clean.")
        else:
            print(f"  ALL CRITICAL CHECKS PASSED ({total_warnings} advisory warning(s) flagged).")
            print("  Historical shocks (e.g. COVID-19 in 2020) are preserved as expected.")
    else:
        print(f"  VALIDATION FAILED: {total_errors} critical error(s), {total_warnings} warning(s).")
    print(f"{'=' * 62}\n")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

