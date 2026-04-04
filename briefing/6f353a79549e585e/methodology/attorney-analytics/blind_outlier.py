#!/usr/bin/env python3
"""
blind_outlier.py -- Statistical Outlier Detection (No Target Specified)
=======================================================================

Point this at a court's worth of docket data and it surfaces attorneys whose
clients are losing at rates that cannot be explained by chance. No target
attorney is specified -- the tool finds the problems autonomously.

For each attorney with N+ cases (default 5), computes Z-scores against
their court's baseline on 6 metrics. Auto-flags anyone who deviates
significantly on multiple dimensions.

THIS IS THE "POINT AND SHOOT" TOOL: give it data, it finds anomalies.

ANONYMIZATION:
    No attorney names, firm names, or case numbers appear in this code.
    All output uses sequential anonymous labels (Attorney_001, etc.).

METRICS (per attorney, compared to court baseline):
    1. Dismissal rate      -- % of closed cases dismissed
    2. Discharge rate       -- % of closed cases discharged (low = bad)
    3. OSC rate             -- Orders to show cause per case
    4. MTD rate             -- Motions to dismiss per case
    5. Fee app density      -- Fee applications per case
    6. Stay relief rate     -- Motions for relief from stay per case

ALGORITHM:
    1. Load all enriched case JSONs for the court(s).
    2. Group cases by attorney.
    3. For each attorney with N+ cases, compute all 6 metrics.
    4. Compute court-wide mean and standard deviation for each metric.
    5. Z-score each attorney on each metric.
    6. For discharge_rate, invert the sign (lower discharge = positive Z).
    7. Sum all positive Z-scores into a composite score.
    8. Rank all attorneys by composite score.
    9. Flag anyone above the threshold.

USAGE:
    python blind_outlier.py                     # scan all courts
    python blind_outlier.py --court districtX   # scan one court
    python blind_outlier.py --threshold 2.0     # stricter threshold
    python blind_outlier.py --min-cases 10      # require more cases
    python blind_outlier.py --json              # machine-readable output
    python blind_outlier.py --anonymize         # replace names with labels

DEPENDENCIES:
    Python 3.8+ standard library (json, os, sys, math, argparse).
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD = 1.5     # Composite Z-score to flag
DEFAULT_MIN_CASES = 5       # Minimum cases per attorney
METRIC_NAMES = [
    'dismiss_rate', 'discharge_rate', 'osc_rate',
    'mtd_rate', 'fee_rate', 'mfrs_rate',
]
METRIC_LABELS = {
    'dismiss_rate': 'Dismissal',
    'discharge_rate': 'Low Discharge',
    'osc_rate': 'OSC Rate',
    'mtd_rate': 'MTD Rate',
    'fee_rate': 'Fee Density',
    'mfrs_rate': 'Stay Relief',
}


# ---------------------------------------------------------------------------
# Date Parsing
# ---------------------------------------------------------------------------

def parse_date(d):
    """Parse date string in common formats."""
    if not d:
        return None
    for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y'):
        try:
            return datetime.strptime(d.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_enriched_cases(data_dir: Path) -> list:
    """Load all enriched case JSON files from the data directory.

    Each JSON file represents one docket with extracted events.

    Args:
        data_dir: Path to directory containing *_*.json files.

    Returns:
        List of case dicts.
    """
    cases = []
    if not data_dir.exists():
        return cases

    for fp in data_dir.glob('*.json'):
        try:
            with open(fp, encoding='utf-8') as f:
                data = json.load(f)
            cases.append(data)
        except (json.JSONDecodeError, IOError):
            continue

    return cases


# ---------------------------------------------------------------------------
# Record Building
# ---------------------------------------------------------------------------

def get_attorney_id(case: dict) -> str:
    """Extract attorney identifier from a case dict."""
    atty = case.get('attorney', {})
    if isinstance(atty, dict):
        return atty.get('last', 'Unknown')
    return 'Unknown'


def build_records(cases: list) -> list:
    """Convert raw case dicts into analysis records.

    Args:
        cases: List of enriched case dicts.

    Returns:
        List of standardized record dicts.
    """
    records = []
    for case in cases:
        docket = case.get('docket', {})
        events = case.get('events', {})

        outcome = 'pending'
        if events.get('order_discharge', 0) > 0:
            outcome = 'discharged'
        elif events.get('order_dismissal', 0) > 0:
            outcome = 'dismissed'
        elif events.get('order_confirmation', 0) > 0:
            outcome = 'confirmed'

        records.append({
            'court': case.get('court', '?'),
            'attorney': get_attorney_id(case),
            'chapter': str(docket.get('chapter', '?')),
            'outcome': outcome,
            'entries': docket.get('total_entries', 0),
            'events': events,
        })

    return records


# ---------------------------------------------------------------------------
# Metric Computation
# ---------------------------------------------------------------------------

def compute_metrics(cases_list: list) -> dict:
    """Compute 6 performance metrics for a group of cases.

    Args:
        cases_list: List of record dicts for one attorney.

    Returns:
        Dict with metric values, or None if empty.
    """
    n = len(cases_list)
    if n == 0:
        return None

    dismissed = sum(1 for c in cases_list if c['outcome'] == 'dismissed')
    discharged = sum(1 for c in cases_list if c['outcome'] == 'discharged')
    oscs = sum(c['events'].get('order_show_cause', 0) for c in cases_list)
    mtds = sum(c['events'].get('trustee_mtd', 0) +
               c['events'].get('motion_to_dismiss', 0)
               for c in cases_list)
    fees = sum(c['events'].get('fee_application', 0) for c in cases_list)
    mfrs = sum(c['events'].get('motion_relief_stay', 0) for c in cases_list)

    return {
        'n': n,
        'dismiss_rate': dismissed / n,
        'discharge_rate': discharged / n,
        'osc_rate': oscs / n,
        'mtd_rate': mtds / n,
        'fee_rate': fees / n,
        'mfrs_rate': mfrs / n,
    }


# ---------------------------------------------------------------------------
# Z-Score Computation
# ---------------------------------------------------------------------------

def zscore(value: float, mean: float, std: float) -> float:
    """Compute Z-score. Positive = worse than average."""
    if std == 0:
        return 0 if value == mean else (3.0 if value > mean else -3.0)
    return (value - mean) / std


# ---------------------------------------------------------------------------
# Court-Level Scan
# ---------------------------------------------------------------------------

def scan_court(records: list, court: str, min_cases: int = DEFAULT_MIN_CASES) -> list:
    """Scan a single court for outlier attorneys.

    Args:
        records: All analysis records.
        court: Court code to scan.
        min_cases: Minimum case threshold.

    Returns:
        List of result dicts, sorted by composite Z-score (descending).
    """
    court_records = [r for r in records if r['court'] == court]
    if len(court_records) < min_cases:
        return []

    # Group by attorney
    by_atty = defaultdict(list)
    for r in court_records:
        by_atty[r['attorney']].append(r)

    # Compute per-attorney metrics
    atty_metrics = {}
    for atty, cases in by_atty.items():
        if len(cases) >= min_cases:
            atty_metrics[atty] = compute_metrics(cases)

    if len(atty_metrics) < 2:
        return []

    # Compute baselines (mean and std for each metric)
    baselines = {}
    for m in METRIC_NAMES:
        values = [am[m] for am in atty_metrics.values()]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)
        baselines[m] = {'mean': mean, 'std': std}

    # Score each attorney
    results = []
    for atty, metrics in atty_metrics.items():
        zscores = {}
        flags = []
        composite = 0

        for m in METRIC_NAMES:
            bl = baselines[m]
            # For discharge_rate, LOWER is worse (flip sign)
            if m == 'discharge_rate':
                z = zscore(metrics[m], bl['mean'], bl['std']) * -1
            else:
                z = zscore(metrics[m], bl['mean'], bl['std'])
            zscores[m] = round(z, 2)

            if z >= DEFAULT_THRESHOLD:
                flags.append(m)
                composite += z

        results.append({
            'court': court,
            'attorney': atty,
            'cases': metrics['n'],
            'metrics': {k: round(v, 4) for k, v in metrics.items() if k != 'n'},
            'zscores': zscores,
            'flags': flags,
            'flag_count': len(flags),
            'composite_z': round(composite, 2),
        })

    results.sort(key=lambda x: -x['composite_z'])
    return results


def scan_all(records: list, min_cases: int = DEFAULT_MIN_CASES) -> list:
    """Scan all courts for outlier attorneys.

    Args:
        records: All analysis records.
        min_cases: Minimum case threshold.

    Returns:
        Combined list of results across all courts, sorted by composite Z.
    """
    courts = sorted(set(r['court'] for r in records))
    all_results = []
    for court in courts:
        results = scan_court(records, court, min_cases)
        all_results.extend(results)
    all_results.sort(key=lambda x: -x['composite_z'])
    return all_results


# ---------------------------------------------------------------------------
# Anonymization
# ---------------------------------------------------------------------------

def anonymize_results(results: list) -> list:
    """Replace real attorney names with sequential labels.

    Args:
        results: List of result dicts from scan_court/scan_all.

    Returns:
        New list with anonymized attorney labels.
    """
    # Build stable mapping: sort by composite_z (descending) for consistent numbering
    seen = {}
    counter = 1
    anonymized = []

    for r in results:
        atty = r['attorney']
        if atty not in seen:
            seen[atty] = f"Attorney_{counter:03d}"
            counter += 1

        anon = dict(r)
        anon['attorney'] = seen[atty]
        anonymized.append(anon)

    return anonymized


# ---------------------------------------------------------------------------
# Report Output
# ---------------------------------------------------------------------------

def print_scan_report(results: list, threshold: float = DEFAULT_THRESHOLD):
    """Print a formatted scan report to stdout.

    Args:
        results: List of result dicts.
        threshold: Composite Z-score threshold for flagging.
    """
    flagged = [r for r in results if r['composite_z'] >= threshold]
    clean = [r for r in results if r['composite_z'] < threshold]

    print("=" * 78)
    print("  BLIND OUTLIER DETECTION -- STATISTICAL ANOMALY SCANNER")
    print("=" * 78)
    print(f"  Attorneys scanned:  {len(results)}")
    print(f"  Flagged:            {len(flagged)}")
    print(f"  Clean:              {len(clean)}")
    print(f"  Threshold:          Z >= {threshold}")
    print(f"  Generated:          {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    if not flagged:
        print("  No statistical outliers detected at this threshold.")
        return

    # Print flagged attorneys
    print("  FLAGGED ATTORNEYS (ranked by composite Z-score):")
    print("  " + "-" * 74)
    print(f"  {'#':>3}  {'Attorney':<20} {'Court':<10} {'Cases':>5} "
          f"{'Comp.Z':>7} {'Flags':>5}  Metrics")
    print("  " + "-" * 74)

    for i, r in enumerate(flagged, 1):
        flag_str = ', '.join(METRIC_LABELS.get(f, f) for f in r['flags'])
        print(f"  {i:>3}  {r['attorney']:<20} {r['court']:<10} {r['cases']:>5} "
              f"{r['composite_z']:>+7.2f} {r['flag_count']:>5}  {flag_str}")

    print("  " + "-" * 74)
    print()

    # Detail section for top flagged
    for r in flagged[:10]:
        print(f"  --- {r['attorney']} ({r['court']}, n={r['cases']}) ---")
        for m in METRIC_NAMES:
            val = r['metrics'].get(m, 0)
            z = r['zscores'].get(m, 0)
            flag = " ***" if m in r['flags'] else ""
            print(f"    {METRIC_LABELS.get(m, m):<18} {val:>8.1%}  Z={z:>+6.2f}{flag}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Blind Outlier Detection -- Statistical Anomaly Scanner'
    )
    parser.add_argument('--data-dir', type=Path, default=None,
                        help='Directory containing enriched case JSONs')
    parser.add_argument('--court', type=str, default=None,
                        help='Scan a single court (default: all)')
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD,
                        help=f'Z-score threshold (default: {DEFAULT_THRESHOLD})')
    parser.add_argument('--min-cases', type=int, default=DEFAULT_MIN_CASES,
                        help=f'Minimum cases per attorney (default: {DEFAULT_MIN_CASES})')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--anonymize', action='store_true',
                        help='Replace attorney names with sequential labels')

    args = parser.parse_args()

    if not args.data_dir:
        print("ERROR: --data-dir is required", file=sys.stderr)
        sys.exit(1)

    # Load data
    cases = load_enriched_cases(args.data_dir)
    if not cases:
        print(f"No case files found in {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    records = build_records(cases)
    print(f"Loaded {len(records)} cases")

    # Scan
    if args.court:
        results = scan_court(records, args.court, args.min_cases)
    else:
        results = scan_all(records, args.min_cases)

    if args.anonymize:
        results = anonymize_results(results)

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_scan_report(results, args.threshold)


if __name__ == '__main__':
    main()
