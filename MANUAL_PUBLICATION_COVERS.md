# Manual Publication Covers

Use this file as the handoff list for manually sourced publication images.

## File Convention

For each publication bundle, place one manually selected paper figure as:

```text
content/en/publication/<bundle>/cover.jpg
content/en/publication/<bundle>/cover.png
content/zh/publication/<bundle>/cover.jpg
content/zh/publication/<bundle>/cover.png
```

Use `cover.*`, not `featured.*`.

Why:
- `cover.*` is used by the publication list thumbnail.
- `featured.*` is rendered as a large hero image on the publication detail page, which is too prominent for most paper figures.

Preferred image source:
- graphical abstract
- Figure 1
- TOC image
- one compact representative result figure

Avoid:
- full PDF first page
- journal cover pages
- screenshots with large white margins
- figures with unreadable dense panels

## Manual Workflow

1. Open the publication URL from the site.
2. Download or crop a representative paper image.
3. Save it into the matching bundle as `cover.jpg` or `cover.png`.
4. If the site has both English and Chinese bundles, copy the same image to both language folders.
5. Rebuild with the project-compatible Hugo:

```bash
/private/tmp/codex-hugo-0.119.0/hugo --minify
```

## Current Priority Queue

Use `tmp/publication-cover-misses.md` after running the fetch script to find remaining entries that need manual covers.

Good first targets:
- recent Wiley/SID papers in `content/en/publication/doi-10-1002-*`
- IEEE conference papers with `HTTP 418` failures
- ACS entries with `HTTP 403` failures

## Notes

The auto fetch script may still be useful for discovering candidates, but manual covers should be committed as `cover.*` when visual quality matters.
