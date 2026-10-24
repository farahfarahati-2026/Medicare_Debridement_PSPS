"""Reproduce the tables in "Economics of Medicare Debridement in Aggregate Claims:
A Scenario Framework" from public data (CY2025 analysis).

Inputs
  1. CMS Physician/Supplier Procedure Summary (PSPS), calendar year 2025, public-use file (free):
     https://data.cms.gov/summary-statistics-on-use-and-payments/physiciansupplier-procedure-summary
     Pass the national CSV, the zip you downloaded, or an extract (CSV or Excel) with --psps.
     Columns used: HCPCS_CD, PLACE_OF_SERVICE_CD, PSPS_SUBMITTED_SERVICE_CNT, PSPS_NCH_PAYMENT_AMT.
  2. U.S. Census Bureau 2023 National Population Projections, main series (np2023_d1_mid.csv).
     Downloaded automatically from the Census URL below, or pass a local copy with --census.

Outputs (written to --out): one CSV per table plus psps_tables.xlsx (values).

Usage
  python psps_debridement.py --psps PSPS_2025.zip --census np2023_d1_mid.csv --out results

Method (see the manuscript for definitions)
  * Eight codes are extracted: primary 11042, 11043, 11044, 97597; add-on 11045, 11046, 11047, 97598.
  * Only the primary codes are modeled. Add-on codes are descriptive (Table 1, Table 3).
  * Visible-cell basis: services and payments limited to cells with an unsuppressed service count.
  * Upper bound: each suppressed cell (shown as '*', 1 to 10 services) holds at most THRESHOLD services.
  * Setting groups: Office = POS 11; HOPD = POS 19, 22; Home and nursing facility = POS 12, 13, 31, 32.
  * Demographic scenarios scale services and payments by growth in the 65+ population relative to BASE_YEAR,
    holding use per person, coding, and prices at base-year levels.
  * Break-even reduction in service frequency = 1 - 1/m for demographic multiplier m.
"""
import argparse
import os

import pandas as pd

PRIMARY = ["11042", "11043", "11044", "97597"]
ADDON = ["11045", "11046", "11047", "97598"]
CODES = PRIMARY + ADDON
POS_GROUPS = {11: "Office", 19: "HOPD", 22: "HOPD",
              12: "Home and nursing facility", 13: "Home and nursing facility",
              31: "Home and nursing facility", 32: "Home and nursing facility"}
GROUP_ORDER = ["Office", "HOPD", "Home and nursing facility"]
THRESHOLD = 10                      # max services in a suppressed cell
SCENARIOS = (1, 2.0, 2.4, 8)        # assumed services per wound-equivalent episode
REDUCTIONS = (0.10, 0.20, 0.30)     # hypothetical reductions in service frequency
BASE_YEAR = 2025
YEARS = (BASE_YEAR, 2030, 2040)
USECOLS = ["HCPCS_CD", "PLACE_OF_SERVICE_CD", "PSPS_SUBMITTED_SERVICE_CNT", "PSPS_NCH_PAYMENT_AMT"]
CENSUS_URL = "https://www2.census.gov/programs-surveys/popproj/datasets/2023/2023-popproj/np2023_d1_mid.csv"


def load_psps(path, chunksize=500_000):
    """Read the PSPS file (CSV, zipped CSV, or Excel) and keep only the eight debridement codes."""
    p = str(path).lower()
    if p.endswith((".xlsx", ".xls")):
        d = pd.read_excel(path, dtype=str)
        return d[d["HCPCS_CD"].astype(str).isin(CODES)][USECOLS].copy()
    parts = []
    for chunk in pd.read_csv(path, dtype=str, usecols=USECOLS, chunksize=chunksize,
                             encoding="utf-8-sig", keep_default_na=False):
        parts.append(chunk[chunk["HCPCS_CD"].isin(CODES)])
    return pd.concat(parts, ignore_index=True)


def prepare(d):
    d = d.copy()
    d["svc"] = pd.to_numeric(d["PSPS_SUBMITTED_SERVICE_CNT"], errors="coerce")   # '*' becomes NaN
    d["supp"] = d["svc"].isna()
    d["nch"] = pd.to_numeric(d["PSPS_NCH_PAYMENT_AMT"], errors="coerce").fillna(0.0)
    d["pos"] = pd.to_numeric(d["PLACE_OF_SERVICE_CD"], errors="coerce")
    d["group"] = d["pos"].map(POS_GROUPS).fillna("Other")
    d["HCPCS_CD"] = d["HCPCS_CD"].astype(str)
    return d


def summarize(x, threshold=THRESHOLD):
    v = x[~x["supp"]]
    n_supp = int(x["supp"].sum())
    svc = float(v["svc"].sum())
    nch_vis = float(v["nch"].sum())
    return pd.Series({
        "cells": len(x),
        "suppressed_cells": n_supp,
        "visible_services": svc,
        "upper_bound_services": svc + threshold * n_supp,
        "nch_visible": nch_vis,
        "nch_all_cells": float(x["nch"].sum()),
        "payment_per_service": nch_vis / svc if svc else float("nan"),
    })


def group_summary(df, key):
    return pd.DataFrame({k: summarize(g) for k, g in df.groupby(key)}).T


def table1_by_code(d):
    t = group_summary(d, "HCPCS_CD").reindex(CODES)
    t.loc["Primary total (excl. add-on codes)"] = summarize(d[d["HCPCS_CD"].isin(PRIMARY)])
    return t


def table2_by_group(d):
    p = d[d["HCPCS_CD"].isin(PRIMARY) & (d["group"] != "Other")]
    t = group_summary(p, "group").reindex(GROUP_ORDER)
    t.loc["Total, three groups"] = summarize(p)
    return t, p


def table3_record_flow(d, analytic):
    allr = summarize(d)
    addon = summarize(d[d["HCPCS_CD"].isin(ADDON)])
    prim_all = summarize(d[d["HCPCS_CD"].isin(PRIMARY)])
    ana = summarize(analytic)
    cols = ["cells", "suppressed_cells", "visible_services", "nch_visible"]
    rows = {
        "All records in extract (eight codes)": allr[cols],
        "Less add-on codes (11045-11047, 97598)": addon[cols],
        "Primary codes, all places of service": prim_all[cols],
        "Less places of service outside three groups": prim_all[cols] - ana[cols],
        "Primary codes, three groups (analytic set)": ana[cols],
    }
    return pd.DataFrame(rows).T


def suppression_shares(d, analytic):
    out = {}
    s_all = summarize(d)
    out["eight_code_cells_suppressed"] = s_all["suppressed_cells"]
    out["eight_code_share_cells_suppressed"] = s_all["suppressed_cells"] / s_all["cells"]
    out["eight_code_nch_in_suppressed_cells"] = s_all["nch_all_cells"] - s_all["nch_visible"]
    out["eight_code_share_nch_suppressed"] = out["eight_code_nch_in_suppressed_cells"] / s_all["nch_all_cells"]
    s_an = summarize(analytic)
    out["analytic_nch_all_cells"] = s_an["nch_all_cells"]
    out["analytic_nch_in_suppressed_cells"] = s_an["nch_all_cells"] - s_an["nch_visible"]
    out["analytic_share_nch_suppressed"] = out["analytic_nch_in_suppressed_cells"] / s_an["nch_all_cells"]
    return pd.Series(out, name="value").to_frame()


def table4_episodes(services, nch):
    rows = []
    for f in SCENARIOS:
        episodes = services / f
        rows.append({"services_per_episode": f, "wound_equivalent_episodes": episodes,
                     "nch_visible": nch, "modeled_payment_per_episode": nch / episodes})
    return pd.DataFrame(rows).set_index("services_per_episode")


def census_65plus(path_or_url=CENSUS_URL):
    """Population aged 65 to 100+ in the base year, 2030 and 2040 (main series, all sexes/origins/races)."""
    cols = ["SEX", "ORIGIN", "RACE", "YEAR"] + [f"POP_{a}" for a in range(65, 101)]
    c = pd.read_csv(path_or_url, usecols=cols)
    c = c[(c.SEX == 0) & (c.ORIGIN == 0) & (c.RACE == 0) & (c.YEAR.isin(YEARS))].set_index("YEAR")
    pop65 = c[[f"POP_{a}" for a in range(65, 101)]].sum(axis=1).astype(int)
    return pop65.reindex(list(YEARS))


def table5_demographic(services, nch, pop65):
    base = pop65[BASE_YEAR]
    rows = []
    for y in YEARS:
        m = pop65[y] / base
        rows.append({"year": y, "pop_65_plus": int(pop65[y]), "pop_millions": round(pop65[y] / 1e6, 1),
                     "multiplier": m, "modeled_services": services * m, "modeled_nch_payment": nch * m})
    return pd.DataFrame(rows).set_index("year")


def table6_thresholds(services, nch, m2040):
    b = BASE_YEAR
    rows = [{"scenario": f"CY{b} baseline, 0%", "reduction": 0.0, "adjusted_services": services,
             "adjusted_nch": nch, "change_vs_base": 0.0}]
    for r in REDUCTIONS:
        rows.append({"scenario": f"CY{b} baseline, {int(r*100)}% reduction", "reduction": r,
                     "adjusted_services": services * (1 - r), "adjusted_nch": nch * (1 - r),
                     "change_vs_base": nch * (1 - r) - nch})
    rows.append({"scenario": "2040 scenario, no reduction", "reduction": 0.0, "adjusted_services": services * m2040,
                 "adjusted_nch": nch * m2040, "change_vs_base": nch * m2040 - nch})
    be = 1 - 1 / m2040
    rows.append({"scenario": "2040 scenario, break-even reduction", "reduction": be,
                 "adjusted_services": services * m2040 * (1 - be), "adjusted_nch": nch * m2040 * (1 - be),
                 "change_vs_base": nch * m2040 * (1 - be) - nch})
    return pd.DataFrame(rows).set_index("scenario")


def run_all(psps_path, census_path=CENSUS_URL):
    d = prepare(load_psps(psps_path))
    t1 = table1_by_code(d)
    t2, analytic = table2_by_group(d)
    t3 = table3_record_flow(d, analytic)
    sup = suppression_shares(d, analytic)
    services = float(t2.loc["Total, three groups", "visible_services"])
    nch = float(t2.loc["Total, three groups", "nch_visible"])
    t4 = table4_episodes(services, nch)
    pop65 = census_65plus(census_path)
    t5 = table5_demographic(services, nch, pop65)
    t6 = table6_thresholds(services, nch, float(t5.loc[2040, "multiplier"]))
    return {"Table1_by_code": t1, "Table2_by_group": t2, "Table3_record_flow": t3,
            "Suppression_shares": sup, "Table4_episodes": t4, "Table5_demographic": t5, "Table6_thresholds": t6}


def save(results, out):
    os.makedirs(out, exist_ok=True)
    with pd.ExcelWriter(os.path.join(out, "psps_tables.xlsx")) as xw:
        for name, df in results.items():
            df.to_csv(os.path.join(out, f"{name}.csv"))
            df.to_excel(xw, sheet_name=name[:31])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--psps", required=True, help="path to the CY2025 PSPS file (CSV, zip, or Excel extract)")
    ap.add_argument("--census", default=CENSUS_URL, help="Census np2023_d1_mid.csv path or URL (default: download)")
    ap.add_argument("--out", default="results", help="output folder")
    a = ap.parse_args()
    res = run_all(a.psps, a.census)
    save(res, a.out)
    pd.set_option("display.width", 200, "display.float_format", "{:,.4f}".format)
    for name, df in res.items():
        print(f"\n## {name}\n{df}")
    print(f"\nSaved to {a.out}/")


if __name__ == "__main__":
    main()
