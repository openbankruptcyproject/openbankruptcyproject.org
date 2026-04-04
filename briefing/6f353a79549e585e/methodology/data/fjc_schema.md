# FJC Integrated Database -- Schema Reference

> Fields used in the OBP 1328(f) analysis and attorney analytics pipeline.
> Source: Federal Judicial Center, Integrated Database for Bankruptcy (IDB).
> Public download: https://www.fjc.gov/research/idb

---

## Primary Table: `fjc_cases`

The FJC IDB contains one row per case snapshot. Cases may appear multiple times
as their status changes. For analysis, we deduplicate using `casekey` and take
the latest record (`MAX(id)`).

### Fields Used in 1328(f) Analysis

| Field | Type | Description | Used For |
|-------|------|-------------|----------|
| `id` | INTEGER | Auto-increment row ID | Deduplication (latest record) |
| `casekey` | TEXT | Unique case identifier assigned by FJC | Deduplication |
| `circuit` | TEXT | Circuit number (1-11, DC, Federal) | Geographic grouping |
| `district` | TEXT | FJC district code (e.g., "66" = W.D. Mo.) | District-level analysis |
| `office` | TEXT | Divisional office code | Sub-district analysis |
| `docket` | TEXT | Docket number | Case identification |
| `filedate` | TEXT | Filing date (YYYYMMDD or similar) | Timeline analysis |
| `filecy` | TEXT | Filing calendar year | Year filtering |
| `filefy` | TEXT | Filing fiscal year (Oct-Sep) | Primary year filter |
| `origin` | TEXT | Origin of proceeding code | New vs. transferred |
| `orgflchp` | TEXT | Original filing chapter | Chapter at filing |
| `crntchp` | TEXT | Current chapter (at time of snapshot) | **Ch.13 filter** |
| `d1zip` | TEXT | Debtor ZIP code (3-digit) | Geographic analysis |
| `d1cnty` | TEXT | Debtor county FIPS code | Geographic analysis |
| `d1fprse` | TEXT | Pro se flag ('Y'/'N') | Pro se rate |
| `ntrdbt` | TEXT | Nature of debt code | Consumer vs. business |
| `joint` | TEXT | Joint filing flag | Joint case analysis |
| `casetyp` | TEXT | Case type | Filing classification |
| `dbtrtyp` | TEXT | Debtor type (individual/business) | Debtor classification |
| `nob` | TEXT | Nature of business code | Business type |
| `prfile` | TEXT | **Prior filing flag ('Y'/'N')** | **Core 1328(f) field** |
| `totassts` | TEXT | Total assets (coded range) | Financial analysis |
| `totlblts` | TEXT | Total liabilities (coded range) | Financial analysis |
| `secured` | TEXT | Secured debt amount (coded) | Debt composition |
| `unsecpr` | TEXT | Unsecured priority debt (coded) | Debt composition |
| `unsecnpr` | TEXT | Unsecured nonpriority debt (coded) | Debt composition |
| `totdbt` | TEXT | Total debt (coded range) | Financial analysis |
| `d1fdsp` | TEXT | **Disposition code** | **Discharge/dismissal** |
| `dschrgd` | TEXT | Discharge date | Discharge timing |
| `ndschrgd` | TEXT | Non-discharge disposition date | Dismissal timing |
| `d1fdspdt` | TEXT | First disposition date | Disposition timing |
| `closedt` | TEXT | Case closed date | Duration calculation |
| `closecy` | TEXT | Closing calendar year | Year analysis |
| `closefy` | TEXT | Closing fiscal year | Year analysis |
| `clchpt` | TEXT | Chapter at closing | Conversion tracking |
| `smllbus` | TEXT | Small business flag | SubV identification |

---

## Key Field: `prfile` (Prior Filing)

This is the single most important field for 1328(f) analysis. It indicates whether
the debtor reported having filed a prior bankruptcy case.

- **Value 'Y':** Debtor reported a prior filing on the petition (Question 9 on
  Official Form 101).
- **Value 'N' or blank:** No prior filing reported.
- **Self-reported:** This data comes from the debtor's petition. There is no
  independent verification by the court or the FJC.
- **Limitation:** Debtors may fail to disclose prior filings (intentionally or
  inadvertently). The true prior filing rate is likely higher than reported.

---

## Key Field: `d1fdsp` (Disposition)

The disposition code determines how a case was resolved.

| Code | Meaning | Category |
|------|---------|----------|
| A | Standard discharge | **Discharged** |
| B | Discharge after conversion | **Discharged** |
| 1 | Discharge (alternate code) | **Discharged** |
| H | Dismissed -- voluntary | **Dismissed** |
| I | Dismissed -- want of prosecution | **Dismissed** |
| J | Dismissed -- failure to file schedules | **Dismissed** |
| K | Dismissed -- other | **Dismissed** |
| T | Dismissed -- trustee motion | **Dismissed** |
| U | Dismissed -- UST motion | **Dismissed** |
| 5 | Dismissed (alternate code) | **Dismissed** |

Cases with no disposition code are still pending or have an unrecorded outcome.

---

## Derived Metrics

These are not raw FJC fields but are computed from the above:

| Metric | Formula | Description |
|--------|---------|-------------|
| `dismiss_rate` | dismissed / (dismissed + discharged) * 100 | % of closed cases dismissed |
| `discharge_rate` | discharged / (dismissed + discharged) * 100 | % of closed cases discharged |
| `prior_rate` | prior_filers / total_filed * 100 | % of filers reporting prior case |
| `prior_discharge_rate` | prior_discharged / prior_closed * 100 | % of prior filers who got discharge |
| `est_1328f_violations` | prior_discharged * 0.43 | Estimated violations (43% bar rate) |
| `pro_se_rate` | pro_se / total_filed * 100 | % filing without attorney |

---

## The 43% Bar Rate

The estimated violation rate (43%) was derived empirically:

1. Pull actual PACER docket data for a sample of prior-filer cases that received
   discharge.
2. For each, find the prior case filing date and the current case filing date.
3. Determine which 1328(f) subsection applies based on the prior case chapter.
4. Calculate the filing gap in days.
5. Check whether the gap falls within the statutory window (4 years for
   1328(f)(1), 2 years for 1328(f)(2)).
6. The fraction that fall within the window = the bar rate.

This 43% rate is applied uniformly as an estimate. The true rate varies by district,
attorney practice patterns, and the mix of Ch.7-to-13 vs. Ch.13-to-13 repeat filings.

---

## Database Structure (Local Analysis DB)

For the attorney analytics pipeline, a separate local database (`bankruptcy_master.db`)
stores PACER-sourced case data with a different schema:

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `case_id` | TEXT | Unique case identifier |
| `court` | TEXT | Court code (e.g., "mowbk") |
| `case_number` | TEXT | Docket number |
| `case_year` | INTEGER | Filing year |
| `debtor_name` | TEXT | Debtor name (anonymized in outputs) |
| `chapter` | TEXT | Bankruptcy chapter |
| `date_filed` | TEXT | Filing date |
| `date_dismissed` | TEXT | Dismissal date (if applicable) |
| `date_discharged` | TEXT | Discharge date (if applicable) |
| `disposition` | TEXT | Case outcome |
| `attorney_id` | INTEGER | FK to attorneys table |
| `attorney_last` | TEXT | Attorney last name |
| `trustee` | TEXT | Assigned trustee |
| `source` | TEXT | Data source identifier |

This database enables per-attorney outcome analysis that the FJC IDB cannot
support (FJC data does not include attorney information).
