# AI Worklog

This file records project-specific requests, implementation decisions, and current status so future Codex chats can resume with context even when the previous conversation is not available.

## 2026-05-09 - Publication Cover Automation

Request:
- Upgrade the existing publication image fetcher so it first reads publisher-page image metadata, then falls back to PDF candidates only when explicitly run with `--download --pdf-first-page`.
- If no direct image is available, find `citation_pdf_url` or PDF links, download the PDF to a temporary directory, render the first page with local `qlmanage`, and save the result as `cover-auto.*`.
- Keep downloaded PDFs temporary and out of git.
- Continue the real download run carefully, avoiding a large uncontrolled fetch.
- From this point onward, keep project-level records of conversation requests and implementation choices for future handoff.

Implementation:
- `scripts/fetch_publication_images.py` now parses Open Graph, Twitter Card, JSON-LD image metadata, `citation_pdf_url`, and anchor PDF links.
- PDF fallback is opt-in via `--pdf-first-page`; OpenAlex open-access PDF lookup is included unless `--no-openalex` is passed.
- PDF rendering uses `qlmanage -t` into a temporary directory, then copies the generated first-page thumbnail to `cover-auto.*`.
- Publisher pages can be blocked by Wiley/ACS/IEEE, so OpenAlex is used as a more reliable fallback source for open PDF URLs.
- Dirty front matter with multiple URLs on one `url:` line is handled by taking the first valid HTTP(S) URL. DOI values written as `https://doi.org/...` are normalized before OpenAlex lookup.

Observed Results:
- Some publisher pages reject automated access, including Wiley/ACS with 403 and IEEE with 418.
- At least one direct publisher metadata image was successfully saved, for example `content/en/publication/rn-667/cover-auto.gif` from an RSC graphical abstract.
- Some OpenAlex PDF URLs still resolve to publisher-hosted PDFs that may be blocked, so the fallback is best-effort rather than guaranteed.

Current Operating Notes:
- Use dry scanning first: `python3 scripts/fetch_publication_images.py --pdf-first-page --limit 10`.
- Use a small controlled download test: `python3 scripts/fetch_publication_images.py --download --pdf-first-page --limit 1`.
- Existing curated `featured.*` and `cover.*` images are skipped unless `--include-manual` is set.
- Existing `cover-auto.*` files are kept unless `--force` is set.
- In download mode, existing `cover-auto.*` bundles are now skipped before network access unless `--force` is set.
- Verification on 80 English publication bundles showed no crash on dirty multi-URL entries; most misses were external 403/418 responses or PDF candidates that could not be directly downloaded/rendered.

## 2026-05-09 - Cover Fallback Hardening

Request:
- Improve the publication cover pipeline beyond publisher-page scraping.
- Prefer stable scholarly metadata sources before heavier browser automation.
- Add a maintainable manual path for stubborn 403/418 publisher cases.
- Export a clean list of misses so manual follow-up does not require reading terminal logs.

Implementation:
- Added Unpaywall PDF fallback after OpenAlex, enabled by default when `--pdf-first-page` is used.
- Added `--no-unpaywall` and `--unpaywall-email`; email defaults to `UNPAYWALL_EMAIL` or the site contact email.
- Added `data/publication_covers.yaml` for DOI-keyed manual overrides with `image`, `pdf`, and `note` fields.
- Added `--cover-overrides` to point at a different override file.
- Added automatic miss report generation at `tmp/publication-cover-misses.md`; `tmp/` is ignored by git.
- Kept the YAML parser intentionally narrow so the script does not need PyYAML.

Current Operating Notes:
- For normal controlled fetching: `python3 scripts/fetch_publication_images.py --download --pdf-first-page --insecure --limit 80`.
- For manual fixes, add DOI entries to `data/publication_covers.yaml`, then rerun with `--force` only for the target bundle if an existing auto cover must be replaced.
- Review `tmp/publication-cover-misses.md` after a run for the remaining manual search queue.

## 2026-05-09 - Local PDF Covers Visible in Hugo

Request:
- The live publication page still looked unchanged, with document placeholders in the list.
- Save accessible PDFs locally and render their first page into a visible publication preview.

Implementation:
- Added `--keep-pdf` to save successfully downloaded PDF candidates as `paper-auto.pdf` inside the publication bundle.
- Added `--output-basename`, so runs can write `featured.*` instead of only `cover-auto.*`.
- `featured.*` is Hugo Blox's strongest image convention and is now used for downloaded/rendered covers when running with `--output-basename featured`.
- Added Crossref title lookup for entries that lack DOI but have an exact title match, plus `--no-crossref-title` to disable it.
- Added `--match` to target a single bundle/title/DOI for reruns.

Observed Results:
- `python3 scripts/fetch_publication_images.py --download --pdf-first-page --keep-pdf --output-basename featured --insecure --roots content/en/publication --limit 80` wrote six visible English `featured.*` covers.
- `content/en/publication/rn-671/paper-auto.pdf` was saved locally and rendered into `content/en/publication/rn-671/featured.png`.
- Direct image candidates were also copied to visible `featured.*` files for `rn-667`, `rn-689`, `rn-695`, `rn-705`, and `rn-950`.
- The screenshot item `rn-686` can now recover DOI `10.1109/icet55676.2022.9824791` from Crossref by title, but IEEE still blocks PDF access with HTTP 418 and no open PDF candidate was found.
- Hugo 0.161 fails on this Hugo Blox version because `getCSV` is missing; use `/private/tmp/codex-hugo-0.119.0/hugo --minify` or the matching server command.

Update:
- The `featured.*` approach was too heavy because Hugo Blox renders it as a large image on publication detail pages.
- Generated `featured.*` files and `paper-auto.pdf` were removed from the affected English bundles.
- Manual publication images should use `cover.jpg` or `cover.png` inside each publication bundle instead.
- Added `MANUAL_PUBLICATION_COVERS.md` with the file convention and handoff workflow.

## 2026-05-12 - Publication Thumbnail Full-Page Display

Request:
- Publication list thumbnails were still visually incomplete after changing CSS from `object-fit: cover` to `object-fit: contain`.
- Desired effect: PDF/page-style covers should appear as complete scaled-down pages in the list, even if this leaves white margins.
- Continue keeping project-level records of conversation requests and implementation choices.

Root Cause:
- CSS alone did not fix the issue because the list template was already generating cropped raster thumbnails with Hugo image processing.
- `layouts/partials/views/citation.html` used `$image.Fill "220x160 Center"`, which creates `_220x160_fill_...` files and crops the source image before CSS receives it.

Implementation:
- Changed `layouts/partials/views/citation.html` to use `$image.Fit "220x160"` for non-SVG publication thumbnails.
- Kept `.np-publication-thumb { background: #fff; }` and `.np-publication-image { object-fit: contain; }` in `assets/scss/template.scss`.
- Rebuilt with the local compatible Hugo binary, not Homebrew Hugo 0.161:
  `/private/tmp/codex-hugo-0.119.0/hugo --ignoreCache`

Observed Results:
- Generated publication list HTML now references `_220x160_fit_...` thumbnails instead of `_220x160_fill_...`.
- In-app browser verification at `http://localhost:1313/publication/` showed the first PDF-style cover as a complete scaled-down page with white margins, matching the requested effect.
- Browser console had no relevant errors or warnings.

Current Operating Notes:
- For the remaining manual PDF/cover work, continue placing manually selected images as `cover.jpg` or `cover.png` in the matching publication bundle.
- Do not switch list thumbnails back to `Fill`; use `Fit` whenever full cover/page visibility matters.
- If local preview or builds behave differently, verify with `/private/tmp/codex-hugo-0.119.0/hugo`; the newer Homebrew Hugo can fail this theme with `function "getCSV" not defined`.

## 2026-05-12 - Manual Cover Batch Applied

Request:
- User added several manually downloaded publication PDFs and image files under `Manual Publication Cover Queue/`.
- Convert those sources into publication list covers, mirror them into both English and Chinese publication bundles, and update the tracking files.

Implementation:
- Converted two manually supplied WebP images into `cover.png`:
  - `doi-10-1002-adom-202502078`
  - `doi-10-1021-acs-jpclett-5c01032`
- Rendered the first page of eight manually supplied PDFs into `cover.png`:
  - `rn-952`
  - `doi-10-1002-sdtp-18587`
  - `doi-10-1002-sdtp-19121`
  - `doi-10-1002-sdtp-19127`
  - `doi-10-1109-eeice65049-2025-11033964`
  - `doi-10-1109-emp67345-2025-11428573`
  - `doi-10-1109-emp67345-2025-11428625`
  - `doi-10-1109-led-2024-3496412`
- Wrote each cover to both `content/en/publication/<bundle>/cover.png` and `content/zh/publication/<bundle>/cover.png`.
- Regenerated `tmp/manual-cover-queue.md` by removing all English bundles that now have a real `cover.*`, `cover-auto.*`, or `featured.*` image.

Observed Results:
- The manual queue dropped from 83 entries to 71 entries.
- The removed 12 entries include the two earlier completed covers plus the 10 covers processed in this batch.

Current Operating Notes:
- Keep using `Manual Publication Cover Queue/` as a staging folder for downloaded PDFs or images.
- For PDF sources, render page 1 to `cover.png` only when no better representative figure is available.
- After each batch, update `tmp/manual-cover-queue.md` so it remains the live remaining-work list.
