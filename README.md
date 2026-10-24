# Economics of Medicare Debridement in Aggregate Claims: reproducible analysis

Code and data that reproduce Tables 1 to 6 of the manuscript "Economics of Medicare Debridement in Aggregate Claims: A Scenario Framework" (Farahati and Rahimian), using calendar year 2025 public data.

## Data

| Source | Where | In this repository? |
|---|---|---|
| CMS Physician/Supplier Procedure Summary (PSPS), CY2025, public use file (free). Full file: 14,474,585 rows. Downloaded October 23, 2026. https://data.cms.gov/summary-statistics-on-use-and-payments/physiciansupplier-procedure-summary | CMS | No (330 MB zip). Download it yourself. |
| Eight-code extract of the PSPS file (139,875 rows: HCPCS 11042, 11043, 11044, 11045, 11046, 11047, 97597, 97598) | `PSPS25_8codes.csv` | Yes |
| U.S. Census Bureau 2023 National Population Projections, main series, `np2023_d1_mid.csv`. https://www2.census.gov/programs-surveys/popproj/datasets/2023/2023-popproj/np2023_d1_mid.csv | Census | Yes (repository root) |

Do not use the paid Limited Data Set page. Columns used: `HCPCS_CD`, `PLACE_OF_SERVICE_CD`, `PSPS_SUBMITTED_SERVICE_CNT`, `PSPS_NCH_PAYMENT_AMT`.

## Run

Command line (use the extract, or the full CMS zip):

```
pip install -r requirements.txt
python psps_debridement.py --psps PSPS25_8codes.csv --census np2023_d1_mid.csv --out results
```

Google Colab: open `PSPS_Debridement_Colab.ipynb`, upload the PSPS file (extract or full zip) when prompted, and run all cells.

Outputs: one CSV per table and `psps_tables.xlsx` in the output folder.

An Excel version with live formulas, built step by step from the same raw data, is in `PSPS25_Steps.xlsx`.

## Check the install

```
python test_pipeline.py
```

This builds a synthetic file that matches the CY2025 aggregates behind the manuscript, runs the pipeline, and confirms the published numbers. It needs no download.

## Method in brief

- Primary codes 11042, 11043, 11044, 97597 are modeled. Add-on codes 11045, 11046, 11047, 97598 are descriptive only.
- Visible-cell basis: services and payments are limited to cells with an unsuppressed service count. Suppressed cells (shown as `*`, 1 to 10 services) still carry payment.
- Upper bound: each suppressed cell holds at most 10 services.
- Setting groups: Office (POS 11); Hospital outpatient department, HOPD (POS 19, 22); Home and nursing facility (POS 12 home, 13 assisted living, 31 skilled nursing, 32 nursing facility).
- Demographic scenarios scale services and payments by growth in the 65+ population relative to 2025, holding use per person, coding, and prices constant.
- Break-even reduction in service frequency = 1 - 1/m for demographic multiplier m.

## Key results (CY2025)

3,495,453 visible primary-code services and $240.3 million in NCH payments across the three settings; at most 563,060 additional services in suppressed cells; 2040 multiplier 1.24; break-even reduction 19.1%.

## Citation

Farahati F, Rahimian M. Economics of Medicare Debridement in Aggregate Claims: A Scenario Framework. Manuscript submitted to Applied Health Economics and Health Policy, 2026.

## License

Code: MIT License (see `LICENSE`). Copyright (c) 2026 Farah Farahati, Global Wellness Advisors LLC.

Data: the CMS PSPS file and the Census projections are U.S. government public data and remain subject to the terms of their publishers. The extract in the repository root contains only rows from the public CMS file.
