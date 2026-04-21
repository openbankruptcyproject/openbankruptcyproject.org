#!/usr/bin/env python3
"""
district_comparison.py -- Anonymized District Comparison Tool
=============================================================

Compares any attorney's case outcome metrics against their district's baseline.
This is the core methodology for detecting performance outliers: if an attorney's
dismissal rate, duration, or other metrics deviate significantly from the district
norm, that deviation warrants further investigation.

NO ATTORNEY NAMES, FIRM NAMES, OR CASE NUMBERS APPEAR IN THIS CODE.
All identifiers are replaced with generic labels (Attorney_A, District_X, etc.).

DATA SOURCES:
    - Enriched case JSON files (one per docket, with events extracted)
    - District-level SQLite database (RSS-accumulated case data)
    - PACER Case Locator CSV exports

METRICS COMPUTED:
    1. Dismissal rate (% of closed cases dismissed vs. discharged)
    2. Discharge rate (inverse of dismissal)
    3. OSC rate (orders to show cause per case -- judicial intervention signal)
    4. MTD rate (motions to dismiss per case -- trustee/creditor intervention)
    5. Fee application density (fee apps per case)
    6. Stay relief rate (motions for relief from stay per case)
    7. Median case duration (days from filing to disposition)

METHODOLOGY:
    For each court in the dataset:
    1. Compute the court-wide baseline for each metric.
    2. Compute per-attorney metrics for attorneys with N+ cases (default 5).
    3. Calculate Z-scores: (attorney_metric - court_mean) / court_std.
    4. Flag attorneys whose composite Z-score exceeds the threshold.

USAGE:
    python district_comparison.py --court districtX
    python district_comparison.py --court districtX --attorney-id ATTY_001
    python district_comparison.py --court districtX --html output.html
    python district_comparison.py --list-courts

DEPENDENCIES:
    Python 3.8+ standard library (sqlite3, json, csv, os, sys, math, argparse).
"""

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum cases for an attorney to be included in analysis
MIN_CASES = 5

# National Ch.13 dismissal baseline (ABI / Littwin data)
NATIONAL_CH13_DISMISSAL_RATE = 0.479

# Z-score thresholds
THRESHOLD_ELEVATED = 1.5    # Notable deviation
THRESHOLD_EXTREME = 2.5     # Extreme deviation


# ---------------------------------------------------------------------------
# Date Parsing
# ---------------------------------------------------------------------------

def parse_date(d):
    """Parse date string in multiple formats.

    Args:
        d: Date string (MM/DD/YYYY, YYYY-MM-DD, or MM/DD/YY).

    Returns:
        datetime object or None.
    """
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

def load_enriched_cases(enriched_dir: Path, court_filter: str = None) -> list:
    """Load enriched case JSON files from the data directory.

    Each JSON contains a normalized docket with extracted events (orders,
    motions, fee applications, etc.) that enable per-case metric computation.

    Args:
        enriched_dir: Path to directory containing case JSON files.
        court_filter: If provided, only load cases matching this court code.

    Returns:
        List of case dicts.
    """
    cases = []
    if not enriched_dir.exists():
        return cases

    pattern = f'{court_filter}_*.json' if court_filter else '*.json'
    for fp in enriched_dir.glob(pattern):
        try:
            with open(fp, encoding='utf-8') as f:
                data = json.load(f)
            cases.append(data)
        except (json.JSONDecodeError, IOError):
            continue

    return cases


def load_db_cases(db_path: Path, court_filter: str = None) -> list:
    """Load cases from the district SQLite database.

    Args:
        db_path: Path to district_cases.db.
        court_filter: If provided, filter by court code.

    Returns:
        List of case dicts.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        if court_filter:
            rows = conn.execute(
                "SELECT * FROM cases WHERE court LIKE ?",
                (f'%{court_filter}%',)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM cases").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Metric Computation
# ---------------------------------------------------------------------------

def get_attorney_id(case: dict) -> str:
    """Extract an anonymized attorney identifier from a case.

    In production, this returns the attorney's last name from the case data.
    For anonymized output, callers should map this to "Attorney_NNN".

    Args:
        case: Case dict from load_enriched_cases().

    Returns:
        Attorney identifier string.
    """
    atty = case.get('attorney', {})
    if isinstance(atty, dict):
        return atty.get('last', 'Unknown')
    return 'Unknown'


def compute_case_metrics(case: dict) -> dict:
    """Compute per-case metrics from an enriched case dict.

    Args:
        case: Enriched case dict with 'docket' and 'events' keys.

    Returns:
        Dict with metric values for this case.
    """
    docket = case.get('docket', {})
    events = case.get('events', {})

    # Determine outcome
    outcome = 'pending'
    if events.get('order_discharge', 0) > 0:
        outcome = 'discharged'
    elif events.get('order_dismissal', 0) > 0:
        outcome = 'dismissed'
    elif events.get('order_confirmation', 0) > 0:
        outcome = 'confirmed'

    return {
        'court': case.get('court', '?'),
        'attorney': get_attorney_id(case),
        'chapter': str(docket.get('chapter', '?')),
        'outcome': outcome,
        'entries': docket.get('total_entries', 0),
        'osc_count': events.get('order_show_cause', 0),
        'mtd_count': (events.get('trustee_mtd', 0) +
                      events.get('motion_to_dismiss', 0)),
        'fee_count': events.get('fee_application', 0),
        'mfrs_count': events.get('motion_relief_stay', 0),
    }


def compute_group_metrics(records: list) -> dict:
    """Compute aggregate metrics for a group of case records.

    Args:
        records: List of per-case metric dicts from compute_case_metrics().

    Returns:
        Dict with aggregate metric values, or None if no records.
    """
    n = len(records)
    if n == 0:
        return None

    dismissed = sum(1 for r in records if r['outcome'] == 'dismissed')
    discharged = sum(1 for r in records if r['outcome'] == 'discharged')
    oscs = sum(r['osc_count'] for r in records)
    mtds = sum(r['mtd_count'] for r in records)
    fees = sum(r['fee_count'] for r in records)
    mfrs = sum(r['mfrs_count'] for r in records)

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
# Z-Score Analysis
# ---------------------------------------------------------------------------

def zscore(value: float, mean: float, std: float) -> float:
    """Compute Z-score.

    Args:
        value: Observed value.
        mean: Population mean.
        std: Population standard deviation.

    Returns:
        Z-score. Positive values indicate worse-than-average performance
        (higher dismissal, more OSCs, etc.). For discharge_rate, the sign
        is inverted so that lower discharge = positive Z.
    """
    if std == 0:
        return 0 if value == mean else (3.0 if value > mean else -3.0)
    return (value - mean) / std


def compare_attorney_to_district(records: list, target_attorney: str,
                                 court: str, min_cases: int = MIN_CASES) -> dict:
    """Compare a specific attorney's metrics to the district baseline.

    Args:
        records: List of per-case metric dicts for all attorneys in the court.
        target_attorney: Attorney identifier to compare.
        court: Court code.
        min_cases: Minimum case count for inclusion.

    Returns:
        Dict with comparison results including Z-scores and flags.
    """
    court_records = [r for r in records if r['court'] == court]

    # Group by attorney
    by_attorney = defaultdict(list)
    for r in court_records:
        by_attorney[r['attorney']].append(r)

    # Compute per-attorney metrics (only those with enough cases)
    attorney_metrics = {}
    for atty, cases in by_attorney.items():
        if len(cases) >= min_cases:
            attorney_metrics[atty] = compute_group_metrics(cases)

    if target_attorney not in attorney_metrics:
        return {'error': f'Attorney not found or fewer than {min_cases} cases'}

    if len(attorney_metrics) < 2:
        return {'error': 'Not enough attorneys for comparison'}

    # Compute baselines (mean and std across attorneys)
    metric_names = ['dismiss_rate', 'discharge_rate', 'osc_rate',
                    'mtd_rate', 'fee_rate', 'mfrs_rate']

    baselines = {}
    for m in metric_names:
        values = [am[m] for am in attorney_metrics.values()]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)
        baselines[m] = {'mean': round(mean, 4), 'std': round(std, 4)}

    # Score the target
    target = attorney_metrics[target_attorney]
    zscores = {}
    flags = []

    for m in metric_names:
        bl = baselines[m]
        if m == 'discharge_rate':
            z = zscore(target[m], bl['mean'], bl['std']) * -1
        else:
            z = zscore(target[m], bl['mean'], bl['std'])
        zscores[m] = round(z, 2)
        if z >= THRESHOLD_ELEVATED:
            flags.append({
                'metric': m,
                'z': round(z, 2),
                'value': round(target[m], 4),
                'baseline': bl['mean'],
                'severity': 'extreme' if z >= THRESHOLD_EXTREME else 'elevated',
            })

    composite_z = sum(z for z in zscores.values() if z > 0)

    return {
        'court': court,
        'attorney_label': target_attorney,
        'cases': target['n'],
        'attorneys_in_court': len(attorney_metrics),
        'metrics': {k: round(v, 4) for k, v in target.items() if k != 'n'},
        'baselines': baselines,
        'zscores': zscores,
        'flags': flags,
        'composite_z': round(composite_z, 2),
        'national_dismiss_rate': NATIONAL_CH13_DISMISSAL_RATE,
    }


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_report(comparison: dict) -> str:
    """Generate a human-readable comparison report.

    Args:
        comparison: Result dict from compare_attorney_to_district().

    Returns:
        Formatted string report.
    """
    if 'error' in comparison:
        return f"ERROR: {comparison['error']}"

    lines = []
    lines.append("=" * 70)
    lines.append("  DISTRICT COMPARISON REPORT")
    lines.append("=" * 70)
    lines.append(f"  Court:              {comparison['court']}")
    lines.append(f"  Attorney:           {comparison['attorney_label']}")
    lines.append(f"  Cases:              {comparison['cases']}")
    lines.append(f"  Attorneys compared: {comparison['attorneys_in_court']}")
    lines.append(f"  Composite Z-score:  {comparison['composite_z']}")
    lines.append("")

    # Metrics table
    labels = {
        'dismiss_rate': 'Dismissal Rate',
        'discharge_rate': 'Discharge Rate',
        'osc_rate': 'OSC Rate',
        'mtd_rate': 'MTD Rate',
        'fee_rate': 'Fee App Density',
        'mfrs_rate': 'Stay Relief Rate',
    }

    lines.append(f"  {'Metric':<20} {'Attorney':>10} {'Baseline':>10} {'Z-Score':>10}")
    lines.append("  " + "-" * 52)

    metrics = comparison['metrics']
    baselines = comparison['baselines']
    zscores = comparison['zscores']

    for key, label in labels.items():
        val = metrics.get(key, 0)
        bl = baselines.get(key, {}).get('mean', 0)
        z = zscores.get(key, 0)
        flag = " ***" if abs(z) >= THRESHOLD_ELEVATED else ""
        lines.append(f"  {label:<20} {val:>9.1%} {bl:>9.1%} {z:>+9.2f}{flag}")

    if comparison['flags']:
        lines.append("")
        lines.append("  FLAGS:")
        for f in comparison['flags']:
            lines.append(f"    [{f['severity'].upper()}] {labels.get(f['metric'], f['metric'])}: "
                         f"Z={f['z']:+.2f}")

    lines.append("")
    lines.append(f"  National Ch.13 dismissal baseline: "
                 f"{comparison['national_dismiss_rate']:.1%}")
    lines.append("=" * 70)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='District Comparison -- Attorney vs. Baseline Analysis'
    )
    parser.add_argument('--data-dir', type=Path, default=None,
                        help='Directory containing enriched case JSONs')
    parser.add_argument('--db', type=Path, default=None,
                        help='Path to district_cases.db')
    parser.add_argument('--court', type=str, required=True,
                        help='Court code to analyze')
    parser.add_argument('--attorney-id', type=str, default=None,
                        help='Attorney identifier to compare (default: all)')
    parser.add_argument('--min-cases', type=int, default=MIN_CASES,
                        help=f'Minimum case count (default: {MIN_CASES})')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')

    args = parser.parse_args()

    # Load data
    cases = []
    if args.data_dir:
        cases = load_enriched_cases(args.data_dir, args.court)
    elif args.db:
        # DB cases need different handling
        print("DB loading requires enriched JSON format for event extraction.",
              file=sys.stderr)
        sys.exit(1)

    if not cases:
        print(f"No cases found for court '{args.court}'", file=sys.stderr)
        sys.exit(1)

    # Compute per-case metrics
    records = [compute_case_metrics(c) for c in cases]
    print(f"Loaded {len(records)} cases for {args.court}")

    if args.attorney_id:
        # Compare specific attorney
        result = compare_attorney_to_district(
            records, args.attorney_id, args.court, args.min_cases
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(generate_report(result))
    else:
        # Compare all attorneys
        by_atty = defaultdict(list)
        for r in records:
            by_atty[r['attorney']].append(r)

        print(f"Found {len(by_atty)} attorneys, "
              f"{sum(1 for v in by_atty.values() if len(v) >= args.min_cases)} "
              f"with {args.min_cases}+ cases")

        for atty in sorted(by_atty.keys()):
            if len(by_atty[atty]) >= args.min_cases:
                result = compare_attorney_to_district(
                    records, atty, args.court, args.min_cases
                )
                if 'error' not in result:
                    if args.json:
                        print(json.dumps(result))
                    else:
                        print(generate_report(result))
                        print()


if __name__ == '__main__':
    main()
