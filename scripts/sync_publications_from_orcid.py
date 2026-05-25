#!/usr/bin/env python3
"""Find missing publication bundles from an ORCID works record.

ORCID is used only as the DOI discovery source. Missing DOIs are imported
through create_publication_from_doi.py logic so Crossref remains the metadata
source for local Hugo publication pages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import create_publication_from_doi as publication


ORCID_WORKS_URL = "https://pub.orcid.org/v3.0/{orcid}/works"


def normalize_orcid(raw: str) -> str:
    value = raw.strip()
    if "orcid=" in value:
        query = urllib.parse.urlparse(value).query
        parsed = urllib.parse.parse_qs(query).get("orcid", [])
        if parsed:
            value = parsed[0]
    value = re.sub(r"^https?://orcid\.org/", "", value, flags=re.I)
    value = value.strip("/")
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", value):
        raise ValueError(f"invalid ORCID iD: {raw}")
    return value


def fetch_orcid_works(orcid: str, *, verify_tls: bool = True) -> dict[str, Any]:
    url = ORCID_WORKS_URL.format(orcid=urllib.parse.quote(orcid, safe=""))
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "nanophotonics.cc ORCID publication sync",
        },
    )
    context = None if verify_tls else ssl._create_unverified_context()

    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"ORCID returned HTTP {error.code} for {orcid}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach ORCID: {error.reason}") from error


def walk_json(value: Any) -> list[Any]:
    nodes = [value]
    if isinstance(value, dict):
        for child in value.values():
            nodes.extend(walk_json(child))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(walk_json(child))
    return nodes


def external_id_value(node: dict[str, Any]) -> str:
    value = node.get("external-id-normalized") or node.get("external-id-value")
    if isinstance(value, dict):
        value = value.get("value")
    return str(value or "").strip()


def extract_dois(orcid_payload: dict[str, Any]) -> list[str]:
    dois: list[str] = []
    seen: set[str] = set()
    for node in walk_json(orcid_payload):
        if not isinstance(node, dict):
            continue
        id_type = str(node.get("external-id-type", "")).lower()
        if id_type != "doi":
            continue
        doi = publication.normalize_doi(external_id_value(node))
        key = publication.doi_key(doi)
        if doi and key not in seen:
            seen.add(key)
            dois.append(doi)
    return dois


def existing_by_doi(roots: list[Path], doi: str) -> list[Path]:
    return publication.existing_publications(roots, doi)


def import_publication(
    *,
    doi: str,
    roots: list[Path],
    mailto: str | None,
    verify_tls: bool,
    force: bool,
) -> list[Path]:
    work = publication.fetch_crossref_work(doi, mailto, verify_tls=verify_tls)
    date = publication.publication_date(work)
    slug = publication.slugify_from_doi(doi)
    index_md = publication.build_index_md(work, doi, date)
    cite_bib = publication.build_cite_bib(work, doi, date)

    targets = [(root / slug / "index.md", index_md) for root in roots]
    targets += [(root / slug / "cite.bib", cite_bib) for root in roots]

    for path, _content in targets:
        if path.exists() and not force:
            raise RuntimeError(f"{path} already exists; pass --force to overwrite")

    for path, content in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return [root / slug for root in roots]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use ORCID as a DOI radar and import missing publications via Crossref.",
    )
    parser.add_argument("orcid", help="ORCID iD or ORCID URL")
    parser.add_argument(
        "--roots",
        nargs="+",
        default=[Path("content/en/publication"), Path("content/zh/publication")],
        type=Path,
        help="Publication root directories to check and write",
    )
    parser.add_argument("--mailto", help="Optional email passed to Crossref")
    parser.add_argument(
        "--import-missing",
        action="store_true",
        help="Write missing publication bundles instead of only reporting them",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only process the first N missing DOIs when importing",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite target files")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification for local certificate-chain problems",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        orcid = normalize_orcid(args.orcid)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    verify_tls = not args.insecure
    try:
        payload = fetch_orcid_works(orcid, verify_tls=verify_tls)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        if "CERTIFICATE_VERIFY_FAILED" in str(error):
            print(
                "hint: install/update Python certificates, or retry with --insecure "
                "on a trusted network.",
                file=sys.stderr,
            )
        return 1

    dois = extract_dois(payload)
    existing: list[tuple[str, list[Path]]] = []
    missing: list[str] = []
    for doi in dois:
        matches = existing_by_doi(args.roots, doi)
        if matches:
            existing.append((doi, matches))
        else:
            missing.append(doi)

    print(f"ORCID: {orcid}")
    print(f"DOIs found in public ORCID works: {len(dois)}")
    print(f"Already present locally: {len(existing)}")
    print(f"Missing locally: {len(missing)}")

    if missing:
        print("\nMissing DOI candidates:")
        for doi in missing:
            print(f"- {doi}")

    if not args.import_missing:
        print("\nNo files written. Re-run with --import-missing to create bundles.")
        return 0

    to_import = missing[: args.limit] if args.limit else missing
    if not to_import:
        print("\nNothing to import.")
        return 0

    print("\nImporting missing publications via Crossref:")
    for doi in to_import:
        try:
            created = import_publication(
                doi=doi,
                roots=args.roots,
                mailto=args.mailto,
                verify_tls=verify_tls,
                force=args.force,
            )
        except RuntimeError as error:
            print(f"- {doi}: failed: {error}", file=sys.stderr)
            continue
        for path in created:
            print(f"- {doi}: created {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
