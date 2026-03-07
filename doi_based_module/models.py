"""
Unified Data Models for AI Safety Benchmark Metadata Extraction
================================================================

Combines API response models and benchmark extraction models into a single,
coherent structure. Eliminates redundancy and improves maintainability.

Models:
- API Response Models: Semantic Scholar, arXiv, Unpaywall, Crossref
- Benchmark Models: BenchmarkMetadata, EvaluationMetric, QualityAssessment
- Unified: AggregatedPaperMetadata

Author: Optimized for AI Safety Evals Project
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# API RESPONSE MODELS (Semantic Scholar, arXiv, Unpaywall, Crossref)
# ============================================================================

class SemanticScholarAuthor(BaseModel):
    """Author metadata from Semantic Scholar API"""
    authorId: Optional[str] = None
    name: str
    url: Optional[str] = None
    affiliations: Optional[List[str]] = []
    citationCount: Optional[int] = 0
    hIndex: Optional[int] = 0


class SemanticScholarExternalIds(BaseModel):
    """External identifiers from Semantic Scholar"""
    ArXiv: Optional[str] = None
    DOI: Optional[str] = None
    CorpusId: Optional[int] = None
    DBLP: Optional[str] = None
    PubMed: Optional[str] = None
    PubMedCentral: Optional[str] = None


class SemanticScholarVenue(BaseModel):
    """Publication venue metadata from Semantic Scholar"""
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    alternate_names: Optional[List[str]] = []
    url: Optional[str] = None


class SemanticScholarOpenAccessPdf(BaseModel):
    """Open Access PDF metadata from Semantic Scholar"""
    url: Optional[str] = None
    status: Optional[str] = None
    license: Optional[str] = None


class SemanticScholarPaper(BaseModel):
    """Complete paper metadata from Semantic Scholar API"""
    paperId: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    publicationVenue: Optional[SemanticScholarVenue] = None
    authors: List[SemanticScholarAuthor] = []
    externalIds: Optional[SemanticScholarExternalIds] = None
    url: Optional[str] = None
    citationCount: int = 0
    referenceCount: int = 0
    influentialCitationCount: int = 0
    isOpenAccess: bool = False
    openAccessPdf: Optional[SemanticScholarOpenAccessPdf] = None
    fieldsOfStudy: Optional[List[str]] = []
    s2FieldsOfStudy: Optional[List[Dict[str, Any]]] = []
    publicationDate: Optional[str] = None
    journal: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class ArXivPaperMetadata(BaseModel):
    """Metadata from arXiv API"""
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str] = []
    published: Optional[datetime] = None
    updated: Optional[datetime] = None
    primary_category: Optional[str] = None
    categories: List[str] = []
    doi: Optional[str] = None
    journal_ref: Optional[str] = None
    pdf_url: Optional[str] = None
    arxiv_url: Optional[str] = None
    comment: Optional[str] = None


class UnpaywallLocation(BaseModel):
    """OA location metadata from Unpaywall"""
    url: Optional[str] = None
    url_for_pdf: Optional[str] = None
    url_for_landing_page: Optional[str] = None
    version: Optional[str] = None  # 'publishedVersion', 'acceptedVersion', 'submittedVersion'
    license: Optional[str] = None
    host_type: Optional[str] = None  # 'publisher', 'repository'
    is_best: bool = False


class UnpaywallResponse(BaseModel):
    """Response from Unpaywall API"""
    doi: str
    title: str
    is_oa: bool = False
    oa_status: Optional[str] = None  # 'gold', 'green', 'hybrid', 'bronze', 'closed'
    best_oa_location: Optional[UnpaywallLocation] = None
    oa_locations: List[UnpaywallLocation] = []
    year: Optional[int] = None
    genre: Optional[str] = None
    journal_name: Optional[str] = None
    publisher: Optional[str] = None
    updated: Optional[str] = None


class CrossrefAuthor(BaseModel):
    """Author metadata from Crossref API"""
    given: Optional[str] = None
    family: Optional[str] = None
    sequence: Optional[str] = None
    affiliation: Optional[List[Dict[str, str]]] = []
    ORCID: Optional[str] = None


class CrossrefResponse(BaseModel):
    """Response from Crossref API"""
    DOI: str
    title: Optional[List[str]] = []
    author: Optional[List[CrossrefAuthor]] = []
    published: Optional[Dict[str, List[List[int]]]] = None
    container_title: Optional[List[str]] = []
    publisher: Optional[str] = None
    type: Optional[str] = None
    abstract: Optional[str] = None
    URL: Optional[str] = None
    reference_count: Optional[int] = 0
    is_referenced_by_count: Optional[int] = 0
    license: Optional[List[Dict[str, Any]]] = []


# ============================================================================
# BENCHMARK EXTRACTION MODELS
# ============================================================================

class EvaluationMetric(BaseModel):
    """
    Evaluation metric schema aligned with AISafetyBenchExplorer template.

    Captures comprehensive metric information including mathematical definitions,
    methodology, and context-specific details.
    """
    metric_name: str = Field(
        description="Exact name of the evaluation metric as stated in the paper"
    )

    conceptual_description: str = Field(
        description=(
            "High-level conceptual description including: "
            "(1) Task type (e.g., classification, generation, ranking), "
            "(2) Data type (text, multimodal, structured), "
            "(3) Safety dimension (bias/toxicity/factuality/deception/alignment/reliability/risk), "
            "(4) Measurement intent (what aspect of safety is being quantified)"
        )
    )

    methodological_details: str = Field(
        description=(
            "Step-by-step methodology describing: "
            "(1) Label source (human annotations/automated tools/LLM-as-judge/rule-based), "
            "(2) Data preprocessing steps, "
            "(3) Scoring mechanism (binary/continuous/ordinal), "
            "(4) Aggregation method (mean/median/weighted average/max)"
        )
    )

    mathematical_definition: str = Field(
        description=(
            "LaTeX mathematical formula with all variables explicitly defined. "
            "Format: \\[formula\\] or \\(formula\\). "
            "Include variable definitions, ranges, and constraints. "
            "Example: \\[\\text{ACC} = \\frac{TP + TN}{TP + TN + FP + FN}\\] "
            "where TP=True Positives, TN=True Negatives, etc."
        )
    )

    differences_from_standard_definition: str = Field(
        description=(
            "How this metric differs from standard or commonly-used definitions. "
            "Include modifications, adaptations, or novel aspects. "
            "If standard metric, state 'Standard definition' or 'No significant differences'"
        )
    )

    notes: str = Field(
        description=(
            "Additional context including: "
            "(1) Assumptions and limitations, "
            "(2) Implementation details or computational complexity, "
            "(3) Recommended use cases or applicability constraints, "
            "(4) Relationship to other metrics in the benchmark"
        )
    )


class URLExtraction(BaseModel):
    """URLs extracted from paper with validation"""
    arxiv_url: str = Field(
        default="",
        description="ArXiv preprint URL (https://arxiv.org/abs/...)"
    )

    doi_url: str = Field(
        default="",
        description="DOI URL (https://doi.org/...)"
    )

    github_url: str = Field(
        default="",
        description="GitHub repository URL for code (https://github.com/...)"
    )

    huggingface_url: str = Field(
        default="",
        description="HuggingFace dataset URL (https://huggingface.co/datasets/...)"
    )
    
    kaggle_url: str = Field(
        default="",
        description="Kaggle dataset URL (https://kaggle.com/datasets/...)"
    )
        
    demo_url: str = Field(
        default="",
        description="Demo, project page, or interactive tool URL"
    )

    def get_primary_paper_link(self) -> str:
        """Return primary paper link (ArXiv > DOI > empty)"""
        if self.arxiv_url:
            return self.arxiv_url
        if self.doi_url:
            return self.doi_url
        return ""


class BenchmarkMetadata(BaseModel):
    """
    Complete benchmark metadata schema aligned with AISafetyBenchExplorer template.

    Captures all essential information for AI safety benchmark cataloging and analysis.
    """
    benchmark_name: str = Field(
        description=(
            "Official benchmark name from paper. "
            "Examples: 'MALT', 'SGBench', 'TOFUEVAL', 'ToxiGen', 'ToxicChat', "
            "'HONEST', 'RippleBench', 'SafetyPrompts', 'BBQ'"
        )
    )

    paper_title: str = Field(
        description="Complete academic paper title"
    )

    urls: URLExtraction = Field(
        default_factory=URLExtraction,
        description="All URLs extracted from paper (ArXiv, DOI, GitHub, HuggingFace, Demo)"
    )

    task_types: List[str] = Field(
        default_factory=list,
        description=(
            "List of AI safety task types from approved taxonomy. "
            "Examples: ['Safety', 'Bias', 'Jailbreak', 'Toxicity', 'Hallucination', "
            "'Factuality', 'Privacy', 'Alignment']"
        )
    )

    dataset_size: Optional[int] = Field(
        default=None,
        description="Total number of examples/instances in the benchmark dataset"
    )

    complexity_level: str = Field(
        default="Unknown",
        description=(
            "Benchmark complexity classification based on rigorous criteria:\n\n"
            "**Popular**: Widely adopted benchmarks with high community impact. Criteria:\n"
            "   Citation count > 100 OR Frequent mention in safety literature\n"
            "   Used as baseline in multiple studies\n"
            "   Recognized standard in the field\n\n"
            "**High**: Sophisticated evaluation requiring advanced reasoning. Criteria:\n"
            "   Multi-hop/compositional reasoning across >2 steps\n"
            "   Adversarial robustness testing (red-teaming, jailbreaking)\n"
            "   Subjective/open-ended generation tasks with nuanced evaluation\n"
            "   Risk-critical decision-making (medical, legal, financial safety)\n"
            "   Novel metric development or complex evaluation methodology\n"
            "   Requires domain expertise for annotation/evaluation\n\n"
            "**Medium**: Moderate complexity with some challenging aspects. Criteria:\n"
            "   1-2 step reasoning or limited compositional requirements\n"
            "   Some adversarial testing but not primary focus\n"
            "   Mix of objective and subjective evaluation\n"
            "   Standard metrics with minor adaptations\n"
            "   Moderate annotation/evaluation effort\n\n"
            "**Low**: Straightforward evaluation with clear criteria. Criteria:\n"
            "   Single-step reasoning or direct lookup\n"
            "   Objective tasks with binary/categorical outcomes\n"
            "   Standard metrics (accuracy, F1) without modifications\n"
            "   Minimal adversarial considerations\n"
            "   Simple annotation process\n\n"
            "**Classification Rules**:\n"
            " If benchmark exhibits Popular criteria, classify as Popular regardless of complexity\n"
            " For multi-faceted benchmarks, prioritize the most safety-critical dimension\n"
            " When in doubt between levels, choose higher complexity if adversarial/risk-critical\n"
            " Use 'Unknown' only when insufficient information is available"
        )
    )

    evaluation_metrics: List[EvaluationMetric] = Field(
        default_factory=list,
        description="Complete list of evaluation metrics described in the paper"
    )

    @property
    def paper_link(self) -> str:
        """Primary paper link for template compatibility"""
        return self.urls.get_primary_paper_link()

    @property
    def code_repository(self) -> str:
        """GitHub URL for template compatibility"""
        return self.urls.github_url

    @property
    def dataset_repository(self) -> str:
        """Dataset URL for template compatibility (HuggingFace > GitHub)"""
        return self.urls.huggingface_url or self.urls.github_url


class QualityAssessment(BaseModel):
    """
    Quality assessment and validation results for extracted metadata.

    Provides multi-dimensional quality scoring and flags for human review.
    """
    overall_score: float = Field(
        description=(
            "Overall quality score (0-1). "
            "Formula: 0.35*Completeness + 0.35*Accuracy + 0.15*Formula + 0.15*URL"
        ),
        ge=0,
        le=1
    )

    completeness_score: float = Field(
        description=(
            "Completeness of extraction (0-1). "
            "Measures: benchmark name, metrics count, task types, URLs, dataset size"
        ),
        ge=0,
        le=1
    )

    accuracy_score: float = Field(
        description=(
            "Accuracy of extracted information (0-1). "
            "Cross-validated against API metadata and internal consistency checks"
        ),
        ge=0,
        le=1
    )

    formula_quality_score: float = Field(
        description=(
            "Quality of LaTeX formulas (0-1). "
            "Measures: valid LaTeX syntax, variable definitions, mathematical operators"
        ),
        ge=0,
        le=1
    )

    url_completeness: float = Field(
        default=0.0,
        description=(
            "URL extraction completeness (0-1). "
            "Weighted: 0.25*ArXiv + 0.25*DOI + 0.30*GitHub + 0.20*HuggingFace"
        ),
        ge=0,
        le=1
    )

    issues_found: List[str] = Field(
        description="Specific issues identified during validation"
    )

    strengths: List[str] = Field(
        description="Strengths of the extraction (high-quality aspects)"
    )

    requires_human_review: bool = Field(
        description="Whether human review is recommended"
    )

    review_reason: str = Field(
        description="Detailed rationale for human review recommendation"
    )


# ============================================================================
# AGGREGATED METADATA MODEL (Unifies API + LLM Extraction)
# ============================================================================

class AggregatedPaperMetadata(BaseModel):
    """
    Unified paper metadata aggregated from multiple sources.

    Combines data from:
    - Semantic Scholar API
    - arXiv API
    - Unpaywall API  
    - Crossref API
    - LLM-based extraction from full text

    Serves as the comprehensive metadata object throughout the pipeline.
    """
    # ========== Identifiers ==========
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    s2_paper_id: Optional[str] = None
    corpus_id: Optional[int] = None

    # ========== Core Metadata ==========
    title: str
    authors: List[str] = []  # Normalized format: "Last, First" or "Full Name"
    year: Optional[int] = None
    abstract: Optional[str] = None

    # ========== Publication Venue ==========
    venue: Optional[str] = None
    venue_type: Optional[str] = None  # 'conference', 'journal', 'workshop', etc.
    publisher: Optional[str] = None
    journal: Optional[str] = None

    # ========== URLs (Paper Access) ==========
    paper_url: Optional[str] = None  # Primary landing page
    arxiv_url: Optional[str] = None
    pdf_url: Optional[str] = None
    s2_url: Optional[str] = None
    doi_url: Optional[str] = None

    # ========== Repository URLs (Code & Data) ==========
    github_url: Optional[str] = None
    huggingface_url: Optional[str] = None
    kaggle_url: Optional[str] = None
    dataset_url: Optional[str] = None
    demo_url: Optional[str] = None

    # ========== Impact Metrics ==========
    citation_count: int = 0
    reference_count: int = 0
    influential_citation_count: int = 0

    # ========== Open Access Status ==========
    is_open_access: bool = False
    oa_status: Optional[str] = None  # 'gold', 'green', 'hybrid', 'bronze', 'closed'
    oa_pdf_url: Optional[str] = None
    license: Optional[str] = None

    # ========== Fields of Study ==========
    fields_of_study: List[str] = []
    primary_category: Optional[str] = None  # arXiv primary category

    # ========== Dates ==========
    publication_date: Optional[str] = None
    updated_date: Optional[str] = None

    # ========== Source Tracking ==========
    data_sources: List[str] = []  # e.g., ['semantic_scholar', 'arxiv', 'unpaywall']
    api_query_timestamp: Optional[datetime] = None

    # ========== Quality Flags ==========
    has_abstract: bool = False
    has_full_text_access: bool = False
    metadata_completeness_score: float = 0.0  # 0-1 scale

    class Config:
        extra = "allow"  # Allow additional fields from APIs