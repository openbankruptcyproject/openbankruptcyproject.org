#!/usr/bin/env python3
"""
AI Sanctions Tracker build/maintenance tool.

Makes data.json the source of truth for ADDITIONS and CONSISTENCY without
destructively rewriting the hand-tuned index.html (which carries bespoke cards
the data model does not capture). Three modes:

  check                 Audit data.json <-> index.html <-> per-case dirs. Reports
                        entries missing a card, orphan cards, DUPLICATE cards
                        (the bug class that put FTC under Bankruptcy), entries
                        missing a detail-page dir, and entries with placeholder
                        "pending" data. Exit 1 on drift -> usable as a pre-deploy gate.

  card <id>             Print the correct <a class="entry-card"> HTML for a data
                        entry (verified field->tag mapping), ready to paste.

  promote <entry.json>  Add a VERIFIED entry: append to data.json, write its
                        detail page, insert its card into the right section of
                        index.html, and bump last_updated / entry_count.
                        The entry.json must already be human-verified against the
                        primary source. This tool does no verification of its own.

Discipline: a match is a hypothesis, not a finding. Only promote entries a human
has confirmed against the order itself.
"""
import argparse
import html
import json
import os
import re
import sys
from datetime import date

DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(DIR, "data.json")
INDEX = os.path.join(DIR, "index.html")

TYPE_TAG = {
    "sanctions_order": ("tag-sanctions", "Sanctions Order"),
    "standing_order": ("tag-standing", "Standing Order"),
    "disciplinary_referral": ("tag-disciplinary", "Disciplinary Referral"),
    "opinion": ("tag-sanctions", "Opinion"),
    "agency_rule": ("tag-executive", "Agency Rule"),
    "executive_order": ("tag-executive", "Executive Order"),
    "legislation": ("tag-legislative", "Legislation"),
}


def verif_tag(status):
    s = (status or "").lower()
    if s.startswith("primary_source_verified"):
        return ("tag-verified", "Primary source verified")
    return ("tag-corroborated", "Corroborated")


# Section heading text (must match the literal headings in index.html).
SEC_BANKRUPTCY = "Bankruptcy Court Orders (Primary Focus)"
SEC_BY_TYPE = {
    "sanctions_order": "Sanctions Orders",
    "standing_order": "Standing Orders",
    "disciplinary_referral": "Disciplinary Referrals",
    "opinion": "Other Orders",
    "agency_rule": "Executive Branch Actions",
    "executive_order": "Executive Branch Actions",
    "legislation": "Legislation",
}


def section_for(entry):
    if str(entry.get("bankruptcy_relevance", "")).lower() == "primary" and entry.get(
        "order_type"
    ) in ("sanctions_order", "opinion"):
        return SEC_BANKRUPTCY
    return SEC_BY_TYPE.get(entry.get("order_type", ""), "Other Orders")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def truncate(s, n=300):
    s = str(s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut + "..."


def load_data():
    return json.load(open(DATA, encoding="utf-8"))


def render_card(e):
    tcls, tlabel = TYPE_TAG.get(e.get("order_type", ""), ("tag-sanctions", "Order"))
    vcls, vlabel = verif_tag(e.get("verification_status"))
    circuit = f" ({esc(e['circuit'])})" if e.get("circuit") else ""
    court_line = f"{esc(e.get('court'))}{circuit} &middot; {esc(e.get('date_issued'))}"
    return (
        f'<a href="{esc(e["id"])}/" class="entry-card">\n'
        f'  <div class="tags">\n'
        f'    <span class="tag {tcls}">{tlabel}</span>\n'
        f'    <span class="tag {vcls}">{vlabel}</span>\n'
        f"  </div>\n"
        f"  <h2>{esc(e.get('title'))}</h2>\n"
        f'  <div class="court-line">{court_line}</div>\n'
        f'  <p class="holding">{esc(truncate(e.get("holding_summary")))}</p>\n'
        f'  <span class="arrow">View entry &rarr;</span>\n'
        f"</a>"
    )


def card_hrefs(index_html):
    return re.findall(r'<a href="([^"/]+)/" class="entry-card">', index_html)


def cmd_check():
    d = load_data()
    entries = d.get("entries", [])
    ids = [e["id"] for e in entries]
    idx = open(INDEX, encoding="utf-8").read()
    hrefs = card_hrefs(idx)

    problems = 0
    # duplicates on the page (the FTC bug class)
    seen = {}
    for h in hrefs:
        seen[h] = seen.get(h, 0) + 1
    dupes = {h: c for h, c in seen.items() if c > 1}
    if dupes:
        problems += 1
        print(f"DUPLICATE cards on page: {dupes}")
    # data entry without a card
    missing_card = [i for i in ids if i not in seen]
    if missing_card:
        problems += 1
        print(f"data entries with NO card on page: {missing_card}")
    # card without a data entry (orphan)
    orphan = [h for h in seen if h not in ids]
    if orphan:
        problems += 1
        print(f"orphan cards (no data entry): {orphan}")
    # entry missing a detail-page dir
    no_dir = [i for i in ids if not os.path.isdir(os.path.join(DIR, i))]
    if no_dir:
        problems += 1
        print(f"entries missing a detail-page directory: {no_dir}")
    # placeholder/pending data to resolve
    pending = [
        e["id"]
        for e in entries
        if "pending" in str(e.get("date_issued", "")).lower()
        or "pending" in str(e.get("verification_status", "")).lower()
    ]
    if pending:
        print(f"NOTE: {len(pending)} entries have placeholder/pending data to resolve: {pending}")

    print(
        f"\nsummary: {len(ids)} data entries | {len(hrefs)} cards | "
        f"{len(set(hrefs))} unique cards | drift problems: {problems}"
    )
    return 1 if problems else 0


def cmd_card(entry_id):
    d = load_data()
    e = next((x for x in d["entries"] if x["id"] == entry_id), None)
    if not e:
        print(f"no entry with id {entry_id}", file=sys.stderr)
        return 1
    print(render_card(e))
    print(f"\n# section: {section_for(e)}", file=sys.stderr)
    return 0


DETAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | AI Sanctions Tracker | Open Bankruptcy Project</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:title" content="{title} | AI Sanctions Tracker | Open Bankruptcy Project">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-053Z64N82F"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-053Z64N82F');
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":{title_json},"url":"{url}","description":{desc_json},"datePublished":"{date}","isPartOf":{{"@type":"Dataset","name":"AI Sanctions Tracker: U.S. Courts","url":"https://openbankruptcyproject.org/research/ai-court-tracker/","license":"https://creativecommons.org/licenses/by/4.0/","creator":{{"@type":"Organization","name":"Open Bankruptcy Project","url":"https://openbankruptcyproject.org"}}}}}}
</script>
<link rel="stylesheet" href="/assets/obp-tracker.css">
</head>
<body>
<nav><div class="nav-inner">
<span class="nav-brand"><a href="/">Open Bankruptcy Project</a></span>
<div class="nav-links"><a href="/">Home</a><a href="/research/ai-court-tracker/">AI Sanctions Tracker</a><a href="/about.html">About</a></div>
</div></nav>
<div class="content"><div class="container">
<a class="back-link" href="/research/ai-court-tracker/">&larr; Back to the AI Sanctions Tracker</a>
<h1>{title}</h1>
<div class="detail-meta"><dl>
<dt>Court</dt><dd>{court}{circuit}</dd>
<dt>Date</dt><dd>{date}</dd>
<dt>Docket</dt><dd>{docket}</dd>
<dt>Citation</dt><dd>{citation}</dd>
<dt>Order type</dt><dd>{order_type}</dd>
<dt>Sanctions</dt><dd>{sanctions}</dd>
<dt>Verification</dt><dd>{verification}</dd>
</dl></div>
<div class="detail-section"><h3>Triggering conduct</h3><p>{triggering}</p></div>
<div class="detail-section"><h3>Holding</h3><p>{holding}</p></div>
<div class="detail-section"><h3>Primary source</h3><p><a href="{source_url}" rel="noopener">{source_url}</a> ({source_type})</p></div>
<a class="back-link" href="/research/ai-court-tracker/">&larr; Back to the AI Sanctions Tracker</a>
</div></div>
</body>
</html>
"""


def render_detail(e):
    url = f"https://openbankruptcyproject.org/research/ai-court-tracker/{e['id']}/"
    desc = truncate(e.get("holding_summary"), 180)
    circuit = f" ({esc(e['circuit'])})" if e.get("circuit") else ""
    return DETAIL_TEMPLATE.format(
        title=esc(e.get("title")),
        title_json=json.dumps(e.get("title", "")),
        desc=esc(desc),
        desc_json=json.dumps(desc),
        url=url,
        date=esc(e.get("date_issued")),
        court=esc(e.get("court")),
        circuit=circuit,
        docket=esc(e.get("docket_no") or "n/a"),
        citation=esc(e.get("case_citation") or "n/a"),
        order_type=esc(e.get("order_type")),
        sanctions=esc(e.get("sanctions_imposed") or "n/a"),
        verification=esc(e.get("verification_status")),
        triggering=esc(e.get("triggering_conduct") or "n/a"),
        holding=esc(e.get("holding_summary") or "n/a"),
        source_url=esc(e.get("source_url") or ""),
        source_type=esc(e.get("source_type") or ""),
    )


def cmd_promote(entry_path):
    e = json.load(open(entry_path, encoding="utf-8"))
    required = ["id", "title", "court", "date_issued", "order_type", "holding_summary", "source_url"]
    miss = [k for k in required if not e.get(k)]
    if miss:
        print(f"entry missing required fields: {miss}", file=sys.stderr)
        return 1
    e.setdefault("verification_status", "primary_source_verified")

    d = load_data()
    if any(x["id"] == e["id"] for x in d["entries"]):
        print(f"entry {e['id']} already in data.json", file=sys.stderr)
        return 1
    d["entries"].append(e)
    d["entry_count"] = len(d["entries"])
    d["last_updated"] = date.today().isoformat()
    json.dump(d, open(DATA, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    detail_dir = os.path.join(DIR, e["id"])
    os.makedirs(detail_dir, exist_ok=True)
    open(os.path.join(detail_dir, "index.html"), "w", encoding="utf-8").write(render_detail(e))

    # insert card after its section heading
    idx = open(INDEX, encoding="utf-8").read()
    section = section_for(e)
    heading = f'<h2 class="section-heading">{section}</h2>'
    if heading not in idx:
        print(f"WARNING: section heading not found: {section}. Card NOT inserted; paste manually:")
        print(render_card(e))
    else:
        idx = idx.replace(heading, heading + "\n" + render_card(e), 1)
        open(INDEX, "w", encoding="utf-8").write(idx)
    print(f"promoted {e['id']} -> data.json (+detail page +card in '{section}'). entries now {d['entry_count']}.")
    print("RUN: python _build.py check")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    c = sub.add_parser("card")
    c.add_argument("id")
    p = sub.add_parser("promote")
    p.add_argument("entry_json")
    a = ap.parse_args()
    if a.cmd == "check":
        sys.exit(cmd_check())
    elif a.cmd == "card":
        sys.exit(cmd_card(a.id))
    elif a.cmd == "promote":
        sys.exit(cmd_promote(a.entry_json))


if __name__ == "__main__":
    main()
