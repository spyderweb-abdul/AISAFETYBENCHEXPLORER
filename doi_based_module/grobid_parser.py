"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors

GROBID-Based Structured Metadata Extractor
===========================================

Integrates GROBID (GeneRation Of BIbliographic Data) for high-accuracy
extraction of bibliographic metadata from academic PDFs.

GROBID achieves ~90% F1-score on title/author/abstract extraction.

Installation:
- Docker: docker pull lfoppiano/grobid:0.8.0
- Run: docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0

Or use public API: https://cloud.science-miner.com/grobid/
"""

import requests
from typing import Dict, Optional, List
import xml.etree.ElementTree as ET
import logging
import time

logger = logging.getLogger(__name__)

class GROBIDParser:
    """
    GROBID-based structured metadata extractor for academic papers.
    Extracts title, authors, abstract, references with high accuracy.
    """

    def __init__(self, grobid_url: str = "http://localhost:8070", timeout: int = 120):
        """
        Initialize GROBID parser.

        Args:
            grobid_url: GROBID service URL (default: localhost:8070)
            timeout: Request timeout in seconds
        """
        self.grobid_url = grobid_url.rstrip('/')
        self.timeout = timeout
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if GROBID service is available"""
        try:
            response = requests.get(
                f"{self.grobid_url}/api/isalive",
                timeout=5
            )
            if response.status_code == 200:
                logger.info("GROBID service available")
                return True
            else:
                logger.warning("GROBID service not responding properly")
                return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"GROBID not available: {e}")
            logger.info("Install: docker run -p 8070:8070 lfoppiano/grobid:0.8.0")
            return False

    def extract_metadata(self, pdf_path: str) -> Optional[Dict]:
        """
        Extract structured metadata from PDF using GROBID.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with title, authors, abstract, keywords, references
        """
        if not self.available:
            logger.debug("GROBID not available, skipping")
            return None

        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                headers = {"Accept": "application/xml"}  # force TEI XML [page:1][page:0]

                response = requests.post(
                    f"{self.grobid_url}/api/processHeaderDocument",
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    text = response.text or ""
                    # Guard: if GROBID returns BibTeX/plaintext/HTML, don't try to parse as XML.
                    if not text.lstrip().startswith("<"):
                        content_type = response.headers.get("Content-Type", "")
                        preview = text[:200].replace("\n", "\\n").replace("\r", "\\r")
                        logger.error(
                            "GROBID did not return XML; cannot parse. "
                            f"Content-Type={content_type!r}, body_preview={preview!r}"
                        )
                        return None

                    metadata = self._parse_tei_xml(text)
                    logger.info(f"GROBID: Extracted {len(metadata.get('authors', []))} authors")
                    return metadata
                else:
                    logger.warning(f"GROBID extraction failed: HTTP {response.status_code}")
                    return None

        except requests.exceptions.Timeout:
            logger.error(f"GROBID timeout after {self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"GROBID error: {e}")
            return None


    def extract_full_text(self, pdf_path: str) -> Optional[str]:
        """
        Extract full text using GROBID's processFulltextDocument.
        More comprehensive than header extraction.
        """
        if not self.available:
            return None

        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                headers = {"Accept": "application/xml"}  # force TEI XML

                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    text = response.text or ""
                    if not text.lstrip().startswith("<"):
                        content_type = response.headers.get("Content-Type", "")
                        preview = text[:200].replace("\n", "\\n").replace("\r", "\\r")
                        logger.error(
                            "GROBID did not return XML full text; cannot use. "
                            f"Content-Type={content_type!r}, body_preview={preview!r}"
                        )
                        return None

                    return text, "TEI-XML"  # Returns TEI-XML
                else:
                    return None

        except Exception as e:
            logger.error(f"GROBID full-text extraction error: {e}")
            return None


    def _parse_tei_xml(self, tei_xml: str) -> Dict:
        """Parse GROBID TEI-XML output"""
        try:
            root = ET.fromstring(tei_xml)
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return self._empty_metadata()

        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

        metadata = {
            'title': '',
            'authors': [],
            'abstract': '',
            'keywords': [],
            'affiliations': [],
            'year': None,
            'doi': '',
            'journal': ''
        }

        # Extract title
        title_elem = root.find('.//tei:titleStmt/tei:title[@type="main"]', ns)
        if title_elem is not None:
            metadata['title'] = ''.join(title_elem.itertext()).strip()

        # Extract authors with affiliations
        for author in root.findall('.//tei:sourceDesc//tei:author', ns):
            author_info = self._extract_author_info(author, ns)
            if author_info['name']:
                metadata['authors'].append(author_info['name'])
                if author_info['affiliation']:
                    metadata['affiliations'].append(author_info['affiliation'])

        # Extract abstract
        abstract_elem = root.find('.//tei:profileDesc//tei:abstract', ns)
        if abstract_elem is not None:
            abstract_text = ''.join(abstract_elem.itertext()).strip()
            # Remove "Abstract" header if present
            abstract_text = abstract_text.replace('Abstract', '').strip()
            metadata['abstract'] = abstract_text

        # Extract keywords
        for keyword in root.findall('.//tei:profileDesc//tei:keywords//tei:term', ns):
            if keyword.text:
                metadata['keywords'].append(keyword.text.strip())

        # Extract publication year
        date_elem = root.find('.//tei:sourceDesc//tei:date[@type="published"]', ns)
        if date_elem is not None and date_elem.get('when'):
            try:
                metadata['year'] = int(date_elem.get('when')[:4])
            except (ValueError, TypeError):
                pass

        # Extract DOI
        idno_elem = root.find('.//tei:sourceDesc//tei:idno[@type="DOI"]', ns)
        if idno_elem is not None and idno_elem.text:
            metadata['doi'] = idno_elem.text.strip()

        # Extract journal/venue
        journal_elem = root.find('.//tei:sourceDesc//tei:title[@level="j"]', ns)
        if journal_elem is not None:
            metadata['journal'] = ''.join(journal_elem.itertext()).strip()

        return metadata

    def _extract_author_info(self, author_elem, ns) -> Dict:
        """Extract author name and affiliation from XML element"""
        info = {'name': '', 'affiliation': ''}

        persName = author_elem.find('.//tei:persName', ns)
        if persName is not None:
            forename = persName.find('.//tei:forename[@type="first"]', ns)
            surname = persName.find('.//tei:surname', ns)

            name_parts = []
            if forename is not None and forename.text:
                name_parts.append(forename.text.strip())
            if surname is not None and surname.text:
                name_parts.append(surname.text.strip())

            info['name'] = ' '.join(name_parts)

        # Extract affiliation
        affiliation_elem = author_elem.find('.//tei:affiliation', ns)
        if affiliation_elem is not None:
            org_name = affiliation_elem.find('.//tei:orgName', ns)
            if org_name is not None and org_name.text:
                info['affiliation'] = org_name.text.strip()

        return info

    def _empty_metadata(self) -> Dict:
        """Return empty metadata structure"""
        return {
            'title': '',
            'authors': [],
            'abstract': '',
            'keywords': [],
            'affiliations': [],
            'year': None,
            'doi': '',
            'journal': ''
        }


# Convenience function
def extract_with_grobid(pdf_path: str, grobid_url: str = "http://localhost:8070") -> Optional[Dict]:
    """
    Convenience function to extract metadata using GROBID.

    Usage:
        metadata = extract_with_grobid("paper.pdf")
        if metadata:
            print(f"Title: {metadata['title']}")
            print(f"Authors: {', '.join(metadata['authors'])}")
    """
    parser = GROBIDParser(grobid_url=grobid_url)
    return parser.extract_metadata(pdf_path)