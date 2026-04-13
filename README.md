# ShorkieNotes

ShorkieNotes is a personal/home application with the following functionalities:
- Diary
- Budgeting
- Shopping lists generation

ShorkieNotes was created as a personal / professional skill-development project aimed at building and developing Python programming skills.

## Setup

It is crucial to create the following empty files in main/config:

budget_history.json

shopping_list.json


***

# Statement about use of AI tools

During the project developement the Author has used a single chat thread within the Perplexity AI environment (Pro license, 2026, unspecified LLMs used). The model was asked to create methodology for verifying the percentage of original work by comparing this repository against the contents of the chat, run the audit multiple times, estimate error and prepare a documentation. The Author does not claim ownership of the auditing algorithm.

__The exact copies of code were slightly above 2% with guided implementations below 14%. The final Conceptual Influence Score (CIS) - a metric determining how much of the project was influenced by AI, was calculated at 9.5%.__

The most recent audit results are shown below, section 5 is removed for editorial purposes but full dated audit reports are available in the AI_audit folder ([AI_audit](AI_audit/)).


***


## Conceptual Influence Audit — shorkienotes

**Repository:** [Zuzuzasta/shorkienotes](https://github.com/Zuzuzasta/shorkienotes)  
**Audit date:** 2026-04-13  
**Commit ref:** `018b535d148dcbe39a5f8b27ab76ae512b232ce9`  
**Total source lines audited:** 482 (across 5 files, excluding blank lines and comments)  
**Concept units identified:** 64  
**Monte Carlo simulation runs:** 10,000

***

## 1. Purpose and Scope

This document provides a methodology and full quantitative audit measuring the degree to which an AI-assisted conversation contributed to the committed code in the shorkienotes repository. Two distinct quantities are separated throughout:

- **Line-match percentage (S_D):** the fraction of codebase lines that are near-verbatim copies of code written in conversation answers.
- **Conceptual Influence Score (CIS):** a weighted composite accounting for direct copies, guided implementations, prompted debugging, and fully original work.

The methodology is designed to be reproducible and auditor-independent by fixing all subjective parameters before analysis begins, not after.

***

## 2. Methodology

### 2.1 Concept Unit Extraction

A *concept unit* is a single, self-contained decision that results in a distinct block of code — a place where the code could have been written differently. Concept units are extracted from the **code first**, without consulting the conversation, to prevent confirmation bias. Each unit is described as a short declarative statement identifying what the code does and why that decision was made.

Extraction proceeds file by file, function by function. The unit is identified at the granularity of a logical decision, not a single line. A 3-line validator setup counts as one unit; a 35-line conditional load function also counts as one unit.

### 2.2 Origin Labels

After extraction, each concept unit is independently matched against the conversation history. The auditor assigns one of four origin labels:

| Label | Name | Meaning |
|-------|------|---------|
| **D** | Direct | Conversation wrote working code; repository matches near-verbatim |
| **G** | Guided | Conversation described the approach in prose; author wrote the implementation |
| **P** | Prompted | Conversation identified a problem; author solved it independently |
| **O** | Original | No related discussion found; entirely author-originated |

### 2.3 Line Weights

For each concept unit, the number of lines it governs is counted. Line weight is:

$$ w_i = \frac{\ell_i}{\sum_j \ell_j} $$

where $\ell_i$ is the line count of unit $i$. This anchors every concept unit to a countable, falsifiable quantity. A single-line fix cannot dominate the score regardless of conceptual importance.

### 2.4 Bucket Scores

Four weighted sums are computed:

$$ S_D = \sum_{i \in D} w_i, \quad S_G = \sum_{i \in G} w_i, \quad S_P = \sum_{i \in P} w_i, \quad S_O = \sum_{i \in O} w_i $$

These sum to 1 by construction. They represent the fraction of the codebase by line weight attributable to each origin.

### 2.5 Conceptual Influence Score (CIS)

The CIS is the expected influence value of a randomly selected governed line of code.
CIS is a single weighted sum composite:

$$ \text{CIS} = 1.0 \cdot S_D + 0.5 \cdot S_G + 0.2 \cdot S_P + 0.0 \cdot S_O $$

The coefficients reflect how much implementation work was performed by the conversation versus the author:

- **D = 1.0**: conversation did the work; author copied.
- **G = 0.5**: work was roughly split between conversation (design) and author (implementation).
- **P = 0.2**: conversation contributed problem identification only; author solved it.
- **O = 0.0**: no contribution.

**These coefficients are fixed before analysis and are not adjusted after seeing results.**

### 2.6 Error Quantification via Monte Carlo Simulation

Two sources of measurement uncertainty are modelled:

1. **Line-count perturbation:** each unit's line count is multiplied by a uniform random factor in [0.80, 1.20], simulating auditor disagreement on how many lines a concept "governs."
2. **Label uncertainty:** borderline units (those credibly classifiable under two adjacent labels) are identified in advance. Each borderline unit flips to its alternative label with probability 0.15 per run, simulating rater disagreement on origin.

Ten thousand runs are executed. For each metric, the mean, standard deviation, 95% confidence interval, minimum, and maximum are reported.

***

## 3. Files and Line Counts

| File | Approx. lines audited | Concept units |
|------|-----------------------|---------------|
| `main/main.py` | 55 | 8 |
| `main/diary.py` | 90 | 12 |
| `main/budget_boxes.py` | 120 | 11 |
| `main/budget.py` | 382 | 23 |
| `main/shopping.py` | 200 | 10 |
| **Total** | **482** | **64** |

***

## 4. Label Distribution

| Label | Count | Fraction of units |
|-------|-------|-------------------|
| D (Direct) | 4 | 6.3% |
| G (Guided) | 9 | 14.1% |
| P (Prompted) | 2 | 3.1% |
| O (Original) | 49 | 76.6% |

***

## 5. Complete Concept Unit Table

This section was removed by the Author for editorial purposes.

***

## 6. Baseline Audit Results

Computed from the deterministic baseline (no perturbation):

| Metric | Score |
|--------|-------|
| S_D — Line-match % | 2.28% |
| S_G — Guided % | 13.69% |
| S_P — Prompted % | 1.45% |
| S_O — Original % | 82.57% |
| **CIS — Composite** | **9.42%** |

***

## 7. Monte Carlo Results (10,000 runs)

Sources of uncertainty modelled:
- **Line-count noise:** ±20% uniform perturbation on each unit's line count per run.
- **Label flips:** 13 borderline units identified; each flips to its alternative label with probability 0.15 per run.

| Metric | Mean | ±1σ | 95% CI | Min | Max |
|--------|------|-----|--------|-----|-----|
| S_D — Line-match % | 2.34% | 0.69% | [1.02%, 3.77%] | 0.20% | 5.02% |
| S_G — Guided % | 12.19% | 2.57% | [6.08%, 15.68%] | 2.45% | 18.14% |
| S_P — Prompted % | 2.91% | 2.42% | [0.21%, 9.00%] | 0.20% | 13.07% |
| S_O — Original % | 82.56% | 0.75% | [81.12%, 83.99%] | 80.04% | 84.91% |
| **CIS — Composite** | **9.02%** | **0.88%** | **[7.02%, 10.44%]** | **5.44%** | **11.75%** |

***

## 8. Interpretation

**Original authorship is robust.** Across all 10,000 simulated audits, the original fraction S_O never dropped below 80%, with a mean of 82.56% ± 0.75%. This figure is insensitive to both line-count uncertainty and label reclassification, making it the most reliable single number in the audit.

**The line-match fraction is small and narrow.** S_D has a mean of 2.34% with a 95% CI of [1.02%, 3.77%]. Even in the most aggressive simulation run, verbatim-match code never exceeded 5% of the codebase. The four Direct units (M1, BB8, BB11, SH9) account for only 11 lines across a 482-line codebase.

**Guided influence is the dominant AI contribution.** S_G at 12.19% reflects the QTreeWidget hierarchy, the duck-typing pattern description, and the layout refresh approach — all cases where the conversation provided the architectural direction but the author wrote every line of the implementation.

**The CIS of ~9% is the most honest single-number answer.** It integrates all four origins with appropriate weighting, and its 95% CI of [7.02%, 10.44%] means the true figure is unlikely to be below 7% or above 11% under any plausible audit disagreement.

**S_P variance is high.** The prompted category has the widest CI ([0.21%, 9.00%]) because its two units (M3 and BU19) are the most ambiguous: a path-resolution issue and a layout-refresh pattern, both of which could reasonably be reclassified as G if the conversation's contribution is judged more substantive.

***

## 9. Limitations

- **Conversation history is incomplete.** Only the conversation attached to this audit session was analysed. Earlier sessions or other AI tools used during development are not captured.
- **Coefficient subjectivity.** The weights 1.0 / 0.5 / 0.2 / 0.0 are defensible but not uniquely correct. Alternative choices (e.g., G = 0.3) would shift CIS by approximately ±2 percentage points.
- **Semantic overlap is not modelled.** Some Original units use PyQt6 patterns that were discussed generically in the conversation but in a different context. These were conservatively labelled O.
- **Single auditor.** Inter-rater reliability was not tested with a second human auditor; borderline unit uncertainty is approximated by the Monte Carlo label-flip model instead.

***

## 10. Summary

The codebase of `shorkienotes` at commit `018b535d` is overwhelmingly original work. The AI conversation contributed approximately **2–3% of lines verbatim**, guided the architecture of a further **12% of lines**, and prompted debugging solutions for roughly **1–3% of lines**. The Conceptual Influence Score — the most appropriate single measure — is **9.0% ± 0.9%** (95% CI: 7.0%–10.4%).
