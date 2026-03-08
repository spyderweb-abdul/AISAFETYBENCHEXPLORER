"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors

Optimized DOI-Based Extraction Pipeline
========================================

IMPROVEMENTS OVER ORIGINAL:
1.  Integrated enhanced repository URL extractor (fixes empty Code/Dataset Repository)
2.  Uses unified_models.py (no more api_models.py + models.py confusion)
3.  Streamlined full-text acquisition with better error handling
4.  Enhanced LLM extraction with repository-focused prompts
5.  Improved quality scoring with repository completeness
6.  Better logging and progress tracking

Orchestrates:
1. DOI  Multi-API metadata resolution (S2, arXiv, Unpaywall, Crossref)
2. Full-text PDF download and parsing (Nougat/Marker/PyMuPDF)
3. Repository URL extraction (GitHub, HuggingFace) - NEW & IMPROVED
4. LLM-based benchmark metadata extraction
5. Cross-validation and quality assessment
6. Template alignment for AISafetyBenchExplorer
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tempfile
import requests
import re

from doi_based_resolver import DOIMetadataResolver
from models import (AggregatedPaperMetadata, BenchmarkMetadata, QualityAssessment, URLExtraction, EvaluationMetric)
from mainExtractor import EnhancedPaperMetadataExtractor
from pdf_parser import EnhancedPDFParser
from chunker import LaTeXAwareChunker
from repo_extractor import EnhancedRepositoryExtractor
from grobid_parser import GROBIDParser

logger = logging.getLogger(__name__)


# ============================================================================
# EXPANDED TASK TYPES TAXONOMY
# ============================================================================

APPROVED_TASK_TYPES = [
    # Core Safety Categories
    'Safety', 'Adversarial', 'Adversarial Method', 'Red Teaming', 'Jailbreak',
    'Attack Eval', 'Robustness', 'Vulnerability', 'Risk Assessment',

    # Bias and Fairness
    'Bias', 'Fairness', 'Stereotype', 'Gender', 'Social', 'Sociodemographics',
    'Cultural', 'Norm Alignment',

    # Truth and Accuracy
    'Factuality', 'Factual Consistency', 'Hallucination', 'Truthfulness',
    'Grounding', 'Faithfulness', 'Claim Verification',

    # Toxicity and Harm
    'Toxicity', 'Harmfulness', 'Hate Speech', 'Content Moderation',
    'Hazardous', 'Hazardous Knowledge', 'Physical Safety', 'Medical Safety',

    # Alignment and Values
    'Alignment', 'Value Alignment', 'Moral', 'Trustworthiness',
    'Helpfulness Eval', 'Preference Eval', 'Satisfaction Eval',

    # Privacy and Security
    'Privacy', 'Prompt Extraction', 'Cyberattacks', 'Unlearning',

    # Agent Behavior
    'Agents Safety', 'Agents Behavior Detection', 'Reasoning',

    # Response Characteristics
    'Refusal', 'False Refusal', 'Over Refusal', 'Non-compliance',
    'Consistency', 'Calibration',

    # Task-Specific
    'Instruction-following', 'Rule-following', 'RAG', 'Multimodal',
    'Conversational Safety', 'Opinion Steering',

    # Methodology/Meta
    'Benchmark', 'Evaluation', 'Crowdsourced', 'Lie Detection',
    'Capabilities', 'Language'
]


# ============================================================================
# EXPANDED EVALUATION METRICS CATALOGUE
# ============================================================================

KNOWN_EVALUATION_METRICS = [
    # Accuracy-based
    'Accuracy', 'ACC', 'F1 Score', 'Precision', 'Recall', 'AUPRC', 'AUROC',
    'Balanced Accuracy', 'CACC', 'Common Knowledge Accuracy',

    # Safety and Harm
    'Attack Success Rate', 'ASR', 'Jailbreak Success Rate', 'Jailbreak effectiveness',
    'Harmful Generation Rate', 'Harmfulness Score', 'Harmfulness Intensity Score',
    'Harmless Rate', 'Harmless Score', 'Harmlessness Score', 'HR',
    'Safety Score', 'Safety Rate', 'Safety Severity Score', 'Safety Generalization Score',
    'Safety Restoration Score', 'Unsafe Behavior Rate', 'Unsafe Response Rate',
    'Unsafety Score', 'Risk Score', 'Threat model clarity',

    # Toxicity
    'Toxicity Score', 'Expected Maximum Toxicity', 'Expected Max Toxicity',
    'Average Toxicity', 'Added Toxicity', 'Detoxification Rate',

    # Refusal and Compliance
    'Refusal Rate', 'RR', 'Refusal Detection Rate', 'Rejection Rate',
    'True Refusal Rate', 'False Refusal Rate', 'Attempt Rate',
    'Compliance Rate', 'Non-compliance Rate',
    'Agent Refusal Rate', 'Agent Harmful Completion Rate',

    # Bias and Fairness
    'Bias Score', 'Bias Score Ambiguous', 'Bias Score Disambiguous',
    'Fairness Score', 'Gender Bias Score', 'Gender Bias Score chrF',
    'Male Bias Rate', 'Female Bias Rate', 'Gender Stereotype Score',
    'Stereotype Score', 'Stereotype Rate fs for MT', 'Stereotype Rate gs for LMs',
    'Stereotype Correlation Measures', 'Implicit bias scores',
    'Social Bias Detection', 'Delta Disparity Score',
    'Demographic Consistency Score', 'Category-wise Bias Distribution',

    # Factuality and Truthfulness
    'Factuality Score', 'Factuality', 'Factual Consistency Score',
    'Truthfulness Score', 'Unadjusted Factuality Score',
    'Hallucination Rate', 'Hallucination Ratio', 'Detection Accuracy',
    'Honesty Score',

    # Retrieval and Grounding
    'Retrieval', 'Retrieval Accuracy', 'Grounding Score',

    # Alignment and Preference
    'Alignment', 'Value Alignment Score', 'Moral Belief Alignment',
    'Moral Belief Consistency', 'Moral Judgment Accuracy',
    'Moral Reasoning Accuracy', 'Moral Reasoning Consistency',
    'Contextual Preference Alignment', 'Pairwise Alignment Consistency',
    'Privacy Norm Alignment Score', 'Cultural Value Alignment',
    'Cultural Value Alignment Score', 'Social Value Alignment Score',
    'Ethical Stance Analysis',

    # Task Performance
    'Task Completion Rate', 'Task Performance Consistency',
    'Task Performance Score', 'Task-Specific Bias Score',
    'Win-Rate Against Baseline', 'Capability Loss', 'Capability Retention',

    # Reasoning and Consistency
    'Reasoning', 'Reasoning Score', 'Consistency Score',
    'Difference Awareness Score', 'Contextual Awareness Score',

    # Multi-dimensional
    '3H Controllability Score', 'SOFA Score', 'StrongREJECT Score',
    'Multi-objective Alignment', 'Multi-turn Safety Score',

    # Specialized Metrics
    'Rule Violation Rate by Type', 'Rule-Following Accuracy',
    'Prediction Mismatch', 'Prediction Mismatch Rate',
    'No-information Response Rate', 'Calibration',
    'Defense Robustness', 'Unalignment Attack Success Rate',

    # Domain-Specific
    'Medical Safety Score', 'Hazardous knowledge measurement',
    'Chinese-specific Safety Metrics', 'Arabic Language Vulnerability Score',
    'Arabizi Effectiveness Rate', 'Cross-lingual Safety Gap',

    # Comparative and Statistical
    'Category-Specific Harm Rate', 'Cross-National Steering Effectiveness',
    'Country-Model Similarity', 'Global Masculine Rate fm for MT',
    'Global vs. Local Harm Reduction',

    # User-centric
    'User Satisfaction Scores', 'Stated Preference Ratings',
    'Helpfulness Score', 'Response Harmfulness Score',
    'Prompt Harmfulness Score', 'Failure Rate',
]


# ============================================================================
# OPTIMIZED DOI PIPELINE CLASS
# ============================================================================

class OptimizedDOIPipeline:
    """
    Optimized extraction pipeline with enhanced repository URL extraction.

    Key improvements:
    - Integrated EnhancedRepositoryExtractor (solves empty repository fields)
    - Uses unified_models.py (eliminates model file confusion)
    - Better error handling and logging
    - Enhanced quality scoring including repository completeness
    """

    def __init__(self, email: str, s2_api_key: Optional[str] = None, extractor_model: str = "qwen2.5:32b", validation_model: str = "qwen2.5:14b", backend: str = "ollama", openai_api_key: Optional[str] = None,):
        """
        Initialize optimized pipeline.

        Args:
            email: Email for Unpaywall API (required)
            s2_api_key: Semantic Scholar API key (optional)
            extractor_model: LLM model for extraction
            validation_model: LLM model for validation
            backend: 'ollama' or 'openai'
            openai_api_key: OpenAI API key (if backend='openai')
        """
        self.email = email

        # Initialize components
        logger.info("Initializing Optimized DOI Pipeline...")

        self.grobid_parser = GROBIDParser()

        self.resolver = DOIMetadataResolver(email=email, s2_api_key=s2_api_key)
        logger.info("DOI metadata resolver")

        self.extractor = EnhancedPaperMetadataExtractor(
            model_name=extractor_model,
            validation_model=validation_model,
            backend=backend,
            api_key=openai_api_key,
            chunker=LaTeXAwareChunker()
        )
        logger.info(f"LLM metadata extractor ({backend}: {extractor_model})")

        self.pdf_parser = EnhancedPDFParser(prefer_nougat=False, enable_grobid=True)
        logger.info("PDF parser")

        # NEW: Repository extractor
        self.repo_extractor = EnhancedRepositoryExtractor()
        logger.info("Repository URL extractor (NEW)")

        logger.info("Pipeline ready!")

    def process_from_pdf(self, pdf_path: str, doi: Optional[str] = None):
        """Process PDF directly without DOI resolution"""
        logger.info(f"Processing PDF: {pdf_path}")
        
        # 1. Parse with adaptive backend
        text, format_hint, grobid_metadata = self.pdf_parser.parse_pdf(pdf_path)
        
        if not text:
            logger.error("Failed to parse PDF")
            return None, self._failed_quality(), None
        
        logger.info(f"Parsed {len(text)} characters ({format_hint} format)")
        
        # 2. Chunk document into sections
        sections = self.extractor.select_relevant_chunks(text, format_hint)
        logger.info("Document chunked into sections")
        
        # 3. Extract formulas
        formulas = self.extractor.chunker.extract_formulas(text)
        logger.info(f"Extracted {len(formulas)} formulas")
        
        # 4. Extract ArXiv ID from text or GROBID metadata
        arxiv_id = None
        if grobid_metadata and grobid_metadata.get('arxiv_url'):
            arxiv_match = re.search(r'(\d{4}\.\d{4,5})', grobid_metadata['arxiv_url'])
            if arxiv_match:
                arxiv_id = arxiv_match.group(1)
        
        if not arxiv_id:
            # Try to extract from text using chunker's URL extraction
            url_data = self.extractor.chunker.extract_urls(text)
            if url_data.get('arxiv'):
                arxiv_match = re.search(r'(\d{4}\.\d{4,5})', url_data['arxiv'])
                if arxiv_match:
                    arxiv_id = arxiv_match.group(1)
        
        logger.info(f"ArXiv ID: {arxiv_id if arxiv_id else 'Not found'}")
        
        # 5. Extract benchmark name
        benchmark_name = self.extractor._extract_benchmark_name_dedicated(
            grobid_metadata.get('title', '') if grobid_metadata else '',
            grobid_metadata.get('abstract', '') if grobid_metadata else '',
            text
        )
        logger.info(f"Benchmark name: {benchmark_name}")
        
        # 6. Build URLs 
        url_data = self.extractor.chunker.extract_urls(text)
        urls = URLExtraction(
            arxiv_url=url_data.get('arxiv') or '',      
            doi_url=doi or '',
            github_url=url_data.get('github') or '',     
            huggingface_url=url_data.get('huggingface') or '',
            kaggle_url=url_data.get('kaggle') or '',
            demo_url=''
        )

        # 7. Extract repo URLs (with Papers With Code API)
        repo_urls = self.repo_extractor.extract_all_repositories(
            full_text=text,
            benchmark_name=benchmark_name,
            sections=sections,
            arxiv_id=arxiv_id,
            paper_title=grobid_metadata.get('title') if grobid_metadata else None
        )
        
        # Update URLs with repository extraction results
        if repo_urls.github_url:
            urls.github_url = repo_urls.github_url
        if repo_urls.huggingface_url:
            urls.huggingface_url = repo_urls.huggingface_url
        if repo_urls.kaggle_url:
            urls.kaggle_url = repo_urls.kaggle_url
        
        logger.info(f"Repository URLs extracted: GitHub={bool(urls.github_url)}, HF={bool(urls.huggingface_url)}, Kaggle={bool(urls.kaggle_url)}")
        
        # 8. Multi-pass extraction
        result = self.extractor.extract_with_multi_pass(
            sections=sections,
            urls=urls,
            benchmark_name=benchmark_name,
            format_hint=format_hint,
            formulas=formulas,
            num_passes=3,  # 3-pass refinement
            grobid_metadata=grobid_metadata
        )
        
        if not result:
            logger.error("Multi-pass extraction failed")
            return None, self._failed_quality(), None
        
        # 9. Validate extraction
        # Calculate quality assessment (validate_extraction method doesn't exist)
        completeness_items = []
        if result.benchmark_name:
            completeness_items.append(1.0)
        if result.paper_title:
            completeness_items.append(1.0)
        if result.task_types:
            completeness_items.append(1.0)
        if result.dataset_size:
            completeness_items.append(1.0)
        if result.evaluation_metrics:
            completeness_items.append(1.0)
        completeness_score = sum(completeness_items) / 5.0 if completeness_items else 0.0

        # Formula quality
        formula_quality = self.extractor.formula_scorer.score_formula_quality(result.evaluation_metrics)

        # URL completeness
        url_score = 0.0
        if urls.arxiv_url:
            url_score += 0.25
        if urls.github_url:
            url_score += 0.35
        if urls.huggingface_url or urls.kaggle_url:
            url_score += 0.30
        if urls.doi_url:
            url_score += 0.10

        # Issues and strengths
        issues = []
        strengths = []

        if not urls.github_url:
            issues.append("No GitHub repository URL")
        if not urls.huggingface_url and not urls.kaggle_url:
            issues.append("No dataset repository URL")
        if not result.evaluation_metrics:
            issues.append("No evaluation metrics extracted")
        else:
            strengths.append(f"{len(result.evaluation_metrics)} metrics extracted")
        if result.task_types:
            strengths.append(f"{len(result.task_types)} task types identified")

        # Create quality assessment
        quality = QualityAssessment(
            overall_score=round(0.35 * completeness_score + 0.35 * 0.8 + 0.15 * formula_quality + 0.15 * url_score, 2),
            completeness_score=round(completeness_score, 2),
            accuracy_score=0.8,
            formula_quality_score=formula_quality,
            url_completeness=round(url_score, 2),
            issues_found=issues,
            strengths=strengths,
            requires_human_review=completeness_score < 0.6 or url_score < 0.4,
            review_reason="Low completeness" if completeness_score < 0.6 else "Missing repository URLs" if url_score < 0.4 else ""
        )
        
        # 10. Align to template
        extracted = self.extractor.align_to_template_format(result)
        
        # 11. Create minimal API metadata for consistency
        api_metadata = AggregatedPaperMetadata(
            title=grobid_metadata.get('title', '') if grobid_metadata else '',
            abstract=grobid_metadata.get('abstract', '') if grobid_metadata else '',
            authors=grobid_metadata.get('authors', []) if grobid_metadata else [],
            year=None,
            doi=doi,
            arxiv_id=arxiv_id,
            arxiv_url=urls.arxiv_url,
            doi_url=doi if doi else '',
            github_url=urls.github_url,
            huggingface_url=urls.huggingface_url,
            kaggle_url=urls.kaggle_url,
            data_sources=['PDF Direct']
        )
        
        return extracted, quality, api_metadata


        
    def process_from_doi(self, identifier: str, extract_full_text: bool = True, save_pdf: bool = False, output_dir: Optional[Path] = None) -> Tuple[Optional[Dict[str, Any]], QualityAssessment, AggregatedPaperMetadata]:
        """
        Complete extraction pipeline from DOI/arXiv ID.

        ENHANCED with repository URL extraction to solve empty field issue.

        Args:
            identifier: DOI, arXiv ID, or Semantic Scholar ID
            extract_full_text: Download and parse full text if available
            save_pdf: Save downloaded PDF
            output_dir: Directory for saved files

        Returns:
            (extracted_metadata_dict, quality_assessment, api_metadata)
        """
        logger.info("=" * 80)
        logger.info(f"Processing: {identifier}")
        logger.info("=" * 80)

        # ===== PHASE 1: API Metadata Resolution =====
        logger.info("Phase 1: Resolving via APIs...")
        api_metadata = self.resolver.resolve(identifier)

        if not api_metadata.title:
            logger.error("Failed to resolve identifier")
            return None, self._failed_quality(), api_metadata

        self._log_api_results(api_metadata)

        # ===== PHASE 2: Full-Text Acquisition =====
        full_text = None
        format_hint = "text"

        if extract_full_text and api_metadata.has_full_text_access:
            logger.info("Phase 2: Acquiring full text...")
            full_text, format_hint = self._download_and_parse_pdf(
                api_metadata, save_pdf, output_dir
            )
            if full_text:
                logger.info(f"{len(full_text)} characters ({format_hint} format)")
            else:
                logger.warning("Full text acquisition failed")
        else:
            logger.info("Phase 2: Skipping full text (not available or requested)")

        # ===== PHASE 3: LLM Metadata Extraction =====
        logger.info("Phase 3: LLM metadata extraction...")

        if full_text:
            extracted, quality = self._extract_with_full_text(api_metadata, full_text, format_hint)
        else:
            extracted, quality = self._extract_from_api_only(api_metadata)

        if not extracted:
            logger.error(" Extraction failed")
            return {}, self._failed_quality(), api_metadata

        # ===== PHASE 4: Enhanced Repository URL Extraction (NEW!) =====
        logger.info("Phase 4: Enhanced repository URL extraction...")
        extracted = self._enhance_with_repository_urls(extracted, full_text or "", api_metadata)

        # ===== PHASE 5: Cross-Validation =====
        logger.info("Phase 5: Cross-validation with API metadata...")
        quality = self._cross_validate(extracted, quality, api_metadata)

        # ===== Final Summary =====
        self._log_final_summary(extracted, quality)

        return extracted, quality, api_metadata


    def _enhance_with_repository_urls(self, extracted: Dict[str, Any], full_text: str, 
                                      api_metadata: AggregatedPaperMetadata) -> Dict[str, Any]:
        """
        NEW METHOD: Enhance extraction with repository URLs.

        This solves the core issue: Code Repository and Dataset Repository
        were empty in previous versions.
        """
        benchmark_name = extracted.get('Benchmark Name', '')

        # Prepare sections for extraction
        sections = {
            'abstract': extracted.get('Paper Title', ''),
            'fulltext': full_text[:10000] if full_text else ''  # First 10k chars
        }

        # Run multi-strategy extraction
        repo_urls = self.repo_extractor.extract_all_repositories(
            full_text=full_text or "",
            benchmark_name=benchmark_name,
            sections=sections,
            api_metadata=api_metadata
        )
        
        # Extract individual URLs from the result object
        github_url = repo_urls.github_url
        hf_url = repo_urls.huggingface_url
        dataset_url = repo_urls.dataset_url
        demo_url = repo_urls.demo_url
        kaggle_url = repo_urls.kaggle_url

        # Update extracted metadata
        if github_url:
            extracted['Code Repository'] = github_url
            logger.info(f"GitHub: {github_url}")
        else:
            logger.warning("GitHub URL not found")

        if hf_url or dataset_url:
            extracted['Dataset Repository'] = hf_url or dataset_url
            logger.info(f"Dataset (HuggingFace): {hf_url or dataset_url}")
        elif kaggle_url:
            extracted['Dataset Repository'] = kaggle_url
            logger.info(f"Dataset (kaggle): {kaggle_url or dataset_url}")
        else:
            logger.warning("Dataset URL not found")

        return extracted


    def _download_and_parse_pdf(self, api_metadata: AggregatedPaperMetadata, save_pdf: bool, output_dir: Optional[Path]) -> Tuple[Optional[str], str]:
        """Download and parse full-text PDF"""
        pdf_url = api_metadata.pdf_url or api_metadata.oa_pdf_url

        if not pdf_url:
            logger.warning("No PDF URL available")
            return None, "text"

        response = None
        pdf_path = None

        try:
            logger.info(f"Downloading: {pdf_url}")
            response = requests.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()

            # Save to file
            if save_pdf and output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                safe_name = self._sanitize_filename(api_metadata.title)
                pdf_path = output_dir / f"{safe_name}.pdf"
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Saved: {pdf_path}")
            else:
                # Temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    for chunk in response.iter_content(chunk_size=8192):
                        tmp.write(chunk)
                    pdf_path = Path(tmp.name)

            # Parse PDF
            logger.info("Parsing PDF...")
            text, format_hint, grobid_metadata = self.pdf_parser.parse_pdf(str(pdf_path))

            # Clean up temp file
            if not save_pdf:
                pdf_path.unlink()

            return text, format_hint

        except Exception as e:
            logger.error(f"PDF download/parse failed: {e}")
            return None, "text"
        finally:
            if response:
                response.close()
                
                
    def _compute_quality_score(self, metadata: BenchmarkMetadata, 
                              sections: Dict[str, str], 
                              urls: URLExtraction) -> QualityAssessment:
        """Compute quality score for extracted metadata."""

        # Completeness score
        completeness_score = 0.0
        if metadata.benchmark_name and metadata.benchmark_name != "Unknown":
            completeness_score += 0.25
        if metadata.paper_title:
            completeness_score += 0.10
        if metadata.task_types and len(metadata.task_types) > 0:
            completeness_score += 0.20
        if metadata.evaluation_metrics and len(metadata.evaluation_metrics) > 0:
            completeness_score += 0.25
        if metadata.dataset_size and metadata.dataset_size > 0:
            completeness_score += 0.20

        # Formula quality
        formula_scores = []
        if metadata.evaluation_metrics:
            for metric in metadata.evaluation_metrics:
                if metric.mathematical_definition and len(metric.mathematical_definition) > 10:
                    formula_scores.append(1.0)
                elif metric.mathematical_definition:
                    formula_scores.append(0.5)
                else:
                    formula_scores.append(0.0)
        formula_quality_score = sum(formula_scores) / len(formula_scores) if formula_scores else 0.0

        # URL completeness
        url_completeness = 0.0
        if urls.arxiv_url:
            url_completeness += 0.25
        if urls.github_url:
            url_completeness += 0.35
        if urls.huggingface_url or urls.kaggle_url:
            url_completeness += 0.30
        if urls.doi_url:
            url_completeness += 0.10

        # Overall score
        overall_score = (
            0.35 * completeness_score +
            0.35 * formula_quality_score +
            0.15 * url_completeness +
            0.15 * (1.0 if len(sections.get("methodology", "")) > 500 else 0.5)
        )

        # Identify issues and strengths
        issues = []
        strengths = []

        if metadata.evaluation_metrics and len(metadata.evaluation_metrics) > 0:
            strengths.append(f"{len(metadata.evaluation_metrics)} metrics extracted")
        else:
            issues.append("No evaluation metrics extracted")

        if not urls.github_url and not urls.huggingface_url:
            issues.append("No repository URLs found")

        return QualityAssessment(
            overall_score=round(overall_score, 2),
            completeness_score=round(completeness_score, 2),
            accuracy_score=0.75,  # Default for full-text
            formula_quality_score=round(formula_quality_score, 2),
            url_completeness=round(url_completeness, 2),
            issues_found=issues,
            strengths=strengths,
            requires_human_review=overall_score < 0.7,
            review_reason=f"Quality score: {overall_score:.2f}" if overall_score < 0.7 else ""
        )


    def _extract_with_full_text(self, api_metadata: AggregatedPaperMetadata, full_text: str, format_hint: str) -> Tuple[Dict[str, Any], QualityAssessment]:
        """Extract metadata using full text + API metadata"""
        # Chunk document
        sections = self.extractor.select_relevant_chunks(full_text, format_hint)

        # Build URLs from API
        urls = URLExtraction(
            arxiv_url=api_metadata.arxiv_url or "",
            doi_url=api_metadata.doi_url or "",
            github_url=api_metadata.github_url or "",
            huggingface_url=api_metadata.huggingface_url or "",
            kaggle_url=api_metadata.kaggle_url or "",
            demo_url=api_metadata.demo_url or ""
        )

        # Extract benchmark name
        benchmark_name = self.extractor._extract_benchmark_name_dedicated(
            api_metadata.title,
            api_metadata.abstract or "",
            full_text
        )

        # Extract formulas
        formulas = self.extractor.chunker.extract_formulas(full_text)

        # Run LLM extraction
        metadata = self.extractor.extract_with_cot(
            sections, urls, benchmark_name, format_hint, formulas
        )

        if not metadata:
            return {}, self._failed_quality()

        # Validate
        quality = self._compute_quality_score(metadata, sections, urls)

        # Align to template
        aligned = self.extractor.align_to_template_format(metadata)

        # Enrich with API metadata
        aligned = self._enrich_with_api(aligned, api_metadata)

        return aligned, quality


    def _extract_from_api_only(self, api_metadata: AggregatedPaperMetadata) -> Tuple[Dict[str, Any], QualityAssessment]:
        """Extract metadata using only API data (fallback)"""
        logger.info("Using API-only mode (no full text)")

        # Build minimal sections
        sections = {
            'title': api_metadata.title,
            'abstract': api_metadata.abstract or "",
            'title_and_abstract': f"{api_metadata.title}\n\n{api_metadata.abstract or ''}",
            'full_text': api_metadata.abstract or ""
        }

        urls = URLExtraction(
            arxiv_url=api_metadata.arxiv_url or "",
            doi_url=api_metadata.doi_url or ""
        )

        benchmark_name = self.extractor._extract_benchmark_name_dedicated(
            api_metadata.title, api_metadata.abstract or "", ""
        )

        metadata = self.extractor.extract_with_cot(
            sections, urls, benchmark_name, "text", []
        )

        if not metadata:
            return {}, self._failed_quality()

        quality = QualityAssessment(
            overall_score=0.5,
            completeness_score=0.4,
            accuracy_score=0.6,
            formula_quality_score=0.0,
            url_completeness=0.3,
            issues_found=["No full text available"],
            strengths=["API metadata present"],
            requires_human_review=True,
            review_reason="API-only extraction (no full text)"
        )

        aligned = self.extractor.align_to_template_format(metadata)
        aligned = self._enrich_with_api(aligned, api_metadata)

        return aligned, quality


    def _enrich_with_api(self, extracted: Dict[str, Any], api_metadata: AggregatedPaperMetadata) -> Dict[str, Any]:
        """Enrich extracted metadata with API data"""
        # Add API-sourced fields
        if not extracted.get('Authors') and api_metadata.authors:
            extracted['Authors'] = ', '.join(api_metadata.authors)

        if not extracted.get('Year') and api_metadata.year:
            extracted['Year'] = api_metadata.year

        if not extracted.get('Venue') and api_metadata.venue:
            extracted['Venue'] = api_metadata.venue

        extracted['Publisher'] = api_metadata.publisher or ""
        extracted['Citation Count'] = api_metadata.citation_count
        extracted['Reference Count'] = api_metadata.reference_count
        extracted['Open Access'] = "Yes" if api_metadata.is_open_access else "No"
        extracted['OA Status'] = api_metadata.oa_status or ""
        extracted['Fields of Study'] = ', '.join(api_metadata.fields_of_study) if api_metadata.fields_of_study else ""
        extracted['Metadata Completeness'] = api_metadata.metadata_completeness_score
        extracted['Data Sources'] = ', '.join(api_metadata.data_sources)

        return extracted


    def _cross_validate(self, extracted: Dict[str, Any], quality: QualityAssessment, api_metadata: AggregatedPaperMetadata) -> QualityAssessment:
        """Cross-validate extraction against API metadata"""
        issues = list(quality.issues_found)
        strengths = list(quality.strengths)

        # Check title similarity
        if api_metadata.title:
            extracted_title = extracted.get('Paper Title', '').lower()
            api_title = api_metadata.title.lower()
            if api_title[:50] not in extracted_title and extracted_title[:50] not in api_title:
                issues.append("Title mismatch with API metadata")

        # Check year
        if api_metadata.year:
            extracted_year = extracted.get('Year')
            if extracted_year and abs(int(extracted_year) - api_metadata.year) > 1:
                issues.append(f"Year mismatch: extracted={extracted_year}, API={api_metadata.year}")

        # Check citation count (as indicator of popularity)
        if api_metadata.citation_count > 100:
            strengths.append(f"High-impact paper ({api_metadata.citation_count} citations)")

        # Enhanced URL completeness check
        url_score = 0.0
        if extracted.get('Paper Link'):
            url_score += 0.25
        if extracted.get('Code Repository'):
            url_score += 0.35  # Increased weight
        else:
            issues.append("Code Repository missing")
        if extracted.get('Dataset Repository'):
            url_score += 0.30  # Increased weight
        else:
            issues.append("Dataset Repository missing")
        if api_metadata.doi_url:
            url_score += 0.10

        # Update quality scores
        quality.url_completeness = url_score
        quality.issues_found = issues
        quality.strengths = strengths

        # Recalculate overall score with new weighting
        quality.overall_score = (
            0.35 * quality.completeness_score +
            0.35 * quality.accuracy_score +
            0.15 * quality.formula_quality_score +
            0.15 * quality.url_completeness  # Repository URLs now contribute
        )

        # Determine if human review needed
        if quality.overall_score < 0.7:
            quality.requires_human_review = True
            quality.review_reason = f"Quality score below threshold: {quality.overall_score:.2f}"
        elif not extracted.get('Code Repository') and not extracted.get('Dataset Repository'):
            quality.requires_human_review = True
            quality.review_reason = "Missing both code and dataset repositories"

        return quality


    def _failed_quality(self) -> QualityAssessment:
        """Return quality assessment for failed extraction"""
        return QualityAssessment(
            overall_score=0.0,
            completeness_score=0.0,
            accuracy_score=0.0,
            formula_quality_score=0.0,
            url_completeness=0.0,
            issues_found=["Extraction failed completely"],
            strengths=[],
            requires_human_review=True,
            review_reason="Extraction failed"
        )


    def _sanitize_filename(self, title: str) -> str:
        """Create safe filename from title"""
        safe = re.sub(r'[^a-zA-Z0-9\s\-]', '', title)
        safe = safe[:100]  # Limit length
        safe = re.sub(r'\s+', '_', safe.strip())
        return safe or 'paper'


    def _log_api_results(self, api_metadata: AggregatedPaperMetadata):
        """Log API resolution results"""
        logger.info(f"Title: {api_metadata.title[:70]}{'...' if len(api_metadata.title) > 70 else ''}")
        logger.info(f"Authors: {len(api_metadata.authors)} authors")
        logger.info(f"Year: {api_metadata.year}")
        logger.info(f"Citations: {api_metadata.citation_count}")
        logger.info(f"Open Access: {api_metadata.is_open_access}")
        logger.info(f"Completeness: {api_metadata.metadata_completeness_score:.2f}")


    def _log_final_summary(self, extracted: Dict[str, Any], quality: QualityAssessment):
        """Log final extraction summary"""
        logger.info("=" * 80)
        logger.info("EXTRACTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Benchmark: {extracted.get('Benchmark Name', 'Unknown')}")
        logger.info(f"Task Types: {len(extracted.get('Task Types', []))}")
        logger.info(f"Metrics: {len(extracted.get('Evaluation Metrics', []))}")
        logger.info(f"Dataset Size: {extracted.get('Dataset Size', 'Unknown')}")
        logger.info(f"Code Repo: {'' if extracted.get('Code Repository') else ''}")
        logger.info(f"Dataset Repo: {'' if extracted.get('Dataset Repository') else ''}")
        logger.info(f"Quality: {quality.overall_score:.2f}/1.00")
        logger.info(f"Human Review: {'Yes' if quality.requires_human_review else 'No'}")
        if quality.requires_human_review:
            logger.info(f"  Review Reason: {quality.review_reason}")
    logger.info("=" * 80)