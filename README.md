## License
- **Code** (`*.py`, `requirements*.txt`): [Apache License 2.0](LICENSE-CODE)
- **Data & Documentation** (`*.xlsx`, `*.md`): [CC-BY 4.0](LICENSE-DATA)

# AISafetyBenchExplorer

> **A living catalogue of AI safety benchmarks and a multi-modal extraction pipeline for structured metadata, evaluation metrics, and complexity classification.**

---

## Project Overview

AISafetyBenchExplorer is an open research tool that maintains a structured, annotated catalogue of **182+ AI safety benchmarks** for Large Language Models (LLMs). It provides:

1. **An Excel catalogue** (`AISafetyBenchExplorer.xlsx`) — two-sheet workbook covering benchmark metadata (Sheet 1) and evaluation metrics (Sheet 2), plus a dashboard with use-case quick filters.
2. **A DOI-based Python extraction pipeline** — resolves DOIs/arXiv IDs against multiple scholarly APIs and uses an LLM to extract structured metadata.
3. **An AI extraction master prompt** (`AISafety_Benchmark_Extraction_Master_Prompt.md`) — a reusable prompt (v1.1) for AI agents to extract metadata into the Excel template with full quality-assurance checks.
4. **A complexity classification methodology** (`complexity-methodology.md`) — decision-tree rules for classifying benchmarks as `Popular`, `High`, `Medium`, or `Low` complexity.

---

## Repository Structure

```
AISAFETYBENCHEXPLORER/
├── AISafetyBenchExplorer.xlsx               # Master catalogue (182+ benchmarks)
├── safety-benchmarks-eval-metrics-catalogue.xlsx  # Evaluation metrics catalogue
├── AISafety_Benchmark_Extraction_Master_Prompt.md # AI extraction master prompt (v1.1)
├── complexity-methodology.md                # Complexity classification methodology
├── README.md                                # This file
├── requirements_doi_pipeline.txt            # Python dependencies
│
├── api_models.py          # Pydantic models for API responses (~230 lines)
├── doi_based_resolver.py  # Multi-API metadata aggregator (~535 lines)
├── doi_pipeline.py        # DOI → extraction orchestrator (~537 lines)
├── doi_extractor_cli.py   # Command-line interface (~380 lines)
│
├── models.py                  # Shared Pydantic models for benchmark metadata
├── enhanced_mainExtractor.py  # LLM-based structured metadata extractor
├── enhanced_pdf_parser.py     # PDF → Markdown conversion (multi-backend)
├── latex_aware_chunker.py     # LaTeX-aware text chunker for long papers
└── integrated_paperParser.py  # Original PDF-based pipeline (still supported)
```

**Total pipeline code:** ~1,700 lines of production-ready Python.

---

## The Excel Catalogue

### Sheet 1 — Safety Evaluation Benchmarks

Each row captures one benchmark across **22 columns**:

| Column | Description |
|--------|-------------|
| Benchmark Name | Short canonical name (e.g., `HarmBench`, `TruthfulQA`) |
| Task Type | Controlled vocabulary (e.g., `Safety`, `Jailbreak`, `Bias`) |
| Benchmark Paper Title | Full verbatim paper title |
| Release | Month-Year of first public release |
| Description | 3–5 sentence synthesis of purpose and innovation |
| Code / Dataset | `Yes` / `No` with verified URL |
| No. of Samples | Integer with units (e.g., `10,166 conversations`) |
| Created By | `Human`, `Machine`, or `Hybrid` |
| Entry Modalities | Data format (e.g., `Prompts`, `Conversations`, `MCQ`) |
| Dev Purpose | `Eval`, `Train`, or `Train & Eval` |
| License | SPDX identifier (e.g., `MIT`, `Apache-2.0`, `CC-BY-4.0`) |
| Evaluation Metrics | Comma-separated; every metric must have a Sheet 2 row |
| Complexity Level | `Popular` / `High` / `Medium` / `Low` + justification |
| Language Support | ISO 639-1 codes or `Multilingual` |
| Integration Option | `API`, `Export`, `API & Export`, or `NA` |
| Citation Range | Banded integer (e.g., `101–500`) |
| Cited By | Live integer from Semantic Scholar at extraction date |
| Code Repository | Verified GitHub or HuggingFace URL |
| Dataset Repository | Verified HuggingFace or canonical dataset URL |
| Benchmark Paper | Full verbatim title (duplicate for cross-reference) |
| Paper Link | Canonical DOI or arXiv URL |

### Sheet 2 — Evaluation Metrics Catalogue

One row per metric, with **9 columns**:

`benchmark_name` · `paper_title` · `paper_link` · `metric_name` · `conceptual_description` · `methodological_details` · `mathematical_definition` · `differences_from_standard_definition` · `notes`

All metrics use **LaTeX display notation** for `mathematical_definition` with every symbol defined inline.

### Dashboard

- **Use-Case Quick Filter** — tags each benchmark with 1–3 use cases (Medical AI, Financial Services, Content Moderation, Education, General Purpose).
- **Research Gap Heatmap** — colour-coded view of coverage gaps by task type and complexity level.
- **Repository Activity Statistics** — GitHub stars, commit recency, and activity status for 148 benchmarks.

---

## Extraction Pipelines

### Pipeline A — DOI-Based Python Pipeline (Recommended)

The primary automated pipeline resolves a DOI or arXiv ID through four scholarly APIs, optionally fetches the full text, and uses an LLM with structured output to populate the Excel template.

```
DOI / arXiv ID
      │
      ▼
┌─────────────────────────────────────────────┐
│         doi_based_resolver.py               │
│  1. Semantic Scholar  (authors, citations,  │
│     venue, OA status, abstract)             │
│  2. arXiv API         (preprint metadata,   │
│     LaTeX source, PDF link)                 │
│  3. Unpaywall         (OA PDF, license)     │
│  4. Crossref          (DOI resolution,      │
│     publisher, references)                  │
└───────────────┬─────────────────────────────┘
                │  AggregatedMetadata object
                ▼
┌─────────────────────────────────────────────┐
│  [Optional] enhanced_pdf_parser.py          │
│  PDF → Markdown via PyMuPDF / marker-pdf /  │
│  nougat-ocr  →  latex_aware_chunker.py      │
└───────────────┬─────────────────────────────┘
                │  text chunks + format hint
                ▼
┌─────────────────────────────────────────────┐
│  enhanced_mainExtractor.py                  │
│  LLM extraction (instructor + OpenAI or     │
│  Ollama) guided by API metadata context     │
│  → cross-validated against API values       │
└───────────────┬─────────────────────────────┘
                │  extracted dict + quality scores
                ▼
┌─────────────────────────────────────────────┐
│  doi_pipeline.py  (orchestrator)            │
│  Writes three output files per paper:       │
│  {doi}_metadata.json  /  _quality.json      │
│  /  _api.json                               │
└─────────────────────────────────────────────┘
```

### Pipeline B — AI Extraction Master Prompt

For manual or agent-assisted extraction from any source (PDF, HTML, or arXiv page), the master prompt (`AISafety_Benchmark_Extraction_Master_Prompt.md`) guides an AI assistant through five phases:

| Phase | Action |
|-------|--------|
| 1 | Extract Sheet 1 metadata using controlled vocabularies |
| 2 | Generate Sheet 2 metric rows with LaTeX formulas |
| 3 | Apply complexity classification decision tree |
| 4 | Run QA checklist (15 Sheet 1 + 6 Sheet 2 + 3 global checks) |
| 5 | Emit `openpyxl`-based Python code and a written summary |

### Pipeline C — PDF-Based Pipeline (Legacy, Still Supported)

The original `integrated_paperParser.py` accepts a local PDF file and uses `enhanced_pdf_parser.py` + `latex_aware_chunker.py` + `enhanced_mainExtractor.py` without any API enrichment.

```
PDF file → enhanced_pdf_parser.py → latex_aware_chunker.py
        → enhanced_mainExtractor.py → metadata dict
```

---

## Complexity Classification

Benchmarks are classified by `complexity-methodology.md` using a strict four-level decision tree applied in order:

| Level | Override Rule | Key Criteria |
|-------|--------------|--------------|
| **Popular** | Overrides all others | ≥100 citations OR cited as baseline in ≥3 safety papers OR community standard (HarmBench, TruthfulQA, MMLU) |
| **High** | If not Popular | ≥2 of: multi-hop reasoning, adversarial/red-teaming, open-ended generation, risk-critical domain, novel metric, complex pipeline, domain-expert annotation, pluralistic annotation (≥50 annotators) |
| **Medium** | If not Popular/High | ≥2 of: 1–2 step reasoning, some adversarial testing, mix of objective/subjective, standard metrics with minor adaptations, moderate annotation effort |
| **Low** | Default | Single-step reasoning, binary/categorical outcomes, standard unmodified metrics, minimal adversarial considerations |

Every complexity value must include a one-sentence justification citing exactly 2 criteria.

---

## Quick Start

### Installation

```bash
git clone https://github.com/spyderweb-abdul/AISAFETYBENCHEXPLORER.git
cd AISAFETYBENCHEXPLORER
pip install -r requirements_doi_pipeline.txt

# Optional: advanced PDF parsers
pip install marker-pdf[full]   # Fast Markdown conversion
pip install nougat-ocr          # Best for math-heavy papers

# Optional: LLM backends
pip install anthropic            # For Claude models
pip install ollama               # For local Ollama models
```

### Environment Variables

```bash
export UNPAYWALL_EMAIL="your@email.com"              # Required for Unpaywall
export SEMANTIC_SCHOLAR_API_KEY="your_s2_key"        # Optional: higher rate limits
export OPENAI_API_KEY="sk-..."                        # For OpenAI backend
# export ANTHROPIC_API_KEY="sk-ant-..."              # For Anthropic backend
```

### Single DOI Extraction

```bash
# Basic (API metadata only, ~5–10 s)
python doi_extractor_cli.py \
    --doi "10.18653/v1/2021.acl-long.330" \
    --email your@email.com

# Full extraction with PDF parsing (~30–60 s)
python doi_extractor_cli.py \
    --doi "10.18653/v1/2021.acl-long.330" \
    --full-text --save-pdfs \
    --email your@email.com

# From arXiv ID
python doi_extractor_cli.py \
    --doi "2103.14296" \
    --email your@email.com
```

### Batch Processing

```bash
# Prepare CSV
echo "DOI,Title" > dois.csv
echo "10.18653/v1/2021.acl-long.330,BOLD" >> dois.csv
echo "2402.04249,HarmBench" >> dois.csv

python doi_extractor_cli.py \
    --batch dois.csv \
    --doi-column DOI \
    --full-text \
    --email your@email.com \
    --output-dir batch_results/
```

### Python API

```python
from doi_pipeline import DOIPipeline
from pathlib import Path

pipeline = DOIPipeline(
    email="your@email.com",
    s2_api_key="optional",
    extractor_model="qwen2.5:32b",   # or "gpt-4o"
    backend="ollama"                  # or "openai"
)

extracted, quality, api_metadata = pipeline.process_from_doi(
    identifier="10.18653/v1/2021.acl-long.330",
    extract_full_text=True,
    save_pdf=True,
    output_dir=Path("outputs/")
)

print(f"Benchmark   : {extracted['Benchmark Name']}")
print(f"Complexity  : {extracted['Complexity Level']}")
print(f"Citations   : {extracted['Citation Count']}")
print(f"Quality     : {quality.overall_score:.2f}")
print(f"Needs review: {quality.requires_human_review}")
```

### Hybrid Mode (DOI + Existing PDF Pipeline)

```python
from doi_based_resolver import DOIMetadataResolver
from enhanced_pdf_parser import parse_pdf_to_markdown
from enhanced_mainExtractor import EnhancedPaperMetadataExtractor

# 1. Enrich from APIs
resolver = DOIMetadataResolver(email="your@email.com")
api_metadata = resolver.resolve("10.18653/v1/2021.acl-long.330")

# 2. Parse local PDF
text, format_hint = parse_pdf_to_markdown("paper.pdf")

# 3. LLM extraction with API context
extractor = EnhancedPaperMetadataExtractor()
extracted, quality = extractor.process_paper(text, format_hint)

# 4. Override with authoritative API values
extracted["Authors"]        = ", ".join(api_metadata.authors)
extracted["Citation Count"] = api_metadata.citation_count
extracted["Venue"]          = api_metadata.venue
extracted["Open Access"]    = "Yes" if api_metadata.is_open_access else "No"
```

---

## API Sources

| API | Primary Use | Rate Limit | Auth Required |
|-----|------------|------------|---------------|
| **Semantic Scholar** | Authors, citations, venue, abstract, OA status | 100 req/5 min (public); 1 req/s (with key) | Optional — [get key](https://www.semanticscholar.org/product/api) |
| **arXiv** | Preprint metadata, PDF links, LaTeX source | 1 req/3 s (polite) | None |
| **Unpaywall** | Legal OA PDF download, license | 100,000 req/day | Email address required |
| **Crossref** | DOI resolution, publisher info, references | Unlimited (polite) | None |

---

## Output Files

Three JSON files are produced per processed paper:

### `{doi_slug}_metadata.json` — Benchmark metadata aligned to AISafetyBenchExplorer template

```json
{
  "Benchmark Name": "BOLD",
  "Paper Title": "BOLD: Dataset and Metrics for Measuring Biases in Open-Ended Language Generation",
  "Authors": "Dhamala, J., Sun, T., Kumar, V., ...",
  "Year": 2021,
  "Venue": "ACL",
  "Citation Count": 245,
  "Paper Link": "https://aclanthology.org/2021.acl-long.330/",
  "Code Repository": "https://github.com/...",
  "Dataset Repository": "https://huggingface.co/...",
  "Task Types": ["Bias", "Fairness"],
  "Dataset Size": 23679,
  "Evaluation Metrics": [
    {
      "Metric Name": "Regard Score",
      "Conceptual Description": "...",
      "Methodological Details": "...",
      "Mathematical Definition": "..."
    }
  ],
  "Complexity Level": "Popular (citation count exceeds 100; widely adopted as bias benchmark baseline)",
  "Open Access": "Yes",
  "Metadata Completeness": 0.92
}
```

### `{doi_slug}_quality.json` — Extraction quality assessment

```json
{
  "overall_score": 0.87,
  "completeness_score": 0.92,
  "accuracy_score": 0.85,
  "formula_quality_score": 0.78,
  "url_completeness": 0.95,
  "issues_found": [],
  "requires_human_review": false
}
```

### `{doi_slug}_api.json` — Raw aggregated API response (for audit/debug)

---

## Comparison: Pipeline Modes

| Aspect | PDF-Based (Legacy) | DOI-Based (Primary) | Master Prompt (Manual) |
|--------|--------------------|---------------------|------------------------|
| Input | Local PDF file | DOI / arXiv ID | Any source (PDF, URL, text) |
| Speed | 60–120 s | 5–15 s (no full-text) | Human/agent time |
| Citation count | Not available | Live from Semantic Scholar | Manual lookup required |
| Venue / Authors | PDF extraction (error-prone) | From API (authoritative) | Manual |
| LaTeX formulas | Regex/heuristic | LLM from full text | Forced by prompt rules |
| Excel output | Via extractor | Via pipeline | Via generated `openpyxl` code |
| Validation | LLM only | LLM + API cross-check | 24-point QA checklist |
| Best for | Offline/local PDFs | New or known-DOI papers | Complex/novel benchmarks |

---

## Advanced Usage

### Custom LLM Backend

```bash
# OpenAI GPT-4o
python doi_extractor_cli.py \
    --doi "2402.04249" \
    --backend openai \
    --model gpt-4o \
    --openai-key $OPENAI_API_KEY

# Local Ollama
python doi_extractor_cli.py \
    --doi "2402.04249" \
    --model llama3.1:70b \
    --validation-model llama3.1:8b
```

### Updating the Excel Catalogue

```bash
# 1. Export DOI column from AISafetyBenchExplorer.xlsx to dois.csv
# 2. Run batch extraction
python doi_extractor_cli.py \
    --batch dois.csv \
    --doi-column "Paper Link" \
    --full-text \
    --email your@email.com \
    --output-dir catalog_update/

# 3. Review outputs and merge into Excel via openpyxl
```

---

## Controlled Vocabularies

All `Task Type`, `Entry Modalities`, `Integration`, `Created By`, and `Development Purpose` values use controlled vocabularies defined in `AISafety_Benchmark_Extraction_Master_Prompt.md` (Appendix 1A). Key categories:

- **Task Types (sample):** `Safety`, `Jailbreak`, `Red Teaming`, `Bias`, `Hallucination`, `Toxicity`, `Alignment`, `Privacy`, `Agents Safety`, `Refusal`, `Sycophancy`
- **Entry Modalities:** `Prompts`, `Conversations`, `Binary-choice Questions`, `Multiple-choice Questions`, `Scenarios`, `Sentence Pairs`
- **Created By:** `Human`, `Machine`, `Hybrid`
- **Integration:** `API`, `Export`, `API & Export`, `NA`

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No PDF parsing backend available` | `pip install pymupdf` |
| `Semantic Scholar rate limit exceeded` | Get a free API key at https://www.semanticscholar.org/product/api |
| `Unpaywall requires email` | Set `UNPAYWALL_EMAIL` env variable or use `--email` flag |
| `DOI not found` | Try the arXiv ID instead (e.g., `2402.04249`); verify DOI format `10.XXXX/YYYYY` |
| `instructor` version conflict | Upgrade: `pip install "instructor>=1.2.0" "openai>=1.30.0"` |
| Non-printable characters in output | Run `python -c "import unicodedata"` check; re-generate with clean prompt |

---

## Related Resources

- **Complexity methodology:** `complexity-methodology.md` — full classification report for 176 benchmarks
- **Master extraction prompt:** `AISafety_Benchmark_Extraction_Master_Prompt.md` — reusable v1.1 prompt with worked examples (PluriHarms)
- **Semantic Scholar API docs:** https://www.semanticscholar.org/product/api
- **arXiv API:** https://arxiv.org/help/api/index
- **Unpaywall API:** https://unpaywall.org/products/api
- **Crossref REST API:** https://api.crossref.org/swagger-ui/index.html

---

## Contributing

1. Add new benchmarks using the master prompt (Phase 1–5).
2. Verify all URLs and citation counts against Semantic Scholar.
3. Ensure no non-printable Unicode characters in any cell.
4. Run the 24-point QA checklist before committing.

---

*Questions or issues? Open a GitHub issue or consult the inline documentation in each Python module.*
