#!/usr/bin/env python3
"""Inject a self-contained donate strip above the footer of every page that lacks a donate link.

Why: Ad Grants traffic (9/17/26) lands on /pro-se/, /means-test-calculator/, /exemptions/, /forms/,
/states/<state>.html — none of which carried any donation ask. Only the homepage and /states/ did.
Dan (9/17): "all pages should have a donate link."

Rules
- Idempotent: pages carrying the marker comment are skipped.
- Pages that already link to /donate.html, /donate-es.html or buy.stripe.com are left alone
  (they satisfy the requirement; the homepage has a full donate section).
- Insert point: immediately before the first `<footer` tag; if the page has no footer, before `</body>`;
  if neither, the page is reported and skipped.
- Spanish pages (filename ends in -es.html, or <html lang="es">) get Spanish copy and link /donate-es.html.
- Self-contained inline styles (no dependency on per-template CSS variables; 41,959 pages, 7+ templates).
- The button fires a GA4 `donate_click` event when gtag is present (every sampled page loads G-FTWLM223G7),
  so it can be imported into Ads as a conversion.
- Files dirty in git before the run are skipped so the commit stays a single clean change.

Usage
  python scripts/inject_donate_strip.py            # dry run: counts + a few examples
  python scripts/inject_donate_strip.py --apply    # write
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLY = "--apply" in sys.argv
MARKER = "<!-- obp-donate-strip -->"

EN = {
    "label": "Support this work",
    "text": "Open Bankruptcy Project is a 501(c)(3) public charity. Free guides like this one are funded by readers, not law firms.",
    "cta": "♥ Donate",
    "href": "/donate.html",
    "aria": "Support the Open Bankruptcy Project",
}
ES = {
    "label": "Apoye este trabajo",
    "text": "Open Bankruptcy Project es una organización 501(c)(3). Las guías gratuitas como esta las financian los lectores, no los bufetes.",
    "cta": "♥ Donar",
    "href": "/donate-es.html",
    "aria": "Apoye al Open Bankruptcy Project",
}

STRIP = (
    MARKER +
    '<aside class="obp-donate-strip" role="complementary" aria-label="{aria}" '
    'style="margin:2rem auto 0;max-width:960px;padding:1rem 1.25rem;border:1px solid #30363d;border-radius:8px;'
    'background:#161b22;color:#c9d1d9;font-family:inherit;font-size:.92rem;line-height:1.45;'
    'display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.75rem 1.5rem;box-sizing:border-box">'
    '<div style="flex:1 1 320px;min-width:0"><strong style="display:block;color:#f0f6fc;margin-bottom:.15rem">{label}</strong>'
    '<span style="color:#8b949e">{text}</span></div>'
    '<a href="{href}" '
    'onclick="if(window.gtag){{gtag(\'event\',\'donate_click\',{{event_category:\'donate\',event_label:location.pathname,transport_type:\'beacon\'}})}}" '
    'style="flex:0 0 auto;display:inline-block;background:#bf3989;color:#fff;padding:.55rem 1.4rem;border-radius:6px;'
    'font-weight:600;text-decoration:none;white-space:nowrap">{cta}</a>'
    '</aside>\n'
)

HAS_DONATE_LINK = re.compile(r'href="[^"]*(?:/donate(?:-es)?\.html|buy\.stripe\.com)', re.I)
FOOTER_TAG = re.compile(r'<footer\b', re.I)
BODY_CLOSE = re.compile(r'</body>', re.I)
LANG_ES = re.compile(r'<html[^>]*\blang="es', re.I)


def git_dirty():
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    return {line[3:].strip().replace("\\", "/") for line in out.splitlines() if line.strip()}


def is_spanish(rel, head):
    return rel.endswith("-es.html") or "/es/" in rel or bool(LANG_ES.search(head))


def main():
    dirty = git_dirty()
    stats = {"scanned": 0, "already_marked": 0, "has_link": 0, "dirty_skipped": 0,
             "no_anchor": 0, "injected_footer": 0, "injected_body": 0, "spanish": 0}
    examples, no_anchor = [], []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            stats["scanned"] += 1
            if rel in dirty:
                stats["dirty_skipped"] += 1
                continue
            with open(path, "rb") as fh:
                raw = fh.read()
            text = raw.decode("utf-8", errors="surrogateescape")
            if MARKER in text:
                stats["already_marked"] += 1
                continue
            if HAS_DONATE_LINK.search(text):
                stats["has_link"] += 1
                continue

            copy = ES if is_spanish(rel, text[:2000]) else EN
            strip = STRIP.format(**copy)
            m = FOOTER_TAG.search(text)
            if m:
                new = text[:m.start()] + strip + text[m.start():]
                stats["injected_footer"] += 1
            else:
                m = BODY_CLOSE.search(text)
                if not m:
                    stats["no_anchor"] += 1
                    no_anchor.append(rel)
                    continue
                new = text[:m.start()] + strip + text[m.start():]
                stats["injected_body"] += 1
            if copy is ES:
                stats["spanish"] += 1
            if len(examples) < 6:
                examples.append(rel)
            if APPLY:
                with open(path, "wb") as fh:
                    fh.write(new.encode("utf-8", errors="surrogateescape"))

    mode = "APPLIED" if APPLY else "DRY RUN"
    print(f"[{mode}] " + " · ".join(f"{k}={v}" for k, v in stats.items()))
    print("examples:", ", ".join(examples))
    if no_anchor:
        print(f"no <footer or </body> ({len(no_anchor)}):", ", ".join(no_anchor[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
