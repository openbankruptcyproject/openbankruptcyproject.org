#!/usr/bin/env python3
"""
screener_logic.py -- Section 1328(f) Discharge Bar Violation Screener
=====================================================================

Standalone Python implementation of the OBP 1328(f) screening methodology.
This script takes PACER Case Locator (PCL) CSV exports and identifies cases
where a Chapter 13 was filed despite a prior discharge that may bar a new
discharge under 11 U.S.C. 1328(f).

STATUTORY FRAMEWORK:
    1328(f)(1): Prior Ch.7/11/12 case FILED within 4 YEARS before current
                Ch.13 filing -> discharge barred.
    1328(f)(2): Prior Ch.13 case FILED within 2 YEARS before current Ch.13
                filing -> discharge barred.

CRITICAL: The statutory period runs from the FILING DATE of the prior case
to the filing date (order for relief) of the current Ch.13, NOT from the
discharge date. See In re Blendheim, 803 F.3d 477 (9th Cir. 2015).

The prior case must have resulted in a discharge, but the gap is measured
filing-to-filing.

BAPCPA effective date: October 17, 2005. Only Ch.13 cases filed on or after
that date are subject to 1328(f).

DATA FORMAT:
    Input: PACER Case Locator CSV exports (https://pcl.uscourts.gov)
    Expected columns: caseId, caseTitle, caseNumberFull, courtId,
                      bankruptcyChapter, dateFiled, dateDischarged, etc.

ANONYMIZATION:
    This script contains no attorney names, firm names, or specific case
    references. It implements pure statutory logic against public data.

USAGE:
    python screener_logic.py --data-dir ./csv-exports
    python screener_logic.py --data-dir ./csv-exports --output-json results.json
    python screener_logic.py --data-dir ./csv-exports --summary-only

DEPENDENCIES:
    Python 3.8+ standard library only. No pip packages required.
"""

import csv
import re
import os
import sys
import glob
import json
import argparse
from datetime import datetime
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# BAPCPA effective date -- 1328(f) only applies to cases filed on/after this
BAPCPA_EFFECTIVE = datetime(2005, 10, 17)

# Statutory windows (in days)
WINDOW_F1_DAYS = 4 * 365 + 1   # 4 years for 1328(f)(1) -- Ch.7/11/12 prior
WINDOW_F2_DAYS = 2 * 365 + 1   # 2 years for 1328(f)(2) -- Ch.13 prior

# Name suffix patterns to strip during normalization
SUFFIXES = re.compile(
    r'\b(jr\.?|sr\.?|ii|iii|iv|v|vi|vii|viii|2nd|3rd|4th)\s*$',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Name Normalization
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Normalize a debtor name for matching.

    Lowercases, strips suffixes (Jr., Sr., II, etc.), removes periods,
    strips 'NMN' (no middle name placeholder), collapses whitespace.

    Args:
        name: Raw debtor name string from PACER.

    Returns:
        Normalized name string suitable for matching.
    """
    if not name:
        return ""
    n = name.lower().strip()
    n = n.replace(".", "")
    n = re.sub(r'\bnmn\b', '', n)
    n = SUFFIXES.sub('', n).strip()
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def extract_names(case_title: str) -> list:
    """Extract individual debtor names from a case title.

    Joint cases use ' and ' as separator (e.g., "John Smith and Jane Smith").
    Returns list of normalized name keys for matching.
    Generates both full-name and first+last keys to catch middle-name variants.

    Args:
        case_title: The caseTitle field from PACER CSV.

    Returns:
        List of normalized name strings. Each debtor produces 1-2 keys:
        the full normalized name and (if different) a first+last key.
    """
    if not case_title:
        return []
    parts = re.split(r'\s+and\s+', case_title, flags=re.IGNORECASE)
    names = []
    for part in parts:
        norm = normalize_name(part)
        if norm:
            names.append(norm)
            tokens = norm.split()
            if len(tokens) >= 2:
                fl_key = f"{tokens[0]} {tokens[-1]}"
                if fl_key != norm:
                    names.append(fl_key)
    return names


# ---------------------------------------------------------------------------
# Date Parsing
# ---------------------------------------------------------------------------

def parse_date(date_str: str):
    """Parse a YYYY-MM-DD date string from PACER CSV.

    Args:
        date_str: Date string in YYYY-MM-DD format.

    Returns:
        datetime object, or None if unparseable.
    """
    if not date_str or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d')
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# CSV Loading
# ---------------------------------------------------------------------------

def discover_csvs(data_dir: Path):
    """Discover all PACER CSV files in the data directory.

    Expected filename pattern: api_*.csv (PACER Case Locator export format).

    Args:
        data_dir: Path to directory containing CSV files.

    Returns:
        List of Path objects for discovered CSV files.
    """
    pattern = str(data_dir / "api_*.csv")
    return sorted(Path(p) for p in glob.glob(pattern))


def load_all_cases(data_dir: Path):
    """Load all cases from PACER CSV exports, deduplicating by caseId.

    Args:
        data_dir: Path to directory containing CSV files.

    Returns:
        Tuple of (cases_list, stats_dict) where:
        - cases_list: list of dicts (one per unique case)
        - stats_dict: loading statistics
    """
    csv_files = discover_csvs(data_dir)

    if not csv_files:
        print("ERROR: No matching CSV files found.", file=sys.stderr)
        print(f"  Searched: {data_dir}", file=sys.stderr)
        print(f"  Expected pattern: api_*.csv", file=sys.stderr)
        sys.exit(1)

    seen = {}
    total_rows = 0

    for csv_path in csv_files:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                case_id = row.get('caseId', '').strip()
                if case_id and case_id not in seen:
                    seen[case_id] = row

    stats = {
        'files_loaded': len(csv_files),
        'total_rows': total_rows,
        'unique_cases': len(seen),
    }

    print(f"Loaded {len(seen):,} unique cases from {len(csv_files)} files "
          f"({total_rows:,} total rows)")
    return list(seen.values()), stats


# ---------------------------------------------------------------------------
# Debtor Grouping
# ---------------------------------------------------------------------------

def group_by_debtor(cases: list) -> dict:
    """Group cases by normalized debtor name.

    This is the core matching step: we need to find all cases filed by or
    for the same individual to detect repeat filings.

    Args:
        cases: List of case dicts from load_all_cases().

    Returns:
        Dict mapping normalized name key -> list of case dicts.
    """
    groups = defaultdict(list)
    for case in cases:
        title = case.get('caseTitle', '')
        name_keys = extract_names(title)
        for key in name_keys:
            groups[key].append(case)
    return groups


# ---------------------------------------------------------------------------
# 1328(f) Screening Core
# ---------------------------------------------------------------------------

def screen_1328f(cases: list):
    """Screen all cases for 1328(f) discharge bar violations.

    Algorithm:
    1. Group cases by normalized debtor name.
    2. For each debtor with 2+ cases, identify:
       - Cases that received a discharge (potential "prior" cases)
       - Chapter 13 filings (potential "current" cases subject to the bar)
    3. For each Ch.13 filing, check every prior discharged case:
       - Was the prior case filed within the statutory window?
       - Is the prior case a different chapter (f)(1) or same Ch.13 (f)(2)?
    4. Deduplicate hits by (prior_case_id, ch13_case_id, section).

    Args:
        cases: List of case dicts from load_all_cases().

    Returns:
        Dict with keys:
        - 'f1_hits': list of 1328(f)(1) violations (4-year bar)
        - 'f2_hits': list of 1328(f)(2) violations (2-year bar)
        - 'stats': screening statistics
    """
    debtor_groups = group_by_debtor(cases)
    repeat_groups = {k: v for k, v in debtor_groups.items() if len(v) >= 2}
    print(f"Found {len(repeat_groups):,} debtor name keys with 2+ cases")

    f1_seen = set()
    f2_seen = set()
    f1_hits = []
    f2_hits = []
    pre_bapcpa_skipped = 0

    for name_key, group_cases in repeat_groups.items():
        # Deduplicate within group by case ID
        unique = {}
        for c in group_cases:
            cid = c.get('caseId', '')
            if cid not in unique:
                unique[cid] = c
        cases_list = list(unique.values())

        if len(cases_list) < 2:
            continue

        # Identify discharged cases (potential priors)
        discharged = [c for c in cases_list
                      if parse_date(c.get('dateDischarged', ''))]

        # Identify Ch.13 filings (potential current cases)
        ch13_filings = [c for c in cases_list
                        if c.get('bankruptcyChapter', '').strip() == '13']

        if not discharged or not ch13_filings:
            continue

        for ch13 in ch13_filings:
            ch13_filed = parse_date(ch13.get('dateFiled', ''))
            if not ch13_filed:
                continue

            # Skip pre-BAPCPA cases
            if ch13_filed < BAPCPA_EFFECTIVE:
                pre_bapcpa_skipped += 1
                continue

            ch13_case_id = ch13.get('caseId', '')

            for prior in discharged:
                prior_case_id = prior.get('caseId', '')
                if prior_case_id == ch13_case_id:
                    continue

                prior_discharge = parse_date(prior.get('dateDischarged', ''))
                if not prior_discharge:
                    continue

                # Gap measured from prior FILING date, not discharge date
                prior_filed = parse_date(prior.get('dateFiled', ''))
                if not prior_filed:
                    continue

                # Prior must be before current
                if prior_filed >= ch13_filed:
                    continue

                # Prior discharge must be before current filing
                if prior_discharge >= ch13_filed:
                    continue

                gap_days = (ch13_filed - prior_filed).days
                prior_ch = prior.get('bankruptcyChapter', '').strip()

                # Determine which subsection applies
                # 1328(f)(1): Prior Ch.7, 11, or 12 -- 4 year bar
                # 1328(f)(2): Prior Ch.13 -- 2 year bar
                hit = None

                if prior_ch in ('7', '11', '12'):
                    if gap_days <= WINDOW_F1_DAYS:
                        dedup_key = (prior_case_id, ch13_case_id, 'f1')
                        if dedup_key not in f1_seen:
                            f1_seen.add(dedup_key)
                            hit = {
                                'section': '1328(f)(1)',
                                'window_years': 4,
                                'gap_days': gap_days,
                                'gap_years': round(gap_days / 365.25, 2),
                                'prior_chapter': prior_ch,
                                'prior_filed': prior_filed.strftime('%Y-%m-%d'),
                                'prior_discharged': prior_discharge.strftime('%Y-%m-%d'),
                                'ch13_filed': ch13_filed.strftime('%Y-%m-%d'),
                            }
                            f1_hits.append(hit)

                elif prior_ch == '13':
                    if gap_days <= WINDOW_F2_DAYS:
                        dedup_key = (prior_case_id, ch13_case_id, 'f2')
                        if dedup_key not in f2_seen:
                            f2_seen.add(dedup_key)
                            hit = {
                                'section': '1328(f)(2)',
                                'window_years': 2,
                                'gap_days': gap_days,
                                'gap_years': round(gap_days / 365.25, 2),
                                'prior_chapter': prior_ch,
                                'prior_filed': prior_filed.strftime('%Y-%m-%d'),
                                'prior_discharged': prior_discharge.strftime('%Y-%m-%d'),
                                'ch13_filed': ch13_filed.strftime('%Y-%m-%d'),
                            }
                            f2_hits.append(hit)

    stats = {
        'total_cases': len(cases),
        'repeat_debtor_groups': len(repeat_groups),
        'pre_bapcpa_skipped': pre_bapcpa_skipped,
        'f1_violations': len(f1_hits),
        'f2_violations': len(f2_hits),
        'total_violations': len(f1_hits) + len(f2_hits),
    }

    return {
        'f1_hits': f1_hits,
        'f2_hits': f2_hits,
        'stats': stats,
    }


# ---------------------------------------------------------------------------
# FJC IDB Screening (National Analysis)
# ---------------------------------------------------------------------------

def screen_fjc_national(db_path: str, start_year: int = 2008, end_year: int = 2024):
    """Screen the FJC IDB for prior filers who received discharge.

    This is the national-scale analysis. The FJC data does not contain
    individual case filing dates needed for exact gap calculation, but it
    does contain:
    - prfile: whether the debtor reported a prior filing
    - d1fdsp: the disposition (discharge/dismissal)

    By counting prior filers who received discharge, we identify the
    391,951 pool. The 43% estimated bar rate is then applied.

    Args:
        db_path: Path to FJC IDB SQLite database.
        start_year: First fiscal year to include.
        end_year: Last fiscal year to include.

    Returns:
        Dict with national and per-district statistics.
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Disposition code mappings
    discharged_codes = ('A', 'B', '1')
    dismissed_codes = ('H', 'I', 'J', 'K', 'T', 'U', '5')
    estimated_bar_rate = 0.43

    # Query: for each district, count Ch.13 filings by prior-filer status
    # and disposition. Deduplicate by casekey (take latest record).
    cur.execute("""
        WITH latest AS (
            SELECT casekey, MAX(id) AS max_id
            FROM fjc_cases
            WHERE crntchp = '13'
              AND CAST(filefy AS INTEGER) BETWEEN ? AND ?
            GROUP BY casekey
        )
        SELECT f.district, f.d1fdsp, f.prfile, f.d1fprse
        FROM fjc_cases f
        JOIN latest l ON f.id = l.max_id
    """, (start_year, end_year))

    # Accumulate per-district
    districts = defaultdict(lambda: {
        'total': 0, 'discharged': 0, 'dismissed': 0,
        'prior': 0, 'prior_discharged': 0, 'prior_dismissed': 0,
        'prose': 0,
    })

    for district, dsp, prfile, fprse in cur:
        d = districts[district]
        d['total'] += 1

        dsp_s = (dsp or '').strip()
        is_disch = dsp_s in discharged_codes
        is_dism = dsp_s in dismissed_codes
        is_prior = (prfile or '').strip().upper() == 'Y'
        is_prose = (fprse or '').strip().lower() == 'y'

        if is_disch:
            d['discharged'] += 1
        elif is_dism:
            d['dismissed'] += 1

        if is_prior:
            d['prior'] += 1
            if is_disch:
                d['prior_discharged'] += 1
            elif is_dism:
                d['prior_dismissed'] += 1

        if is_prose:
            d['prose'] += 1

    conn.close()

    # Compute rates
    results = []
    national = {
        'total': 0, 'discharged': 0, 'dismissed': 0,
        'prior': 0, 'prior_discharged': 0, 'prose': 0,
    }

    for district, d in sorted(districts.items()):
        closed = d['discharged'] + d['dismissed']
        prior_closed = d['prior_discharged'] + d['prior_dismissed']

        result = {
            'district': district,
            'total_filed': d['total'],
            'discharged': d['discharged'],
            'dismissed': d['dismissed'],
            'dismiss_rate': round(d['dismissed'] / closed * 100, 1) if closed > 0 else None,
            'prior_filers': d['prior'],
            'prior_rate': round(d['prior'] / d['total'] * 100, 1) if d['total'] > 0 else 0,
            'prior_discharged': d['prior_discharged'],
            'prior_discharge_rate': (
                round(d['prior_discharged'] / prior_closed * 100, 1)
                if prior_closed >= 20 else None
            ),
            'est_violations': (
                round(d['prior_discharged'] * estimated_bar_rate)
                if prior_closed >= 20 else None
            ),
            'pro_se_rate': round(d['prose'] / d['total'] * 100, 1) if d['total'] > 0 else 0,
        }
        results.append(result)

        # Accumulate national
        for key in ('total', 'discharged', 'dismissed', 'prior', 'prior_discharged', 'prose'):
            national[key] += d[key]

    national_closed = national['discharged'] + national['dismissed']
    national_summary = {
        'period': f'FY{start_year}-{end_year}',
        'total_filed': national['total'],
        'discharged': national['discharged'],
        'dismissed': national['dismissed'],
        'dismiss_rate': round(national['dismissed'] / national_closed * 100, 1),
        'prior_filers': national['prior'],
        'prior_rate': round(national['prior'] / national['total'] * 100, 1),
        'prior_discharged': national['prior_discharged'],
        'prior_discharge_rate': round(
            national['prior_discharged'] /
            (national['prior_discharged'] + national['dismissed']) * 100, 1
        ),
        'est_violations': round(national['prior_discharged'] * estimated_bar_rate),
        'districts': len(districts),
    }

    return {
        'national': national_summary,
        'districts': results,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_summary(results: dict):
    """Print a human-readable summary of screening results."""
    stats = results['stats']
    f1 = results['f1_hits']
    f2 = results['f2_hits']

    print("\n" + "=" * 70)
    print("  SECTION 1328(f) DISCHARGE BAR SCREENING RESULTS")
    print("=" * 70)
    print(f"  Cases screened:          {stats['total_cases']:,}")
    print(f"  Repeat debtor groups:    {stats['repeat_debtor_groups']:,}")
    print(f"  Pre-BAPCPA skipped:      {stats['pre_bapcpa_skipped']:,}")
    print()
    print(f"  1328(f)(1) violations:   {stats['f1_violations']:,}  (4-year bar, Ch.7/11/12 prior)")
    print(f"  1328(f)(2) violations:   {stats['f2_violations']:,}  (2-year bar, Ch.13 prior)")
    print(f"  TOTAL VIOLATIONS:        {stats['total_violations']:,}")
    print("=" * 70)

    if f1:
        gaps = [h['gap_days'] for h in f1]
        print(f"\n  (f)(1) gap range: {min(gaps)}-{max(gaps)} days "
              f"(median {sorted(gaps)[len(gaps)//2]})")

    if f2:
        gaps = [h['gap_days'] for h in f2]
        print(f"  (f)(2) gap range: {min(gaps)}-{max(gaps)} days "
              f"(median {sorted(gaps)[len(gaps)//2]})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Section 1328(f) Discharge Bar Violation Screener'
    )
    parser.add_argument('--data-dir', type=Path, required=True,
                        help='Directory containing PACER CSV exports')
    parser.add_argument('--output-json', type=Path, default=None,
                        help='Write results to JSON file')
    parser.add_argument('--summary-only', action='store_true',
                        help='Print summary only, skip per-hit details')
    parser.add_argument('--fjc-db', type=Path, default=None,
                        help='Path to FJC IDB SQLite for national screening')
    parser.add_argument('--start-year', type=int, default=2008,
                        help='First fiscal year (default: 2008)')
    parser.add_argument('--end-year', type=int, default=2024,
                        help='Last fiscal year (default: 2024)')

    args = parser.parse_args()

    if args.fjc_db:
        # National FJC screening mode
        print("Running national FJC IDB screening...")
        results = screen_fjc_national(str(args.fjc_db), args.start_year, args.end_year)
        nat = results['national']
        print(f"\nNational: {nat['total_filed']:,} filed, "
              f"{nat['prior_filers']:,} prior filers, "
              f"{nat['prior_discharged']:,} prior filers discharged, "
              f"~{nat['est_violations']:,} estimated violations")
        if args.output_json:
            with open(args.output_json, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results written to {args.output_json}")
        return

    # PACER CSV screening mode
    cases, load_stats = load_all_cases(args.data_dir)
    results = screen_1328f(cases)
    print_summary(results)

    if args.output_json:
        output = {
            'load_stats': load_stats,
            'screening': results['stats'],
            'f1_hits': results['f1_hits'],
            'f2_hits': results['f2_hits'],
        }
        with open(args.output_json, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nResults written to {args.output_json}")


if __name__ == '__main__':
    main()
