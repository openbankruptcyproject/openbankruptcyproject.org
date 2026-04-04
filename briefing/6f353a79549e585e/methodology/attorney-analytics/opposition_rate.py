#!/usr/bin/env python3
"""
opposition_rate.py -- Creditor Motion Response Rate Calculator
==============================================================

Parses downloaded PACER docket HTML files and calculates how frequently
a debtor's attorney files responses/oppositions to creditor motions.

ANONYMIZATION:
    No attorney names, firm names, or case numbers appear in this code.
    Replace TARGET_FIRM_PATTERN and CREDITOR_FIRM_PATTERN with the actual
    regex patterns for the firm(s) being analyzed.

METHODOLOGY:
    1. Scan docket HTML files for cases attributed to the target firm.
    2. Identify creditor motions (MFRS, MTD, OBJ_CONF, etc.) -- exclude
       trustee-initiated motions and non-filing entries (receipts, orders).
    3. For each creditor motion, search subsequent docket entries for a
       debtor response/opposition referencing the motion's document number.
    4. Also check for agreed orders (imply negotiation, count as response).
    5. Compute response rate: responded / total creditor motions.

MOTION TYPES TRACKED:
    - MFRS: Motion for Relief from Stay
    - MTD: Motion to Dismiss
    - OBJ_CONF: Objection to Confirmation/Plan
    - OBJ_DISCH: Objection to Discharge
    - OBJ_CLAIM: Objection to Exemption/Claim
    - CONVERT: Motion to Convert
    - ADEQUATE: Motion for Adequate Protection

USAGE:
    python opposition_rate.py --data-dir ./pacer_docs
    python opposition_rate.py --data-dir ./pacer_docs --courts districtA districtB

DEPENDENCIES:
    Python 3.8+ standard library (os, re, html, collections).
"""

import os
import re
import html
import argparse
from collections import defaultdict


# ---------------------------------------------------------------------------
# Configuration -- Replace these patterns for your analysis
# ---------------------------------------------------------------------------

# Pattern to identify the target firm/attorney in docket HTML.
# In production, this matches the specific firm name and attorney names.
TARGET_FIRM_PATTERN = re.compile(
    r'(?i)(target\s+firm|attorney_a,?\s+firstname|firm\s+name\s+llc)',
    re.IGNORECASE
)

# Pattern to identify a specific creditor attorney for sub-analysis.
CREDITOR_FIRM_PATTERN = re.compile(
    r'(?i)(creditor_firm_a|creditor_firm_b)',
    re.IGNORECASE
)

# Courts to scan
DEFAULT_COURTS = ['districtA', 'districtB']


# ---------------------------------------------------------------------------
# Motion Classification Patterns
# ---------------------------------------------------------------------------

MOTION_TYPES = [
    (re.compile(r'(?i)motion\s+for\s+relief\s+from\s+(the\s+)?stay'), 'MFRS'),
    (re.compile(r'(?i)motion\s+to\s+dismiss'), 'MTD'),
    (re.compile(r'(?i)objection\s+to\s+(confirmation|plan)'), 'OBJ_CONF'),
    (re.compile(r'(?i)objection\s+to\s+discharge'), 'OBJ_DISCH'),
    (re.compile(r'(?i)objection\s+to\s+(exemption|claim)'), 'OBJ_CLAIM'),
    (re.compile(r'(?i)motion\s+to\s+convert'), 'CONVERT'),
    (re.compile(r'(?i)motion\s+for\s+adequate\s+protection'), 'ADEQUATE'),
]

# Entries that are NOT actual filings (orders, receipts, notices)
NOT_A_FILING = re.compile(
    r'(?i)(receipt\s+of|certificate\s+of\s+mailing|'
    r'hearing\s+(held|set|continued)|'
    r'order\s+(of\s+the\s+court|granting|denying|sustaining|dismissing|'
    r'overruling|on\s+motion|resolving|re:)|'
    r'minute\s+sheet|courtroom|auto-?docketed|'
    r'trustee\s+withdraws|trustee.s\s+certificate|proposed\s+order)'
)

# Trustee-filed entries (exclude from creditor motion count)
TRUSTEE_FILER = re.compile(
    r'(?i)(filed\s+by\s+trustee|trustee.s\s+(motion|objection)|'
    r'filed\s+by\s+.*trustee\s+\w+|chapter\s+13\s+trustee)'
)

# Debtor-filed entries
DEBTOR_FILER = re.compile(
    r'(?i)(filed\s+by\s+debtor|filed\s+by\s+joint\s+debtor)'
)

# Check for page count (indicates actual filing vs. text-only entry)
HAS_PAGES = re.compile(r'\(\d+\s+pgs?\)')


# ---------------------------------------------------------------------------
# Docket Parsing
# ---------------------------------------------------------------------------

def parse_docket_entries(html_content: str) -> list:
    """Extract docket entries from PACER docket HTML.

    Args:
        html_content: Raw HTML from a PACER docket report.

    Returns:
        List of dicts with 'text', 'date', and 'doc' (document number) keys.
    """
    entries = re.findall(r'<tr[^>]*>(.*?)</tr>', html_content, re.DOTALL)
    parsed = []

    for entry in entries:
        text = re.sub(r'<[^>]+>', ' ', entry)
        text = html.unescape(text).strip()
        text = re.sub(r'\s+', ' ', text)

        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        date = date_match.group(1) if date_match else None

        doc_match = re.search(r'(?:^|\s)(\d+)\s+\(\d+\s+pgs?\)', text)
        if not doc_match:
            doc_match = re.search(r'(?:^|\s)(\d+)\s+\(', text)
        doc_num = int(doc_match.group(1)) if doc_match else None

        parsed.append({'text': text, 'date': date, 'doc': doc_num})

    return parsed


def identify_creditor_motions(entries: list) -> list:
    """Identify creditor motions from parsed docket entries.

    Filters out: non-filings, trustee motions, debtor's own motions.

    Args:
        entries: List of parsed entry dicts.

    Returns:
        List of creditor motion dicts.
    """
    motions = []
    for p in entries:
        text = p['text']
        if NOT_A_FILING.search(text):
            continue
        if not HAS_PAGES.search(text):
            continue
        if TRUSTEE_FILER.search(text):
            continue

        mtype = None
        for pat, mt in MOTION_TYPES:
            if pat.search(text):
                mtype = mt
                break
        if not mtype:
            continue

        # Exclude debtor's own motions (unless it's a response)
        if DEBTOR_FILER.search(text) and not re.search(r'(?i)response\s+to', text):
            continue

        is_creditor_firm = bool(CREDITOR_FIRM_PATTERN.search(text))
        motions.append({
            'doc': p['doc'],
            'date': p['date'],
            'text': text[:300],
            'type': mtype,
            'is_creditor_firm': is_creditor_firm,
            'responded': False,
            'response_doc': None,
        })

    return motions


def match_responses(entries: list, motions: list):
    """Match debtor responses to creditor motions.

    Matching strategies:
    1. "Related document" reference in the response entry.
    2. Motion type keyword match (e.g., response mentions "relief from stay").
    3. Agreed orders referencing the motion's document number.

    Modifies motions in place (sets 'responded' and 'response_doc').

    Args:
        entries: List of parsed entry dicts.
        motions: List of creditor motion dicts from identify_creditor_motions().
    """
    # Pass 1: Debtor responses
    for p in entries:
        text = p['text']
        if not HAS_PAGES.search(text):
            continue
        if not re.search(r'(?i)(response|opposition)', text):
            continue
        if not DEBTOR_FILER.search(text):
            continue

        # Match by related document reference
        related_doc = re.search(r'related\s+document\D*?(\d+)', text)
        if related_doc:
            ref_doc = int(related_doc.group(1))
            for cm in motions:
                if cm['doc'] == ref_doc and not cm['responded']:
                    cm['responded'] = True
                    cm['response_doc'] = p['doc']
                    break

        # Match by motion type keyword
        for cm in motions:
            if cm['responded']:
                continue
            if cm['type'] == 'MFRS' and re.search(r'(?i)motion\s+for\s+relief', text):
                cm['responded'] = True
                cm['response_doc'] = p['doc']
                break
            elif cm['type'] == 'OBJ_CONF' and re.search(r'(?i)objection\s+to\s+confirmation', text):
                cm['responded'] = True
                cm['response_doc'] = p['doc']
                break

    # Pass 2: Agreed orders (imply negotiation/response)
    for p in entries:
        text = p['text']
        if re.search(r'(?i)agreed\s+order', text):
            related_doc = re.search(r'related\s+doc\D*?(\d+)', text)
            if related_doc:
                ref_doc = int(related_doc.group(1))
                for cm in motions:
                    if cm['doc'] == ref_doc and not cm['responded']:
                        cm['responded'] = True
                        cm['response_doc'] = f'agreed-{p["doc"]}'
                        break


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_cases(data_dir: str, courts: list) -> dict:
    """Analyze all cases across specified courts.

    Args:
        data_dir: Path to directory containing court/case/docket.html files.
        courts: List of court directory names to scan.

    Returns:
        Dict with aggregate statistics and per-case summaries.
    """
    all_motions = []
    case_summaries = []
    target_case_count = 0
    total_scanned = 0

    for court in courts:
        court_dir = os.path.join(data_dir, court)
        if not os.path.isdir(court_dir):
            continue

        for case_num in sorted(os.listdir(court_dir)):
            docket_path = os.path.join(court_dir, case_num, 'docket.html')
            if not os.path.isfile(docket_path):
                continue
            total_scanned += 1

            try:
                with open(docket_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception:
                continue

            # Filter to target firm cases
            if not TARGET_FIRM_PATTERN.search(content):
                continue

            target_case_count += 1
            case_id = f'{court}/{case_num}'

            entries = parse_docket_entries(content)
            motions = identify_creditor_motions(entries)

            if not motions:
                continue

            match_responses(entries, motions)

            for m in motions:
                m['case'] = case_id
            all_motions.extend(motions)

            responded_count = sum(1 for m in motions if m['responded'])
            case_summaries.append({
                'case': case_id,
                'motions': motions,
                'responded': responded_count,
                'total': len(motions),
            })

    # Aggregate statistics
    total_motions = len(all_motions)
    total_responded = sum(1 for m in all_motions if m['responded'])

    creditor_firm_motions = [m for m in all_motions if m['is_creditor_firm']]
    creditor_firm_responded = sum(1 for m in creditor_firm_motions if m['responded'])

    other_motions = [m for m in all_motions if not m['is_creditor_firm']]
    other_responded = sum(1 for m in other_motions if m['responded'])

    by_type = defaultdict(lambda: {'total': 0, 'responded': 0})
    for m in all_motions:
        by_type[m['type']]['total'] += 1
        if m['responded']:
            by_type[m['type']]['responded'] += 1

    return {
        'total_scanned': total_scanned,
        'target_cases': target_case_count,
        'cases_with_motions': len(case_summaries),
        'total_motions': total_motions,
        'total_responded': total_responded,
        'response_rate': total_responded / max(total_motions, 1),
        'creditor_firm_motions': len(creditor_firm_motions),
        'creditor_firm_responded': creditor_firm_responded,
        'other_motions': len(other_motions),
        'other_responded': other_responded,
        'by_type': dict(by_type),
        'case_summaries': case_summaries,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(results: dict):
    """Print formatted analysis report."""
    print("=" * 70)
    print("  OPPOSITION RATE ANALYSIS")
    print("=" * 70)
    print(f"  Total dockets scanned:               {results['total_scanned']}")
    print(f"  Target firm cases:                    {results['target_cases']}")
    print(f"  Cases with creditor motions:          {results['cases_with_motions']}")
    print()
    print(f"  TOTAL CREDITOR MOTIONS (excl trustee): {results['total_motions']}")
    print(f"  DEBTOR RESPONDED:                      {results['total_responded']}")
    print(f"  NO RESPONSE FILED:                     {results['total_motions'] - results['total_responded']}")
    print(f"  OVERALL RESPONSE RATE:                 "
          f"{results['total_responded']}/{results['total_motions']} = "
          f"{results['response_rate']*100:.1f}%")
    print()

    print("  BY MOTION TYPE:")
    for t, v in sorted(results['by_type'].items(), key=lambda x: -x[1]['total']):
        rate = v['responded'] / max(v['total'], 1) * 100
        print(f"    {t:15s}  {v['responded']}/{v['total']} = {rate:.1f}%")

    print()
    print("  CREDITOR FIRM COMPARISON:")
    cf = results['creditor_firm_motions']
    cfr = results['creditor_firm_responded']
    ot = results['other_motions']
    otr = results['other_responded']
    print(f"    Creditor firm motions:  {cf} total, {cfr} responded = "
          f"{cfr/max(cf,1)*100:.1f}%")
    print(f"    Other motions:          {ot} total, {otr} responded = "
          f"{otr/max(ot,1)*100:.1f}%")

    # Zero-response cases
    zero_resp = [cs for cs in results['case_summaries'] if cs['responded'] == 0]
    if zero_resp:
        print()
        print(f"  CASES WITH ZERO DEBTOR RESPONSE: {len(zero_resp)}")
        for cs in zero_resp:
            types = ', '.join(set(m['type'] for m in cs['motions']))
            print(f"    {cs['case']}: {cs['total']} motions ({types})")

    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Creditor Motion Response Rate Calculator'
    )
    parser.add_argument('--data-dir', type=str, default='./pacer_docs',
                        help='Directory containing court/case/docket.html files')
    parser.add_argument('--courts', nargs='+', default=DEFAULT_COURTS,
                        help='Court directories to scan')

    args = parser.parse_args()

    results = analyze_cases(args.data_dir, args.courts)
    print_report(results)


if __name__ == '__main__':
    main()
