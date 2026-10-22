# OBP Notice & Mailing Kit, maintainer notes

Public route: `https://openbankruptcyproject.org/mailing-kit/` (landing) and `/mailing-kit/app/` (workspace).
Built 2026-10-22 during the Bankruptcy Noticing Center (BNC) service disruption. The utility is meant to outlive the incident.

## Files
- `index.html`: landing page. Standard site page (GA4 block + `btn-engage.js`, donate strip, JSON-LD).
- `app/index.html` + `app/app.js`: the workspace. No inline scripts; CSP meta restricts scripts to this origin and Google Tag Manager, and connections to this origin and Google Analytics. No `btn-engage.js`. One analytics event, `mailing_kit_download_complete`, fires once per page load when a generated file is downloaded; its only parameters are `site` and the list of component names. Never add names, counts, filenames, districts, or case data to it.
- `vendor/pdf-lib.min.js` (1.17.1, MIT) and `vendor/papaparse.min.js` (5.4.1, MIT). Hashes in `vendor/VENDOR_HASHES.txt`. Pinned on purpose; no runtime CDN.
- `data/districts.json`: the 94 bankruptcy districts with the official court website (taken from this site's `courthouses/` pages) and, for a reviewed subset, the court's own BNC-disruption page, its date, a short summary, and `last_verified`. `status` is `confirmed` only for districts whose page a maintainer actually read. Everything else is `unreviewed` and shows no guidance. Do not invent guidance.
- `sample-recipients.csv`: the CSV shape the importer recognizes (headers: name, address1, address2, city, state, zip). Fictional names only.

## Retiring or updating the outage advisory
1. Re-read the U.S. Courts statement and each `confirmed` district page.
2. Edit `data/districts.json`: update `national.summary`, `national.last_verified`, and each district's `guidance.summary` / `last_verified`. When the BNC is restored, set `national.advisory_active` to `false` (the workspace ribbon disappears) and change each confirmed district's summary to say the court reported restoration, with the date.
3. Edit `index.html` (landing): the "Status" paragraph near the top carries the same date and summary by hand. Update both or neither.
4. `national.advisory_review_by` is the date by which someone should re-check. Move it forward each time.

## Privacy checks before any release
- Open DevTools, Network tab, on `/mailing-kit/app/`. Add recipients, open a PDF, generate, download. The only requests allowed are this origin (page, vendor scripts, `districts.json`) and Google Analytics / Tag Manager hits that carry no form data. Any request containing a name, address, or document is a release blocker.
- Application tab: Local Storage, Session Storage, IndexedDB, and Cookies for this origin must be empty of anything the tool wrote. The tool never writes to them.
- Reload the page: everything is gone. That is by design.

## Known limits
- Text is drawn with the built-in Helvetica font (WinAnsi). Characters outside it (for example CJK) are replaced with `?` and the recipient is flagged.
- Labels assume Avery 5160 / 8160 geometry (3 x 10, 2.625 in x 1 in, 0.5 in top margin, 0.1875 in side margin). X/Y offsets and the test sheet handle printer drift.
- Envelopes are #10 (9.5 in x 4.125 in), landscape page, optional 90-degree rotation.
- Up to 500 recipients and a 60-page, 25 MB source PDF per run. Packet output is split into files of about 200 pages (adjustable) so the browser never holds one enormous file.
- No address verification, no postage purchase, no mail fulfillment, no court filing, no determination of whom to serve.

## 94-court homepage scan (tracker)
`data/districts.json` carries `homepage_scan` per district (date, reachable, bnc_mentions, court_notice_url/text) and a `tracker` label (`confirmed`, `notice_found`, `mention_only`, `none`, `unreachable`; legend in `tracker_legend`). The explainer's tracker table and the workspace panel read from it. To refresh: fetch each `official_url`, extract links whose text or href matches /noticing center|\bBNC\b/i, drop links to the BNC's own sites, write the fields, re-render the explainer table (the section between the `tracker` heading and the next h2) and update the dates in it. Never promote a district to `confirmed` without a human reading the page.
