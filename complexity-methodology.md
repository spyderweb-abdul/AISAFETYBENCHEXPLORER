
## Complexity Classification Rules

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

## Extended Classification Criteria & Methodology

### 1. POPULAR Complexity Level

**Definition:** Foundational benchmarks with exceptional community adoption and impact

**Primary Indicators:**
- **Citation count:** >1000 citations (foundational threshold)
- **Community reach:** Multiple derived benchmarks and variants
- **Adoption breadth:** Referenced in multiple frameworks and papers
- **GitHub presence:** High star count (>200) and active community
- **Leaderboard presence:** Official leaderboards or evaluation platforms
- **Multi-language variants:** Translated versions indicating global adoption

**Characteristics:**
1. Used as de facto standards in safety research
2. Cited in 95%+ of recent safety evaluation papers
3. Multiple derived benchmarks and improvements
4. Integrated into major evaluation frameworks
5. Long-term citation velocity (increasing over time)
6. Community contributions and extensions

**Examples:**
- **TruthfulQA** (2,718 citations) - Factuality benchmark pioneer
- **RealToxicityPrompts** (1,656 citations) - Toxicity detection standard
- **StereoSet** (1,435 citations) - Gender/occupational bias assessment
- **WinoBias** (1,366 citations) - Coreference gender bias
- **CrowS-Pairs** (955 citations) - Social bias measurement
- **HaluEval** (685 citations) - Hallucination evaluation
- **BBQ** (644 citations) - Multi-faceted bias benchmark

---

### 2. HIGH Complexity Level

**Definition:** Advanced benchmarks requiring sophisticated evaluation infrastructure

**Primary Indicators:**
- **Task complexity:** Multi-step reasoning, adversarial components, or subjective generation
- **Evaluation infrastructure:** Requires LLM classifiers, human annotators, or specialized judges
- **Safety-critical focus:** Risk-critical decision scenarios or behavioral evaluation
- **Behavioral tracking:** Requires monitoring LLM responses over time or contexts
- **Citation count:** 100-600 citations (active research area)
- **GitHub indicators:** Active repositories (30-150 stars), multiple contributors

**Technical Characteristics:**
1. **Multi-hop reasoning:** Requires chains of thought or multi-step evaluation
2. **Adversarial components:** Specifically designed to test robustness
3. **Subjective generation tasks:** Open-ended responses requiring nuanced evaluation
4. **Risk-critical scenarios:** Safety-critical applications or decision-making contexts
5. **Complex behavioral metrics:** More than simple classification accuracy
6. **Requires sophisticated evaluation:** LLM-based judges, classifier ensembles, or human expertise
7. **Domain specialization:** Medical, legal, financial, or other specialized safety domains
8. **Contextual dependency:** Requires understanding context or dialog history

---

### 3. MEDIUM Complexity Level

**Definition:** Balanced benchmarks with moderate reasoning requirements and mixed evaluation approaches

**Primary Indicators:**
- **Task characteristics:** Some multi-step reasoning, limited adversariality
- **Evaluation mix:** Combination of objective metrics and subjective assessment
- **Citation count:** 100-500 citations (established research area)
- **GitHub presence:** Moderate activity (20-100 stars), growing community
- **Reasoning depth:** Moderate context or chain-of-thought requirements
- **Safety impact:** Important but not immediately risk-critical scenarios

**Technical Characteristics:**
1. **Moderate reasoning chains:** 2-3 step reasoning or context understanding
2. **Specific domain focus:** Bias, toxicity, factuality, but not multi-dimensional
3. **Clear evaluation metrics:** Established scoring systems and benchmarking approaches
4. **Dataset-driven:** Primarily data-focused with standardized evaluation
5. **Some adversarial components:** But not primarily designed for adversarial robustness
6. **Objective scoring possible:** Though may include subjective human evaluation
7. **Limited context requirements:** Single-turn or limited multi-turn evaluation

---

### 4. LOW Complexity Level

**Definition:** Single-step, objective benchmarks with limited reasoning or adversarial components

**Primary Indicators:**
- **Task type:** Single-step classification, objective matching, or simple evaluation
- **Reasoning depth:** Minimal or no multi-step reasoning required
- **Safety impact:** Limited or specialized safety concerns
- **Citation count:** <100 citations (newer or niche benchmarks)
- **GitHub presence:** Minimal activity (<20 stars) or no active development
- **Evaluation:** Straightforward scoring metrics, minimal subjective assessment

**Technical Characteristics:**
1. **Simple evaluation:** Classification accuracy or F1-score primarily
2. **Single-step logic:** No reasoning chains or context integration
3. **Objective metrics:** No human evaluation or subjective components
4. **Limited dataset scope:** Often <1000 examples
5. **No adversarial components:** Tests knowledge or consistency rather than robustness
6. **Specific/narrow focus:** Single safety dimension or use case
7. **Straightforward implementation:** Can be evaluated with simple scripts

---
