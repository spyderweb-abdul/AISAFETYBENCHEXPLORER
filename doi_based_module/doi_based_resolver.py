"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors

DOI-Based Paper Metadata Resolver
=================================

Multi-API strategy for comprehensive metadata extraction:
1. Semantic Scholar (primary) - citations, authors, venues, OA status
2. arXiv API - preprints, LaTeX source access
3. Unpaywall - OA status and full-text PDFs
4. Crossref - DOI resolution, publisher metadata

Usage:
    resolver = DOIMetadataResolver(email="your@email.com")
    metadata = await resolver.resolve("10.1234/example.doi")
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import time
import re

from models import (SemanticScholarPaper, ArXivPaperMetadata, UnpaywallResponse, CrossrefResponse,  AggregatedPaperMetadata)

logger = logging.getLogger(__name__)


class DOIMetadataResolver:
    """
    Resolves DOI to comprehensive paper metadata using multiple APIs.
    """

    def __init__(self, email: str, s2_api_key: Optional[str] = None, rate_limit_delay: float = 1.0, timeout: int = 30):
        """
        Initialize resolver with API credentials.

        Args:
            email: Required for Unpaywall API (polite usage)
            s2_api_key: Optional Semantic Scholar API key (higher rate limits)
            rate_limit_delay: Seconds to wait between API calls
            timeout: Request timeout in seconds
        """
        self.email = email
        self.s2_api_key = s2_api_key
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout

        # API base URLs
        self.s2_base = "https://api.semanticscholar.org/graph/v1"
        self.unpaywall_base = "https://api.unpaywall.org/v2"
        self.crossref_base = "https://api.crossref.org/works"

        # Headers
        self.s2_headers = {}
        if s2_api_key:
            self.s2_headers["x-api-key"] = s2_api_key

        logger.info("DOI resolver initialized")
        logger.info(f"Email: {email}")
        logger.info(f"S2 API key: {'Yes' if s2_api_key else 'No'}")

    def resolve(self, identifier: str, prefer_full_text: bool = True) -> AggregatedPaperMetadata:
        """
        Resolve paper identifier to aggregated metadata.

        Args:
            identifier: DOI, arXiv ID, or Semantic Scholar ID
            prefer_full_text: If True, prioritize finding full-text access

        Returns:
            AggregatedPaperMetadata with data from all available APIs
        """
        logger.info(f"Resolving identifier: {identifier}")

        # Normalize identifier
        id_type, normalized_id = self._normalize_identifier(identifier)
        logger.info(f"Detected type: {id_type}")
        logger.info(f"Normalized: {normalized_id}")

        # Start with empty metadata
        aggregated = AggregatedPaperMetadata(title="", api_query_timestamp=datetime.now())

        # Strategy 1: Query Semantic Scholar (best single source)
        s2_data = self._query_semantic_scholar(normalized_id, id_type)
        if s2_data:
            self._merge_semantic_scholar(aggregated, s2_data)
            logger.info(f"Semantic Scholar: {aggregated.title[:50]}...")
        else:
            logger.warning("Semantic Scholar: No data")

        # Strategy 2: If arXiv paper, get arXiv metadata
        if aggregated.arxiv_id or id_type == "arxiv":
            arxiv_id = aggregated.arxiv_id or normalized_id
            arxiv_data = self._query_arxiv(arxiv_id)
            if arxiv_data:
                self._merge_arxiv(aggregated, arxiv_data)
                logger.info(f"arXiv: {arxiv_id}")

        # Strategy 3: If DOI available, query Unpaywall for OA
        if aggregated.doi or id_type == "doi":
            doi = aggregated.doi or normalized_id
            unpaywall_data = self._query_unpaywall(doi)
            if unpaywall_data:
                self._merge_unpaywall(aggregated, unpaywall_data)
                logger.info(f"Unpaywall: OA={aggregated.is_open_access}")

        # Strategy 4: Fallback to Crossref if needed
        if not aggregated.title or (not aggregated.abstract and id_type == "doi"):
            crossref_data = self._query_crossref(aggregated.doi or normalized_id)
            if crossref_data:
                self._merge_crossref(aggregated, crossref_data)
                logger.info("Crossref: Supplemented metadata")

        # Compute completeness score
        aggregated.metadata_completeness_score = self._compute_completeness(aggregated)

        logger.info(f"Resolved paper: {aggregated.title}")
        logger.info(f"Authors: {len(aggregated.authors)}")
        logger.info(f"Citations: {aggregated.citation_count}")
        logger.info(f"OA: {aggregated.is_open_access}")
        logger.info(f"Completeness: {aggregated.metadata_completeness_score:.2f}")

        return aggregated

    def _normalize_identifier(self, identifier: str) -> tuple[str, str]:
        """Detect and normalize identifier type."""

        identifier = identifier.strip()

        # DOI pattern
        doi_match = re.search(r'10\.\d{4,}/[^\s]+', identifier)
        if doi_match:
            return ("doi", doi_match.group(0))

        # arXiv patterns
        # ormat: YYMM.NNNNN or YYMM.NNNNNN
        arxiv_new = re.search(r'(\d{4}\.\d{4,5})', identifier)
        if arxiv_new:
            return ("arxiv", arxiv_new.group(1))

        # format: arch-ive/YYMMNNN
        arxiv_old = re.search(r'([a-z\-]+/\d{7})', identifier, re.IGNORECASE)
        if arxiv_old:
            return ("arxiv", arxiv_old.group(1))

        # Semantic Scholar ID (40-char hex)
        if re.match(r'^[a-f0-9]{40}$', identifier, re.IGNORECASE):
            return ("s2", identifier)

        # Default: treat as DOI
        return ("doi", identifier)

    def _query_semantic_scholar(self, identifier: str, id_type: str) -> Optional[SemanticScholarPaper]:
        """Query Semantic Scholar API."""

        try:
            # Build query based on identifier type
            if id_type == "doi":
                query_id = f"DOI:{identifier}"
            elif id_type == "arxiv":
                query_id = f"ARXIV:{identifier}"
            elif id_type == "s2":
                query_id = identifier
            else:
                query_id = identifier

            # Fields to request
            fields = [
                "paperId", "title", "abstract", "year", "venue",
                "publicationVenue", "authors", "externalIds", "url",
                "citationCount", "referenceCount", "influentialCitationCount",
                "isOpenAccess", "openAccessPdf", "fieldsOfStudy",
                "s2FieldsOfStudy", "publicationDate", "journal"
            ]

            url = f"{self.s2_base}/paper/{query_id}"
            params = {"fields": ",".join(fields)}

            response = requests.get(
                url,
                headers=self.s2_headers,
                params=params,
                timeout=self.timeout
            )

            time.sleep(self.rate_limit_delay)

            if response.status_code == 200:
                data = response.json()
                return SemanticScholarPaper(**data)
            elif response.status_code == 404:
                logger.warning(f"S2: Paper not found for {identifier}")
                return None
            else:
                logger.error(f"S2 API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"S2 query failed: {e}")
            return None

    def _query_arxiv(self, arxiv_id: str) -> Optional[ArXivPaperMetadata]:
        """Query arXiv API using arxiv Python library."""

        try:
            import arxiv

            search = arxiv.Search(id_list=[arxiv_id])
            result = next(search.results())

            return ArXivPaperMetadata(
                arxiv_id=arxiv_id,
                title=result.title,
                abstract=result.summary,
                authors=[author.name for author in result.authors],
                published=result.published,
                updated=result.updated,
                primary_category=result.primary_category,
                categories=result.categories,
                doi=result.doi,
                journal_ref=result.journal_ref,
                pdf_url=result.pdf_url,
                arxiv_url=result.entry_id,
                comment=result.comment
            )

        except ImportError:
            logger.warning("arxiv package not installed (pip install arxiv)")
            return self._query_arxiv_rest(arxiv_id)
        except Exception as e:
            logger.error(f"arXiv query failed: {e}")
            return None

    def _query_arxiv_rest(self, arxiv_id: str) -> Optional[ArXivPaperMetadata]:
        """Fallback: Query arXiv via REST API."""

        try:
            import feedparser

            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url, timeout=self.timeout)

            time.sleep(self.rate_limit_delay)

            if response.status_code != 200:
                return None

            feed = feedparser.parse(response.content)

            if not feed.entries:
                return None

            entry = feed.entries[0]

            return ArXivPaperMetadata(
                arxiv_id=arxiv_id,
                title=entry.title,
                abstract=entry.summary,
                authors=[author.name for author in entry.authors],
                published=datetime.strptime(entry.published, "%Y-%m-%dT%H:%M:%SZ"),
                primary_category=entry.arxiv_primary_category.get('term', ''),
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                arxiv_url=f"https://arxiv.org/abs/{arxiv_id}"
            )

        except Exception as e:
            logger.error(f"arXiv REST query failed: {e}")
            return None

    def _query_unpaywall(self, doi: str) -> Optional[UnpaywallResponse]:
        """Query Unpaywall API for OA status."""

        try:
            url = f"{self.unpaywall_base}/{doi}"
            params = {"email": self.email}

            response = requests.get(url, params=params, timeout=self.timeout)

            time.sleep(self.rate_limit_delay)

            if response.status_code == 200:
                data = response.json()
                return UnpaywallResponse(**data)
            elif response.status_code == 404:
                logger.warning(f"Unpaywall: DOI not found {doi}")
                return None
            else:
                logger.error(f"Unpaywall API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Unpaywall query failed: {e}")
            return None

    def _query_crossref(self, doi: str) -> Optional[CrossrefResponse]:
        """Query Crossref API."""

        try:
            url = f"{self.crossref_base}/{doi}"
            headers = {"User-Agent": f"DOIResolver/1.0 (mailto:{self.email})"}

            response = requests.get(url, headers=headers, timeout=self.timeout)

            time.sleep(self.rate_limit_delay)

            if response.status_code == 200:
                data = response.json()["message"]
                return CrossrefResponse(**data)
            else:
                logger.warning(f"Crossref: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Crossref query failed: {e}")
            return None

    def _merge_semantic_scholar(self, aggregated: AggregatedPaperMetadata, s2_data: SemanticScholarPaper):
        """Merge Semantic Scholar data into aggregated metadata."""

        aggregated.s2_paper_id = s2_data.paperId
        aggregated.title = s2_data.title
        aggregated.abstract = s2_data.abstract
        aggregated.year = s2_data.year
        aggregated.venue = s2_data.venue
        aggregated.s2_url = s2_data.url

        # Authors
        aggregated.authors = [author.name for author in s2_data.authors]

        # External IDs
        if s2_data.externalIds:
            aggregated.doi = s2_data.externalIds.DOI
            aggregated.arxiv_id = s2_data.externalIds.ArXiv
            aggregated.corpus_id = s2_data.externalIds.CorpusId

        # Citations
        aggregated.citation_count = s2_data.citationCount
        aggregated.reference_count = s2_data.referenceCount
        aggregated.influential_citation_count = s2_data.influentialCitationCount

        # Open Access
        aggregated.is_open_access = s2_data.isOpenAccess

        # Handle openAccessPdf as Pydantic model, not dict
        if s2_data.openAccessPdf:
            aggregated.pdf_url = s2_data.openAccessPdf.url
            # Store status and license if available
            if hasattr(s2_data.openAccessPdf, 'status'):
                aggregated.oa_status = s2_data.openAccessPdf.status
            if hasattr(s2_data.openAccessPdf, 'license'):
                aggregated.license = s2_data.openAccessPdf.license

        # Fields of study
        if s2_data.fieldsOfStudy:
            aggregated.fields_of_study = s2_data.fieldsOfStudy

        # Venue details
        if s2_data.publicationVenue:
            aggregated.venue_type = s2_data.publicationVenue.type
            aggregated.publisher = s2_data.publicationVenue.name

        # Dates
        aggregated.publication_date = s2_data.publicationDate

        # URLs
        if aggregated.doi:
            aggregated.doi_url = f"https://doi.org/{aggregated.doi}"
        if aggregated.arxiv_id:
            aggregated.arxiv_url = f"https://arxiv.org/abs/{aggregated.arxiv_id}"

        aggregated.paper_url = s2_data.url or aggregated.doi_url
        aggregated.has_abstract = bool(aggregated.abstract)

        aggregated.data_sources.append("semantic_scholar")

    def _merge_arxiv(self, aggregated: AggregatedPaperMetadata, arxiv_data: ArXivPaperMetadata):
        """Merge arXiv data into aggregated metadata."""

        # Only override if not already set
        if not aggregated.title:
            aggregated.title = arxiv_data.title

        if not aggregated.abstract:
            aggregated.abstract = arxiv_data.abstract

        if not aggregated.authors:
            aggregated.authors = arxiv_data.authors

        # arXiv-specific fields
        aggregated.arxiv_id = arxiv_data.arxiv_id
        aggregated.arxiv_url = arxiv_data.arxiv_url
        aggregated.primary_category = arxiv_data.primary_category

        if arxiv_data.categories:
            aggregated.fields_of_study.extend(arxiv_data.categories)

        # PDF access
        if arxiv_data.pdf_url:
            aggregated.pdf_url = arxiv_data.pdf_url
            aggregated.is_open_access = True
            aggregated.oa_status = "green"  # arXiv is preprint repository
            aggregated.has_full_text_access = True

        # Dates
        if arxiv_data.published:
            aggregated.publication_date = arxiv_data.published.isoformat()

        aggregated.data_sources.append("arxiv")

    def _merge_unpaywall(self, aggregated: AggregatedPaperMetadata, unpaywall_data: UnpaywallResponse):
        """Merge Unpaywall data into aggregated metadata."""

        aggregated.is_open_access = unpaywall_data.is_oa
        aggregated.oa_status = unpaywall_data.oa_status

        if unpaywall_data.best_oa_location:
            loc = unpaywall_data.best_oa_location
            aggregated.oa_pdf_url = loc.url_for_pdf
            aggregated.license = loc.license

            if loc.url_for_pdf:
                aggregated.pdf_url = loc.url_for_pdf
                aggregated.has_full_text_access = True

        if not aggregated.publisher:
            aggregated.publisher = unpaywall_data.publisher

        if not aggregated.journal and unpaywall_data.journal_name:
            aggregated.journal = unpaywall_data.journal_name

        aggregated.data_sources.append("unpaywall")

    def _merge_crossref(self, aggregated: AggregatedPaperMetadata, crossref_data: CrossrefResponse):
        """Merge Crossref data into aggregated metadata."""

        # Only fill missing fields
        if not aggregated.title and crossref_data.title:
            aggregated.title = crossref_data.title[0]

        if not aggregated.abstract:
            aggregated.abstract = crossref_data.abstract

        if not aggregated.authors and crossref_data.author:
            aggregated.authors = [
                f"{a.family}, {a.given}" if a.given else a.family
                for a in crossref_data.author
                if a.family
            ]

        if not aggregated.publisher:
            aggregated.publisher = crossref_data.publisher

        if not aggregated.venue and crossref_data.container_title:
            aggregated.venue = crossref_data.container_title[0]

        # Citation count (if S2 didn't provide)
        if aggregated.citation_count == 0:
            aggregated.citation_count = crossref_data.is_referenced_by_count or 0

        if aggregated.reference_count == 0:
            aggregated.reference_count = crossref_data.reference_count or 0

        aggregated.data_sources.append("crossref")

    def _compute_completeness(self, metadata: AggregatedPaperMetadata) -> float:
        """Compute metadata completeness score (0-1)."""

        score = 0.0
        weights = {
            "title": 0.15,
            "authors": 0.10,
            "abstract": 0.15,
            "year": 0.05,
            "venue": 0.05,
            "doi": 0.10,
            "citations": 0.05,
            "pdf_access": 0.20,
            "arxiv": 0.05,
            "github": 0.10
        }

        if metadata.title:
            score += weights["title"]
        if metadata.authors:
            score += weights["authors"]
        if metadata.abstract and len(metadata.abstract) > 100:
            score += weights["abstract"]
        if metadata.year:
            score += weights["year"]
        if metadata.venue:
            score += weights["venue"]
        if metadata.doi:
            score += weights["doi"]
        if metadata.citation_count > 0:
            score += weights["citations"]
        if metadata.has_full_text_access:
            score += weights["pdf_access"]
        if metadata.arxiv_id:
            score += weights["arxiv"]
        if metadata.github_url:
            score += weights["github"]

        return round(score, 2)