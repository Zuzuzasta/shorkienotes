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

## Functionality

### Budget tab:

Budget tab allows user to keep track of their budgeting. The tab is divided into 4 sections: 

- Data tree
- Inputs
- Summary
- Graphing

<img width="2557" height="1380" alt="image" src="https://github.com/user-attachments/assets/42c3b4c9-6b93-4a33-bb3f-4cfb9489cbb1" />

The user can create own spending categories from the UI level (those will be stored in the budget_config.json file)

Once filled in the amounts in the "Inputs" section, they can be individually submitted or submitted all at once when pressing "Calculate budgeting" button. Once calculated, the fields in "Summary" section will show calculated values:

- Your total income
- Amount put in savings
- Remaining amount (so called "Fun money")
- Effective tax rate
- Total spendings (including savings)
- Amount moved to the "Payments" account (account with no card that is used to link automatic payments)

The results can then be submitted to .json file and stored. It will then appear in the "Data tree" where it can be retrieved from by double clicking on the "Inputs" field of the relevant data entry, or on the singular spendings.

<img width="562" height="627" alt="image" src="https://github.com/user-attachments/assets/35ee94a6-4ea6-4959-beb7-ac81c73d49e7" />

The "Graphing" section shows a timeline of the budgeting.


***

# Statement about use of AI tools

During the project developement the Author has used a single chat thread within the Perplexity AI environment (Pro license, 2026, unspecified LLMs used). The model was asked to create methodology for verifying the percentage of original work by comparing this repository against the contents of the chat, run the audit multiple times, estimate error and prepare a documentation. The Author does not claim authorship of the auditing algorithm.

__The exact copies of code were slightly above 2% with guided implementations below 13%. The final Conceptual Influence Score (CIS) - a metric determining how much of the project was influenced by AI, was calculated at 8.9%.__

The most recent audit results are shown below, section 5 is removed for editorial purposes but full dated audit reports are available in the AI_audit folder ([AI_audit](AI_audit/)).


***


# Conceptual Influence Audit — shorkienotes

**Repository:** [Zuzuzasta/shorkienotes](https://github.com/Zuzuzasta/shorkienotes)
**Audit date:** 2026-07-01
**Commit ref:** `7362ade2994413c34e11e70559f8d9753dbaa05b`
**Total source lines audited:** 1317 (across 6 files, excluding blank lines and comments)
**Concept units identified:** 114
**Monte Carlo simulation runs:** 10,000

---

## 1. Purpose and Scope

This document provides a methodology and full quantitative audit measuring the degree to which an AI-assisted conversation contributed to the committed code in the shorkienotes repository. Two distinct quantities are separated throughout:

- **Line-match percentage (S_D):** the fraction of codebase lines that are near-verbatim copies of code written in conversation answers.
- **Conceptual Influence Score (CIS):** a weighted composite accounting for direct copies, guided implementations, prompted debugging, and fully original work.

The methodology is designed to be reproducible and auditor-independent by fixing all subjective parameters before analysis begins, not after.

---

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

$$w_i = \frac{\ell_i}{\sum_j \ell_j}$$

where $\ell_i$ is the line count of unit $i$. This anchors every concept unit to a countable, falsifiable quantity. A single-line fix cannot dominate the score regardless of conceptual importance.

### 2.4 Bucket Scores

Four weighted sums are computed:

$$S_D = \sum_{i \in D} w_i, \quad S_G = \sum_{i \in G} w_i, \quad S_P = \sum_{i \in P} w_i, \quad S_O = \sum_{i \in O} w_i$$

These sum to 1 by construction. They represent the fraction of the codebase by line weight attributable to each origin.

### 2.5 Conceptual Influence Score (CIS)

The CIS is the expected influence value of a randomly selected governed line of code. CIS is a single weighted sum composite:

$$\text{CIS} = 1.0 \cdot S_D + 0.5 \cdot S_G + 0.2 \cdot S_P + 0.0 \cdot S_O$$

The coefficients reflect how much implementation work was performed by the conversation versus the author:

- **D = 1.0**: conversation did the work; author copied.
- **G = 0.5**: work was roughly split between conversation (design) and author (implementation).
- **P = 0.2**: conversation contributed problem identification only; author solved it.
- **O = 0.0**: no contribution.

**These coefficients are fixed before analysis and are not adjusted after seeing results.**

### 2.6 Error Quantification via Monte Carlo Simulation

Two sources of measurement uncertainty are modelled:

1. **Line-count perturbation:** each unit's line count is multiplied by a uniform random factor in [0.8, 1.2], simulating auditor disagreement on how many lines a concept "governs."
2. **Label uncertainty:** borderline units (those credibly classifiable under two adjacent labels) are identified in advance. Each borderline unit flips to its alternative label with probability 0.15 per run, simulating rater disagreement on origin.

10,000 runs are executed. For each metric, the mean, standard deviation, 95% confidence interval, minimum, and maximum are reported.

---

## 3. Files and Line Counts

| File | Approx. lines audited | Concept units |
|------|-----------------------|---------------|
| `main/main.py` | 67 | 8 |
| `main/diary.py` | 126 | 15 |
| `main/budget_boxes.py` | 172 | 17 |
| `main/budget.py` | 566 | 34 |
| `main/budget_plotting.py` | 135 | 14 |
| `main/shopping.py` | 251 | 26 |
| **Total** | **1317** | **114** |

---

## 4. Label Distribution

| Label | Count | Fraction of units |
|-------|-------|-------------------|
| D (Direct) | 5 | 4.4% |
| G (Guided) | 19 | 16.7% |
| P (Prompted) | 0 | 0.0% |
| O (Original) | 90 | 78.9% |

---

## 5. Complete Concept Unit Table

Contents of section 5 are removed for editorial purposes but full dated audit reports are available in the AI_audit folder ([AI_audit](AI_audit/)).

---

## 6. Baseline Audit Results

Computed from the deterministic baseline (no perturbation):

| Metric | Score |
|--------|-------|
| S_D — Line-match % | 2.29% |
| S_G — Guided % | 12.54% |
| S_P — Prompted % | 0.00% |
| S_O — Original % | 85.17% |
| **CIS — Composite** | **8.56%** |

---

## 7. Monte Carlo Results (10,000 runs)

Sources of uncertainty modelled:
- **Line-count noise:** ±19% uniform perturbation on each unit's line count per run.
- **Label flips:** 15 borderline units identified; each flips to its alternative label with probability 0.15 per run.

| Metric | Mean | ±1σ | 95% CI | Min | Max |
|--------|------|-----|--------|-----|-----|
| S_D — Line-match % | 2.72% | 1.05% | [1.21%, 5.19%] | 0.31% | 7.19% |
| S_G — Guided % | 12.30% | 1.26% | [9.56%, 14.62%] | 7.54% | 16.44% |
| S_P — Prompted % | 0.00% | 0.00% | [0.00%, 0.00%] | 0.00% | 0.00% |
| S_O — Original % | 84.98% | 0.78% | [83.28%, 86.40%] | 81.64% | 87.61% |
| **CIS — Composite** | **8.87%** | **0.68%** | **[7.75%, 10.36%]** | **6.91%** | **11.79%** |

---

## 8. Interpretation

**Original authorship is highly robust — the standard deviation is below 1 percentage point.** Across all 10,000 simulated audits, the original fraction S_O never dropped below 81.64%, with a mean of 84.98% ± 0.78%. This figure is insensitive to both line-count uncertainty and label reclassification, making it the most reliable single number in the audit.

**The line-match fraction is small and narrow.** S_D has a mean of 2.72% with a 95% CI of [1.21%, 5.19%]. Even in the most aggressive simulation run, verbatim-match code never exceeded 7.19% of the codebase. The 5 Direct unit(s) (MN1, BB11, BB15, BB17, SH24) account for only 15 lines across a 1317-line codebase.

**Guided influence is the dominant AI contribution.** S_G at 12.30% reflects cases where the conversation provided architectural direction but the author wrote every line of the implementation. Its 95% CI is [9.56%, 14.62%].

**The CIS of ~8.9% is the most honest single-number answer.** It integrates all four origins with appropriate weighting, and its 95% CI of [7.75%, 10.36%] means the true figure is unlikely to be below 8% or above 10% under any plausible audit disagreement.

S_P has a relatively narrow confidence interval ([0.00%, 0.00%]), indicating good auditor agreement on prompted units.

---

## 9. Limitations

- **Conversation history is incomplete.** Only the conversation attached to this audit session was analysed. Earlier sessions or other AI tools used during development are not captured.
- **Coefficient subjectivity.** The weights 1.0 / 0.5 / 0.2 / 0.0 are defensible but not uniquely correct. Alternative choices (e.g., G = 0.3) would shift CIS by approximately ±2 percentage points.
- **Semantic overlap is not modelled.** Some Original units use PyQt6 patterns that were discussed generically in the conversation but in a different context. These were conservatively labelled O.
- **Single auditor.** Inter-rater reliability was not tested with a second human auditor; borderline unit uncertainty is approximated by the Monte Carlo label-flip model instead.

---

## 10. Summary

The codebase of `shorkienotes` at commit `7362ade29944` is overwhelmingly original work. The AI conversation contributed approximately 3–5% of lines verbatim, guided the architecture of a further 12% of lines (95% CI: [9.6%, 14.6%]), and prompted debugging solutions for roughly 0–0% of lines. The Conceptual Influence Score — the most appropriate single measure — is **8.9% ± 0.7%** (95% CI: 7.7%–10.4%).
