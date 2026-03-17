"""
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025-2026 AISafetyBenchExplorer Contributors

Enhanced Paper Metadata Extractor with Multi-Pass Extraction
=============================================================

MAJOR IMPROVEMENTS:
1. Multi-pass extraction with iterative refinement
2. Formula-specific extraction pass for evaluation metrics
3. Few-shot prompting for better structured output
4. Enhanced validation and quality scoring
5. Targeted extraction for missing fields

"""

import os
import sys
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json

import instructor
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from models import BenchmarkMetadata, QualityAssessment, URLExtraction, EvaluationMetric
from chunker import LaTeXAwareChunker

logger = logging.getLogger(__name__)


FEW_SHOT_METRIC_EXAMPLES = """
EXAMPLE 1 - Attack Success Rate:
metric_name: "Attack Success Rate (ASR)"
mathematical_definition: "\\[ASR = \\frac{1}{N} \\sum_{i=1}^{N} \\mathbb{1}[\\text{harmful}(r_i)]\\] where \\(N\\) is total prompts, \\(r_i\\) is LLM response to adversarial prompt \\(i\\), and \\(\\mathbb{1}[\\cdot]\\) is indicator function (1 if response harmful, 0 otherwise)."
conceptual_description: "ASR measures proportion of adversarial prompts that successfully elicit harmful responses. 
Task type: adversarial safety evaluation. 
Data type: jailbreak prompts. 
Safety dimension: toxicity/harmful content. 
Intent: quantify jailbreak vulnerability. 
Judge: GPT-4 binary classifier."
methodological_details: 
"1) Generate N=500 adversarial prompts using GCG algorithm. 
2) Query target LLM. 
3) GPT-4 (temp=0) judges each response via 5-point rubric (0=safe, 4=extreme harm).
4) Responses scoring >=3 labeled harmful. 
5) ASR = (# harmful responses) / N. 
6) Report macro-average across 12 harm categories."

EXAMPLE 2 - Hallucination Rate:
metric_name: "Hallucination Rate"
mathematical_definition: "\\[HR = \\frac{|\\{r \\in R : \\text{hallucinated}(r, C)\\}|}{|R|}\\] where \\(R\\) is set of LLM responses, \\(C\\) is reference context, and \\(\\text{hallucinated}(r, C)\\) returns true if response \\(r\\) contains claims not supported by \\(C\\)."
conceptual_description: "HR quantifies factual inconsistency in generated text. 
Task type: factuality evaluation in RAG systems. 
Data type: question-answering over documents. 
Safety dimension: truthfulness. 
Intent: measure grounding accuracy. 
Judge: rule-based NLI model (RoBERTa-large fine-tuned on ANLI)."
methodological_details: 
"1) Extract 100 claims from each LLM response via dependency parsing. 
2) For each claim, retrieve top-3 most similar sentences from source context using sentence-BERT. 
3) Run NLI model: entailment (score=1), neutral (score=0.5), contradiction (score=0). 
4) Claim is hallucinated if NLI score < 0.5. 
5) HR = (# hallucinated claims) / (total claims). 
6) Macro-average across 5 document domains."

EXAMPLE 3 - F1 Score:
metric_name: "F1 Score"
mathematical_definition: "\\[F1 = 2 \\cdot \\frac{\\text{Precision} \\cdot \\text{Recall}}{\\text{Precision} + \\text{Recall}} = \\frac{2TP}{2TP + FP + FN}\\] where \\(TP\\)=True Positives, \\(FP\\)=False Positives, \\(FN\\)=False Negatives."
conceptual_description: "F1 score is harmonic mean of precision and recall. 
Task type: binary/multi-class classification. 
Data type: labeled instances. 
Safety dimension: detection accuracy. 
Intent: balance false positives and false negatives. 
Judge: comparison with ground-truth labels."
methodological_details: 
"1) For each test instance, predict label. 
2) Compare prediction with ground-truth. 
3) Compute TP, FP, FN, TN. 
4) Calculate Precision = TP/(TP+FP) and Recall = TP/(TP+FN). 
5) F1 = harmonic mean. 
6) For multi-class: compute per-class F1, then macro-average (unweighted mean) or micro-average (pool predictions first)."

NOW EXTRACT METRICS FROM THE PAPER BELOW FOLLOWING THIS FORMAT:
"""

class TaskTypeValidator:
    """
    Validate task types against approved taxonomy.
    Ensures all task types are in approved list.
    """

    APPROVED_TYPES = {
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
        'Capabilities', 'Language',
    }

    def validate(self, task_types: List[str]) -> List[str]:
        """Validate and normalize task types"""
        validated = []

        for task_type in task_types:
            # Direct match
            if task_type in self.APPROVED_TYPES:
                validated.append(task_type)
                continue

            # Case-insensitive match
            matched = False
            for approved in self.APPROVED_TYPES:
                if task_type.lower() == approved.lower():
                    validated.append(approved)
                    matched = True
                    break

            if not matched:
                # Try semantic match
                semantic_match = self._semantic_match(task_type)
                if semantic_match:
                    logger.warning(f"Mapped '{task_type}'  '{semantic_match}'")
                    validated.append(semantic_match)
                else:
                    logger.warning(f"Unknown task type: '{task_type}'")

        if not validated:
            logger.warning("No valid task types, defaulting to 'Safety'")
            validated = ["Safety"]

        return validated

    def _semantic_match(self, task_type: str) -> Optional[str]:
        """Attempt semantic mapping for unknown types"""
        mappings = {
            'hallucination detection': 'Hallucination',
            'fact verification': 'Factuality',
            'truthfulness': 'Truthfulness',
            'stereotype bias': 'Stereotype',
            'gender bias': 'Bias',
            'rag hallucination': 'Hallucination',
            'retrieval augmented': 'Factuality',
            'hurtful completions': 'Harmfulness',
            'jailbreaking': 'Jailbreak',
            'red teaming': 'Red Teaming',
        }

        task_lower = task_type.lower()
        for pattern, official_type in mappings.items():
            if pattern in task_lower:
                return official_type

        return None

class URLValidator:
    """Validate extracted URLs relate to actual benchmarks"""

    def validate_urls(self, urls_dict: Dict, benchmark_name: str) -> Dict:
        """Validate all extracted URLs"""
        validated = {
            'arxiv_url': '',
            'github_url': '',
            'huggingface_url': '',
            'kaggle_url': '',
            'doi_url': '',
            'demo_url': ''
        }

        bench_normalized = (
            benchmark_name.lower()
            .replace('-', '').replace('_', '').replace(' ', '')
        )

        for url_type, url_value in urls_dict.items():
            if not url_value or not url_value.startswith('http'):
                continue

            if 'github.com' in url_value:
                if self._validate_github_url(url_value, bench_normalized, benchmark_name):
                    validated['github_url'] = url_value
            elif 'huggingface.co' in url_value:
                if self._validate_huggingface_url(url_value, bench_normalized, benchmark_name):
                    validated['huggingface_url'] = url_value
            elif 'kaggle.com' in url_value:
                if self._validate_kaggle_url(url_value, bench_normalized, benchmark_name):
                    validated['kaggle_url'] = url_value
            elif 'arxiv.org' in url_value:
                validated['arxiv_url'] = url_value
            elif 'doi.org' in url_value:
                validated['doi_url'] = url_value
            else:
                if 'demo' in url_type.lower():
                    validated['demo_url'] = url_value

        return validated

    def _validate_github_url(self, url: str, bench_normalized: str, benchmark_name: str) -> bool:
        """Validate GitHub URL matches benchmark"""
        try:
            parts = url.strip('/').split('/')
            repo_name = parts[-1].lower().replace('-', '').replace('_', '')

            if bench_normalized in repo_name or repo_name in bench_normalized:
                return True

            if 'dataset' in repo_name or 'benchmark' in repo_name:
                return True

            logger.warning(f"GitHub '{repo_name}' doesn't match '{benchmark_name}'")
            return False
        except:
            return False

    def _validate_huggingface_url(self, url: str, bench_normalized: str, benchmark_name: str) -> bool:
        """Validate HuggingFace URL matches benchmark"""
        try:
            dataset_name = url.split('datasets/')[-1].lower() if 'datasets/' in url else url.split('/')[-1].lower()
            dataset_normalized = dataset_name.replace('-', '').replace('_', '')

            if bench_normalized in dataset_normalized or dataset_normalized in bench_normalized:
                return True

            logger.warning(f"HuggingFace '{dataset_name}' doesn't match '{benchmark_name}'")
            return False
        except:
            return False

    def _validate_kaggle_url(self, url: str, bench_normalized: str, benchmark_name: str) -> bool:
        """Validate Kaggle URL matches benchmark"""
        try:
            dataset_name = url.split('datasets/')[-1].lower() if 'datasets/' in url else url.split('/')[-1].lower()
            dataset_normalized = dataset_name.replace('-', '').replace('_', '')

            if bench_normalized in dataset_normalized or dataset_normalized in bench_normalized:
                return True

            logger.warning(f"Kaggle '{dataset_name}' doesn't match '{benchmark_name}'")
            return False
        except:
            return False


class FormulaQualityScorer:
    """Score quality of extracted mathematical formulas"""

    def score_formula_quality(self, metrics: List[EvaluationMetric]) -> float:
        """Score overall formula quality"""
        if not metrics:
            return 0.0

        formula_scores = []
        for metric in metrics:
            if not metric.mathematical_definition:
                formula_scores.append(0.0)
                continue

            score = self._score_single_formula(metric.mathematical_definition)
            formula_scores.append(score)

        return round(sum(formula_scores) / len(formula_scores), 2) if formula_scores else 0.0

    def _score_single_formula(self, formula: str) -> float:
        """Score a single formula"""
        score = 1.0

        # Check LaTeX syntax
        if not self._is_valid_latex(formula):
            score -= 0.3

        # Check variable count
        variables = self._extract_variables(formula)
        if len(variables) < 2:
            score -= 0.4

        # Check math operators
        if not self._has_math_operators(formula):
            score -= 0.3

        # Bonus for proper delimiters
        if self._has_proper_delimiters(formula):
            score = min(1.0, score + 0.05)

        return max(0.0, score)

    def _is_valid_latex(self, formula: str) -> bool:
        """Check LaTeX syntax validity"""
        has_latex = bool(re.search(r'\\[a-zA-Z]+', formula))
        has_math = bool(re.search(r'[+\-*/=<>]', formula))

        if not (has_latex or has_math):
            return False

        if formula.count('{') != formula.count('}'):
            return False

        if formula.count('$') % 2 != 0:
            return False

        return True

    def _extract_variables(self, formula: str) -> set:
        """Extract unique variables"""
        variables = re.findall(r'(?:^|[^\\])([a-zA-Z_]{1,3})', formula)
        return set(variables)

    def _has_math_operators(self, formula: str) -> bool:
        """Check for mathematical operators"""
        operators = [
            '+', '-', '*', '/', '=', '<', '>',
            '', '', '', '',
            r'\sum', r'\int', r'\prod',
            r'\frac', r'\sqrt',
        ]

        for op in operators:
            if op in formula:
                return True

        return False

    def _has_proper_delimiters(self, formula: str) -> bool:
        """Check for proper mathematical delimiters"""
        has_fraction = r'\frac' in formula or '/' in formula
        has_power = '^' in formula
        has_subscript = '_' in formula
        has_summation = r'\sum' in formula or '' in formula

        return any([has_fraction, has_power, has_subscript, has_summation])


class BenchmarkNameExtraction(BaseModel):
    """Simple model for extracting benchmark name"""
    benchmark_name: str

class EnhancedPaperMetadataExtractor:
    """
    Enhanced metadata extractor with multi-pass extraction and validation.

    Key Features:
    - Multi-pass extraction with iterative refinement
    - Formula-specific extraction pass
    - Few-shot prompting for better outputs
    - Targeted extraction for missing fields
    - Enhanced validation and quality scoring
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:32b",
        validation_model: str = "qwen2.5:14b",
        backend: str = "ollama",
        api_key: Optional[str] = None,
        chunker: Optional[LaTeXAwareChunker] = None
    ):
        """
        Initialize extractor with LLM backend.

        Args:
            model_name: Main extraction model
            validation_model: Validation model (can be smaller/faster)
            backend: 'ollama' or 'openai'
            api_key: API key (for OpenAI backend)
            chunker: LaTeX-aware chunker instance
        """
        self.backend = backend
        self.model_name = model_name
        self.validation_model = validation_model
        self.chunker = chunker or LaTeXAwareChunker()

        # Initialize validators and scorers
        self.task_validator = TaskTypeValidator()
        self.url_validator = URLValidator()
        self.formula_scorer = FormulaQualityScorer()

        # Initialize LLM client
        if backend == "openai":
            base_client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            self.raw_client = base_client
            self.client = instructor.from_openai(base_client)
            logger.info(f"OpenAI backend: {model_name}")
        else:
            base_client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")
            self.raw_client = base_client
            self.client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
            self._ensure_model_available(model_name)
            self._ensure_model_available(validation_model)
            logger.info(f"Ollama backend: {model_name}, {validation_model}")

    def _ensure_model_available(self, model_name: str) -> None:
        """Ensure Ollama model is available"""
        import requests

        try:
            response = requests.post(
                "http://127.0.0.1:11434/api/show",
                json={"name": model_name},
                timeout=5
            )

            if response.status_code == 200:
                logger.info(f"  Model {model_name} loaded")
                return

            logger.info(f"Pulling {model_name}...")
            pull_response = requests.post(
                "http://127.0.0.1:11434/api/pull",
                json={"name": model_name},
                timeout=600
            )

            if pull_response.status_code != 200:
                raise RuntimeError(f"Failed to pull model {model_name}")

            logger.info(f"Model {model_name} ready")

        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            raise RuntimeError("Ollama server not running. Start with: ollama serve")

    def select_relevant_chunks(self, text: str, format_hint: str = "markdown") -> Dict[str, str]:
        """Select relevant chunks using LaTeX-aware chunker"""
        try:
            return self.chunker.chunk_document(text, format_hint)
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            return {
                'title': text[:200],
                'abstract': text[200:3000],
                'title_and_abstract': text[:3000],
                'methodology': text[3000:15000],
                'evaluation_metrics': text[10000:25000],
                'experiments': text[20000:35000],
                'references': text[-5000:],
                'fulltext': text
            }

    def extract_with_multi_pass(
        self,
        sections: Dict[str, str],
        urls: URLExtraction,
        benchmark_name: str,
        format_hint: str,
        formulas: List[str],
        num_passes: int = 2,
        grobid_metadata: Optional[Dict] = None
    ) -> Optional[BenchmarkMetadata]:
        """
        Multi-pass extraction with iterative refinement.

        Pass 1: Initial extraction with full context
        Pass 2: Fill missing fields + validate existing
        Pass 3: Formula-specific extraction (if needed)

        Args:
            sections: Chunked paper sections
            urls: Pre-extracted URLs
            benchmark_name: Benchmark name
            format_hint: 'latex', 'markdown', or 'text'
            formulas: Extracted mathematical formulas
            num_passes: Number of extraction passes (1-3)
            grobid_metadata: GROBID-extracted metadata (optional)

        Returns:
            BenchmarkMetadata object or None
        """
        logger.info("=" * 70)
        logger.info("MULTI-PASS EXTRACTION STARTING")
        logger.info("=" * 70)

        # PASS 1: Initial extraction
        logger.info("Pass 1: Initial comprehensive extraction")
        result = self.extract_with_cot(
            sections=sections,
            urls=urls,
            benchmark_name=benchmark_name,
            format_hint=format_hint,
            formulas=formulas,
            grobid_metadata=grobid_metadata
        )

        if not result:
            logger.error("Pass 1 failed completely")
            return None

        self._log_extraction_status(result, pass_num=1)

        if num_passes == 1:
            return result

        # PASS 2: Fill gaps and validate
        if num_passes >= 2:
            logger.info("Pass 2: Filling gaps and validating")
            missing_fields = self._identify_missing_fields(result)

            if missing_fields:
                logger.info(f"Missing fields: {', '.join(missing_fields)}")
                refined_result = self._targeted_extraction(
                    sections=sections,
                    existing_result=result,
                    missing_fields=missing_fields,
                    formulas=formulas
                )
                result = self._merge_extraction_results(result, refined_result)
                self._log_extraction_status(result, pass_num=2)
            else:
                logger.info("All fields complete after Pass 1")

        # PASS 3: Formula-specific extraction (if metrics still incomplete)
        if num_passes >= 3:
            incomplete_metrics = self._check_metric_completeness(result)
            if incomplete_metrics:
                logger.info("Pass 3: Formula-specific extraction for metrics")
                formula_metrics = self.extract_formulas_with_context(sections, benchmark_name)
                if formula_metrics:
                    result = self._merge_metrics(result, formula_metrics)
                    self._log_extraction_status(result, pass_num=3)

        logger.info("=" * 70)
        logger.info("MULTI-PASS EXTRACTION COMPLETE")
        logger.info("=" * 70)

        return result

    def extract_with_cot(
        self,
        sections: Dict[str, str],
        urls: URLExtraction,
        benchmark_name: str,
        format_hint: str,
        formulas: List[str],
        grobid_metadata: Optional[Dict] = None
    ) -> Optional[BenchmarkMetadata]:
        """
        Extract metadata with chain-of-thought prompting and few-shot examples.
        """
        # Build context section
        formula_section = ""
        if formulas:
            formula_section = f"""
            FORMULAS FOUND ({len(formulas)} total):
            {chr(10).join(f"  {i+1}. {formula[:100]}" for i, formula in enumerate(formulas[:10]))}
            """

        format_note = ""
        if format_hint == "latex":
            format_note = """
        **FORMAT NOTE:** This paper is in LaTeX format.
        - Math formulas are in LaTeX notation (extract as-is)
        - Section structure uses \\section{}, \\subsection{}
        - URLs may be in \\url{} or \\href{} commands
        """

        # Include GROBID metadata if available
        grobid_section = ""
        if grobid_metadata and grobid_metadata.get('title'):
            grobid_section = f"""
            PRE-EXTRACTED METADATA (from GROBID):
            - Title: {grobid_metadata.get('title', '')}
            - Authors: {', '.join(grobid_metadata.get('authors', [])[:5])}
            - Abstract: {grobid_metadata.get('abstract', '')[:200]}...
            """

        # Build comprehensive extraction prompt with few-shot examples
        cot_prompt = f"""{FEW_SHOT_METRIC_EXAMPLES}

        EXTRACTION TASK:
        Extract AI safety benchmark metadata for AISafetyBenchExplorer template.

        PRE-EXTRACTED INFORMATION:
        - Benchmark Name: {benchmark_name}
        - ArXiv URL: {urls.arxiv_url or "NOT FOUND"}
        - GitHub Repository: {urls.github_url or "NOT FOUND"}
        - HuggingFace Repository: {urls.huggingface_url or "NOT FOUND"}
        - Kaggle Dataset: {urls.kaggle_url or "NOT FOUND"}

        {grobid_section}
        {format_note}
        {formula_section}

        REQUIRED FIELDS (use snake_case):
        1. benchmark_name: "{benchmark_name}"
        2. paper_title: Complete official title
        3. urls: Use pre-extracted URLExtraction above
        4. task_types: All task categories from approved taxonomy
        5. dataset_size: Total number of test examples
        6. evaluation_metrics: See detailed requirements below

        EVALUATION METRICS - 6 MANDATORY FIELDS PER METRIC:

        For EACH metric, extract ALL 6 fields as shown in examples above:

        1. metric_name: Exact name from paper
        2. mathematical_definition: LaTeX formula with all variables defined
        3. conceptual_description: 2-4 sentences covering task type, data type, safety dimension, intent, judge type
        4. methodological_details: Step-by-step computation with: (a) Event definitions, (b) Label sources, (c) Multi-turn handling, (d) Category/instance handling, (e) Aggregation method
        5. differences_from_standard_definition: How it differs from standard definitions
        6. notes: Assumptions, limitations, use cases

        CRITICAL: For mathematical_definition, if formula exists in FORMULAS section above, reproduce it EXACTLY.

        PAPER SECTIONS:
        TITLE & ABSTRACT:
        {sections.get('title_and_abstract', '')[:2000]}

        METHODOLOGY:
        {sections.get('methodology', '')[:3000]}

        EVALUATION METRICS:
        {sections.get('evaluation_metrics', '')[:4000]}

        EXPERIMENTS:
        {sections.get('experiments', '')[:2000]}

        Extract complete metadata with ALL fields filled. For evaluation metrics, ensure mathematical formulas are in proper LaTeX format.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_model=BenchmarkMetadata,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting AI safety benchmark metadata with mathematical precision."},
                    {"role": "user", "content": cot_prompt}
                ],
                temperature=0.1,  # Low temperature for factual extraction
                max_retries=3
            )

            # Validate and normalize
            response.task_types = self.task_validator.validate(response.task_types)

            return response

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return None

    def extract_formulas_with_context(
        self,
        sections: Dict[str, str],
        benchmark_name: str
    ) -> List[EvaluationMetric]:
        """
        Dedicated pass to extract evaluation metrics WITH formulas.
        Uses formula context to guide LLM.
        """
        logger.info("Starting formula-specific extraction pass...")

        # Extract formulas with context
        formula_contexts = self._extract_formula_contexts(
            sections.get('evaluation_metrics', '') + '\n\n' + sections.get('methodology', '')
        )

        if not formula_contexts:
            logger.warning("No formulas found for dedicated extraction")
            return []

        formula_prompt = f"""
        Extract ALL evaluation metrics from {benchmark_name} with their mathematical formulas.

        DETECTED FORMULAS WITH CONTEXT:
        {chr(10).join(f"Formula {i+1}:{chr(10)}{ctx}{chr(10)}" for i, ctx in enumerate(formula_contexts))}

        For EACH formula above, extract:
        1. metric_name: Name of the metric
        2. mathematical_definition: The LaTeX formula (reproduce EXACTLY as shown)
        3. conceptual_description: What does this metric measure? (2-3 sentences)
        4. methodological_details: How is it computed step-by-step?
        5. differences_from_standard_definition: Any modifications?
        6. notes: Assumptions, limitations, use cases

        Extract ALL metrics with complete information.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_model=List[EvaluationMetric],
                messages=[
                    {"role": "system", "content": "You are an expert at extracting evaluation metrics with mathematical formulas."},
                    {"role": "user", "content": formula_prompt}
                ],
                temperature=0.0,  # Zero temperature for formula accuracy
                max_retries=2
            )

            logger.info(f"Formula extraction: {len(response)} metrics")
            return response

        except Exception as e:
            logger.error(f"Formula extraction failed: {e}")
            return []

    def _extract_formula_contexts(self, text: str, context_window: int = 300) -> List[str]:
        """Extract formulas with surrounding context"""
        contexts = []

        # LaTeX formula patterns
        formula_patterns = [
            (r'\\\[(.*?)\\\]', re.DOTALL),  # Display math
            (r'\\\((.*?)\\\)', 0),  # Inline math
            (r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', re.DOTALL),
            (r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}', re.DOTALL)
        ]

        for pattern, flags in formula_patterns:
            for match in re.finditer(pattern, text, flags):
                start_pos = max(0, match.start() - context_window)
                end_pos = min(len(text), match.end() + context_window)
                context = text[start_pos:end_pos]
                contexts.append(context)

        return contexts[:20]  # Limit to top 20

    def _identify_missing_fields(self, result: BenchmarkMetadata) -> List[str]:
        """Identify fields that are missing or incomplete"""
        missing = []

        # Check evaluation metrics
        if not result.evaluation_metrics or len(result.evaluation_metrics) == 0:
            missing.append("evaluation_metrics")
        else:
            for i, metric in enumerate(result.evaluation_metrics):
                if not metric.mathematical_definition or len(metric.mathematical_definition) < 10:
                    missing.append(f"metric_{metric.metric_name}_formula")
                if not metric.methodological_details or len(metric.methodological_details) < 50:
                    missing.append(f"metric_{metric.metric_name}_methodology")

        # Check dataset size
        if not result.dataset_size or result.dataset_size == 0:
            missing.append("dataset_size")

        # Check task types
        if not result.task_types or len(result.task_types) == 0:
            missing.append("task_types")

        return missing

    def _targeted_extraction(self, sections: Dict[str, str], existing_result: BenchmarkMetadata, missing_fields: List[str], formulas: List[str]) -> BenchmarkMetadata:
        """Targeted extraction focusing on missing fields only"""

        focused_prompt = f"""
        You previously extracted metadata for {existing_result.benchmark_name}.
        However, the following fields are INCOMPLETE or MISSING:

        {chr(10).join(f"- {field}" for field in missing_fields)}

        Your task: Extract ONLY these missing fields from the paper sections below.

        CRITICAL REQUIREMENTS:
        - For evaluation metrics: Include complete mathematical_definition with LaTeX formulas
        - For methodological_details: Provide step-by-step computation details
        - For dataset_size: Extract exact number from paper

        FORMULAS FOUND IN PAPER:
        {chr(10).join(f"{i+1}. {formula[:150]}" for i, formula in enumerate(formulas[:10]))}

        SECTIONS:
        METHODOLOGY:
        {sections.get('methodology', '')[:3000]}

        EVALUATION:
        {sections.get('evaluation_metrics', '')[:3000]}

        EXPERIMENTS:
        {sections.get('experiments', '')[:2000]}

        Extract with maximum detail for the missing fields listed above.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_model=BenchmarkMetadata,
                messages=[
                    {"role": "system", "content": "You are filling in missing metadata fields."},
                    {"role": "user", "content": focused_prompt}
                ],
                temperature=0.1,
                max_retries=2
            )
            return response
        except Exception as e:
            logger.error(f"Targeted extraction failed: {e}")
            return existing_result

    def _merge_extraction_results(self, initial: BenchmarkMetadata, refined: BenchmarkMetadata) -> BenchmarkMetadata:
        """Merge two extraction results, preferring more complete data"""

        # Merge metrics: combine and deduplicate
        merged_metrics = {m.metric_name: m for m in initial.evaluation_metrics}

        for metric in refined.evaluation_metrics:
            if metric.metric_name in merged_metrics:
                existing = merged_metrics[metric.metric_name]
                # Prefer refined if more complete
                if len(metric.mathematical_definition) > len(existing.mathematical_definition):
                    merged_metrics[metric.metric_name] = metric
                elif len(metric.methodological_details) > len(existing.methodological_details):
                    # Update methodology while keeping formula
                    existing.methodological_details = metric.methodological_details
            else:
                merged_metrics[metric.metric_name] = metric

        initial.evaluation_metrics = list(merged_metrics.values())

        # Fill other missing fields
        if not initial.dataset_size and refined.dataset_size:
            initial.dataset_size = refined.dataset_size

        if not initial.task_types and refined.task_types:
            initial.task_types = refined.task_types
        elif refined.task_types:
            # Merge task types
            initial.task_types = list(set(initial.task_types + refined.task_types))

        return initial

    def _merge_metrics(self, result: BenchmarkMetadata, formula_metrics: List[EvaluationMetric]) -> BenchmarkMetadata:
        """Merge formula-extracted metrics into main result"""

        metric_dict = {m.metric_name: m for m in result.evaluation_metrics}

        for fm in formula_metrics:
            if fm.metric_name in metric_dict:
                # Update existing metric with better formula
                if len(fm.mathematical_definition) > len(metric_dict[fm.metric_name].mathematical_definition):
                    metric_dict[fm.metric_name].mathematical_definition = fm.mathematical_definition
            else:
                # Add new metric
                metric_dict[fm.metric_name] = fm

        result.evaluation_metrics = list(metric_dict.values())
        return result

    def _check_metric_completeness(self, result: BenchmarkMetadata) -> List[str]:
        """Check which metrics have incomplete formulas"""
        incomplete = []

        for metric in result.evaluation_metrics:
            if not metric.mathematical_definition or len(metric.mathematical_definition) < 10:
                incomplete.append(metric.metric_name)

        return incomplete

    def _log_extraction_status(self, result: BenchmarkMetadata, pass_num: int):
        """Log current extraction status"""
        num_metrics = len(result.evaluation_metrics)
        metrics_with_formulas = sum(
            1 for m in result.evaluation_metrics
            if m.mathematical_definition and len(m.mathematical_definition) > 10
        )

        logger.info(f"Pass {pass_num} Status:")
        logger.info(f"Benchmark: {result.benchmark_name}")
        logger.info(f"Metrics: {num_metrics} ({metrics_with_formulas} with formulas)")
        logger.info(f"Dataset Size: {result.dataset_size if result.dataset_size else 'MISSING'}")
        logger.info(f"Task Types: {len(result.task_types)}")

    def _extract_benchmark_name_dedicated(self, title: str, abstract: str, full_text: str = "") -> str:
        """Enhanced benchmark name extraction"""
        intro_text = f"{title}\n\n{abstract}"[:1500]

        name_prompt = f"""Extract the benchmark name from this AI safety paper.

        **CHARACTERISTICS:**
        - Often an acronym (MALT, SGBench, HONEST, RippleBench, BOLD, Scruples)
        - Appears in title or early in abstract
        - Short (1-3 words)

        **TEXT:**
        {intro_text}

        Extract ONLY the benchmark name (no explanation).
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_model=BenchmarkNameExtraction,
                messages=[
                    {"role": "system", "content": "Extract benchmark names from papers."},
                    {"role": "user", "content": name_prompt}
                ],
                temperature=0.0,
                max_retries=2
            )

            name = response.benchmark_name.strip()
            name = name.replace('"', '').replace("'", '').replace('`', '')
            name = re.sub(r'^(?:The\s+)?Benchmark\s+Name:\s*', '', name, flags=re.IGNORECASE)

            if name.lower() not in ['unknown', 'benchmark', 'dataset', 'n/a', '']:
                logger.info(f"LLM extracted benchmark name: {name}")
                return name

        except Exception as e:
            logger.warning(f"LLM benchmark extraction failed: {e}")

        return self._regex_benchmark_name_extraction(title, intro_text)

    def align_to_template_format(self, metadata: BenchmarkMetadata) -> Dict[str, Any]:
        """
        Convert BenchmarkMetadata object to template-compatible dictionary.

        Args:
            metadata: Extracted BenchmarkMetadata object

        Returns:
            Dictionary aligned with AISafetyBenchExplorer template
        """
        # Convert evaluation metrics to dict format
        metrics_list = []
        if metadata.evaluation_metrics:
            for metric in metadata.evaluation_metrics:
                metrics_list.append({
                    "Metric Name": metric.metric_name or "",
                    "Mathematical Definition": metric.mathematical_definition or "",
                    "Conceptual Description": metric.conceptual_description or "",
                    "Methodological Details": metric.methodological_details or "",
                    "Differences from Standard": metric.differences_from_standard_definition or "",
                    "Notes": metric.notes or ""
                })

        # Build template-aligned dictionary using ONLY BenchmarkMetadata fields
        template_dict = {
            "Benchmark Name": metadata.benchmark_name or "",
            "Paper Title": metadata.paper_title or "",
            "Paper Link": metadata.urls.arxiv_url if metadata.urls else "",
            "Code Repository": metadata.urls.github_url if metadata.urls else "",
            "Dataset Repository": metadata.urls.huggingface_url or (metadata.urls.kaggle_url if metadata.urls else ""),
            "Task Types": ", ".join(metadata.task_types) if metadata.task_types else "",
            "Dataset Size": str(metadata.dataset_size) if metadata.dataset_size else "",
            "Evaluation Metrics": metrics_list,
            "Complexity": metadata.complexity_level or "Unknown"
        }

        return template_dict

    def _regex_benchmark_name_extraction(self, title: str, intro_text: str) -> str:
        """Regex-based name extraction fallback"""
        # Try acronym in title
        match = re.search(r'\b([A-Z]{3,}(?:-[A-Z]+)?)\b', title)
        if match:
            candidate = match.group(1)
            if candidate not in ['PDF', 'HTTP', 'LLM', 'NLP', 'GPT', 'API', 'BERT']:
                return candidate

        # Try CamelCase
        match = re.search(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', title)
        if match:
            return match.group(1)

        # Try after colon
        match = re.search(r':\s*([A-Z][A-Za-z0-9]+)\b', title)
        if match:
            return match.group(1)

        return "Unknown"