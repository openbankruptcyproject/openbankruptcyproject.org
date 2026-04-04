# RSS Feed Monitoring Methodology

> How free, public court RSS feeds are used for real-time bankruptcy case monitoring
> without any PACER costs.

---

## Overview

Every federal bankruptcy court publishes a free RSS feed of recent docket activity.
These feeds typically roll every 24 hours -- meaning each day's entries are available
for roughly one day before being replaced by the next day's entries. By polling
daily, we build a complete longitudinal database of case activity across monitored
districts.

**Cost: $0.** No PACER account required for RSS. No subscription fees. The data is
published by the courts themselves at publicly accessible URLs.

---

## Architecture

### 1. RSS Accumulation

A daily polling script fetches the RSS feed for each monitored district. Each feed
entry contains:

- **Case number** (docket identifier)
- **Entry title** (filing description, e.g., "Order Granting Discharge")
- **Entry date** (filing timestamp)
- **Entry link** (URL to the docket entry on PACER)

These entries are parsed and stored in a SQLite database. The database schema:

```
cases:
  - case_id (TEXT, unique)
  - court (TEXT)
  - case_number (TEXT)
  - chapter (TEXT, if determinable)
  - date_filed (TEXT)
  - attorney_last (TEXT, from cross-reference)
  - first_seen (TEXT)
  - last_activity (TEXT)

events:
  - case_id (TEXT, FK)
  - event_date (TEXT)
  - event_type (TEXT, classified)
  - raw_title (TEXT)
  - source (TEXT, "rss")
```

### 2. Event Classification

Raw docket entry titles are classified into event types using pattern matching:

| Pattern | Event Type | Significance |
|---------|-----------|--------------|
| "Order.*Discharge" | `order_discharge` | Case completed successfully |
| "Order.*Dismiss" | `order_dismissal` | Case failed |
| "Order.*Show Cause" | `order_show_cause` | Judicial intervention |
| "Motion.*Dismiss" | `motion_to_dismiss` | Trustee/creditor action |
| "Order.*Confirm" | `order_confirmation` | Plan confirmed |
| "Fee Application" | `fee_application` | Attorney fee event |
| "Motion.*Relief.*Stay" | `motion_relief_stay` | Creditor seeking relief |
| "Notice.*Conversion" | `conversion` | Chapter change |

Classification uses regular expressions with case-insensitive matching. The
patterns are designed to be over-inclusive (minimize false negatives) at the
cost of some false positives that are filtered in downstream analysis.

### 3. Attorney Cross-Reference

RSS feeds do not include attorney information. To associate cases with attorneys,
we cross-reference against PACER Case Locator (PCL) CSV exports:

1. Pull PCL data for all attorneys of interest in the monitored districts.
2. Build an index: case_id -> attorney_last_name.
3. When a new RSS case appears, look it up in the PCL index.
4. Cases not in any PCL export are flagged as "unknown attorney" for later
   investigation.

This enables real-time attribution of outcomes to specific attorneys without
requiring ongoing PACER access -- the PCL export is a one-time cost per attorney.

### 4. Outcome Tracking

As cases accumulate events over time, outcomes are determined:

- **Discharged:** At least one `order_discharge` event.
- **Dismissed:** At least one `order_dismissal` event (and no discharge).
- **Confirmed:** At least one `order_confirmation` event (plan approved, not yet
  completed).
- **Pending:** No disposition event yet.

Duration is calculated from the earliest event to the disposition event.

---

## Monitoring Capabilities

### Real-Time Alerts

The system generates alerts when:

- A monitored attorney's case is dismissed (tracks running dismissal rate)
- An order to show cause is issued (judicial red flag)
- A case is converted to a different chapter
- Unusual activity patterns emerge (e.g., cluster of dismissals in a short period)

### Trend Detection

Daily accumulation enables longitudinal analysis:

- **Filing rate changes:** Is an attorney filing more/fewer cases than historical norm?
- **Outcome shifts:** Is the dismissal rate trending up or down?
- **Seasonal patterns:** Do outcomes vary by time of year?
- **Duration trends:** Are cases taking longer or shorter to resolve?

### Unknown Attorney Discovery

Cases that appear in RSS but not in any PCL export represent attorneys not yet
in the monitoring database. By tracking these, the system can:

1. Identify active attorneys missed by initial PCL pulls.
2. Detect new attorneys entering a practice.
3. Find cases that may have been reassigned between attorneys.

---

## Data Quality

### Coverage

RSS captures **all docket activity** for a court, not just cases matching a filter.
This means:

- Every case with any activity in the polling window is captured.
- No cases are missed due to filtering or sampling.
- The database naturally builds toward comprehensive coverage.

### Limitations

1. **24-hour window:** If polling fails for a day, that day's entries are lost.
   Mitigation: redundant polling with retry logic.

2. **No retrospective data:** RSS only provides current activity. Historical data
   requires PCL exports or PACER access.

3. **Attorney attribution requires cross-reference:** RSS alone cannot identify
   attorneys. PCL data is needed.

4. **Event classification is imperfect:** Pattern matching on docket entry titles
   has ~95% accuracy. Edge cases (unusual wording, local conventions) may be
   misclassified.

5. **Pending cases are undercounted:** If a case has no activity during the monitoring
   period, it will not appear in the RSS database.

---

## Replication

To replicate this methodology for any federal bankruptcy court:

1. **Identify the RSS feed URL.** Format is typically:
   `https://ecf.{court}.uscourts.gov/cgi-bin/rss_outside.pl`

2. **Set up daily polling.** A cron job or Task Scheduler task running once per day
   is sufficient. Parse the XML, extract entries, store in SQLite.

3. **Pull PCL data.** For attorney attribution, export CSVs from pcl.uscourts.gov
   for the attorneys and courts of interest.

4. **Run event classification.** Apply the pattern matching rules to each docket
   entry title.

5. **Compute metrics.** Aggregate outcomes and event counts per attorney, then
   compare against the court-wide baseline.

The total infrastructure cost is effectively zero: Python standard library,
SQLite (no server needed), and free RSS feeds. A single laptop can monitor
multiple districts indefinitely.

---

## Privacy and Ethics

- All data comes from public court records (RSS feeds and PACER).
- No private or sealed information is accessed.
- Analysis focuses on systemic patterns, not individual debtors.
- Attorney performance metrics are computed from public case outcomes.
- This methodology does not scrape, hack, or circumvent any access controls.
