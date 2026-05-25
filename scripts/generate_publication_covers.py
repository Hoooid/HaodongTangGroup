#!/usr/bin/env python3
"""Generate local SVG preview covers for publication bundles.

The covers are deterministic metadata cards. They give every publication a
stable local thumbnail without depending on Google Scholar or publisher images.
Manual `featured.*`, `preview.*`, or `cover.*` files can still override them.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
from pathlib import Path


PALETTES = [
    ("#8c1515", "#2e2d29", "#f7f7f5", "#dedbd2"),
    ("#006b5f", "#2e2d29", "#f5f7f4", "#d7dfd8"),
    ("#5f2a7a", "#2e2d29", "#f8f6fa", "#ded6e6"),
    ("#b65f00", "#2e2d29", "#faf7f1", "#e6d8c5"),
    ("#305f8f", "#2e2d29", "#f4f7fa", "#d3dce6"),
]

ROOTS = [Path("content/en/publication"), Path("content/zh/publication")]


def clean(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<\s*/?\s*(sub|sup)\s*>", "", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("*", "")
    return re.sub(r"\s+", " ", value).strip()


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.replace("''", "'").strip()


def read_front_matter(index_path: Path) -> dict[str, str]:
    lines = index_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fields: dict[str, str] = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            i += 1
            continue
        key, value = match.groups()
        continuation: list[str] = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            if next_line.strip() == "---":
                break
            if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*", next_line):
                break
            if next_line.startswith(" ") and not next_line.lstrip().startswith("- "):
                continuation.append(next_line.strip())
                j += 1
                continue
            break
        fields[key] = clean(strip_quotes(" ".join([value, *continuation])))
        i = j
    return fields


def wrap_words(text: str, max_chars: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and words:
        original = " ".join(words)
        visible = " ".join(lines)
        if len(visible) < len(original):
            lines[-1] = lines[-1].rstrip(".") + "..."
    return lines or ["Publication"]


def palette_for(seed: str) -> tuple[str, str, str, str]:
    digest = hashlib.sha1(seed.encode("utf-8")).digest()
    return PALETTES[digest[0] % len(PALETTES)]


def svg_text_lines(lines: list[str], *, x: int, y: int, size: int, weight: int, fill: str) -> str:
    tspans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else int(size * 1.28)
        tspans.append(
            f'<tspan x="{x}" dy="{dy}">{html.escape(line)}</tspan>'
        )
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Source Sans 3, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">'
        + "".join(tspans)
        + "</text>"
    )


def build_svg(fields: dict[str, str]) -> str:
    title = fields.get("title") or "Publication"
    publication = fields.get("publication") or "Nano Photonics Group"
    year = (fields.get("date") or "0000")[:4]
    doi = fields.get("doi", "")
    accent, ink, paper, border = palette_for(doi or title)
    title_lines = wrap_words(title, 34, 5)
    publication_lines = wrap_words(publication, 42, 2)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800" role="img" aria-label="{html.escape(title)}">
  <rect width="1200" height="800" fill="{paper}"/>
  <rect x="56" y="56" width="1088" height="688" rx="28" fill="#ffffff" stroke="{border}" stroke-width="4"/>
  <rect x="56" y="56" width="20" height="688" rx="10" fill="{accent}"/>
  <circle cx="996" cy="166" r="84" fill="{accent}" opacity="0.10"/>
  <circle cx="1058" cy="228" r="118" fill="{accent}" opacity="0.055"/>
  <text x="118" y="150" font-family="Inter, Source Sans 3, Arial, sans-serif" font-size="54" font-weight="850" fill="{accent}">NP</text>
  <text x="266" y="150" font-family="Inter, Source Sans 3, Arial, sans-serif" font-size="28" font-weight="760" letter-spacing="4" fill="{ink}" opacity="0.70">PUBLICATION</text>
  {svg_text_lines(title_lines, x=118, y=278, size=52, weight=780, fill=ink)}
  <line x1="118" y1="594" x2="426" y2="594" stroke="{accent}" stroke-width="10" stroke-linecap="round"/>
  {svg_text_lines(publication_lines, x=118, y=654, size=30, weight=680, fill=ink)}
  <text x="1046" y="674" text-anchor="end" font-family="Inter, Source Sans 3, Arial, sans-serif" font-size="66" font-weight="820" fill="{accent}">{html.escape(year)}</text>
</svg>
'''


def publication_dirs(roots: list[Path]) -> list[Path]:
    dirs: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        dirs.extend(path for path in root.iterdir() if (path / "index.md").exists())
    return sorted(dirs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SVG publication cover cards.")
    parser.add_argument("--roots", nargs="+", default=ROOTS, type=Path)
    parser.add_argument("--force", action="store_true", help="Overwrite existing preview.svg files")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be generated")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    written = 0
    skipped = 0
    for bundle_dir in publication_dirs(args.roots):
        output = bundle_dir / "preview.svg"
        if output.exists() and not args.force:
            skipped += 1
            continue
        fields = read_front_matter(bundle_dir / "index.md")
        svg = build_svg(fields)
        if args.dry_run:
            print(output)
        else:
            output.write_text(svg, encoding="utf-8")
        written += 1
    print(f"{'Would generate' if args.dry_run else 'Generated'} {written} publication covers; skipped {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
