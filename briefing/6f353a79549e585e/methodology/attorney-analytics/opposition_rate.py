"""V4: Precise matching of debtor responses to creditor motions.
For each creditor motion, check if any subsequent debtor response references it."""

import os, re, html
from collections import defaultdict

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pacer_docs')
courts = ['mowbk', 'ksbk', 'moebk']

ATTORNEY_patterns = re.compile(r'(?i)(ryan\s+ATTORNEY|ATTORNEY,?\s+ryan|wm\s+law|wagoner\s+&\s+miller|wagoner\s+miller|wagoner\s+&amp;\s+miller)')

# Motion types
motion_types = [
    (re.compile(r'(?i)motion\s+for\s+relief\s+from\s+(the\s+)?stay'), 'MFRS'),
    (re.compile(r'(?i)motion\s+to\s+dismiss'), 'MTD'),
    (re.compile(r'(?i)objection\s+to\s+(confirmation|plan)'), 'OBJ_CONF'),
    (re.compile(r'(?i)objection\s+to\s+discharge'), 'OBJ_DISCH'),
    (re.compile(r'(?i)objection\s+to\s+(exemption|claim)'), 'OBJ_CLAIM'),
    (re.compile(r'(?i)motion\s+to\s+convert'), 'CONVERT'),
    (re.compile(r'(?i)motion\s+for\s+adequate\s+protection'), 'ADEQUATE'),
]

not_a_filing = re.compile(r'(?i)(receipt\s+of|certificate\s+of\s+mailing|hearing\s+(held|set|continued)|order\s+(of\s+the\s+court|granting|denying|sustaining|dismissing|overruling|on\s+motion|resolving|re:)|minute\s+sheet|courtroom|auto-?docketed|chapter\s+13\s+trustee\s+withdraws|trustee.s\s+certificate|proposed\s+order)')

trustee_filer = re.compile(r'(?i)(filed\s+by\s+trustee|trustee.s\s+(motion|objection)|filed\s+by\s+.*trustee\s+(william|carl|richard|jan|robert)|chapter\s+13\s+trustee)')
debtor_filer = re.compile(r'(?i)(filed\s+by\s+debtor|filed\s+by\s+joint\s+debtor)')
CREDITOR_ATY_re = re.compile(r'(?i)(CREDITOR_ATY|messerli|becket\s+&\s+lee|sara\s+bass)')
has_pages = re.compile(r'\(\d+\s+pgs?\)')

# Track everything
all_cred_motions = []
all_matched_responses = []
case_summaries = []

ATTORNEY_case_count = 0
total_scanned = 0

for court in courts:
    court_dir = os.path.join(base, court)
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
        except:
            continue

        if not ATTORNEY_patterns.search(content):
            continue

        ATTORNEY_case_count += 1
        case_id = f'{court}/{case_num}'

        entries = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL)
        parsed = []

        for entry in entries:
            text = re.sub(r'<[^>]+>', ' ', entry)
            text = html.unescape(text).strip()
            text = re.sub(r'\s+', ' ', text)

            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
            date = date_match.group(1) if date_match else None

            # Extract doc number
            doc_match = re.search(r'(?:^|\s)(\d+)\s+\(\d+\s+pgs?\)', text)
            if not doc_match:
                doc_match = re.search(r'(?:^|\s)(\d+)\s+\(', text)
            doc_num = int(doc_match.group(1)) if doc_match else None

            parsed.append({'text': text, 'date': date, 'doc': doc_num})

        # Pass 1: Find creditor motions (actual filings, not from trustee)
        creditor_motions = []
        for p in parsed:
            text = p['text']
            if not_a_filing.search(text):
                continue
            if not has_pages.search(text):
                continue
            if trustee_filer.search(text):
                continue

            mtype = None
            for pat, mt in motion_types:
                if pat.search(text):
                    mtype = mt
                    break
            if not mtype:
                continue

            # Exclude debtor's own motions
            if debtor_filer.search(text) and not re.search(r'(?i)response\s+to', text):
                continue

            is_CREDITOR_ATY = bool(CREDITOR_ATY_re.search(text))
            creditor_motions.append({
                'doc': p['doc'], 'date': p['date'], 'text': text[:300],
                'type': mtype, 'is_CREDITOR_ATY': is_CREDITOR_ATY, 'case': case_id,
                'responded': False, 'response_doc': None
            })

        if not creditor_motions:
            continue

        # Pass 2: Find debtor responses and try to match to creditor motions
        for p in parsed:
            text = p['text']
            if not has_pages.search(text):
                continue

            # Must be response from debtor
            if not re.search(r'(?i)(response|opposition)', text):
                continue
            if not debtor_filer.search(text):
                continue

            # Try to match to a creditor motion by "related document" reference
            related_doc = re.search(r'related\s+document\D*?(\d+)', text)
            if related_doc:
                ref_doc = int(related_doc.group(1))
                for cm in creditor_motions:
                    if cm['doc'] == ref_doc and not cm['responded']:
                        cm['responded'] = True
                        cm['response_doc'] = p['doc']
                        break

            # Also check if response text mentions the motion type
            for cm in creditor_motions:
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

        # Also check for agreed orders (which imply negotiation/response)
        for p in parsed:
            text = p['text']
            if re.search(r'(?i)agreed\s+order', text):
                related_doc = re.search(r'related\s+doc\D*?(\d+)', text)
                if related_doc:
                    ref_doc = int(related_doc.group(1))
                    for cm in creditor_motions:
                        if cm['doc'] == ref_doc and not cm['responded']:
                            cm['responded'] = True
                            cm['response_doc'] = f'agreed-{p["doc"]}'
                            break

        all_cred_motions.extend(creditor_motions)
        responded_count = sum(1 for m in creditor_motions if m['responded'])

        case_summaries.append({
            'case': case_id,
            'motions': creditor_motions,
            'responded': responded_count,
            'total': len(creditor_motions)
        })

# ============================================================
# OUTPUT
# ============================================================
print(f'BLAY OPPOSITION RATE ANALYSIS')
print(f'=' * 70)
print(f'Total dockets scanned: {total_scanned}')
print(f'ATTORNEY/FIRM cases: {ATTORNEY_case_count}')
print(f'Cases with creditor motions (excl. trustee): {len(case_summaries)}')
print()

# Detailed per-case
for cs in case_summaries:
    CREDITOR_ATY_in_case = any(m['is_CREDITOR_ATY'] for m in cs['motions'])
    tag = ' *** MOSCOV ***' if CREDITOR_ATY_in_case else ''
    print(f'=== {cs["case"]}{tag} ===')
    for m in cs['motions']:
        status = 'RESPONDED' if m['responded'] else 'NO RESPONSE'
        mtag = ' [MOSCOV]' if m['is_CREDITOR_ATY'] else ''
        resp_info = f' (resp Doc {m["response_doc"]})' if m['response_doc'] else ''
        print(f'  [{m["type"]}] Doc {m["doc"]} ({m["date"]}){mtag} -> {status}{resp_info}')
        print(f'    {m["text"][:180]}')
    print()

# ============================================================
# AGGREGATE STATS
# ============================================================
total_motions = len(all_cred_motions)
total_responded = sum(1 for m in all_cred_motions if m['responded'])
total_no_response = total_motions - total_responded

CREDITOR_ATY_motions = [m for m in all_cred_motions if m['is_CREDITOR_ATY']]
CREDITOR_ATY_responded = sum(1 for m in CREDITOR_ATY_motions if m['responded'])
non_CREDITOR_ATY = [m for m in all_cred_motions if not m['is_CREDITOR_ATY']]
non_CREDITOR_ATY_responded = sum(1 for m in non_CREDITOR_ATY if m['responded'])

# By type
by_type = defaultdict(lambda: {'total': 0, 'responded': 0})
for m in all_cred_motions:
    by_type[m['type']]['total'] += 1
    if m['responded']:
        by_type[m['type']]['responded'] += 1

print(f'=' * 70)
print(f'AGGREGATE STATISTICS')
print(f'=' * 70)
print()
print(f'TOTAL CREDITOR MOTIONS (excl. trustee):  {total_motions}')
print(f'DEBTOR RESPONDED:                        {total_responded}')
print(f'NO RESPONSE FILED:                       {total_no_response}')
print(f'OVERALL RESPONSE RATE:                   {total_responded}/{total_motions} = {total_responded/max(total_motions,1)*100:.1f}%')
print()
print(f'BY MOTION TYPE:')
for t, v in sorted(by_type.items(), key=lambda x: -x[1]['total']):
    rate = v['responded']/max(v['total'],1)*100
    print(f'  {t:15s}  {v["responded"]}/{v["total"]} = {rate:.1f}%')
print()
print(f'MOSCOV/MESSERLI COMPARISON:')
print(f'  CREDITOR_ATY motions:     {len(CREDITOR_ATY_motions)} total, {CREDITOR_ATY_responded} responded = {CREDITOR_ATY_responded/max(len(CREDITOR_ATY_motions),1)*100:.1f}%')
print(f'  Non-CREDITOR_ATY motions: {len(non_CREDITOR_ATY)} total, {non_CREDITOR_ATY_responded} responded = {non_CREDITOR_ATY_responded/max(len(non_CREDITOR_ATY),1)*100:.1f}%')
print()

# Cases with NO response at all
zero_response_cases = [cs for cs in case_summaries if cs['responded'] == 0]
print(f'CASES WITH ZERO DEBTOR RESPONSE:')
for cs in zero_response_cases:
    types = ', '.join(set(m['type'] for m in cs['motions']))
    CREDITOR_ATY_tag = ' [MOSCOV]' if any(m['is_CREDITOR_ATY'] for m in cs['motions']) else ''
    print(f'  {cs["case"]}: {cs["total"]} motions ({types}){CREDITOR_ATY_tag}')

print()
print(f'MOSCOV CASE DETAIL:')
for cs in case_summaries:
    CREDITOR_ATY_m = [m for m in cs['motions'] if m['is_CREDITOR_ATY']]
    if not CREDITOR_ATY_m:
        continue
    print(f'  {cs["case"]}:')
    for m in CREDITOR_ATY_m:
        status = 'RESPONDED' if m['responded'] else '** NO RESPONSE **'
        print(f'    [{m["type"]}] Doc {m["doc"]} ({m["date"]}) -> {status}')
    non_m = [m for m in cs['motions'] if not m['is_CREDITOR_ATY']]
    if non_m:
        for m in non_m:
            status = 'RESPONDED' if m['responded'] else '** NO RESPONSE **'
            print(f'    [{m["type"]}] Doc {m["doc"]} ({m["date"]}) [other creditor] -> {status}')
