"""Self-test. Builds a synthetic PSPS-like file whose cells match the CY2025 aggregates used in the
manuscript, runs the pipeline, and checks the published numbers. No download is needed.
Run:  python test_pipeline.py
(The synthetic file reproduces aggregates only; it is not real PSPS data. To reproduce the tables from
the real file, see README.md.)"""
import os
import tempfile

import pandas as pd

import psps_debridement as pd_mod

# (code, setting group) -> cells, suppressed cells, visible services, NCH all cells, NCH visible cells
AGG = {
    ("11042", "HOPD"): (12456, 9544, 833038.0, 33684999.11, 32989463.65),
    ("11042", "Home and nursing facility"): (11127, 7368, 738309.0, 46651108.54, 45525184.34),
    ("11042", "Office"): (10729, 8171, 588450.0, 50648548.94, 49182586.54),
    ("11042", "Other"): (10912, 10037, 46823.0, 2973036.07, 2287491.44),
    ("11043", "HOPD"): (5607, 4720, 73629.0, 8543935.19, 7686316.81),
    ("11043", "Home and nursing facility"): (5425, 3452, 343060.0, 47461408.81, 46369315.66),
    ("11043", "Office"): (3268, 2586, 60701.0, 10228572.98, 9327315.22),
    ("11043", "Other"): (9480, 8791, 41939.0, 6293997.03, 4882133.98),
    ("11044", "HOPD"): (3990, 3610, 15966.0, 3324950.49, 2428026.16),
    ("11044", "Home and nursing facility"): (2146, 1498, 50477.0, 10077350.69, 9324009.29),
    ("11044", "Office"): (1758, 1532, 9404.0, 2541434.42, 1915616.83),
    ("11044", "Other"): (6971, 6617, 11761.0, 3110325.34, 1640797.82),
    ("11045", "HOPD"): (3851, 2157, 313211.0, 4718441.83, 4610747.04),
    ("11045", "Home and nursing facility"): (3548, 1842, 353276.6, 6688012.6, 6546037.1),
    ("11045", "Office"): (1630, 1045, 93198.0, 2183631.84, 2107283.02),
    ("11045", "Other"): (3489, 2220, 89051.0, 1296625.51, 1187221.12),
    ("11046", "HOPD"): (2155, 1473, 47084.0, 1682265.19, 1514124.21),
    ("11046", "Home and nursing facility"): (2491, 1275, 185694.0, 7480662.85, 7285822.78),
    ("11046", "Office"): (798, 576, 16892.0, 780743.25, 700121.14),
    ("11046", "Other"): (4392, 2675, 159513.0, 4672460.27, 4349831.15),
    ("11047", "HOPD"): (1045, 852, 9541.0, 650975.32, 492786.0),
    ("11047", "Home and nursing facility"): (1174, 705, 44822.0, 3295367.89, 3114911.19),
    ("11047", "Office"): (260, 211, 1661.0, 159630.18, 123664.21),
    ("11047", "Other"): (2551, 1716, 72011.0, 3303790.87, 2926244.32),
    ("97597", "HOPD"): (5704, 4045, 254056.0, 5295133.46, 5089668.58),
    ("97597", "Home and nursing facility"): (6084, 4236, 165487.5, 7761056.46, 7260244.9),
    ("97597", "Office"): (7453, 5544, 362875.0, 24079204.82, 23240733.89),
    ("97597", "Other"): (3058, 2799, 12071.0, 517933.53, 364064.84),
    ("97598", "HOPD"): (2086, 1190, 100171.8, 1064634.47, 1012164.13),
    ("97598", "Home and nursing facility"): (2240, 1328, 75167.0, 1354900.79, 1277768.63),
    ("97598", "Office"): (1185, 838, 28378.0, 643401.27, 589113.29),
    ("97598", "Other"): (812, 589, 17790.0, 207705.94, 180575.73),
}
POS = {"Office": "11", "HOPD": "22", "Home and nursing facility": "12", "Other": "99"}

# Census 65+ population (sum of single years 65 to 100+), from np2023_d1_mid.csv
POP65 = {2025: 63326603, 2030: 71183498, 2040: 78293900}


def cells(code, pos, n, s, v, a, b):
    """n cells, s of them suppressed ('*'); visible cells share v services and b payment."""
    rows = []
    nv = n - s
    for _ in range(nv):
        rows.append((code, pos, repr(v / nv), b / nv))
    for _ in range(s):
        rows.append((code, pos, "*", (a - b) / s if s else 0.0))
    return rows


def build():
    rows = []
    for (code, g), (n, s, v, a, b) in AGG.items():
        rows += cells(code, POS[g], n, s, v, a, b)
    return pd.DataFrame(rows, columns=["HCPCS_CD", "PLACE_OF_SERVICE_CD", "PSPS_SUBMITTED_SERVICE_CNT", "PSPS_NCH_PAYMENT_AMT"])


def fake_census(path):
    cols = ["SEX", "ORIGIN", "RACE", "YEAR"] + [f"POP_{a}" for a in range(65, 101)]
    rows = []
    for y, tot in POP65.items():
        per = tot // 36
        vals = [per] * 36
        vals[-1] += tot - per * 36
        rows.append([0, 0, 0, y] + vals)
    pd.DataFrame(rows, columns=cols).to_csv(path, index=False)


def close(a, b, tol):
    assert abs(a - b) <= tol, f"{a} vs {b}"


def main():
    with tempfile.TemporaryDirectory() as tmp:
        psps = os.path.join(tmp, "psps.csv")
        cen = os.path.join(tmp, "census.csv")
        build().to_csv(psps, index=False)
        fake_census(cen)
        r = pd_mod.run_all(psps, cen)
    t2 = r["Table2_by_group"]; tot = t2.loc["Total, three groups"]
    close(tot.visible_services, 3495452.5, 0.05); close(tot.nch_visible, 240338481.87, 1)
    close(tot.upper_bound_services - tot.visible_services, 563060, 0.5)
    close(t2.loc["HOPD", "payment_per_service"], 40.96, 0.01)
    close(t2.loc["Home and nursing facility", "payment_per_service"], 83.62, 0.01)
    close(t2.loc["Office", "payment_per_service"], 81.91, 0.01)
    t1 = r["Table1_by_code"]
    close(t1.loc["Primary total (excl. add-on codes)", "visible_services"], 3608046.5, 0.05)
    t3 = r["Table3_record_flow"]
    assert int(t3.iloc[0]["cells"]) == 139875 and int(t3.iloc[4]["cells"]) == 75747 and int(t3.iloc[3]["cells"]) == 30421
    assert int(t3.iloc[2]["cells"]) == 106168
    s = r["Suppression_shares"]["value"]
    close(s["eight_code_share_nch_suppressed"], 0.0522, 0.0001); close(s["analytic_share_nch_suppressed"], 0.0398, 0.0001)
    t4 = r["Table4_episodes"]
    close(t4.loc[8, "wound_equivalent_episodes"], 436931.56, 0.1); close(t4.loc[1, "wound_equivalent_episodes"], 3495452.5, 0.05)
    t5 = r["Table5_demographic"]
    close(t5.loc[2040, "multiplier"], 1.2364, 0.00005); close(t5.loc[2030, "multiplier"], 1.1241, 0.00005)
    close(t5.loc[2040, "modeled_nch_payment"], 297142688, 2)
    t6 = r["Table6_thresholds"]
    close(t6.loc["2040 scenario, break-even reduction", "reduction"], 0.1912, 0.0001)
    close(t6.loc["2040 scenario, break-even reduction", "change_vs_base"], 0, 1)
    print("All self-tests passed: pipeline reproduces the published numbers.")


if __name__ == "__main__":
    main()
