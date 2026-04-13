#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors
#
# doi_metadata_enricher.py
# ========================
# Reads "Safety Evaluation Benchmarks" sheet from AISafetyBenchExplorer.xlsx,
# extracts DOIs from well-formed Paper Link URLs, queries Semantic Scholar (primary)
# and Crossref (fallback), then writes a new enriched .xlsx file.
#
# Lookup strategy (mirrors doi_based_resolver.py):
#   1. S2 via arXiv ID       -- highest hit-rate for arXiv-hosted preprints
#   2. S2 via full DOI       -- conference / journal papers
#   3. Crossref via DOI      -- fills remaining venue gaps (ACL, ACM, IEEE, etc.)
#   4. S2 via title search   -- last resort for non-DOI links (e.g. metr.org)
#
# Usage:
#   pip install requests pandas openpyxl
#   python doi_metadata_enricher.py
#
# Optional: set S2_API_KEY for 10 req/s (free key at api.semanticscholar.org/product)

import re
import time
import json
import logging
import requests
import pandas as pd
from typing import Optional, Dict, Any, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("enricher.log")]
)
logger = logging.getLogger(__name__)

EXCEL_INPUT_PATH = "Copy-of-AISafetyBenchExplorer.xlsx"
SHEET_NAME = "Safety Evaluation Benchmarks"
OUTPUT_PATH = "paper_metadata_enriched.xlsx"
OUTPUT_SHEET_NAME = "Paper Metadata"

S2_API_KEY = None               # Optional: free key from api.semanticscholar.org/product
CONTACT_EMAIL = "Your email"    # Crossref polite-pool identifier
RATE_LIMIT_DELAY = 1.0          # seconds between API calls (no-key safe value)
TIMEOUT = 30                    # request timeout in seconds

S2_BASE = "https://api.semanticscholar.org/graph/v1"
CROSSREF_BASE = "https://api.crossref.org/works"

S2_FIELDS = [
    "paperId", "title", "year", "venue", "publicationVenue",
    "authors", "externalIds", "url", "citationCount", "referenceCount",
    "influentialCitationCount", "isOpenAccess", "openAccessPdf",
    "fieldsOfStudy", "s2FieldsOfStudy", "publicationDate", "journal"
]

def extract_doi_and_arxiv(paper_link: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a well-formed Paper Link URL and return (doi, arxiv_id).

    Handles:
      https://doi.org/10.48550/arXiv.2601.08258         -> doi + arxiv_id
      https://doi.org/10.18653/v1/2024.emnlp-main.968   -> doi only
      https://doi.org/10.1007/s11704-024-41099-x         -> doi only
      https://arxiv.org/abs/2403.12345                   -> arxiv_id only
      https://metr.org/blog/...                          -> (None, None)
      bare DOI without URL prefix                        -> doi (+ arxiv_id if arXiv)
    """
    if not paper_link or not isinstance(paper_link, str):
        return None, None

    link = paper_link.strip()
    doi  = None
    arxiv_id = None

    # Case 1: standard https://doi.org/... URL
    doi_match = re.match(r"https?://doi[.]org/(.+)", link, re.IGNORECASE)
    if doi_match:
        doi = doi_match.group(1).rstrip("/")
        ax = re.search(r"[Aa]r[Xx]iv[./](\d{4}[.]\d{4,6})", doi)
        if ax:
            arxiv_id = ax.group(1)
        return doi, arxiv_id

    # Case 2: direct https://arxiv.org/abs/... or .../pdf/... URL
    arxiv_match = re.search(
        r"arxiv[.]org/(?:abs|pdf)/(\d{4}[.]\d{4,6})", link, re.IGNORECASE
    )
    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        return None, arxiv_id

    # Case 3: bare DOI in the cell (no URL wrapper)
    bare_doi = re.match(r"(10[.]\d{4,}/\S+)", link)
    if bare_doi:
        doi = bare_doi.group(1).rstrip("/")
        ax = re.search(r"[Aa]r[Xx]iv[./](\d{4}[.]\d{4,6})", doi)
        if ax:
            arxiv_id = ax.group(1)
        return doi, arxiv_id

    # Anything else (blog post, GitHub, HuggingFace dataset page, etc.)
    return None, None


def _s2_headers() -> Dict:
    # .strip() guards against hidden whitespace that causes blanket 403 rejections
    key = S2_API_KEY.strip() if isinstance(S2_API_KEY, str) and S2_API_KEY.strip() else None
    return {"x-api-key": key} if key else {}


def query_s2_by_id(identifier: str, id_type: str = "doi") -> Optional[Dict]:
    """
    Query Semantic Scholar for a single paper.

    id_type options:
      "doi"   -> query prefixed with DOI:
      "arxiv" -> query prefixed with ARXIV:
      "s2"    -> raw 40-char hex paper ID
    """
    prefix = {"doi": "DOI:", "arxiv": "ARXIV:", "s2": ""}.get(id_type, "DOI:")
    url = f"{S2_BASE}/paper/{prefix}{identifier}"
    try:
        resp = requests.get(
            url,
            headers=_s2_headers(),
            params={"fields": ",".join(S2_FIELDS)},
            timeout=TIMEOUT
        )
        time.sleep(RATE_LIMIT_DELAY)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            logger.debug(f"S2 not found ({id_type}): {identifier}")
        else:
            logger.warning(f"S2 HTTP {resp.status_code} ({id_type}): {identifier}")
    except Exception as exc:
        logger.error(f"S2 query error [{id_type}={identifier}]: {exc}")
    return None


def search_s2_by_title(title: str) -> Optional[Dict]:
    """Strategy 4: Semantic Scholar full-text title search (last resort)."""
    try:
        resp = requests.get(
            f"{S2_BASE}/paper/search",
            headers=_s2_headers(),
            params={"query": title, "fields": ",".join(S2_FIELDS), "limit": 1},
            timeout=TIMEOUT
        )
        time.sleep(RATE_LIMIT_DELAY)
        if resp.status_code == 200:
            hits = resp.json().get("data", [])
            return hits[0] if hits else None
        logger.warning(f"S2 title search HTTP {resp.status_code}: {title[:60]}")
    except Exception as exc:
        logger.error(f"S2 title search error: {exc}")
    return None


def query_crossref(doi: str) -> Optional[Dict]:
    """Query Crossref for publisher-side metadata (polite pool via email)."""
    headers = {"User-Agent": f"AISafetyBenchExplorer/1.0 (mailto:{CONTACT_EMAIL})"}
    try:
        resp = requests.get(
            f"{CROSSREF_BASE}/{doi}", headers=headers, timeout=TIMEOUT
        )
        time.sleep(RATE_LIMIT_DELAY)
        if resp.status_code == 200:
            return resp.json().get("message")
        logger.warning(f"Crossref HTTP {resp.status_code}: {doi}")
    except Exception as exc:
        logger.error(f"Crossref query error [{doi}]: {exc}")
    return None


def crossref_to_s2_shape(cr: Dict) -> Dict:
    """
    Map a Crossref message dict to the same field schema used by S2 responses.
    Fields absent in Crossref are explicitly set to None so the downstream
    serialize() function handles them uniformly.
    """
    titles = cr.get("title") or []
    title = titles[0] if titles else None

    authors = []
    for a in cr.get("author", []):
        given = a.get("given",  "").strip()
        family = a.get("family", "").strip()
        name = f"{given} {family}".strip() if given else family
        if name:
            authors.append({"authorId": None, "name": name})

    pub_date = None
    dp = cr.get("published-print") or cr.get("published-online")
    if dp:
        parts = (dp.get("date-parts") or [[]])[0]
        if len(parts) == 3:
            pub_date = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
        elif len(parts) >= 1:
            pub_date = str(parts[0])

    year = None
    dp2 = cr.get("published-print") or cr.get("published-online")
    if dp2:
        parts2 = (dp2.get("date-parts") or [[]])[0]
        year = parts2[0] if parts2 else None

    container = cr.get("container-title") or []
    venue = container[0] if container else None

    return {
        "paperId":                  None,
        "title":                    title,
        "year":                     year,
        "venue":                    venue,
        "publicationVenue":         None,
        "authors":                  authors,
        "externalIds":              {"DOI": cr.get("DOI")},
        "url":                      cr.get("URL"),
        "citationCount":            cr.get("is-referenced-by-count", 0),
        "referenceCount":           cr.get("references-count", 0),
        "influentialCitationCount": None,
        "isOpenAccess":             None,
        "openAccessPdf":            None,
        "fieldsOfStudy":            None,
        "s2FieldsOfStudy":          None,
        "publicationDate":          pub_date,
        "journal":                  {"name": venue} if venue else None,
    }

def serialize(value: Any) -> str:
    """Convert any S2 / Crossref field value to a flat, Excel-safe string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        if all(isinstance(v, dict) and "name" in v for v in value):
            return "; ".join(v["name"] for v in value if v.get("name"))
        if all(isinstance(v, str) for v in value):
            return "; ".join(value)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def flatten_record(data: Dict) -> Dict:
    """
    Produce one output-row dict from a raw S2 or Crossref-mapped record.

    Two fields are intentionally simplified instead of emitting full JSON:
      publicationVenue  ->  venue name only  (e.g. "NeurIPS", "arXiv.org")
      openAccessPdf     ->  OA status only   (e.g. "BRONZE" | "GREEN" | "CLOSED" | "")
    All other fields use the generic serialize() function.
    """
    row = {}
    for field in S2_FIELDS:
        raw = data.get(field)

        if field == "publicationVenue":
            row[field] = (raw.get("name") or "") if isinstance(raw, dict) else serialize(raw)

        elif field == "openAccessPdf":
            row[field] = (raw.get("status") or "") if isinstance(raw, dict) else serialize(raw)

        else:
            row[field] = serialize(raw)

    return row


def enrich_benchmarks(input_path: str = EXCEL_INPUT_PATH, sheet_name: str = SHEET_NAME, output_path: str = OUTPUT_PATH) -> pd.DataFrame:
    """
    Full enrichment pipeline.

    1. Reads SHEET_NAME from input_path (must be xlsx).
    2. For every row, extracts DOI / arXiv ID from the Paper Link cell.
    3. Resolves metadata through a 4-strategy lookup chain.
    4. Writes output_path with columns:
         Benchmark Name | Paper Link | Lookup Source | <S2_FIELDS>
    Returns the output DataFrame.
    """
    logger.info("=" * 65)
    logger.info(f"Input: {input_path}")
    logger.info(f"Sheet: {sheet_name}")
    logger.info(f"Output: {output_path}")
    logger.info("=" * 65)

    df = pd.read_excel(input_path, sheet_name=sheet_name)
    df.columns = [str(c).strip() for c in df.columns]

    for required_col in ("Benchmark Name", "Paper Link"):
        if required_col not in df.columns:
            raise ValueError(
                f"Column not found: '{required_col}'. "
                f"Available columns: {list(df.columns)}"
            )

    has_title_col = "Benchmark Paper Title" in df.columns
    total = len(df)
    results = []

    for idx, row in df.iterrows():
        bench_name = str(row["Benchmark Name"]).strip()
        paper_link = str(row.get("Paper Link", "")).strip()
        paper_title = (str(row.get("Benchmark Paper Title", "")).strip() if has_title_col else "")

        logger.info(f"[{idx + 1:3d}/{total}] {bench_name}")

        doi, arxiv_id = extract_doi_and_arxiv(paper_link)
        data = None
        source = "none"

        # Strategy 1: Semantic Scholar via arXiv ID
        if arxiv_id and data is None:
            logger.debug(f"S1  S2/arXiv  {arxiv_id}")
            data = query_s2_by_id(arxiv_id, "arxiv")
            if data:
                source = "S2/arXiv"

        # Strategy 2: Semantic Scholar via full DOI
        if doi and data is None:
            logger.debug(f"S2  S2/DOI    {doi}")
            data = query_s2_by_id(doi, "doi")
            if data:
                source = "S2/DOI"

        # Strategy 3: Crossref via full DOI
        if doi and data is None:
            logger.debug(f"S3  Crossref  {doi}")
            cr = query_crossref(doi)
            if cr:
                data = crossref_to_s2_shape(cr)
                source = "Crossref"

        # Strategy 4: Semantic Scholar title search
        if data is None and paper_title:
            logger.debug(f"S4  S2/title  {paper_title[:60]}")
            data = search_s2_by_title(paper_title)
            if data:
                source = "S2/title"

        if data is None:
            logger.warning(f"No metadata found: {bench_name} | {paper_link}")
            flat = {f: "" for f in S2_FIELDS}
        else:
            flat = flatten_record(data)
            logger.info(f"[{source}] {flat.get('title', '')[:70]}")

        result_row = {
            "Benchmark Name": bench_name,
            "Paper Link":     paper_link,
            "Lookup Source":  source,
        }
        result_row.update(flat)
        results.append(result_row)

    col_order = ["Benchmark Name", "Paper Link", "Lookup Source"] + S2_FIELDS
    out_df = pd.DataFrame(results)[col_order]

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        out_df.to_excel(writer, sheet_name=OUTPUT_SHEET_NAME, index=False)
        ws = writer.sheets[OUTPUT_SHEET_NAME]
        for col_cells in ws.columns:
            max_len = max(
                (len(str(cell.value or "")) for cell in col_cells), default=10
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(
                max_len + 2, 80
            )

    logger.info("=" * 65)
    logger.info(f"Done. {len(results)} benchmarks written to {output_path}")
    logger.info("=" * 65)
    return out_df


if __name__ == "__main__":
    enrich_benchmarks()
