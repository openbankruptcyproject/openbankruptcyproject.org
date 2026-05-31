# OBP data files

JSON feeds consumed by client-side scripts on openbankruptcyproject.org and other BTN-network properties.

## Files

### `new-resources.json`

Source of truth for the homepage "New Resources" box and the `/whats-new/` archive page.

**Schema:**

```json
{
  "schema_version": "1.0",
  "last_updated": "YYYY-MM-DD",
  "resources": [
    {
      "pubdate": "YYYY-MM-DD",
      "icon": "EMOJI",
      "label": "Resource title (under 70 chars works best)",
      "description": "Optional one-sentence subhead. Used on /whats-new/ archive page; not shown in homepage compact view.",
      "url": "https://full-absolute-url",
      "tags": ["lowercase-hyphenated", "tag", "list"]
    }
  ]
}
```

**Required fields:** `pubdate`, `icon`, `label`, `url`.
**Optional fields:** `description`, `tags`.

### `counters.json`

Lives at `https://1328f.com/data/counters.json` (separate repo). Consumed by `btn-counters.js` site-wide. Not in this directory.

## How to add a new resource

1. Edit `data/new-resources.json` and prepend a new entry to the `resources` array (newest first is convention; the script sorts by `pubdate` regardless).
2. Update `last_updated` to today.
3. Run `python scripts/sync_homepage_resources.py` to re-render the static HTML fallback in `index.html` (keeps SEO + no-JS users in sync with the JSON).
4. Commit and push. GitHub Pages redeploys automatically.

The homepage box renders the **5 most recent** entries by `pubdate`. The `/whats-new/` archive renders **all** entries grouped by month.

## How the rendering works

- **Homepage (`index.html`):** static `<ul>` fallback inside `<ul id="new-resources">`. The script `new-resources.js` fetches this JSON and replaces the fallback content with the latest entries on page load. If JS is disabled or the fetch fails, the static fallback remains visible (graceful degradation).
- **Archive (`/whats-new/`):** same JSON, no truncation, grouped by month-year.
- **Sync script (`scripts/sync_homepage_resources.py`):** keeps the static HTML fallback in `index.html` aligned with the latest 5 JSON entries. Run after every JSON edit.

## Conventions

- Use absolute URLs (`https://...`), not root-relative paths. Resources live across the BTN network of domains, not only under `openbankruptcyproject.org`.
- Pick an emoji that matches the existing palette (📑 research brief, 📚 caselaw, 📄 template, 🧮 calculator, 📖 glossary, 🌎 i18n, 📍 geographic, 📰 news, 📊 data, 📋 dataset).
- Keep `label` under ~70 characters for the homepage compact view.
- Tags are free-form but try to match existing ones: `rules-committee`, `pro-se`, `research-brief`, `caselaw`, `motion-template`, `means-test`, `calculator`, `glossary`, `education`, `spanish`, `guides`, `state-guides`, `exemptions`, `news`, `data-analysis`, `dataset`.
