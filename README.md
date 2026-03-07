# DOI-Based AI Safety Benchmark Metadata Extraction Pipeline

## 🎯 Overview

This pipeline extracts comprehensive metadata from AI safety benchmark papers using a **multi-API strategy**, eliminating the need for direct PDF parsing in many cases while maintaining compatibility with your existing extraction infrastructure.

## 🆕 What's New

### Key Innovation: DOI → API → LLM Pipeline

**Old approach:**
```
PDF file → Parse PDF → Extract text → LLM extraction → Validate
```

**New approach:**
```
DOI/arXiv ID → Multi-API resolution → Rich metadata
                     ↓
              Optional full-text download
                     ↓
              LLM extraction (API-guided) → Cross-validation
```

### Benefits

✅ **Correct metadata from authoritative sources** (Semantic Scholar, arXiv, Crossref)
✅ **Citation counts, author info, venues** automatically populated
✅ **No PDF parsing errors** for basic metadata
✅ **Full-text access** via Unpaywall when available
✅ **Faster processing** (API calls faster than PDF parsing)
✅ **Better validation** (cross-check LLM against APIs)

## 📁 New Files

| File | Purpose | Lines |
|------|---------|-------|
| `api_models.py` | Pydantic models for API responses | 230 |
| `doi_based_resolver.py` | Multi-API metadata aggregator | 535 |
| `doi_pipeline.py` | Complete DOI→extraction orchestrator | 537 |
| `doi_extractor_cli.py` | Command-line interface | 380 |

**Total:** ~1,700 lines of production-ready code

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements_doi_pipeline.txt

# Optional: Install PDF parsers
pip install pymupdf  # Basic (required)
pip install marker-pdf[full]  # Fast markdown conversion
pip install nougat-ocr  # Best for math-heavy papers

# Optional: Semantic Scholar client
pip install semanticscholar
```

### Basic Usage

```bash
# Set your email (required for Unpaywall)
export UNPAYWALL_EMAIL="your@email.com"

# Extract from DOI
python doi_extractor_cli.py \
    --doi "10.18653/v1/2021.acl-long.330" \
    --email your@email.com

# Extract from arXiv ID
python doi_extractor_cli.py \
    --doi "2103.14296" \
    --email your@email.com

# With full-text extraction
python doi_extractor_cli.py \
    --doi "10.xxx/yyy" \
    --full-text \
    --save-pdfs \
    --email your@email.com
```

### Batch Processing

```bash
# Create CSV with DOI column
echo "DOI,Title" > dois.csv
echo "10.xxx/yyy,Paper 1" >> dois.csv
echo "2103.14296,Paper 2" >> dois.csv

# Process batch
python doi_extractor_cli.py \
    --batch dois.csv \
    --doi-column DOI \
    --full-text \
    --email your@email.com \
    --output-dir batch_results/
```

## 🔌 Integration with Existing Pipeline

The new DOI pipeline **complements** your existing `integrated_paperParser.py` and can be used alongside it:

### Option 1: Pure DOI Mode (Recommended for new papers)

```python
from doi_pipeline import DOIPipeline

pipeline = DOIPipeline(
    email="your@email.com",
    s2_api_key="optional_key",
    extractor_model="qwen2.5:32b"
)

# Extract from DOI
extracted, quality, api_metadata = pipeline.process_from_doi(
    "10.xxx/yyy",
    extract_full_text=True
)

# Result is compatible with AISafetyBenchExplorer template
print(f"Benchmark: {extracted['Benchmark Name']}")
print(f"Metrics: {len(extracted['Evaluation Metrics'])}")
print(f"Citations: {extracted['Citation Count']}")
```

### Option 2: Hybrid Mode (DOI + existing PDF pipeline)

```python
from doi_based_resolver import DOIMetadataResolver
from enhanced_mainExtractor import EnhancedPaperMetadataExtractor

# 1. Get API metadata first
resolver = DOIMetadataResolver(email="your@email.com")
api_metadata = resolver.resolve("10.xxx/yyy")

# 2. Use existing PDF parser
from enhanced_pdf_parser import parse_pdf_to_markdown
text, format_hint = parse_pdf_to_markdown("paper.pdf")

# 3. Extract with API context
extractor = EnhancedPaperMetadataExtractor()
extracted, quality = extractor.process_paper(text, format_hint)

# 4. Enrich with API metadata
extracted['Authors'] = ', '.join(api_metadata.authors)
extracted['Citation Count'] = api_metadata.citation_count
extracted['Venue'] = api_metadata.venue
```

## 🌐 API Sources

### 1. Semantic Scholar (Primary)

**What it provides:**
- Authors, citations, venues, publication dates
- Abstract, fields of study
- ArXiv/DOI/PubMed IDs
- Open Access status
- Citation & reference counts
- Influential citation metrics

**Rate limits:**
- Public: 100 requests/5 min
- With API key: 1 request/sec

**Get API key:** https://www.semanticscholar.org/product/api

### 2. arXiv API

**What it provides:**
- Preprint metadata
- LaTeX source access (when available)
- Categories, comments
- Direct PDF download links

**Rate limits:**
- 1 request/3 seconds (polite usage)

### 3. Unpaywall

**What it provides:**
- Open Access status
- Legal PDF download links
- OA version (published/accepted/submitted)
- License information

**Rate limits:**
- 100,000 requests/day (with email)

**Usage:** Requires email in requests (polite crawling)

### 4. Crossref

**What it provides:**
- DOI resolution
- Publisher metadata
- References
- Funder information

**Rate limits:**
- Unlimited (polite usage)

## 📊 Output Format

The pipeline produces three files per paper:

### 1. `{doi}_metadata.json`

Extracted benchmark metadata aligned to AISafetyBenchExplorer template:

```json
{
  "Benchmark Name": "BOLD",
  "Paper Title": "BOLD: Dataset and Metrics for Measuring Biases...",
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
      "Mathematical Definition": "...",
      ...
    }
  ],
  "Complexity Level": "Popular",
  "Open Access": "Yes",
  "Metadata Completeness": 0.92
}
```

### 2. `{doi}_quality.json`

Quality assessment:

```json
{
  "overall_score": 0.87,
  "completeness_score": 0.92,
  "accuracy_score": 0.85,
  "formula_quality_score": 0.78,
  "url_completeness": 0.95,
  "issues_found": [],
  "strengths": [
    "High-quality API metadata",
    "Full text available",
    "All metrics extracted"
  ],
  "requires_human_review": false
}
```

### 3. `{doi}_api.json`

Raw API metadata (for reference and debugging):

```json
{
  "doi": "10.xxx/yyy",
  "arxiv_id": "2103.14296",
  "title": "...",
  "authors": ["..."],
  "citation_count": 245,
  "is_open_access": true,
  "data_sources": ["semantic_scholar", "arxiv", "unpaywall"],
  ...
}
```

## 🔬 Advanced Usage

### Custom Models

```bash
# Use OpenAI GPT-4
python doi_extractor_cli.py \
    --doi "10.xxx/yyy" \
    --backend openai \
    --model gpt-4o \
    --openai-key $OPENAI_API_KEY

# Use different Ollama models
python doi_extractor_cli.py \
    --doi "10.xxx/yyy" \
    --model llama3.1:70b \
    --validation-model llama3.1:8b
```

### Semantic Scholar API Key

```bash
# Higher rate limits with API key
export SEMANTIC_SCHOLAR_API_KEY="your_key_here"

python doi_extractor_cli.py \
    --doi "10.xxx/yyy" \
    --s2-key $SEMANTIC_SCHOLAR_API_KEY
```

### Python API

```python
from doi_pipeline import DOIPipeline
from pathlib import Path

# Initialize pipeline
pipeline = DOIPipeline(
    email="your@email.com",
    s2_api_key="optional",
    extractor_model="qwen2.5:32b",
    backend="ollama"
)

# Process DOI
extracted, quality, api_metadata = pipeline.process_from_doi(
    identifier="10.xxx/yyy",
    extract_full_text=True,
    save_pdf=True,
    output_dir=Path("outputs/")
)

# Access results
print(f"Benchmark: {extracted['Benchmark Name']}")
print(f"Completeness: {api_metadata.metadata_completeness_score}")
print(f"Requires review: {quality.requires_human_review}")
```

## 🎯 Use Cases

### Use Case 1: Quick metadata for known papers

```bash
# Just need basic info (no full text)
python doi_extractor_cli.py \
    --doi "10.xxx/yyy" \
    --email your@email.com
# Fast: ~5-10 seconds per paper
```

### Use Case 2: Complete extraction with full text

```bash
# Deep extraction with formulas and metrics
python doi_extractor_cli.py \
    --doi "10.xxx/yyy" \
    --full-text \
    --email your@email.com
# Slower: ~30-60 seconds per paper (includes PDF parsing)
```

### Use Case 3: Batch update of existing catalog

```bash
# Extract DOIs from AISafetyBenchExplorer.xlsx
# Create dois.csv, then:
python doi_extractor_cli.py \
    --batch dois.csv \
    --full-text \
    --email your@email.com \
    --output-dir catalog_update/
```

## 🔍 Comparison: Old vs New Approach

| Aspect | PDF-Based (Old) | DOI-Based (New) |
|--------|----------------|-----------------|
| **Input** | PDF file | DOI/arXiv ID |
| **Speed** | Slow (60-120s) | Fast (5-15s without full text) |
| **Authors** | Extracted from PDF (error-prone) | From API (authoritative) |
| **Citations** | Not available | Live citation counts |
| **Venue** | Extracted from text | From API (structured) |
| **Abstract** | Sometimes missing | Always available (API) |
| **URLs** | Regex extraction | API + validation |
| **Validation** | LLM-only | LLM + API cross-check |
| **Completeness** | Variable | Measured & tracked |
| **Full text** | Always parsed | Optional (on-demand) |

## 🧪 Testing

```python
# Test with a well-known paper
python doi_extractor_cli.py \
    --doi "10.18653/v1/2021.acl-long.330" \
    --full-text \
    --email your@email.com

# Expected: BOLD dataset paper
# Should extract: bias metrics, dataset size 23679, etc.
```

## 📚 Documentation

- **api_models.py**: Pydantic models, see inline docs
- **doi_based_resolver.py**: Multi-API resolver, see class docstrings
- **doi_pipeline.py**: Orchestrator, see method docs
- **doi_extractor_cli.py**: CLI usage in `--help`

## 🐛 Troubleshooting

### "No PDF parsing backend available"

```bash
pip install pymupdf  # Minimum requirement
```

### "Semantic Scholar API rate limit"

```bash
# Get free API key for higher limits
# https://www.semanticscholar.org/product/api
export SEMANTIC_SCHOLAR_API_KEY="your_key"
```

### "Unpaywall requires email"

```bash
export UNPAYWALL_EMAIL="your@email.com"
# Or use --email flag
```

### "DOI not found"

```bash
# Try arXiv ID instead
python doi_extractor_cli.py --doi "2103.14296"

# Or check if DOI is correct
# DOI format: 10.XXXX/YYYYY
```

## 🔗 Related Files

This DOI pipeline integrates with your existing files:

- **models.py**: Shared Pydantic models [file:11]
- **enhanced_mainExtractor.py**: LLM extractor (reused) [file:4]
- **enhanced_pdf_parser.py**: PDF parsing (optional) [file:10]
- **latex_aware_chunker.py**: Text chunking (reused) [file:2]
- **integrated_paperParser.py**: Original pipeline (still works) [file:5]

## 📝 Next Steps

1. **Install dependencies:** `pip install -r requirements_doi_pipeline.txt`
2. **Set email:** `export UNPAYWALL_EMAIL="your@email.com"`
3. **Test single DOI:** See Quick Start above
4. **Process batch:** Create CSV with DOIs from your Excel
5. **Integrate:** Add to your workflow alongside PDF pipeline

## 🎉 Summary

The DOI-based pipeline gives you:

✅ **Authoritative metadata** from scholarly APIs
✅ **Live citation counts** for popularity assessment
✅ **Faster processing** (no PDF parsing for basic info)
✅ **Better validation** (cross-check against APIs)
✅ **Seamless integration** with existing pipeline
✅ **Batch processing** for updating catalogs

All while maintaining compatibility with your AISafetyBenchExplorer template and complexity-methodology! [file:17][file:19]

---

**Questions?** See inline documentation or raise an issue.
