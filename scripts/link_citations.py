#!/usr/bin/env python3
"""link_citations.py -- link the first mention of a case to its /citations/ page.

    python scripts/link_citations.py            # dry run, prints what it would change
    python scripts/link_citations.py --apply    # writes the files
    python scripts/link_citations.py --report FILE

WHY (9/22/26). The site publishes 20 canonical case pages under /citations/, and pages that
discuss those cases mostly do not link them: 156 unlinked mentions across 148 pages against 43
linked. A reader on the Form 122C deep dive meets "Ransom v. FIA Card Services, N.A., 562 U.S.
61 (2011)" as plain text while /citations/ransom-v-fia-card-services/ sits one click away and
unlinkable. The 5/22 build spec only ever linked OUTWARD, from each citation page to the
statute pages; nothing linked back.

WHAT IT DOES. One link per case per page, on the FIRST mention, and only where the page does
not already link that case. It never touches:
  - the /citations/ pages themselves, or a case's own dedicated page elsewhere on the site
  - text already inside a link, a heading, <title>, <meta>, or JSON-LD
  - translated shells (es/, de/, fr/, it/, pl/, *-es.html): the Spanish set is deliberately
    noindexed, and a link there buys nothing
⛔ It adds links only. It never rewrites a citation, a case name, or any other text: the
reporter numbers on these pages were verified against CourtListener on 9/22 and must stay
exactly as they are.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CITES = ROOT / "citations"
SKIP_PREFIX = ("citations/", ".git/", "es/", "de/", "fr/", "it/", "pl/", "nl/", "pt/", "zh/", "ja/", "ko/", "ar/")
SKIP_SUFFIX = ("-es.html",)


def short_names() -> dict[str, list[str]]:
    """slug -> candidate link texts, LONGEST FIRST.

    The longest form the page actually prints is the right link text: linking only the short
    form leaves "<a>Ransom v. FIA</a> Card Services, N.A." on the page, which reads as a
    different case from the one cited.
    """
    out = {}
    for d in sorted(CITES.iterdir()):
        if not d.is_dir():
            continue
        html = (d / "index.html").read_text(encoding="utf-8", errors="replace")
        m = re.search(r"<h1[^>]*>([^<]*)", html)
        if not m:
            continue
        name = re.sub(r"\s+", " ", m.group(1).strip())
        parts = re.match(r"(.+?)\s+v\.\s+(.+)", name)
        if not parts:
            continue
        left_full, right_full = parts.group(1), parts.group(2)
        left, right = left_full.split(",")[0], right_full.split(",")[0]
        cands = [
            name,                                     # Ransom v. FIA Card Services, N.A.
            f"{left} v. {right}",                     # Ransom v. FIA Card Services
            f"{left.split()[0]} v. {right}",          # (first word left)
            f"{left} v. {right.split()[0]}",
            f"{left.split()[0]} v. {right.split()[0]}",  # Ransom v. FIA
        ]
        seen, uniq = set(), []
        for c in sorted(cands, key=len, reverse=True):
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        out[d.name] = uniq
    return out


def forbidden_ranges(html: str) -> list[tuple[int, int]]:
    """Spans where a link must not be inserted: existing links, headings, head metadata, JSON-LD."""
    spans = []
    for pat in (r"(?is)<a\b.*?</a>", r"(?is)<h[1-6]\b.*?</h[1-6]>", r"(?is)<title>.*?</title>",
                r"(?is)<script.*?</script>", r"(?is)<style.*?</style>", r"(?is)<head>.*?</head>"):
        spans += [m.span() for m in re.finditer(pat, html)]
    # attribute values (alt=, content=, aria-label=, ...)
    spans += [m.span() for m in re.finditer(r'(?s)="[^"]*"', html)]
    return spans


def in_span(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def link_page(html: str, names: dict[str, list[str]], own_slug: str | None) -> tuple[str, list[str]]:
    added = []
    spans = forbidden_ranges(html)
    for slug, cands in names.items():
        if slug == own_slug or f"/citations/{slug}" in html:
            continue
        placed = False
        for text in cands:  # longest form first
            if placed:
                break
            for m in re.finditer(re.escape(text), html):
                if in_span(m.start(), spans):
                    continue
                html = html[: m.start()] + f'<a href="/citations/{slug}/">{text}</a>' + html[m.end():]
                added.append(slug)
                spans = forbidden_ranges(html)  # positions moved; recompute before the next case
                placed = True
                break
    return html, added


def own_slug_for(rel: str, names: dict[str, str]) -> str | None:
    """A page that IS about one case (e.g. federal-jurisdiction-bankruptcy/stern-v-marshall/)."""
    for slug in names:
        if f"/{slug}/" in f"/{rel}":
            return slug
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default="")
    a = ap.parse_args()

    names = short_names()
    per_case, changed = Counter(), []
    for f in sorted(ROOT.rglob("*.html")):
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(SKIP_PREFIX) or rel.endswith(SKIP_SUFFIX):
            continue
        try:
            html = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if " v. " not in html:
            continue
        new, added = link_page(html, names, own_slug_for(rel, names))
        if not added:
            continue
        per_case.update(added)
        changed.append({"page": rel, "linked": added})
        if a.apply:
            f.write_text(new, encoding="utf-8", newline="")

    verb = "linked" if a.apply else "would link"
    print(f"{verb} {sum(per_case.values())} mention(s) across {len(changed)} page(s)")
    for slug, n in per_case.most_common():
        print(f"  {n:4d}  {slug}")
    if a.report:
        Path(a.report).write_text(json.dumps({"applied": a.apply, "pages": changed}, indent=1), encoding="utf-8")
        print(f"report: {a.report}")
    if not a.apply:
        print("\ndry run -- nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
