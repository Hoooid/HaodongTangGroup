#!/usr/bin/env python3
"""Find and optionally download publisher thumbnail candidates for publications.

This is intentionally a review-first helper. It follows DOI / URL landing pages,
looks for Open Graph, Twitter Card, and JSON-LD image metadata, then can save the
first valid candidate as `cover-auto.*`. Curated local images still win in the
Publication list.
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOTS = [Path("content/en/publication"), Path("content/zh/publication")]
OPENALEX_WORK_URL = "https://api.openalex.org/works/{doi_url}"
UNPAYWALL_WORK_URL = "https://api.unpaywall.org/v2/{doi}"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
DEFAULT_COVER_OVERRIDES = Path("data/publication_covers.yaml")
DEFAULT_MISS_REPORT = Path("tmp/publication-cover-misses.md")
LOCAL_PDF_NAME = "paper-auto.pdf"
IMAGE_META_KEYS = {
    "og:image",
    "og:image:url",
    "og:image:secure_url",
    "twitter:image",
    "twitter:image:src",
}
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
PDF_META_KEYS = {
    "citation_pdf_url",
    "dc.identifier",
}


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[str] = []
        self.pdfs: list[str] = []
        self._in_json_ld = False
        self._json_ld_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "meta":
            key = (attrs_dict.get("property") or attrs_dict.get("name") or "").lower()
            content = attrs_dict.get("content", "").strip()
            if key in IMAGE_META_KEYS and content:
                self.images.append(html.unescape(content))
            if key in PDF_META_KEYS and content:
                self.pdfs.append(html.unescape(content))
        if tag.lower() == "a":
            href = attrs_dict.get("href", "").strip()
            link_type = attrs_dict.get("type", "").lower()
            if href and (".pdf" in href.lower() or "pdf" in link_type):
                self.pdfs.append(html.unescape(href))
        if tag.lower() == "script" and attrs_dict.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_ld_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_json_ld:
            raw = "".join(self._json_ld_chunks).strip()
            self._in_json_ld = False
            self._json_ld_chunks = []
            self.images.extend(extract_json_ld_images(raw))


def extract_json_ld_images(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    images: list[str] = []
    for node in walk_json(payload):
        if not isinstance(node, dict) or "image" not in node:
            continue
        value = node["image"]
        if isinstance(value, str):
            images.append(value)
        elif isinstance(value, list):
            images.extend(item for item in value if isinstance(item, str))
        elif isinstance(value, dict):
            url = value.get("url") or value.get("@id")
            if isinstance(url, str):
                images.append(url)
    return images


def walk_json(value: Any) -> list[Any]:
    nodes = [value]
    if isinstance(value, dict):
        for child in value.values():
            nodes.extend(walk_json(child))
    elif isinstance(value, list):
        for child in value:
            nodes.extend(walk_json(child))
    return nodes


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def first_url(value: str) -> str:
    matches = re.findall(r"https?://[^\s<>'\")\]]+", value)
    if matches:
        return matches[0].rstrip(".,;:")
    return value.strip()


def normalize_doi(value: str) -> str:
    doi = strip_quotes(value)
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.strip()


def read_front_matter(index_path: Path) -> dict[str, str]:
    lines = index_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    fields: dict[str, str] = {}
    in_links = False
    current_link_name = ""
    pending_key = ""
    pending_quote = ""
    pending_chunks: list[str] = []
    for line in lines:
        if pending_key:
            pending_chunks.append(line.strip())
            if line.strip().endswith(pending_quote):
                fields[pending_key] = strip_quotes(" ".join(pending_chunks))
                pending_key = ""
                pending_quote = ""
                pending_chunks = []
            continue
        if line.strip() == "---" and fields:
            break
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            fields[key] = strip_quotes(value)
            if key == "doi":
                fields[key] = normalize_doi(value)
            if value.startswith(("'", '"')) and not value.endswith(value[0]):
                pending_key = key
                pending_quote = value[0]
                pending_chunks = [value]
            in_links = key == "links"
            current_link_name = ""
            continue
        if in_links:
            name_match = re.match(r"^\s*-\s*name:\s*(.*)$", line)
            if name_match:
                current_link_name = strip_quotes(name_match.group(1)).upper()
                continue
            url_match = re.match(r"^\s*url:\s*(.*)$", line)
            if url_match and current_link_name == "URL":
                fields["url"] = strip_quotes(url_match.group(1))
    cite_fields = read_cite_bib_fields(index_path.parent / "cite.bib")
    for key in ("doi", "url"):
        if not fields.get(key) and cite_fields.get(key):
            fields[key] = cite_fields[key]
    return fields


def read_cite_bib_fields(cite_path: Path) -> dict[str, str]:
    if not cite_path.exists():
        return {}
    text = cite_path.read_text(encoding="utf-8", errors="ignore")
    fields: dict[str, str] = {}
    for key in ("doi", "url"):
        match = re.search(rf"\b{key}\s*=\s*[\{{\"]([^}}\"]+)", text, flags=re.IGNORECASE)
        if not match:
            continue
        value = strip_quotes(match.group(1).rstrip(","))
        fields[key] = normalize_doi(value) if key == "doi" else first_url(value)
    return fields


def read_cover_overrides(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    overrides: dict[str, dict[str, str]] = {}
    current_doi = ""
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        top_match = re.match(r"^([^\s].*):\s*$", line)
        if top_match:
            current_doi = normalize_doi(top_match.group(1))
            overrides.setdefault(current_doi.lower(), {})
            continue
        field_match = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if field_match and current_doi:
            key, value = field_match.groups()
            overrides[current_doi.lower()][key] = strip_quotes(value)
    return overrides


def landing_url(fields: dict[str, str]) -> str:
    if fields.get("url"):
        return first_url(fields["url"])
    if fields.get("doi"):
        return f"https://doi.org/{fields['doi']}"
    return ""


def request_url(url: str, *, verify_tls: bool, timeout: int = 30) -> tuple[str, bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "nanophotonics.cc publication image fetcher",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*;q=0.8,*/*;q=0.7",
        },
    )
    context = None if verify_tls else ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
        return response.geturl(), response.read(3_000_000), content_type


def request_json(url: str, *, verify_tls: bool, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "nanophotonics.cc publication image fetcher",
            "Accept": "application/json",
        },
    )
    context = None if verify_tls else ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def image_candidates(url: str, *, verify_tls: bool) -> list[str]:
    final_url, body, content_type = request_url(url, verify_tls=verify_tls)
    if content_type.startswith("image/"):
        return [final_url]
    html_text = body.decode("utf-8", errors="ignore")
    parser = MetadataParser()
    parser.feed(html_text)
    seen: set[str] = set()
    candidates: list[str] = []
    for candidate in parser.images:
        absolute = urllib.parse.urljoin(final_url, candidate.strip())
        if not absolute or absolute in seen:
            continue
        seen.add(absolute)
        candidates.append(absolute)
    return candidates


def landing_metadata(url: str, *, verify_tls: bool) -> tuple[list[str], list[str]]:
    final_url, body, content_type = request_url(url, verify_tls=verify_tls)
    if content_type.startswith("image/"):
        return [final_url], []
    if content_type == "application/pdf" or final_url.lower().endswith(".pdf"):
        return [], [final_url]

    html_text = body.decode("utf-8", errors="ignore")
    parser = MetadataParser()
    parser.feed(html_text)
    images = unique_absolute_urls(parser.images, final_url)
    pdfs = [
        url
        for url in unique_absolute_urls(parser.pdfs, final_url)
        if looks_like_pdf_url(url)
    ]
    return images, pdfs


def unique_absolute_urls(values: list[str], base_url: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for value in values:
        absolute = urllib.parse.urljoin(base_url, value.strip())
        if not absolute or absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls


def looks_like_pdf_url(url: str) -> bool:
    lowered = url.lower()
    if lowered.endswith(".pdf") or ".pdf?" in lowered:
        return True
    return any(marker in lowered for marker in ("/pdf", "download=true", "pdfdirect"))


def openalex_pdf_candidates(doi: str, *, verify_tls: bool) -> list[str]:
    if not doi:
        return []
    doi_url = f"https://doi.org/{doi.strip()}"
    url = OPENALEX_WORK_URL.format(doi_url=urllib.parse.quote(doi_url, safe=""))
    try:
        payload = request_json(url, verify_tls=verify_tls)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []

    candidates: list[str] = []
    for key in ("best_oa_location", "primary_location"):
        location = payload.get(key)
        if isinstance(location, dict):
            pdf_url = location.get("pdf_url")
            if isinstance(pdf_url, str) and pdf_url:
                candidates.append(pdf_url)
    locations = payload.get("locations")
    if isinstance(locations, list):
        for location in locations:
            if isinstance(location, dict):
                pdf_url = location.get("pdf_url")
                if isinstance(pdf_url, str) and pdf_url:
                    candidates.append(pdf_url)
    oa_url = payload.get("open_access", {}).get("oa_url")
    if isinstance(oa_url, str) and looks_like_pdf_url(oa_url):
        candidates.append(oa_url)
    return unique_absolute_urls(candidates, doi_url)


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def crossref_doi_for_title(title: str, *, verify_tls: bool) -> str:
    if not title:
        return ""
    params = urllib.parse.urlencode({"rows": 3, "query.title": title})
    try:
        payload = request_json(f"{CROSSREF_WORKS_URL}?{params}", verify_tls=verify_tls)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return ""
    target = normalized_title(title)
    items = payload.get("message", {}).get("items", [])
    if not isinstance(items, list):
        return ""
    for item in items:
        if not isinstance(item, dict):
            continue
        titles = item.get("title")
        doi = item.get("DOI")
        if not isinstance(titles, list) or not isinstance(doi, str):
            continue
        if any(normalized_title(candidate) == target for candidate in titles if isinstance(candidate, str)):
            return normalize_doi(doi)
    return ""


def unpaywall_pdf_candidates(doi: str, email: str, *, verify_tls: bool) -> list[str]:
    if not doi or not email:
        return []
    normalized = normalize_doi(doi)
    params = urllib.parse.urlencode({"email": email})
    url = f"{UNPAYWALL_WORK_URL.format(doi=urllib.parse.quote(normalized, safe=''))}?{params}"
    try:
        payload = request_json(url, verify_tls=verify_tls)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []

    candidates: list[str] = []
    for key in ("best_oa_location",):
        location = payload.get(key)
        if isinstance(location, dict):
            add_unpaywall_location_candidates(location, candidates)
    locations = payload.get("oa_locations")
    if isinstance(locations, list):
        for location in locations:
            if isinstance(location, dict):
                add_unpaywall_location_candidates(location, candidates)
    doi_url = f"https://doi.org/{normalized}"
    return unique_absolute_urls(candidates, doi_url)


def add_unpaywall_location_candidates(location: dict[str, Any], candidates: list[str]) -> None:
    pdf_url = location.get("url_for_pdf")
    if isinstance(pdf_url, str) and pdf_url:
        candidates.append(pdf_url)
    landing = location.get("url")
    if isinstance(landing, str) and looks_like_pdf_url(landing):
        candidates.append(landing)


def extension_for(url: str, content_type: str) -> str:
    if content_type in IMAGE_EXTENSIONS:
        return IMAGE_EXTENSIONS[content_type]
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed = mimetypes.guess_extension(content_type)
    return ".jpg" if guessed == ".jpe" else (guessed or ".jpg")


def download_first_valid(
    candidates: list[str],
    output_base: Path,
    *,
    verify_tls: bool,
    min_bytes: int,
    force: bool,
) -> Path | None:
    if list(output_base.parent.glob(f"{output_base.name}.*")) and not force:
        return None
    for candidate in candidates:
        try:
            final_url, body, content_type = request_url(candidate, verify_tls=verify_tls)
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue
        if not content_type.startswith("image/") or len(body) < min_bytes:
            continue
        ext = extension_for(final_url, content_type)
        output = output_base.with_suffix(ext)
        for old in output_base.parent.glob(f"{output_base.name}.*"):
            if force:
                old.unlink()
        output.write_bytes(body)
        return output
    return None


def download_first_pdf(
    candidates: list[str],
    output_pdf: Path,
    *,
    verify_tls: bool,
    min_bytes: int,
) -> Path | None:
    for candidate in candidates:
        try:
            final_url, body, content_type = request_url(candidate, verify_tls=verify_tls)
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue
        final_path = urllib.parse.urlparse(final_url).path.lower()
        is_pdf = content_type == "application/pdf" or final_path.endswith(".pdf")
        if not is_pdf or len(body) < min_bytes:
            continue
        output_pdf.write_bytes(body)
        return output_pdf
    return None


def render_pdf_first_page(pdf_path: Path, output_base: Path, *, force: bool) -> Path | None:
    qlmanage = shutil.which("qlmanage")
    if not qlmanage:
        return None
    if list(output_base.parent.glob(f"{output_base.name}.*")) and not force:
        return None

    with tempfile.TemporaryDirectory(prefix="publication-cover-") as tmp:
        tmp_dir = Path(tmp)
        result = subprocess.run(
            [qlmanage, "-t", "-s", "1200", "-o", str(tmp_dir), str(pdf_path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return None
        thumbnails = sorted(tmp_dir.glob("*"))
        if not thumbnails:
            return None
        source = thumbnails[0]
        ext = ".png" if source.suffix.lower() not in {".jpg", ".jpeg", ".png"} else source.suffix.lower()
        output = output_base.with_suffix(".jpg" if ext == ".jpeg" else ext)
        for old in output_base.parent.glob(f"{output_base.name}.*"):
            if force:
                old.unlink()
        shutil.copyfile(source, output)
        return output


def download_pdf_cover(
    candidates: list[str],
    output_base: Path,
    *,
    verify_tls: bool,
    min_bytes: int,
    force: bool,
    keep_pdf: bool,
) -> Path | None:
    if list(output_base.parent.glob(f"{output_base.name}.*")) and not force:
        return None
    with tempfile.TemporaryDirectory(prefix="publication-pdf-") as tmp:
        pdf_path = Path(tmp) / "source.pdf"
        downloaded = download_first_pdf(
            candidates,
            pdf_path,
            verify_tls=verify_tls,
            min_bytes=min_bytes,
        )
        if not downloaded:
            return None
        if keep_pdf:
            local_pdf = output_base.parent / LOCAL_PDF_NAME
            if force or not local_pdf.exists():
                shutil.copyfile(downloaded, local_pdf)
        return render_pdf_first_page(downloaded, output_base, force=force)


def publication_dirs(roots: list[Path]) -> list[Path]:
    dirs: list[Path] = []
    for root in roots:
        if root.exists():
            dirs.extend(path for path in root.iterdir() if (path / "index.md").exists())
    return sorted(dirs)


def has_manual_image(bundle_dir: Path) -> bool:
    patterns = ["featured.*", "cover.*"]
    return any(match for pattern in patterns for match in bundle_dir.glob(pattern))


def has_auto_image(bundle_dir: Path) -> bool:
    return any(bundle_dir.glob("cover-auto.*"))


def has_named_image(bundle_dir: Path, basename: str) -> bool:
    return any(bundle_dir.glob(f"{basename}.*"))


def build_miss_report(misses: list[dict[str, str]]) -> str:
    lines = [
        "# Publication Cover Misses",
        "",
        "Generated by `scripts/fetch_publication_images.py`.",
        "",
    ]
    if not misses:
        lines.append("No misses recorded.")
        return "\n".join(lines) + "\n"
    for miss in misses:
        lines.extend(
            [
                f"## {miss.get('title') or miss['bundle']}",
                "",
                f"- Bundle: `{miss['bundle']}`",
                f"- DOI: `{miss.get('doi') or 'n/a'}`",
                f"- URL: {miss.get('url') or 'n/a'}",
                f"- Reason: {miss.get('reason') or 'No usable image/PDF candidate'}",
                f"- Suggested search: `{miss.get('search') or ''}`",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find or download publication image candidates.")
    parser.add_argument("--roots", nargs="+", default=ROOTS, type=Path)
    parser.add_argument("--download", action="store_true", help="Download the first valid candidate")
    parser.add_argument(
        "--output-basename",
        default="cover-auto",
        help="Base filename for downloaded/rendered cover images, for example cover-auto or featured",
    )
    parser.add_argument(
        "--pdf-first-page",
        action="store_true",
        help="If no image candidate is usable, download a PDF candidate and render page 1",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing cover-auto files")
    parser.add_argument(
        "--keep-pdf",
        action="store_true",
        help=f"Keep successfully downloaded PDF candidates as {LOCAL_PDF_NAME} inside each publication bundle",
    )
    parser.add_argument(
        "--no-openalex",
        action="store_true",
        help="Do not use OpenAlex open-access PDF URLs as a PDF fallback",
    )
    parser.add_argument(
        "--no-unpaywall",
        action="store_true",
        help="Do not use Unpaywall open-access PDF URLs as a PDF fallback",
    )
    parser.add_argument(
        "--no-crossref-title",
        action="store_true",
        help="Do not use Crossref title search to fill missing DOI values",
    )
    parser.add_argument(
        "--unpaywall-email",
        default=os.environ.get("UNPAYWALL_EMAIL", "tanghaodong@sztu.edu.cn"),
        help="Email address sent to Unpaywall; defaults to UNPAYWALL_EMAIL or the site contact email",
    )
    parser.add_argument(
        "--cover-overrides",
        type=Path,
        default=DEFAULT_COVER_OVERRIDES,
        help="Manual DOI-to-image/PDF override YAML file",
    )
    parser.add_argument(
        "--miss-report",
        type=Path,
        default=DEFAULT_MISS_REPORT,
        help="Write a Markdown report of bundles that still lack a downloadable cover",
    )
    parser.add_argument("--include-manual", action="store_true", help="Also process bundles with featured/cover images")
    parser.add_argument("--limit", type=int, help="Process at most N bundles")
    parser.add_argument("--match", help="Only process bundles whose path, title, or DOI contains this text")
    parser.add_argument("--min-bytes", type=int, default=5_000, help="Minimum downloaded image size")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verify_tls = not args.insecure
    cover_overrides = read_cover_overrides(args.cover_overrides)
    misses: list[dict[str, str]] = []
    processed = 0
    downloaded = 0
    for bundle_dir in publication_dirs(args.roots):
        if args.limit is not None and processed >= args.limit:
            break
        if not args.include_manual and has_manual_image(bundle_dir):
            continue
        fields = read_front_matter(bundle_dir / "index.md")
        if args.match:
            haystack = " ".join([str(bundle_dir), fields.get("title", ""), fields.get("doi", "")]).lower()
            if args.match.lower() not in haystack:
                continue
        if not fields.get("doi") and not args.no_crossref_title:
            doi = crossref_doi_for_title(fields.get("title", ""), verify_tls=verify_tls)
            if doi:
                fields["doi"] = doi
                print(f"{bundle_dir}: matched DOI from Crossref title search: {doi}")
        url = landing_url(fields)
        if not url:
            continue
        processed += 1
        if args.download and has_named_image(bundle_dir, args.output_basename) and not args.force:
            print(f"{bundle_dir}: existing {args.output_basename}.*; skipped")
            continue
        override = cover_overrides.get(fields.get("doi", "").lower(), {})
        image_urls: list[str] = []
        pdf_urls: list[str] = []
        if override.get("image"):
            image_urls.append(override["image"])
        if override.get("pdf"):
            pdf_urls.append(override["pdf"])
        try:
            landing_images, landing_pdfs = landing_metadata(url, verify_tls=verify_tls)
            image_urls.extend(candidate for candidate in landing_images if candidate not in image_urls)
            pdf_urls.extend(candidate for candidate in landing_pdfs if candidate not in pdf_urls)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
            print(f"{bundle_dir}: failed to inspect {url}: {error}", file=sys.stderr)
        if args.pdf_first_page and not args.no_openalex:
            pdf_urls.extend(
                url for url in openalex_pdf_candidates(fields.get("doi", ""), verify_tls=verify_tls)
                if url not in pdf_urls
            )
        if args.pdf_first_page and not args.no_unpaywall:
            pdf_urls.extend(
                url
                for url in unpaywall_pdf_candidates(
                    fields.get("doi", ""),
                    args.unpaywall_email,
                    verify_tls=verify_tls,
                )
                if url not in pdf_urls
            )
        print(f"{bundle_dir}: {len(image_urls)} image candidate(s), {len(pdf_urls)} PDF candidate(s)")
        if override:
            print(f"  override: {override.get('note', 'manual cover source')}")
        for candidate in image_urls[:3]:
            print(f"  - {candidate}")
        for candidate in pdf_urls[:3]:
            print(f"  - PDF {candidate}")
        if args.download and image_urls:
            saved = download_first_valid(
                image_urls,
                bundle_dir / args.output_basename,
                verify_tls=verify_tls,
                min_bytes=args.min_bytes,
                force=args.force,
            )
            if saved:
                downloaded += 1
                print(f"  saved {saved}")
                continue
        if args.download and args.pdf_first_page and pdf_urls:
            saved = download_pdf_cover(
                pdf_urls,
                bundle_dir / args.output_basename,
                verify_tls=verify_tls,
                min_bytes=args.min_bytes,
                force=args.force,
                keep_pdf=args.keep_pdf,
            )
            if saved:
                downloaded += 1
                print(f"  rendered {saved}")
            else:
                print("  PDF fallback did not produce a cover")
        if args.download and not has_named_image(bundle_dir, args.output_basename):
            misses.append(
                {
                    "bundle": str(bundle_dir),
                    "title": fields.get("title", ""),
                    "doi": fields.get("doi", ""),
                    "url": url,
                    "reason": "No image downloaded; publisher/API candidates were missing or blocked",
                    "search": " ".join(
                        part
                        for part in [fields.get("title", ""), fields.get("doi", ""), "graphical abstract"]
                        if part
                    ),
                }
            )
    if args.miss_report:
        args.miss_report.parent.mkdir(parents=True, exist_ok=True)
        args.miss_report.write_text(build_miss_report(misses), encoding="utf-8")
        print(f"Wrote miss report to {args.miss_report}")
    print(f"Processed {processed} publication bundles; downloaded {downloaded} image(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
