#!/usr/bin/env python3
"""Create a local Hugo post bundle from DOI metadata.

The script uses Crossref as a stable DOI metadata source, then creates a
Markdown Page Bundle under content/zh/post/ by default. It intentionally does
not fetch paper images; add an authorized local featured image manually.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import ssl
import sys
import textwrap
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
            "User-Agent": "nanophotonics.cc DOI post generator",
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
        return str(value[0]).strip()
    if isinstance(value, str):
        return value.strip()
    return ""


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
        date = date_from_parts(work.get(key, {}).get("date-parts"))
        if date:
            return date
    return dt.date.today()


def format_author(author: dict[str, Any]) -> str:
    given = str(author.get("given", "")).strip()
    family = str(author.get("family", "")).strip()
    name = " ".join(part for part in (given, family) if part)
    return name or str(author.get("name", "")).strip()


def author_list(work: dict[str, Any]) -> str:
    authors = work.get("author", [])
    if not isinstance(authors, list):
        return "待补充"
    names = [format_author(author) for author in authors if isinstance(author, dict)]
    names = [name for name in names if name]
    return ", ".join(names) if names else "待补充"


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def slugify(title: str, max_words: int = 10, max_length: int = 70) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    words = re.findall(r"[A-Za-z0-9]+", ascii_title.lower())
    selected: list[str] = []
    for word in words:
        candidate = "-".join([*selected, word])
        if len(selected) >= max_words or len(candidate) > max_length:
            break
        selected.append(word)
    slug = "-".join(selected)
    return slug or "paper-highlight"


def build_markdown(
    *,
    title: str,
    journal: str,
    date: dt.date,
    doi: str,
    authors: str,
    draft: bool,
    title_prefix: str,
) -> str:
    front_matter = [
        "---",
        f"title: {yaml_quote(title_prefix + title)}",
        f"date: {date.isoformat()}",
    ]
    if draft:
        front_matter.append("draft: true")
    front_matter.append("---")

    doi_url = f"https://doi.org/{doi}"
    journal_text = f"在 *{journal}* 发表" if journal != "待补充" else "发表"

    body = f"""
    近日，课题组相关论文 “{title}” {journal_text}。本文稿由 DOI 元数据自动生成，请在发布前补充研究背景、核心贡献、图文解析和授权图片。

    <!--more-->

    > 图片待补充：请将论文封面图、Figure 1 或其他授权论文图片保存为 `featured.jpg`，并在正文中加入对应图片说明。

    ## 论文信息

    - 题目：{title}
    - 期刊：{journal}
    - 时间：{date.isoformat()}
    - DOI：<{doi_url}>
    - 作者：{authors}

    ## 研究背景

    待补充：说明该方向为什么重要，以及这篇论文面对的核心科学或工程问题。

    ## 核心贡献

    待补充：用 2-3 段文字概括论文解决了什么问题、采用了什么方法、取得了哪些关键结果。

    ## 图文解析

    待补充：插入已授权的论文图片，例如 `featured.jpg`、`figure-1.jpg`、`figure-2.jpg`，并用短段落解释每张图的作用。

    ## 一句话总结

    待补充：用一段话把这项工作的意义讲清楚。
    """

    return "\n".join(front_matter) + "\n" + textwrap.dedent(body).lstrip()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Crossref metadata for a DOI and create a Hugo post bundle.",
    )
    parser.add_argument("doi", help="DOI, DOI URL, or doi: prefixed value")
    parser.add_argument(
        "--output-root",
        default="content/zh/post",
        type=Path,
        help="Directory that will receive the generated post bundle",
    )
    parser.add_argument(
        "--slug",
        help="Override the generated folder slug after the YYYY-MM-DD prefix",
    )
    parser.add_argument(
        "--title-prefix",
        default="论文速递 | ",
        help="Prefix used for the generated Chinese post title",
    )
    parser.add_argument(
        "--date",
        help="Override publication date as YYYY-MM-DD",
    )
    parser.add_argument(
        "--mailto",
        help="Optional email passed to Crossref for polite API usage",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Do not mark the generated post as draft",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite index.md if the target bundle already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the target path and generated Markdown without writing files",
    )
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
    title = first_text(work.get("title")) or "待补充"
    journal = first_text(work.get("container-title")) or "待补充"
    date = dt.date.fromisoformat(args.date) if args.date else publication_date(work)
    authors = author_list(work)
    slug = args.slug or slugify(title)
    bundle_dir = args.output_root / f"{date.isoformat()}-{slug}"
    index_path = bundle_dir / "index.md"

    markdown = build_markdown(
        title=title,
        journal=journal,
        date=date,
        doi=doi,
        authors=authors,
        draft=not args.publish,
        title_prefix=args.title_prefix,
    )

    if args.dry_run:
        print(f"Target: {index_path}")
        print()
        print(markdown)
        return 0

    if index_path.exists() and not args.force:
        print(f"error: {index_path} already exists; pass --force to overwrite", file=sys.stderr)
        return 1

    bundle_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(markdown, encoding="utf-8")
    print(f"Created {index_path}")
    print("Next: add an authorized local image as featured.jpg before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
