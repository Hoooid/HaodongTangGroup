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

## Marked Partial Figure Covers

These entries previously used cropped article figures as `cover.png`. The local
project tree was searched for matching full PDFs or full article assets on
2026-05-27; no matching source files were found. The cropped `cover.png` files
were removed so the site falls back to `preview.svg` until proper images can be
sourced.

- `doi-10-1109-ogc62429-2024-10738747` - Electrophoretic Deposition of PbS QDs for SWIR Photodetectors
- `doi-10-1109-ogc62429-2024-10738736` - Efficient SWIR PbS QD Photodetector Based on A Hot Spin-coating Method
- `doi-10-1109-led-2025-3532323` - Polyvinylidene Fluoride Enhanced Quantum Dot Short-Wave Infrared Photodetectors
- `doi-10-1109-icet55676-2022-9824791` - Absorption Modulation, Enhancement, and Narrowing Using Sub-Wavelength Gratings
- `rn-686` - Absorption Modulation, Enhancement, and Narrowing Using Sub-Wavelength Gratings
- `doi-10-1109-emp67345-2025-11428792` - High Efficiency QD Photodetector Prepared by Automatic Spin-Coating Equipment
- `doi-10-1109-emp67345-2025-11428663` - A Bilayer LiF/C60 Interfacial Strategy for High Mobility Inverted PbS QD SWIR Photodetectors
- `doi-10-1109-emp67345-2025-11428440` - Fitting Model-Based Dark Current Analysis for Normal and Inverted Quantum Dot Photodiodes
- `doi-10-1109-emp67345-2025-11428369` - Improving the Performance of QD Photodetectors Through PEAI-Based Interface Passivation
- `doi-10-1109-emp67345-2025-11428333` - Dynamical Calibration of Tunable Illumination System by Precise Aperture Control

## Notes

The auto fetch script may still be useful for discovering candidates, but manual covers should be committed as `cover.*` when visual quality matters.
