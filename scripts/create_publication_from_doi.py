#!/usr/bin/env python3
"""Create Hugo Blox publication bundles from DOI metadata.

This script writes local Page Bundles under content/en/publication/ and
content/zh/publication/ by default. It does not create news posts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import ssl
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


CROSSREF_WORKS_URL = "https://api.crossref.org/works/{doi}"


def normalize_doi(raw: str) -> str:
    doi = raw.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    return urllib.parse.unquote(doi).strip()


def doi_key(doi: str) -> str:
    return normalize_doi(doi).lower().rstrip("/")


def fetch_crossref_work(
    doi: str,
    mailto: str | None = None,
    *,
    verify_tls: bool = True,
) -> dict[str, Any]:
    encoded_doi = urllib.parse.quote(doi, safe="")
    url = CROSSREF_WORKS_URL.format(doi=encoded_doi)
    if mailto:
        url = f"{url}?mailto={urllib.parse.quote(mailto)}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "nanophotonics.cc DOI publication generator",
        },
    )
    context = None if verify_tls else ssl._create_unverified_context()

    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Crossref returned HTTP {error.code} for DOI {doi}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach Crossref: {error.reason}") from error

    message = payload.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("Crossref response did not include a work record")
    return message


def first_text(value: Any) -> str:
    if isinstance(value, list) and value:
        return clean_text(str(value[0]))
    if isinstance(value, str):
        return clean_text(value)
    return ""


def clean_text(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"<\s*/?\s*(sub|sup)\s*>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def date_from_parts(parts: Any) -> dt.date | None:
    if not isinstance(parts, list) or not parts:
        return None
    first = parts[0]
    if not isinstance(first, list) or not first:
        return None
    year = int(first[0])
    month = int(first[1]) if len(first) > 1 else 1
    day = int(first[2]) if len(first) > 2 else 1
    return dt.date(year, month, day)


def publication_date(work: dict[str, Any]) -> dt.date:
    for key in ("published-online", "published-print", "published", "issued"):
        value = work.get(key)
        if isinstance(value, dict):
            date = date_from_parts(value.get("date-parts"))
            if date:
                return date
    return dt.date.today()


def format_author(author: dict[str, Any]) -> str:
    given = clean_text(str(author.get("given", "")))
    family = clean_text(str(author.get("family", "")))
    name = " ".join(part for part in (given, family) if part)
    return name or clean_text(str(author.get("name", "")))


def format_bib_author(author: dict[str, Any]) -> str:
    given = clean_text(str(author.get("given", "")))
    family = clean_text(str(author.get("family", "")))
    if family and given:
        return f"{family}, {given}"
    return family or given or clean_text(str(author.get("name", "")))


def authors(work: dict[str, Any]) -> list[str]:
    raw_authors = work.get("author", [])
    if not isinstance(raw_authors, list):
        return []
    names = [format_author(author) for author in raw_authors if isinstance(author, dict)]
    return [name for name in names if name]


def bib_authors(work: dict[str, Any]) -> str:
    raw_authors = work.get("author", [])
    if not isinstance(raw_authors, list):
        return ""
    names = [format_bib_author(author) for author in raw_authors if isinstance(author, dict)]
    return " and ".join(name for name in names if name)


def publication_type(work: dict[str, Any]) -> str:
    crossref_type = str(work.get("type", "")).lower()
    if "proceedings" in crossref_type:
        return "paper-conference"
    if crossref_type in {"book-chapter", "chapter"}:
        return "chapter"
    if crossref_type == "book":
        return "book"
    return "article-journal"


def primary_url(work: dict[str, Any], doi: str) -> str:
    resource = work.get("resource")
    if isinstance(resource, dict):
        primary = resource.get("primary")
        if isinstance(primary, dict) and primary.get("URL"):
            return str(primary["URL"]).strip()
    if work.get("URL"):
        return str(work["URL"]).strip()
    return f"https://doi.org/{doi}"


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def slugify_from_doi(doi: str) -> str:
    normalized = unicodedata.normalize("NFKD", doi_key(doi))
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return f"doi-{slug}" if slug else "doi-publication"


def doi_keys_in_text(text: str) -> set[str]:
    decoded = urllib.parse.unquote(text)
    candidates = re.findall(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", decoded, flags=re.I)
    return {
        doi_key(candidate.rstrip(".,;:)}]'\""))
        for candidate in candidates
        if candidate.strip()
    }


def existing_publications(roots: list[Path], doi: str) -> list[Path]:
    target = doi_key(doi)
    matches: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for bundle_dir in root.iterdir():
            if not bundle_dir.is_dir():
                continue
            publication_files = [
                path
                for path in (bundle_dir / "index.md", bundle_dir / "cite.bib")
                if path.exists()
            ]
            text = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in publication_files
            )
            if target in doi_keys_in_text(text):
                matches.append(bundle_dir / "index.md")
    return matches


def build_index_md(work: dict[str, Any], doi: str, date: dt.date) -> str:
    title = first_text(work.get("title")) or "Untitled"
    journal = first_text(work.get("container-title")) or "Journal information pending"
    names = authors(work)
    url = primary_url(work, doi)
    kind = publication_type(work)

    lines = [
        "---",
        f"title: {yaml_quote(title)}",
        "authors:",
    ]
    if names:
        lines.extend(f"- {yaml_quote(name)}" for name in names)
    else:
        lines.append("- 待补充")
    lines.extend(
        [
            f"date: {yaml_quote(date.isoformat())}",
            f"publishDate: {yaml_quote(date.isoformat() + 'T00:00:00Z')}",
            "publication_types:",
            f"- {kind}",
            f"publication: {yaml_quote('*' + journal + '*')}",
            f"doi: {doi}",
            "links:",
            "- name: URL",
            f"  url: {yaml_quote(url)}",
            "---",
            "",
        ]
    )
    return "\n".join(lines)


def bibtex_key(doi: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "", doi).upper()
    return f"DOI{normalized[:24]}" if normalized else "DOIPUBLICATION"


def build_cite_bib(work: dict[str, Any], doi: str, date: dt.date) -> str:
    title = first_text(work.get("title")) or "Untitled"
    journal = first_text(work.get("container-title"))
    url = primary_url(work, doi)
    fields = [
        f" author = {{{bib_authors(work)}}}",
        f" doi = {{{doi}}}",
    ]
    if journal:
        fields.append(f" journal = {{{journal}}}")
    if work.get("volume"):
        fields.append(f" volume = {{{work['volume']}}}")
    if work.get("issue"):
        fields.append(f" number = {{{work['issue']}}}")
    if work.get("page"):
        fields.append(f" pages = {{{work['page']}}}")
    fields.extend(
        [
            f" title = {{{title}}}",
            f" url = {{{url}}}",
            f" year = {{{date.year}}}",
            " type = {Journal Article}",
        ]
    )
    return "@article{" + bibtex_key(doi) + ",\n" + ",\n".join(fields) + "\n}\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Crossref metadata for a DOI and create publication bundles.",
    )
    parser.add_argument("doi", help="DOI, DOI URL, or doi: prefixed value")
    parser.add_argument(
        "--roots",
        nargs="+",
        default=[Path("content/en/publication"), Path("content/zh/publication")],
        type=Path,
        help="Publication root directories to write into",
    )
    parser.add_argument("--slug", help="Override the generated publication bundle slug")
    parser.add_argument("--date", help="Override publication date as YYYY-MM-DD")
    parser.add_argument("--mailto", help="Optional email passed to Crossref")
    parser.add_argument("--force", action="store_true", help="Overwrite target files")
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Generate even if the DOI already exists elsewhere",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print generated files")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification for local certificate-chain problems",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    doi = normalize_doi(args.doi)
    if not doi:
        print("error: DOI is empty", file=sys.stderr)
        return 2

    roots = list(args.roots)
    existing = existing_publications(roots, doi)
    if existing and not args.allow_duplicate:
        print("This DOI already exists in publication bundles:")
        for path in existing:
            print(f"- {path}")
        print("Use --allow-duplicate only if you intentionally want a duplicate entry.")
        return 0

    try:
        work = fetch_crossref_work(doi, args.mailto, verify_tls=not args.insecure)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        if "CERTIFICATE_VERIFY_FAILED" in str(error):
            print(
                "hint: install/update Python certificates, or retry with --insecure "
                "on a trusted network.",
                file=sys.stderr,
            )
        return 1

    date = dt.date.fromisoformat(args.date) if args.date else publication_date(work)
    slug = args.slug or slugify_from_doi(doi)
    index_md = build_index_md(work, doi, date)
    cite_bib = build_cite_bib(work, doi, date)

    targets = [(root / slug / "index.md", index_md) for root in roots]
    targets += [(root / slug / "cite.bib", cite_bib) for root in roots]

    if args.dry_run:
        for path, content in targets:
            print(f"--- {path} ---")
            print(content)
        return 0

    for path, _content in targets:
        if path.exists() and not args.force:
            print(f"error: {path} already exists; pass --force to overwrite", file=sys.stderr)
            return 1

    for path, content in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    for root in roots:
        print(f"Created {root / slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
