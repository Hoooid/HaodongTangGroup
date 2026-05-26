#!/usr/bin/env python3
"""Fetch journal issue covers as `cover-auto.*` previews.

This is intentionally conservative: it only writes `cover-auto.*`, never
curated `cover.*`, and only for publisher issue-cover URL patterns we can derive
from local publication metadata.
"""

from __future__ import annotations

import argparse
import re
import shutil
import ssl
import urllib.error
import urllib.request
from pathlib import Path


EN_ROOT = Path("content/en/publication")
ZH_ROOT = Path("content/zh/publication")

IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

RSC_SERIES = {
    "Journal of Materials Chemistry C": "TC",
    "Journal of Materials Chemistry A": "TA",
    "RSC Advances": "RA",
    "Nanoscale Horizons": "NH",
    "Energy & Environmental Science": "EE",
}

SPRINGER_JOURNALS = {
    "Nature Electronics": "41928",
}


def strip_quotes(value: str) -> str:
    value = value.strip().rstrip(",")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def read_front_matter(index_path: Path) -> dict[str, str | list[str]]:
    text = index_path.read_text(encoding="utf-8", errors="ignore")
    fields: dict[str, str | list[str]] = {}
    if not text.startswith("---"):
        return fields
    front = text.split("---", 2)[1]
    for key in ("title", "date", "doi", "publication"):
        match = re.search(rf"^{key}:\s*(.*)$", front, re.M)
        if match:
            fields[key] = strip_quotes(match.group(1))
    authors_match = re.search(r"^authors:\n(?P<body>(?:^\s*-\s.*\n?)+)", front, re.M)
    if authors_match:
        fields["authors"] = [
            strip_quotes(line.strip()[1:])
            for line in authors_match.group("body").splitlines()
            if line.strip().startswith("-")
        ]
    return fields


def read_bib_fields(cite_path: Path) -> dict[str, str]:
    if not cite_path.exists():
        return {}
    text = cite_path.read_text(encoding="utf-8", errors="ignore")
    fields: dict[str, str] = {}
    for key in ("doi", "journal", "volume", "number", "year"):
        match = re.search(rf"\b{key}\s*=\s*[\{{\"]([^}}\"]+)", text, flags=re.I)
        if match:
            fields[key] = strip_quotes(match.group(1))
    return fields


def has_tang_author(fields: dict[str, str | list[str]]) -> bool:
    authors = fields.get("authors", [])
    if not isinstance(authors, list):
        return False
    return "haodong tang" in "; ".join(authors).lower()


def has_manual_cover(bundle: Path) -> bool:
    return any(
        path.is_file()
        and path.stem.lower() == "cover"
        and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        for path in bundle.iterdir()
    )


def issue_number_from_date(date: str) -> str:
    match = re.match(r"^(\d{4})-(\d{2})-", date)
    return str(int(match.group(2))) if match else ""


def rsc_issue_cover_url(journal: str, volume: str, issue: str) -> str:
    series = RSC_SERIES.get(journal)
    if not series or not volume or not issue or not issue.isdigit():
        return ""
    issue_id = f"{series}{int(volume):03d}{int(issue):03d}"
    return (
        "https://pubs.rsc.org/en/Image/Get?"
        "imageInfo.ImageType=CoverIssue&"
        f"imageInfo.ImageIdentifier.SerCode={series}&"
        f"imageInfo.ImageIdentifier.IssueId={issue_id}"
    )


def springer_issue_cover_url(journal: str, volume: str, issue: str) -> str:
    journal_id = SPRINGER_JOURNALS.get(journal)
    if not journal_id or not volume or not issue:
        return ""
    return f"https://media.springernature.com/w440/springer-static/cover-hires/journal/{journal_id}/{volume}/{issue}"


def candidate_url(bundle: Path, front: dict[str, str | list[str]], bib: dict[str, str]) -> tuple[str, str]:
    journal = bib.get("journal") or str(front.get("publication", "")).strip("*")
    volume = bib.get("volume", "")
    issue = bib.get("number", "")
    if journal in SPRINGER_JOURNALS and not issue:
        issue = issue_number_from_date(str(front.get("date", "")))
    url = rsc_issue_cover_url(journal, volume, issue)
    if url:
        return "rsc", url
    url = springer_issue_cover_url(journal, volume, issue)
    if url:
        return "springer", url
    return "", ""


def request_image(url: str, *, verify_tls: bool, timeout: int = 30) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "nanophotonics.cc issue cover fetcher",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    context = None if verify_tls else ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
        body = response.read(5_000_000)
    if not content_type.startswith("image/") or len(body) < 5_000:
        raise ValueError(f"not a usable image: {content_type} {len(body)} bytes")
    return body, content_type


def clear_auto(bundle: Path) -> None:
    for old in bundle.glob("cover-auto.*"):
        if old.name == "cover-auto-article.png":
            continue
        old.unlink()


def write_cover(bundle: Path, body: bytes, content_type: str, *, force: bool) -> Path:
    ext = IMAGE_EXTENSIONS.get(content_type, ".jpg")
    output = bundle / f"cover-auto{ext}"
    if output.exists() and not force:
        return output
    if force:
        clear_auto(bundle)
    output.write_bytes(body)
    return output


def sync_to_zh(en_bundle: Path, output: Path, *, force: bool) -> None:
    zh_bundle = ZH_ROOT / en_bundle.name
    if not zh_bundle.exists():
        return
    if has_manual_cover(zh_bundle):
        return
    if force:
        clear_auto(zh_bundle)
    shutil.copyfile(output, zh_bundle / output.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch issue cover previews for publication bundles.")
    parser.add_argument("--force", action="store_true", help="Replace existing cover-auto files")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification")
    parser.add_argument("--match", help="Only process paths/titles/DOIs containing this text")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    processed = 0
    written = 0
    for bundle in sorted(path for path in EN_ROOT.iterdir() if (path / "index.md").exists()):
        front = read_front_matter(bundle / "index.md")
        if not has_tang_author(front) or has_manual_cover(bundle):
            continue
        bib = read_bib_fields(bundle / "cite.bib")
        haystack = " ".join([str(bundle), str(front.get("title", "")), bib.get("doi", "")]).lower()
        if args.match and args.match.lower() not in haystack:
            continue
        source, url = candidate_url(bundle, front, bib)
        if not url:
            continue
        if args.limit is not None and processed >= args.limit:
            break
        processed += 1
        print(f"{bundle}: {source} {url}")
        if args.dry_run:
            continue
        try:
            body, content_type = request_image(url, verify_tls=not args.insecure)
            output = write_cover(bundle, body, content_type, force=args.force)
            sync_to_zh(bundle, output, force=args.force)
            written += 1
            print(f"  saved {output}")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
            print(f"  failed: {error}")
    print(f"Processed {processed}; wrote {written}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
