#!/usr/bin/env python3
"""Sync the homepage 'New Resources' static fallback to data/new-resources.json.

Reads data/new-resources.json, picks the N most recent entries by pubdate,
and rewrites the static <ul id="new-resources"> block in index.html so
SEO crawlers and no-JS visitors see the same content the dynamic script
would render.

Run after every edit to data/new-resources.json:

    python scripts/sync_homepage_resources.py

Idempotent. Only rewrites the block between the START and END markers.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "new-resources.json"
HTML_PATH = ROOT / "index.html"
HOMEPAGE_LIMIT = 5

START_MARKER = "<!-- new-resources:start -->"
END_MARKER = "<!-- new-resources:end -->"


def render_static_fallback(resources, limit):
    sorted_entries = sorted(
        (r for r in resources if r.get("pubdate") and r.get("label") and r.get("url")),
        key=lambda r: r["pubdate"],
        reverse=True,
    )[:limit]
    items = []
    for r in sorted_entries:
        icon = html.escape(r.get("icon") or "")
        label = html.escape(r["label"])
        url = r["url"]
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        items.append(
            f'<li><a href="{html.escape(url)}" '
            f'style="color:#c9d1d9;text-decoration:none">'
            f'{icon} {label}</a></li>'
        )
    return "\n".join(items)


def replace_block(html_text, new_inner):
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    replacement = (
        START_MARKER
        + "\n"
        + new_inner
        + "\n"
        + END_MARKER
    )
    if not pattern.search(html_text):
        raise SystemExit(
            "ERROR: index.html does not contain the new-resources markers. "
            f"Add {START_MARKER} and {END_MARKER} around the static <ul> contents."
        )
    return pattern.sub(replacement, html_text)


def main():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    resources = data.get("resources", [])
    if not resources:
        print("No resources in JSON; aborting.", file=sys.stderr)
        return 1

    new_inner = render_static_fallback(resources, HOMEPAGE_LIMIT)
    html_text = HTML_PATH.read_text(encoding="utf-8")
    updated = replace_block(html_text, new_inner)

    if updated == html_text:
        print("index.html already up to date.")
        return 0

    HTML_PATH.write_text(updated, encoding="utf-8")
    print(f"Wrote {HOMEPAGE_LIMIT} entries to index.html.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
