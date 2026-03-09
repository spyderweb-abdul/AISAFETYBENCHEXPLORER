# AI Safety Benchmark Metadata Extraction — Reusable Master Prompt
**Version 1.1 | February 2026**

---

## Instructions for Use

Submit this prompt together with one or more of the following inputs:

- **(A)** A DOI or arXiv URL pointing to an AI safety benchmark paper
- **(B)** A PDF of the paper directly attached

**Required output:** A single Excel workbook with **two sheets**:

| Sheet | Name | Template Schema |
|---|---|---|
| 1 | `Safety Evaluation Benchmarks` | `Copy of AISafetyBenchExplorer.xlsx` |
| 2 | `Evaluation Metrics Catalogue` | `safety-benchmarks-eval-metrics-catalogue.xlsx` |

Both template files are available in the project Space files and must be treated as persistent canonical schemas. Do **NOT** deviate from their column names, order, or data types unless explicitly instructed.

---

## Role & Context

You are an expert AI safety researcher specialising in LLM evaluation methodology. Your task is to perform exhaustive, technically rigorous metadata extraction from AI safety benchmark papers and populate two complementary structured catalogues:

1. A benchmark-level metadata record (AISafetyBenchExplorer schema)
2. A per-metric deep technical record (safety-benchmarks-eval-metrics-catalogue schema)

Your output must be:

- **Truthful and grounded** — every field must be derived directly from the paper or verifiable external sources
- **Complete** — no field left blank without an explicit `N/A` and a stated reason
- **Template-compatible** — column names and structure must exactly match the canonical schemas
- **Technically precise** — mathematical formulas must use proper LaTeX notation; no dollar signs or code-block math

---

## Phase 0 — Pre-Extraction Research

Before extracting any metadata, complete all three steps below in sequence.

### Step 0.1 — Fetch the Paper

If a DOI or URL is provided (not a direct PDF attachment), retrieve the full paper:

- `https://arxiv.org/abs/<arxiv_id>` for arXiv papers
- `https://doi.org/<doi>` for DOI links
- `https://huggingface.co/papers/<id>` for HuggingFace papers

Extract: Title, Authors, Institutions, Abstract, all body sections, and all Appendices.

### Step 0.2 — Search for Supplementary Information

Perform targeted web searches to locate:

| Target | Search Query |
|---|---|
| Citation count | `"<paper title>" citations semantic scholar` |
| Code repository | `"<benchmark name>" github` |
| Dataset availability | `"<benchmark name>" dataset huggingface` |
| License | `"<benchmark name>" license` |
| HuggingFace card | `huggingface.co/datasets/<benchmark name>` |

Record all URLs found. Test each URL before recording it.

### Step 0.3 — Read the Paper Systematically

Read in this order: **Abstract → Introduction → Related Work → Benchmark Design → Dataset Construction → Evaluation Methodology → Results → Appendix**

Pay special attention to:

- Sections titled "Metrics", "Evaluation", "Methodology", or "Measures"
- All mathematical formulas, definitions, and tables
- Dataset statistics tables (sample counts, annotator details, split sizes)
- Footnotes and appendices (often contain full metric derivations)

---

## Phase 1 — Sheet 1: `Safety Evaluation Benchmarks`

Populate **one row per benchmark paper** using the columns defined below.  
Column names must **exactly** match the `AISafetyBenchExplorer.xlsx` "Safety Evaluation Benchmarks" sheet headers.

For columns marked **→ see Appendix 1A**, use only the controlled vocabulary defined there.

---

### Column Definitions

#### `Benchmark Name`
Short canonical name used in the paper (e.g., `T3`, `GuardEval`, `PluriHarms`). Use the exact abbreviation from the paper title or abstract — do not invent a name.

---

#### `Task Type`
Primary evaluation task(s). Select all that apply from the controlled vocabulary in **→ Appendix 1A, Section 1 (KNOWN_TASK_TYPES)**. Comma-separate multiple values. Extract from sections titled "Task Design", "Benchmark Overview", or equivalent.

---

#### `Paper Title`
Full verbatim paper title — not abbreviated or paraphrased.

---

#### `DOI / Paper Link`
Full URL. Use `https://arxiv.org/abs/XXXX.XXXXX` for arXiv or `https://doi.org/10.XXXXX/XXXXX` for DOI. Include both if available.

---

#### `Release Date`
Month and year of first public release (arXiv v1 submission date or conference publication date).  
Format: `YYYY-MM` (e.g., `2026-01`).

---

#### `Description`
A synthesised 2–3 sentence technical summary covering:
1. What the benchmark evaluates
2. The core methodology or innovation
3. Why it advances AI safety evaluation

Do **not** copy the abstract verbatim.

---

#### `Code Available`
- `Yes — <GitHub URL>` if a code repository was found and URL verified
- `No` if not found after searching
- `N/A` if not applicable (data-only benchmark)

---

#### `Dataset Available`
- `Yes — <HuggingFace/dataset URL>` if dataset is publicly available
- `Partial — <URL>` if only a subset is released
- `No` if unavailable after searching

---

#### `Number of Samples`
Total number of instances, prompts, or examples in the benchmark dataset.  
Format: integer with units (e.g., `15,000 ratings (150 prompts × 100 annotators)`).  
Extract from the dataset statistics table, or from the GitHub/HuggingFace repository if links are identified.

---

#### `Created By`
The mode of data generation. **→ see Appendix 1A, Section 5 (CREATED_BY_KEYWORDS)**.  
One of: `Human` | `Machine` | `Hybrid`

---

#### `Entry Modalities`
The type(s) of input instances in the benchmark. Select all that apply from **→ Appendix 1A, Section 2 (MODALITY_KEYWORDS)**. Comma-separate multiple values.

---

#### `Development Purpose`
The intended use of the benchmark dataset. **→ see Appendix 1A, Section 4 (DEVELOPMENT_PURPOSE_KEYWORDS)**.  
One of: `Train` | `Eval` | `Train & Eval`

---

#### `License`
License for the dataset and/or code. Common values: `MIT`, `Apache 2.0`, `CC-BY 4.0`, `CC-BY-SA 4.0`, `CC0`, `Custom Research`, `Unknown`.  
Search the paper, GitHub README, and HuggingFace dataset card for this information.

---

#### `Metrics`
Comma-separated list of **all** evaluation metrics named or defined in the paper — use the paper's exact terminology. Every metric listed here must have a corresponding row in Sheet 2.

---

#### `Complexity`
Apply the decision tree in **Phase 3** of this prompt.  
Value: `Popular` | `High` | `Medium` | `Low`  
**Append a one-sentence justification in parentheses citing the specific criteria met.**  
Example: `High — adversarial two-turn protocol, novel three-way output space, and multi-level causal hierarchy require domain expertise and novel metric development.`

---

#### `Language`
Primary language(s) of prompts and responses. Use ISO 639-1 codes (`en`, `fr`, `zh`, etc.) or `Multilingual` if more than five languages are covered.

---

#### `Integration`
How the benchmark dataset or code can be accessed programmatically. **→ see Appendix 1A, Section 3 (INTEGRATION_KEYWORDS)**.  
One of: `API` | `Export` | `API & Export` | `N/A`

---

#### `Citation Count`
Number of citations found on Semantic Scholar or Google Scholar at time of extraction.  
Format: `<integer> (accessed <YYYY-MM>)`  
Example: `0 (accessed 2026-02)` — never assume or estimate.

---

#### `Benchmark / Paper Link`
Canonical URL for the benchmark homepage or primary paper page. Use the DOI/arXiv URL if no dedicated homepage exists.

---

### Appendix 1A — Column Reference Vocabulary

Use the controlled vocabularies below when populating the corresponding columns. All keyword matching is case-insensitive. When a value is not found in the lists, infer the closest match and note the deviation in the QA checklist.

---

#### Section 1 — Task Types (`KNOWN_TASK_TYPES`)

```python
KNOWN_TASK_TYPES = [
    # Core Safety
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
    'Conversational Safety', 'Opinion Steering', 'Causal Reasoning',

    # Methodology / Meta
    'Benchmark', 'Evaluation', 'Crowdsourced', 'Lie Detection',
    'Capabilities', 'Language'
]
```

If the benchmark's task type is not listed, infer the closest match and note the new term used.

---

#### Section 2 — Entry Modalities (`MODALITY_KEYWORDS`)

Select the key if any of its associated keywords are found in the paper's dataset description.

```python
MODALITY_KEYWORDS = {
    'Prompts':                   ['prompt', 'query', 'instruction'],
    'Conversations':             ['conversation', 'dialogue', 'chat', 'multi-turn', 'turn'],
    'Examples':                  ['example', 'sample'],
    'Binary-choice Questions':   ['binary', 'yes-no', 'true-false', 'binary-choice'],
    'Multiple-choice Questions': ['multiple-choice', 'mcq', 'multi-choice'],
    'Scenarios':                 ['scenario', 'situation'],
    'Sentences':                 ['sentence'],
    'Excerpts':                  ['excerpt', 'passage'],
    'Posts':                     ['post', 'social media'],
    'Sentence Pairs':            ['sentence pair', 'pair'],
    'Entry Tuples':              ['tuple', 'entry'],
    'Location Templates':        ['location', 'template'],
    'Stories':                   ['story', 'narrative'],
    'Comments':                  ['comment'],
    'Anecdotes':                 ['anecdote'],
    'Transcripts':               ['transcript', 'utterance']
}
```

A new key may be inferred and added if none of the above map to the benchmark's data format.

---

#### Section 3 — Integration Keywords (`INTEGRATION_KEYWORDS`)

Check both the GitHub repository and HuggingFace dataset card.

```python
# HuggingFace dataset card tags
INTEGRATION_KEYWORDS_HF = {
    'API':        ['library:transformers', 'library:evaluate', 'library:autotrain'],
    'Export':     ['format:csv', 'format:json', 'format:parquet'],
    'API & Export': # if both API and Export elements are present
}

# GitHub repository signals
INTEGRATION_KEYWORDS_GH = {
    'API':        ['api', 'python package', 'pip install', 'library',
                   'import', 'client', 'sdk', 'huggingface', 'datasets'],
    'Export':     ['download', 'clone', 'csv file', 'json file',
                   'manual', 'extract', 'archive'],
    'API & Export': # if both API and Export elements are present
}
```

If neither HuggingFace nor GitHub information is available after searching, use `N/A`.

---

#### Section 4 — Development Purpose Keywords (`DEVELOPMENT_PURPOSE_KEYWORDS`)

```python
DEVELOPMENT_PURPOSE_KEYWORDS = {
    'Train':       ['train', 'training', 'fine-tune', 'finetune'],
    'Eval':        ['eval', 'evaluation', 'benchmark', 'test'],
    'Train & Eval': # if both Train and Eval elements are present
}
```

---

#### Section 5 — Created By Keywords (`CREATED_BY_KEYWORDS`)

```python
CREATED_BY_KEYWORDS = {
    'Human':   ['manually', 'annotated', 'human', 'crowdsourced',
                'expert', 'curated'],
    'Machine': ['automatically', 'generated', 'machine',
                'synthetic', 'auto-generated'],
    'Hybrid':  # if both Human and Machine signals are present
}
```

---

## Phase 2 — Sheet 2: `Evaluation Metrics Catalogue`

For **every metric** listed in the `Metrics` column of Sheet 1, generate one row with all 9 columns below.  
Column names must **exactly** match the `safety-benchmarks-eval-metrics-catalogue.xlsx` headers.

```
benchmark_name | paper_title | paper_link | metric_name |
conceptual_description | methodological_details | mathematical_definition |
differences_from_standard_definition | notes
```

---

### Column 1: `benchmark_name`
Exact short name from Sheet 1 "Benchmark Name" column.

---

### Column 2: `paper_title`
Full verbatim paper title (identical to Sheet 1).

---

### Column 3: `paper_link`
Full DOI or arXiv URL (identical to Sheet 1).

---

### Column 4: `metric_name`
Exact name of the metric as used in the paper. Use the paper's own terminology — do not rename or standardise.  
Examples: `Utility (Sensitivity)`, `Macro F1 Score`, `Mean Absolute Error (MAE)`, `Ripple-Effect Function`

---

### Column 5: `conceptual_description`

**All five sub-components are mandatory.** Weave them into 2–4 coherent sentences — do not use bullet points.

| Sub-component | What to cover |
|---|---|
| **(a) Task type** | What evaluation task does this metric support? |
| **(b) Data type** | What data does the metric operate on? Be specific (e.g., "15,000 harm ratings across 150 prompts from 100 annotators"). |
| **(c) Safety dimension** | Which AI safety concern does this metric address? (e.g., epistemic reliability, over-refusal, sycophancy resistance, value pluralism) |
| **(d) Intent** | What research question does the metric answer? What failure mode does it reveal? |
| **(e) Judge type** | What evaluates outputs? Name the model, number of annotators, or type of ground truth. |

---

### Column 6: `methodological_details`

Provide a complete numbered step-by-step computation procedure. **All five sub-components are mandatory.**

| Sub-component | What to cover |
|---|---|
| **(a) Event definitions** | Define all primitive outcomes: TP, TN, FP, FN, or domain equivalents (e.g., "Sheep correctly affirmed", "appropriate refusal"). |
| **(b) Label sources** | Where do ground-truth labels come from? Specify annotator count, qualification, agreement metrics, or automated labelling model. |
| **(c) Multi-turn handling** | State explicitly: "Single-turn only" OR describe how conversation context is incorporated. |
| **(d) Category/instance handling** | If multiple categories or strata exist, explain how each is handled before aggregation. |
| **(e) Aggregation method** | How is the final scalar computed? Specify micro/macro average, AUC, weighted sum, etc., and the aggregation level (per-prompt, per-annotator, global). |

---

### Column 7: `mathematical_definition`

Provide a complete LaTeX formula with **all variables defined inline**.

**Requirements:**
- Use display-style LaTeX: `\[ ... \]`
- Define every symbol used
- Include all sub-formulas needed (e.g., Precision and Recall before F1)
- Specify ranges and constraints (e.g., `where R = 10 runs`, `i = 1, \ldots, N`, `\in [0, 1]`)
- Expand domain-specific indicators: e.g., `\mathbb{1}[	ext{genuine jailbreak}(r_i)]`

**Avoid:** Markdown code blocks, dollar signs (`$`), or Python-style math expressions.

Example from catalogue:
```
\[ 	ext{Macro F1} = rac{1}{C} \sum_{c=1}^{C} 	ext{F1}_c
	ext{ where } C = 	ext{number of risk categories},\;
	ext{F1}_c = rac{2 \cdot 	ext{Prec}_c \cdot 	ext{Rec}_c}{	ext{Prec}_c + 	ext{Rec}_c} \]
```

---

### Column 8: `differences_from_standard_definition`

Explain concisely how **this benchmark's implementation** differs from the canonical version of the same metric name. Address all applicable points:

1. What the standard version measures and how it is normally computed
2. What this benchmark adds, restricts, or redefines
3. Novel aspects unique to this benchmark (adversarial protocols, new aggregation levels, domain-specific adaptations)
4. What the standard metric cannot capture that this variant can

If the metric is entirely novel, state:
> "Novel metric with no direct standard analog. [Explain what it does that existing metrics cannot.]"

---

### Column 9: `notes`

Include all applicable sub-sections:

- **(a) Empirical results** — Key numeric findings from the paper (model name + value). Include at least 2–3 model comparisons where reported.
- **(b) Assumptions & limitations** — What does this metric assume? When might it give misleading results? What edge cases or biases were identified?
- **(c) Use cases** — Which deployment contexts or research questions is this metric best suited for?
- **(d) Interactions with other metrics** — Does this metric complement, conflict with, or trade off against other metrics in the same benchmark?

---

## Phase 3 — Complexity Classification Rules

Apply the following decision tree **in strict order** to assign the `Complexity` field.

---

### Step 1 — Check for POPULAR

Classify as **Popular** (overrides all other levels) if the benchmark meets **any** of:

- [ ] Citation count > 100 (verified via Semantic Scholar)
- [ ] Frequently cited as a baseline in ≥ 3 other safety papers
- [ ] Adopted as a community standard (e.g., HarmBench, TruthfulQA, MMLU)
- [ ] Acknowledged as foundational in the broader safety literature

---

### Step 2 — Check for HIGH (if not Popular)

Classify as **High** if the benchmark exhibits **≥ 2** of:

- [ ] Multi-hop or compositional reasoning across > 2 steps
- [ ] Adversarial robustness testing (red-teaming, jailbreaking, social pressure, structural fallacy detection)
- [ ] Subjective/open-ended generation with nuanced evaluation
- [ ] Risk-critical domain (medical, legal, financial, CBRN)
- [ ] Novel metric development (new formulas not from prior work)
- [ ] Complex evaluation methodology (multi-phase pipeline, multi-judge ensemble, genetic algorithm curation, mixed-effects models)
- [ ] Requires domain expertise for annotation or evaluation
- [ ] Pluralistic or culturally-sensitive annotation (≥ 50 annotators with demographic or psychological stratification)

> **Tie-breaking rule:** When in doubt between High and Medium, and adversarial or risk-critical criteria apply, choose **High**.

---

### Step 3 — Check for MEDIUM (if not Popular or High)

Classify as **Medium** if the benchmark exhibits **≥ 2** of:

- [ ] 1–2 step reasoning or limited compositional requirements
- [ ] Some adversarial testing, but not the primary focus
- [ ] Mix of objective and subjective evaluation
- [ ] Standard metrics with minor domain-specific adaptations
- [ ] Moderate annotation effort (single-pass, specialist annotators)

---

### Step 4 — Default to LOW

Apply if none of the above criteria are met:

- Single-step reasoning or direct lookup
- Binary or categorical outcomes
- Standard unmodified metrics (accuracy, F1)
- Minimal adversarial considerations
- Simple annotation process

---

### Special Rules

- For multi-faceted benchmarks, evaluate against the **most safety-critical dimension** (e.g., an adversarial sub-task dominates over a simple classification sub-task).
- Use `Unknown` **only** when information is genuinely insufficient after full paper reading and web search.

---

### Justification Format

Append a one-sentence justification to every Complexity value, citing ≥ 2 specific criteria:

```
<Level> — <1-sentence reason citing ≥2 specific criteria met>
```

**Example:**
```
High — novel three-way causal judgment metric, adversarial social pressure
protocol, and multi-level Pearl's Ladder evaluation require advanced reasoning
and domain expertise.
```

---

## Phase 4 — Quality Assurance Checklist

Complete this checklist **before generating any output**.

### Sheet 1 Checks
- [ ] Benchmark Name matches the paper's own abbreviation (not invented)
- [ ] Every metric listed in `Metrics` has a corresponding Sheet 2 row
- [ ] Complexity justification cites ≥ 2 specific criteria from the decision tree
- [ ] Citation count sourced from Semantic Scholar or Google Scholar (not assumed)
- [ ] Code and Dataset URLs verified (not guessed)
- [ ] Number of Samples is an integer with units, citing the source table or repo
- [ ] Description is synthesised — not copied from the abstract
- [ ] Created By, Entry Modalities, Development Purpose, and Integration values use only controlled vocabulary from Appendix 1A

### Sheet 2 Checks (per metric)
- [ ] `conceptual_description` contains all 5 sub-components woven into coherent prose
- [ ] `methodological_details` contains all 5 sub-components as numbered steps
- [ ] `mathematical_definition` uses LaTeX display notation; all variables defined; no dollar signs
- [ ] `differences_from_standard_definition` explains specific novelty — not just "domain-specific"
- [ ] `notes` includes empirical results (≥ 2 model comparisons), limitations, use cases, and metric interactions
- [ ] `metric_name` matches exact paper terminology

### Global Checks
- [ ] All data is grounded in the paper — no hallucinated statistics or formulas
- [ ] Mathematical formulas verified against paper text or appendix
- [ ] Sample counts verified against dataset statistics table
- [ ] Author affiliations verified from paper header or acknowledgements section
- [ ] No non-printable Unicode characters in any cell of the output file
- [ ] Excel output uses `openpyxl` with auto-adjusted column widths
- [ ] Both sheets use **exactly** the column headers from the canonical template files

---

## Phase 5 — Output Format

### 1. Python Code (Executed)

Write and execute Python code using `openpyxl` or `pandas + openpyxl` to produce the final Excel file. The code must:

1. Create a DataFrame for Sheet 1 with all columns (1 row per benchmark)
2. Create a DataFrame for Sheet 2 with all 9 columns (N rows = N metrics)
3. Write both DataFrames to a single `.xlsx` workbook
4. Auto-adjust column widths (min 15, max 80 characters)
5. Apply text wrapping to all cells in Sheet 2 columns 5–9 (`conceptual_description` through `notes`)
6. Bold the header row in both sheets
7. Name the output file: `<BenchmarkName>_metadata_<YYYY-MM>.xlsx` (single benchmark) or `AI_Safety_Metadata_<YYYY-MM>.xlsx` (multiple benchmarks)
8. Ensure the code contains **no non-printable characters**

### 2. Written Summary (in Response Text)

After the code block, provide:

1. One paragraph per benchmark: what it evaluates, key innovation, complexity classification with justification
2. A Markdown table listing all extracted metrics (`metric_name` + one-line description)
3. Any deviations from the template format, with explicit justification
4. Any fields that could not be determined, with reason and default value used

### 3. Ambiguity Handling

**Unnamed metric:** If the paper defines a clear measurement procedure but does not name the metric, use a descriptive name in brackets:
- `metric_name`: `[Ripple Accuracy at Distance x]`
- Add to `notes`: *"Metric not explicitly named in paper; inferred from Section X methodology."*

**Missing formula:** If a metric formula is absent but derivable from context:
- Provide the derived formula
- Add to `notes`: *"Formula derived from paper description; not stated explicitly."*

---

## Reference — Worked Examples

---

### Example A — Sheet 1 Row (Benchmark Metadata)

**Benchmark: PluriHarms**

| Column | Value |
|---|---|
| **Benchmark Name** | `PluriHarms` |
| **Task Type** | `Alignment, Preference Eval, Annotation` |
| **Paper Title** | `PLURIHARMS: Benchmarking the Full Spectrum of Human Judgments on AI Harm` |
| **DOI / Paper Link** | `https://arxiv.org/abs/2601.08951` |
| **Release Date** | `2026-01` |
| **Description** | PluriHarms is the first AI harm benchmark to treat annotator disagreement as a signal of pluralistic value differences rather than noise, collecting 15,000 harm ratings from 100 demographically and psychologically diverse annotators across 150 purposively curated prompts. A 4-stage genetic algorithm over-samples borderline harm levels (0.4–0.8) to maximise pluralistic signal, and evaluates both personalised (per-annotator) and aggregated (consensus) LLM alignment. This directly challenges the field's assumption that a single gold-label consensus is sufficient, demonstrating that personalised alignment (MAE 0.196) outperforms aggregated approaches (MAE 0.254) by 23%. |
| **Code Available** | `Yes — https://github.com/mila-aia/pluriharms` *(verify URL before submitting)* |
| **Dataset Available** | `Yes — https://huggingface.co/datasets/mila-aia/pluriharms` *(verify URL before submitting)* |
| **Number of Samples** | `15,000 ratings (150 prompts × 100 annotators)` |
| **Created By** | `Hybrid` — seed prompts machine-generated (DeepSeek) then curated via genetic algorithm; harm ratings collected from 100 human annotators |
| **Entry Modalities** | `Prompts` |
| **Development Purpose** | `Eval` |
| **License** | `CC-BY 4.0` *(verify on HuggingFace card)* |
| **Metrics** | `Mean Absolute Error (MAE), R² (Variance Explained), Spearman Correlation` |
| **Complexity** | `High — pluralistic multi-annotator design with 31 demographic/psychological traits, novel personalised vs aggregated alignment split, and genetic algorithm curation constitute novel complex methodology requiring domain expertise.` |
| **Language** | `en` |
| **Integration** | `API & Export` — HuggingFace `datasets` library + JSON/Parquet export |
| **Citation Count** | `0 (accessed 2026-02)` |
| **Benchmark / Paper Link** | `https://arxiv.org/abs/2601.08951` |

---

### Example B — Sheet 2 Row (Metric Extraction)

**Metric: `Utility (Sensitivity)` | Benchmark: T3**

**`benchmark_name`**
```
T3
```

**`paper_title`**
```
T3: Benchmarking Sycophancy and Skepticism in Causal Judgment
```

**`paper_link`**
```
https://arxiv.org/abs/2601.08258
```

**`metric_name`**
```
Utility (Sensitivity)
```

**`conceptual_description`**
```
Measures the true positive rate — the proportion of valid causal claims that the
model correctly affirms (Sheep). Task type: causal reasoning evaluation across
Pearl's Ladder of Causality (L1 Association, L2 Intervention, L3 Counterfactuals).
Data type: 454 expert-curated vignettes with binary Sheep/Wolf ground-truth labels.
Safety dimension: epistemic reliability — specifically diagnosing the Skepticism Trap,
in which safety-tuned models systematically over-refuse valid causal claims. Intent:
quantify a model's ability to affirm genuine causal relationships under both baseline
and adversarial social-pressure protocols. Judge type: ground-truth expert annotations
(Sheep = causally valid claim confirmed by domain experts via Pearl's do-calculus).
```

**`methodological_details`**
```
1) Present 454 expert-curated vignettes across three causal levels: L1 (seeing /
association), L2 (doing / intervention), L3 (imagining / counterfactuals).
2) Event definitions: TP = Sheep vignette correctly classified AFFIRM; FN = Sheep
vignette incorrectly classified REJECT or CONDITIONAL.
3) Label source: expert curation — causal validity determined by domain experts
applying Pearl's do-calculus and counterfactual logic; no automated labelling.
4) Multi-turn handling: single-turn in baseline protocol; two-turn adversarial
protocol applies a social-pressure challenge in turn 2 testing Sycophancy / Skepticism
Trap resistance.
5) Category handling: Utility computed separately for each causal level (L1, L2, L3)
and reported per-level and as a global average across all 454 vignettes.
6) Aggregation: TP / (TP + FN) across all Sheep vignettes in the relevant level or
the full evaluation set.
```

**`mathematical_definition`**
```
\[ 	ext{Utility} = rac{TP}{TP + FN}
= rac{	ext{\# Sheep correctly affirmed (AFFIRM)}}{	ext{\# total Sheep}} \]

	ext{where:} \
TP = 	ext{valid claims correctly affirmed (model outputs AFFIRM)} \
FN = 	ext{valid claims incorrectly rejected (REJECT) or hedged (CONDITIONAL)}
```

**`differences_from_standard_definition`**
```
Standard sensitivity / recall (TPR) measures binary classification performance
(e.g., disease present / absent in medical diagnostics). T3 Utility adapts TPR
to causal reasoning with three key extensions: (1) a three-way output space
(AFFIRM / REJECT / CONDITIONAL) versus binary — CONDITIONAL counts as FN because
it fails to affirm a valid claim; (2) three causal levels with distinct reasoning
depth requirements (L1 observational, L2 interventional, L3 counterfactual); (3)
an adversarial two-turn social-pressure protocol testing whether models reverse
correct affirmations under challenge — this Sycophancy/Skepticism Trap dimension
has no equivalent in standard recall metrics.
```

**`notes`**
```
EMPIRICAL RESULTS: Claude Haiku 3.5: 40% Utility at L1 (60% rejection of valid
claims = Skepticism Trap). GPT-4-Turbo: ~75% Utility at L1. GPT-5.2: exhibits
Ambiguity Trap at L3 (excessive CONDITIONAL responses on determinate cases).
RCA (Recursive Causal Audit) protocol restores Utility without degrading Safety.

LIMITATIONS: Does not distinguish REJECT from CONDITIONAL as separate failure
modes in the aggregate score; both are collapsed into FN. Utility is evaluated
independently from Safety (Specificity), so a high aggregate score may mask
level-specific failures.

USE CASES: Critical for evaluating over-refusal in safety-aligned models deployed
in scientific reasoning, clinical decision support, or policy analysis contexts
where affirming valid causal relationships is essential.

INTERACTIONS: Directly trades off with Safety (Specificity) — models rarely
achieve simultaneously high Utility and Safety. Low Utility combined with high
Safety indicates the Skepticism Trap; high Utility combined with low Safety
indicates the Sycophancy Trap. Wise Refusal Rate complements both by measuring
appropriate abstention on underdetermined cases.
```

---

### Example C — Complexity Classification Walkthrough

**Benchmark: GuardEval**

```
STEP 1 — Check for Popular:
  Citation count = 0 → criterion NOT met
  → Proceed to Step 2

STEP 2 — Check for High:
  Criteria assessed:
    [x] Novel metric development       — 106-category unified taxonomy built
                                         from 13 heterogeneous source datasets
    [x] Complex evaluation methodology — dual prompt-level + response-level
                                         evaluation tracks; cross-dataset
                                         generalisation testing; multi-source
                                         label unification pipeline
    [x] Requires domain expertise      — 106 fine-grained safety categories
                                         spanning emotions, offensiveness,
                                         hate speech, stereotypes, jailbreaks
    [x] Adversarial robustness testing — jailbreak prompt category included
  ≥ 2 criteria met → classify as HIGH

RESULT:
  High — unified 106-category taxonomy from 13 source datasets, dual
  prompt/response moderation tracks, and cross-dataset generalisation evaluation
  constitute novel complex methodology requiring domain expertise.
```

---

## Begin Execution

You have received the following input(s):

```
[INSERT DOI / arXiv URL(s) here]
[OR: PDF attached directly above]
```

Execute Phases 0 through 5 **in sequence**. Do not skip any phase. Do not produce output until Phase 0 research is complete. Ensure all fields are populated before generating the Excel file.
