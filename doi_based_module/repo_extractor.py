"""
Enhanced Repository URL Extractor with Papers With Code Integration
====================================================================

Multi-strategy extraction of GitHub, HuggingFace, and Kaggle URLs from papers.

NEW in this version:
- Papers With Code API integration for GitHub repo discovery
- Improved URL validation and scoring
- Better benchmark name matching
- Enhanced Kaggle dataset support

Strategies:
1. Direct URL pattern matching (regex-based)
2. Section-specific extraction (abstract, methodology, references)
3. Papers With Code API (50,000+ papers with code)
4. URL validation and benchmark name matching
"""

import re
import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class RepositoryURLs:
    """Container for extracted repository URLs"""
    github_url: str = ""
    huggingface_url: str = ""
    kaggle_url: str = ""
    dataset_url: str = ""
    demo_url: str = ""
    confidence: float = 0.0
    extraction_method: str = ""

class EnhancedRepositoryExtractor:
    """
    Advanced repository URL extractor with multiple fallback strategies.

    NOW SUPPORTS: GitHub, HuggingFace, Kaggle, Papers With Code API
    """

    def __init__(self, pwc_api_timeout: int = 10):
        """
        Initialize extractor with regex patterns.

        Args:
            pwc_api_timeout: Papers With Code API timeout in seconds
        """
        self.pwc_api_timeout = pwc_api_timeout
        self.pwc_base_url = "https://paperswithcode.com/api/v1"

        # GitHub URL patterns
        self.github_patterns = [
            r'https?://(?:www\.)?github\.com/[\w\-]+/[\w\-\.]+',
            r'\[.*?\]\((https?://github\.com/[\w\-]+/[\w\-\.]+)\)',
            r'\\url\{(https?://github\.com/[\w\-]+/[\w\-\.]+)\}',
            r'github:?([\w\-]+/[\w\-\.]+)',
        ]

        # HuggingFace URL patterns
        self.hf_patterns = [
            r'https?://(?:www\.)?huggingface\.co/datasets/[\w\-]+/[\w\-\.]+',
            r'\[.*?\]\((https?://huggingface\.co/datasets/[\w\-]+/[\w\-\.]+)\)',
            r'\\url\{(https?://huggingface\.co/datasets/[\w\-]+/[\w\-\.]+)\}',
            r'huggingface:?([\w\-]+/[\w\-\.]+)',
        ]

        # Kaggle dataset URL patterns
        self.kaggle_patterns = [
            r'https?://(?:www\.)?kaggle\.com/datasets/[\w\-]+/[\w\-\.]+',
            r'\[.*?\]\((https?://kaggle\.com/datasets/[\w\-]+/[\w\-\.]+)\)',
            r'\\url\{(https?://kaggle\.com/datasets/[\w\-]+/[\w\-\.]+)\}',
            r'kaggle:?([\w\-]+/[\w\-\.]+)',
            r'https?://(?:www\.)?kaggle\.com/[\w\-]+/[\w\-]+/data',
        ]

        # Demo/project page patterns
        self.demo_patterns = [
            r'https?://[\w\-]+\.github\.io/[\w\-/]*',
            r'https?://(?:www\.)?[\w\-]+\.(com|org|ai)/[\w\-/]*demo',
            r'https?://(?:www\.)?[\w\-]+\.(com|org|ai)/projects?/[\w\-/]+',
        ]

    def extract_all_repositories(
        self,
        full_text: str,
        benchmark_name: str,
        sections: Dict[str, str],
        arxiv_id: Optional[str] = None,
        paper_title: Optional[str] = None,
        api_metadata: Optional[object] = None
    ) -> RepositoryURLs:
        """
        Extract all repository URLs using multi-strategy approach.

        Args:
            full_text: Complete paper text
            benchmark_name: Extracted benchmark name
            sections: Chunked paper sections
            arxiv_id: ArXiv ID (if available)
            paper_title: Paper title (if available)
            api_metadata: Optional API metadata

        Returns:
            RepositoryURLs object with extracted URLs and confidence
        """
        logger.info("Starting multi-strategy repository URL extraction...")

        # Strategy 1: Direct pattern matching from full text
        result = self._strategy_1_pattern_matching(full_text)
        if self._is_complete(result):
            logger.info("Strategy 1 (Pattern Matching) found complete URLs")
            return result

        # Strategy 2: Section-specific extraction
        section_result = self._strategy_2_section_extraction(sections)
        result = self._merge_results(result, section_result)
        if self._is_complete(result):
            logger.info("Strategy 2 (Section Extraction) found complete URLs")
            return result

        # Strategy 3: Papers With Code API (NEW!)
        if arxiv_id or paper_title:
            pwc_result = self._strategy_3_papers_with_code(
                arxiv_id=arxiv_id,
                paper_title=paper_title
            )
            result = self._merge_results(result, pwc_result)
            if result.github_url:
                logger.info("Strategy 3 (Papers With Code) found GitHub repo")

        # Strategy 4: API metadata enrichment
        if api_metadata:
            api_result = self._strategy_4_api_enrichment(api_metadata)
            result = self._merge_results(result, api_result)

        # Validate URLs match benchmark name
        result = self._validate_urls(result, benchmark_name)

        # Compute final confidence
        result.confidence = self._compute_confidence(result)

        logger.info(
            f"Extraction complete: GitHub={'' if result.github_url else ''}, "
            f"HF={'' if result.huggingface_url else ''}, "
            f"Kaggle={'' if result.kaggle_url else ''} "
            f"(confidence: {result.confidence:.2f})"
        )

        return result

    def _is_complete(self, result: RepositoryURLs) -> bool:
        """Check if we have both code and dataset repositories"""
        has_code = bool(result.github_url)
        has_dataset = bool(result.huggingface_url or result.kaggle_url)
        return has_code and has_dataset

    def _strategy_1_pattern_matching(self, text: str) -> RepositoryURLs:
        """Strategy 1: Direct regex pattern matching"""
        result = RepositoryURLs(extraction_method="pattern_matching")

        if not text:
            return result

        # Extract GitHub URLs
        github_urls = []
        for pattern in self.github_patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                github_urls.extend(matches)
            except re.error as e:
                logger.warning(f"Regex error: {e}")
                continue

        github_urls = list(set([self._normalize_github_url(url) for url in github_urls if url]))
        if github_urls:
            result.github_url = self._select_best_url(github_urls, text, "github")

        # Extract HuggingFace URLs
        hf_urls = []
        for pattern in self.hf_patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                hf_urls.extend(matches)
            except re.error:
                continue

        hf_urls = list(set([self._normalize_hf_url(url) for url in hf_urls if url]))
        if hf_urls:
            result.huggingface_url = self._select_best_url(hf_urls, text, "huggingface")

        # Extract Kaggle URLs
        kaggle_urls = []
        for pattern in self.kaggle_patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                kaggle_urls.extend(matches)
            except re.error:
                continue

        kaggle_urls = list(set([self._normalize_kaggle_url(url) for url in kaggle_urls if url]))
        if kaggle_urls:
            result.kaggle_url = self._select_best_url(kaggle_urls, text, "kaggle")

        # Extract demo URLs
        demo_urls = []
        for pattern in self.demo_patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                demo_urls.extend(matches)
            except re.error:
                continue

        if demo_urls:
            result.demo_url = demo_urls[0]

        return result

    def _strategy_2_section_extraction(self, sections: Dict[str, str]) -> RepositoryURLs:
        """Strategy 2: Extract from specific paper sections"""
        result = RepositoryURLs(extraction_method="section_extraction")

        if not sections:
            return result

        # Priority sections for repository URLs
        priority_sections = [
            sections.get('abstract', ''),
            sections.get('title_and_abstract', ''),
            sections.get('methodology', '')[:2000],
            sections.get('experiments', '')[:1000],
            sections.get('references', '')[:3000],
        ]

        combined_text = '\n\n'.join(priority_sections)
        return self._strategy_1_pattern_matching(combined_text)

    def _strategy_3_papers_with_code(
        self,
        arxiv_id: Optional[str] = None,
        paper_title: Optional[str] = None
    ) -> RepositoryURLs:
        """
        NEW: Strategy 3 - Query Papers With Code API for GitHub repositories.

        Papers With Code indexes 50,000+ papers with associated code repos.
        """
        result = RepositoryURLs(extraction_method="papers_with_code")

        # Try arXiv ID first (most reliable)
        if arxiv_id:
            try:
                # Clean arXiv ID
                arxiv_clean = arxiv_id.replace('arXiv:', '').strip()

                url = f"{self.pwc_base_url}/papers/?arxiv_id={arxiv_clean}"
                response = requests.get(url, timeout=self.pwc_api_timeout)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('results') and len(data['results']) > 0:
                        paper_data = data['results'][0]

                        # Get official code repository
                        if 'url_official' in paper_data and paper_data['url_official']:
                            repo_url = paper_data['url_official']
                            if 'github.com' in repo_url:
                                result.github_url = self._normalize_github_url(repo_url)
                                logger.info(f" Papers With Code (arXiv): {result.github_url}")
                                return result

                        # Fallback: check implementations
                        paper_id = paper_data.get('id')
                        if paper_id:
                            impl_url = f"{self.pwc_base_url}/papers/{paper_id}/repositories/"
                            impl_response = requests.get(impl_url, timeout=self.pwc_api_timeout)
                            if impl_response.status_code == 200:
                                impl_data = impl_response.json()
                                if impl_data.get('results'):
                                    # Get first GitHub repo
                                    for impl in impl_data['results']:
                                        repo_url = impl.get('url', '')
                                        if 'github.com' in repo_url:
                                            result.github_url = self._normalize_github_url(repo_url)
                                            logger.info(f" Papers With Code (impl): {result.github_url}")
                                            return result

            except requests.exceptions.RequestException as e:
                logger.debug(f"Papers With Code API error: {e}")
            except Exception as e:
                logger.warning(f"Papers With Code unexpected error: {e}")

        # Fallback: Search by title
        if not result.github_url and paper_title:
            try:
                # Clean title for URL
                title_query = paper_title[:100].strip()
                url = f"{self.pwc_base_url}/papers/?title={requests.utils.quote(title_query)}"

                response = requests.get(url, timeout=self.pwc_api_timeout)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('results'):
                        # Check if title matches closely
                        for paper_data in data['results'][:3]:  # Check top 3
                            pwc_title = paper_data.get('title', '').lower()
                            if self._titles_match(title_query.lower(), pwc_title):
                                repo_url = paper_data.get('url_official', '')
                                if repo_url and 'github.com' in repo_url:
                                    result.github_url = self._normalize_github_url(repo_url)
                                    logger.info(f" Papers With Code (title): {result.github_url}")
                                    break

            except Exception as e:
                logger.debug(f"Papers With Code title search failed: {e}")

        return result

    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two titles match closely"""
        # Remove punctuation and extra spaces
        clean1 = re.sub(r'[^\w\s]', '', title1.lower()).strip()
        clean2 = re.sub(r'[^\w\s]', '', title2.lower()).strip()

        # Exact match
        if clean1 == clean2:
            return True

        # Check if one title contains the other
        if clean1 in clean2 or clean2 in clean1:
            return True

        # Check word overlap (>80% of words match)
        words1 = set(clean1.split())
        words2 = set(clean2.split())
        if len(words1) > 0 and len(words2) > 0:
            overlap = len(words1 & words2)
            similarity = overlap / min(len(words1), len(words2))
            return similarity > 0.8

        return False

    def _strategy_4_api_enrichment(self, api_metadata: object) -> RepositoryURLs:
        """Strategy 4: Use URLs from API metadata"""
        result = RepositoryURLs(extraction_method="api_metadata")

        if hasattr(api_metadata, 'github_url') and api_metadata.github_url:
            result.github_url = api_metadata.github_url

        if hasattr(api_metadata, 'huggingface_url') and api_metadata.huggingface_url:
            result.huggingface_url = api_metadata.huggingface_url

        if hasattr(api_metadata, 'kaggle_url') and api_metadata.kaggle_url:
            result.kaggle_url = api_metadata.kaggle_url

        if hasattr(api_metadata, 'demo_url') and api_metadata.demo_url:
            result.demo_url = api_metadata.demo_url

        return result

    def _validate_urls(self, result: RepositoryURLs, benchmark_name: str) -> RepositoryURLs:
        """Validate that URLs match the benchmark name"""
        if not benchmark_name:
            return result

        bench_normalized = (
            benchmark_name.lower()
            .replace('-', '').replace('_', '').replace(' ', '')
        )

        # Validate GitHub URL
        if result.github_url:
            repo_name = self._extract_repo_name(result.github_url, 'github')
            if not self._url_matches_benchmark(repo_name, bench_normalized):
                logger.warning(
                    f"GitHub repo '{repo_name}' may not match "
                    f"benchmark '{benchmark_name}'"
                )

        # Validate HuggingFace URL
        if result.huggingface_url:
            dataset_name = self._extract_repo_name(result.huggingface_url, 'huggingface')
            if not self._url_matches_benchmark(dataset_name, bench_normalized):
                logger.warning(
                    f"HF dataset '{dataset_name}' may not match "
                    f"benchmark '{benchmark_name}'"
                )

        # Validate Kaggle URL
        if result.kaggle_url:
            dataset_name = self._extract_repo_name(result.kaggle_url, 'kaggle')
            if not self._url_matches_benchmark(dataset_name, bench_normalized):
                logger.warning(
                    f"Kaggle dataset '{dataset_name}' may not match "
                    f"benchmark '{benchmark_name}'"
                )

        return result

    def _normalize_github_url(self, url: str) -> str:
        """Normalize GitHub URL to standard format"""
        if not url:
            return ""

        if not url.startswith('http'):
            if ':' in url:
                url = url.split(':', 1)[1]
            url = f'https://github.com/{url}'

        url = url.rstrip('/')
        url = url.replace('.git', '')
        url = url.replace('http://', 'https://')

        return url

    def _normalize_hf_url(self, url: str) -> str:
        """Normalize HuggingFace URL to standard format"""
        if not url:
            return ""

        if not url.startswith('http'):
            if ':' in url:
                url = url.split(':', 1)[1]
            url = f'https://huggingface.co/datasets/{url}'

        url = url.rstrip('/')
        url = url.replace('http://', 'https://')

        return url

    def _normalize_kaggle_url(self, url: str) -> str:
        """Normalize Kaggle URL to standard format"""
        if not url:
            return ""

        if not url.startswith('http'):
            if ':' in url:
                url = url.split(':', 1)[1]
            url = f'https://www.kaggle.com/datasets/{url}'

        url = url.rstrip('/')
        url = url.replace('http://', 'https://')

        # Ensure www. prefix
        if 'kaggle.com' in url and 'www.' not in url:
            url = url.replace('kaggle.com', 'www.kaggle.com')

        return url

    def _select_best_url(self, urls: List[str], text: str, url_type: str) -> str:
        """Select the best URL from multiple candidates based on context"""
        if not urls:
            return ""

        if len(urls) == 1:
            return urls[0]

        # Score each URL
        scored_urls = []
        for url in urls:
            score = 0.0

            # Position score (earlier = better)
            try:
                first_pos = text.lower().find(url.lower())
                if first_pos >= 0:
                    score += (1.0 - (first_pos / len(text))) * 0.4
            except:
                pass

            # Frequency score
            count = text.lower().count(url.lower())
            score += min(count / 3.0, 1.0) * 0.3

            # Context keywords score
            context_keywords = ['code', 'dataset', 'available', 'repository', 
                              'github', 'huggingface', 'kaggle', 'data', 'implementation']
            try:
                url_context = text[max(0, first_pos-100):min(len(text), first_pos+100)].lower()
                for kw in context_keywords:
                    if kw in url_context:
                        score += 0.05
            except:
                pass

            scored_urls.append((url, score))

        # Sort by score descending
        scored_urls.sort(key=lambda x: x[1], reverse=True)

        logger.debug(f"Best {url_type} URL: {scored_urls[0][0]} (score: {scored_urls[0][1]:.2f})")
        return scored_urls[0][0]

    def _extract_repo_name(self, url: str, platform: str) -> str:
        """Extract repository/dataset name from URL"""
        try:
            if platform == 'github':
                parts = url.rstrip('/').split('/')
                return parts[-1].lower().replace('-', '').replace('_', '')
            elif platform == 'huggingface':
                parts = url.rstrip('/').split('/')
                return parts[-1].lower().replace('-', '').replace('_', '')
            elif platform == 'kaggle':
                parts = url.rstrip('/').split('/')
                return parts[-1].lower().replace('-', '').replace('_', '')
        except:
            pass

        return ""

    def _url_matches_benchmark(self, repo_name: str, bench_normalized: str) -> bool:
        """Check if repository name matches benchmark name"""
        if not repo_name or not bench_normalized:
            return False

        # Exact substring match
        if bench_normalized in repo_name or repo_name in bench_normalized:
            return True

        # Character overlap threshold
        if len(bench_normalized) > 3 and len(repo_name) > 3:
            overlap = sum(c in repo_name for c in bench_normalized)
            if overlap / len(bench_normalized) > 0.6:
                return True

        return False

    def _merge_results(self, result1: RepositoryURLs, result2: RepositoryURLs) -> RepositoryURLs:
        """Merge two result objects, preferring non-empty values"""
        merged = RepositoryURLs()

        merged.github_url = result1.github_url or result2.github_url
        merged.huggingface_url = result1.huggingface_url or result2.huggingface_url
        merged.kaggle_url = result1.kaggle_url or result2.kaggle_url
        merged.dataset_url = result1.dataset_url or result2.dataset_url
        merged.demo_url = result1.demo_url or result2.demo_url

        merged.extraction_method = (
            result1.extraction_method if result1.github_url 
            else result2.extraction_method
        )

        return merged

    def _compute_confidence(self, result: RepositoryURLs) -> float:
        """Compute confidence score based on completeness"""
        score = 0.0

        if result.github_url:
            score += 0.40

        if result.huggingface_url:
            score += 0.30

        if result.kaggle_url:
            score += 0.20

        if result.demo_url:
            score += 0.10

        return min(score, 1.0)


# Convenience function
def extract_repository_urls(
    full_text: str,
    benchmark_name: str,
    sections: Dict[str, str],
    arxiv_id: Optional[str] = None,
    paper_title: Optional[str] = None,
    api_metadata: Optional[object] = None
) -> Tuple[str, str, str, str, str]:
    """
    Convenience function to extract repository URLs.

    Returns:
        Tuple of (github_url, huggingface_url, kaggle_url, dataset_url, demo_url)
    """
    extractor = EnhancedRepositoryExtractor()
    result = extractor.extract_all_repositories(
        full_text=full_text,
        benchmark_name=benchmark_name,
        sections=sections,
        arxiv_id=arxiv_id,
        paper_title=paper_title,
        api_metadata=api_metadata
    )

    # Prioritize dataset URL: HuggingFace > Kaggle
    dataset_url = result.huggingface_url or result.kaggle_url or result.dataset_url

    return (
        result.github_url,
        result.huggingface_url,
        result.kaggle_url,
        dataset_url,
        result.demo_url
    )