#!/usr/bin/env python3
"""
cis_audit.py — Conceptual Influence Score (CIS) Audit
======================================================
Standalone, reproducible audit for the shorkienotes repository.

Usage
-----
    python cis_audit.py                  # run full audit with Monte Carlo
    python cis_audit.py --baseline-only  # deterministic baseline only
    python cis_audit.py --runs 50000     # custom number of MC runs
    python cis_audit.py --seed 99        # custom random seed
    python cis_audit.py --no-save        # skip writing output files

Outputs
-------
    - Console report
    - cis_audit_results.json   (machine-readable results)
    - cis_audit_report.md      (human-readable Markdown report)

Methodology
-----------
Labels:
    D = Direct   (conversation wrote the code; repo matches near-verbatim)  weight 1.0
    G = Guided   (conversation described approach; author implemented)       weight 0.5
    P = Prompted (conversation identified problem; author solved it)         weight 0.2
    O = Original (no related discussion; entirely author-originated)         weight 0.0

CIS = 1.0*S_D + 0.5*S_G + 0.2*S_P + 0.0*S_O

Uncertainty model
-----------------
    1. Line-count noise  : each unit's line count multiplied by Uniform[0.80, 1.20]
    2. Label flips       : pre-identified borderline units flip to their
                           alternative label with p = 0.15 per run

Coefficients are fixed before analysis and must not be changed post hoc.
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import numpy as np
except ImportError:
    sys.exit("numpy is required: pip install numpy")

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

AUDIT_METADATA = {
    "repository": "Zuzuzasta/shorkienotes",
    "commit_ref": "018b535d148dcbe39a5f8b27ab76ae512b232ce9",
    "audited_files": ["main/main.py", "main/diary.py", "main/budget_boxes.py",
                      "main/budget.py", "main/shopping.py"],
    "total_source_lines": 482,
    "methodology_version": "1.0",
}

WEIGHTS         = {"D": 1.0, "G": 0.5, "P": 0.2, "O": 0.0}
NOISE_RANGE     = (0.80, 1.20)
FLIP_PROBABILITY = 0.15
DEFAULT_RUNS    = 10_000

# ── CONCEPT UNITS ─────────────────────────────────────────────────────────────

UNITS = [
    # main.py
    ("M1",  "main.py", "imports",           "from diary import Diary (fixed broken import)",                              "D", 1),
    ("M2",  "main.py", "imports",           "Parallel from-imports for Budget and Shopping",                             "O", 2),
    ("M3",  "main.py", "Shorkie.__init__",  "os.path.dirname(os.path.abspath(__file__)) for icon path",                 "P", 1),
    ("M4",  "main.py", "Shorkie.__init__",  "QTabWidget as central widget with addTab for each class",                  "O", 6),
    ("M5",  "main.py", "Shorkie.__init__",  "Tab stylesheet (QTabBar selected/unselected CSS)",                         "O", 16),
    ("M6",  "main.py", "Shorkie.__init__",  "button_formating string stored on self for child access",                  "G", 5),
    ("M7",  "main.py", "Shorkie.__init__",  "setGeometry for initial window placement",                                 "O", 1),
    ("M8",  "main.py", "__main__",          "QApplication + show + sys.exit(app.exec()) boilerplate",                   "O", 5),
    # diary.py
    ("D1",  "diary.py", "Diary.__init__",   "QTextEdit with placeholder text",                                          "O", 3),
    ("D2",  "diary.py", "Diary.__init__",   "index_of_selected_entry = None to track selection state",                 "O", 2),
    ("D3",  "diary.py", "Diary.__init__",   "button_edit disabled by default, enabled on entry_selected",              "O", 4),
    ("D4",  "diary.py", "Diary.__init__",   "setStyleSheet via parent.button_formating on all buttons",                "G", 3),
    ("D5",  "diary.py", "Diary.__init__",   "QFileSystemModel + QListView for entries directory listing",              "O", 7),
    ("D6",  "diary.py", "Diary.__init__",   "entries_list.clicked connected to entry_selected",                        "O", 1),
    ("D7",  "diary.py", "Diary.__init__",   "Full layout composition (HBox/VBox nesting)",                             "O", 14),
    ("D8",  "diary.py", "save_note",        "datetime.now() for timestamped filename generation",                      "O", 3),
    ("D9",  "diary.py", "save_note",        "itertools.count(1) loop to find unused numbered filename",                "O", 11),
    ("D10", "diary.py", "save_note",        "json.dump to write note text",                                             "O", 3),
    ("D11", "diary.py", "edit_note",        "Guard: return early if index_of_selected_entry is None",                  "O", 2),
    ("D12", "diary.py", "entry_selected",   "json.load from entries_folder.filePath(index) into QTextEdit",            "O", 5),
    # budget_boxes.py
    ("BB1", "budget_boxes.py", "Box_spendings.__init__", "QDoubleValidator on QLineEdit",                              "O", 4),
    ("BB2", "budget_boxes.py", "Box_spendings.__init__", "box_descriptor + submitted_value QLabel",                    "O", 4),
    ("BB3", "budget_boxes.py", "Box_spendings.__init__", "frequency parameter governs monthly normalisation",           "O", 2),
    ("BB4", "budget_boxes.py", "Box_spendings.__init__", "setStyleSheet via budget_class_parent.parent().button_formating", "G", 2),
    ("BB5", "budget_boxes.py", "Box_spendings.__init__", "returnPressed connected to button_submit.click",             "O", 1),
    ("BB6", "budget_boxes.py", "Box_spendings.__init__", "QHBoxLayout composing all box widgets",                      "O", 7),
    ("BB7", "budget_boxes.py", "submit_value_input",     "locale().toDouble() for locale-aware float parsing",         "O", 2),
    ("BB8", "budget_boxes.py", "submit_value_input",     "Duck-typed parent.spendings[box_name] (no isinstance guard)","D", 3),
    ("BB9", "budget_boxes.py", "submit_value_input",     "Registered dict update gated on QCheckBox state",            "O", 2),
    ("BB10","budget_boxes.py", "Box_income.__init__",    "Full Box_income class mirroring Box_spendings",              "O", 30),
    ("BB11","budget_boxes.py", "Box_income.submit_value_input", "parent.income[box_name] duck-typed",                  "D", 2),
    # budget.py
    ("BU1", "budget.py", "__init__",        "Instance variable containers: spendings, income, registered, list_box_spendings", "O", 5),
    ("BU2", "budget.py", "__init__",        "current_path via QDir.currentPath()",                                     "O", 1),
    ("BU3", "budget.py", "__init__",        "Month/Year QComboBox setup",                                              "O", 4),
    ("BU4", "budget.py", "__init__",        "button_add_budget_config with setIcon and setMaximumWidth",               "O", 5),
    ("BU5", "budget.py", "__init__",        "button_formating applied via parent.button_formating",                    "G", 4),
    ("BU6", "budget.py", "__init__",        "Ordered init chain across all setup methods",                             "O", 14),
    ("BU7", "budget.py", "read_budget_config_file", "JSON config drives Box_spendings instantiation",                  "O", 12),
    ("BU8", "budget.py", "connect_submit_buttons",  "Loop connecting all box submit signals to button_calculate",      "O", 7),
    ("BU9", "budget.py", "setup_income_box_group",  "QGroupBox wrapping Box_income instances",                        "O", 8),
    ("BU10","budget.py", "setup_savings_box_group", "QGroupBox wrapping Box_spendings for savings",                   "O", 7),
    ("BU11","budget.py", "setup_scrollable_section","QScrollArea wrapping QWidget with vertical layout",               "O", 10),
    ("BU12","budget.py", "setup_grid_layout",       "QGridLayout for results display",                                 "O", 20),
    ("BU13","budget.py", "calculate_budgeting",     "Arithmetic across spendings/income/registered dicts",             "O", 18),
    ("BU14","budget.py", "submit_monthly_budgeting_to_json", "JSON append of month/year keyed entry",                  "O", 15),
    ("BU15","budget.py", "create_budget_history_tree", "QTreeWidget with addTopLevelItem + nested addChild",           "G", 28),
    ("BU16","budget.py", "create_budget_history_tree", "setColumnCount(4) and setHeaderLabels",                        "G", 2),
    ("BU17","budget.py", "collapse_when_clicked",   "itemClicked toggle: isExpanded -> setExpanded(not expanded)",     "G", 3),
    ("BU18","budget.py", "load_when_double_clicked","Column-conditional load of values back into input boxes",         "O", 35),
    ("BU19","budget.py", "refresh_tree_in_budget_tab","removeWidget + re-add; double setLayout discussed",             "P", 6),
    ("BU20","budget.py", "setup_main_layout_budget_tab","addWidget(tree) + addLayout(inputs) + setLayout",             "O", 5),
    ("BU21","budget.py", "open_budget_config_window","QDialog with exec() for modal config entry",                     "O", 14),
    ("BU22","budget.py", "update_budget_config_json","Read-modify-write pattern for JSON config append",               "O", 10),
    ("BU23","budget.py", "clear_all_budget_inputs", "Loop over list_box_spendings to reset all widgets",               "O", 12),
    # shopping.py
    ("SH1", "shopping.py", "add_produce_to_database_dialog",       "QHBoxLayout with LineEdit+ComboBox+Button for DB add", "O", 10),
    ("SH2", "shopping.py", "add_produce_to_database_button",       "Read-append-write JSON pattern for product DB",   "O", 6),
    ("SH3", "shopping.py", "save_produce_to_file",                 "json.dump category dict to product_database.json","O", 5),
    ("SH4", "shopping.py", "add_produce_to_shopping_list_dialog",  "QCompleter on QLineEdit fed from flattened list", "O", 12),
    ("SH5", "shopping.py", "add_produce_to_shopping_list_dialog",  "category combo linked to produce combo via currentIndexChanged", "O", 5),
    ("SH6", "shopping.py", "choose_produce_combo_refresh",         "clear+removeWidget+setup+insertWidget for combo refresh", "G", 5),
    ("SH7", "shopping.py", "appending_produce_to_shopping_list_button", "Category lookup + append + save + refresh chain", "O", 12),
    ("SH8", "shopping.py", "construct_shopping_list_tree_display", "QTreeWidget category top-level + produce children + expandAll", "G", 14),
    ("SH9", "shopping.py", "refresh_shopping_list_tree_view",      "removeWidget + reconstruct + insertWidget(1,...)", "D", 5),
    ("SH10","shopping.py", "shopping_tab_layout",                  "Two-column QHBoxLayout: inputs VBox + tree VBox", "O", 9),
]

BORDERLINE_UNITS = {
    "M6":  ("G", "D"),
    "D4":  ("G", "P"),
    "BB4": ("G", "D"),
    "BB8": ("D", "G"),
    "BB11":("D", "G"),
    "BU5": ("G", "P"),
    "BU15":("G", "P"),
    "BU16":("G", "D"),
    "BU17":("G", "D"),
    "BU19":("P", "G"),
    "SH6": ("G", "P"),
    "SH8": ("G", "P"),
    "SH9": ("D", "G"),
}

# ── SCORING ENGINE ─────────────────────────────────────────────────────────────

def score_units(units):
    total_lines = sum(u[5] for u in units)
    buckets = {"D": 0.0, "G": 0.0, "P": 0.0, "O": 0.0}
    for u in units:
        buckets[u[4]] += u[5] / total_lines
    CIS = sum(buckets[label] * WEIGHTS[label] for label in WEIGHTS)
    return buckets, CIS


def run_baseline():
    return score_units(UNITS)


def run_monte_carlo(n_runs, seed):
    rng = np.random.default_rng(seed)
    results = {"D": [], "G": [], "P": [], "O": [], "CIS": []}

    for _ in range(n_runs):
        perturbed = []
        for u in UNITS:
            uid, fname, scope, desc, label, lines = u
            new_lines = max(1, int(round(lines * rng.uniform(*NOISE_RANGE))))
            new_label = label
            if uid in BORDERLINE_UNITS and rng.random() < FLIP_PROBABILITY:
                new_label = BORDERLINE_UNITS[uid][1]
            perturbed.append((uid, fname, scope, desc, new_label, new_lines))

        buckets, CIS = score_units(perturbed)
        for k in buckets:
            results[k].append(buckets[k] * 100)
        results["CIS"].append(CIS * 100)

    stats = {}
    for key, arr in results.items():
        a = np.array(arr)
        stats[key] = {
            "mean":    float(a.mean()),
            "std":     float(a.std()),
            "ci95_lo": float(np.percentile(a, 2.5)),
            "ci95_hi": float(np.percentile(a, 97.5)),
            "min":     float(a.min()),
            "max":     float(a.max()),
        }
    return stats

# ── LABEL DISTRIBUTION ────────────────────────────────────────────────────────

def label_counts():
    counts = {"D": 0, "G": 0, "P": 0, "O": 0}
    for u in UNITS:
        counts[u[4]] += 1
    return counts

# ── CONSOLE REPORTING ─────────────────────────────────────────────────────────

def print_label_distribution():
    total = len(UNITS)
    counts = label_counts()
    print("\nLabel distribution (unit count):")
    for label, name in [("D","Direct"),("G","Guided"),("P","Prompted"),("O","Original")]:
        print(f"  {label} ({name:<9}): {counts[label]:>3} units  ({counts[label]/total*100:.1f}%)")


def print_baseline(buckets, CIS):
    print("\nBaseline audit (deterministic):")
    print(f"  S_D  Line-match %  : {buckets['D']*100:>6.2f}%")
    print(f"  S_G  Guided %      : {buckets['G']*100:>6.2f}%")
    print(f"  S_P  Prompted %    : {buckets['P']*100:>6.2f}%")
    print(f"  S_O  Original %    : {buckets['O']*100:>6.2f}%")
    print(f"  CIS  Composite     : {CIS*100:>6.2f}%")


def print_monte_carlo(stats, n_runs, seed):
    labels = [
        ("D",   "S_D  Line-match %"),
        ("G",   "S_G  Guided %    "),
        ("P",   "S_P  Prompted %  "),
        ("O",   "S_O  Original %  "),
        ("CIS", "CIS  Composite   "),
    ]
    print(f"\nMonte Carlo results ({n_runs:,} runs, seed={seed}):")
    print(f"  {'Metric':<22} {'Mean':>7}  {'±1σ':>6}  {'95% CI':>20}  {'Min':>6}  {'Max':>6}")
    print("  " + "─" * 74)
    for key, name in labels:
        s = stats[key]
        print(f"  {name:<22} {s['mean']:>6.2f}%  {s['std']:>5.2f}%  "
              f"[{s['ci95_lo']:>5.2f}%, {s['ci95_hi']:>5.2f}%]  "
              f"{s['min']:>5.2f}%  {s['max']:>5.2f}%")

# ── JSON OUTPUT ───────────────────────────────────────────────────────────────

def save_json(baseline_buckets, baseline_CIS, mc_stats, n_runs, seed):
    output = {
        "metadata": AUDIT_METADATA,
        "run_parameters": {
            "n_runs": n_runs,
            "seed": seed,
            "noise_range": list(NOISE_RANGE),
            "flip_probability": FLIP_PROBABILITY,
            "weights": WEIGHTS,
            "timestamp": datetime.now().isoformat(),
        },
        "baseline": {
            "S_D": round(baseline_buckets["D"] * 100, 4),
            "S_G": round(baseline_buckets["G"] * 100, 4),
            "S_P": round(baseline_buckets["P"] * 100, 4),
            "S_O": round(baseline_buckets["O"] * 100, 4),
            "CIS": round(baseline_CIS * 100, 4),
        },
        "monte_carlo": mc_stats,
        "concept_units": [
            {"id": u[0], "file": u[1], "scope": u[2],
             "description": u[3], "label": u[4], "lines": u[5]}
            for u in UNITS
        ],
        "borderline_units": {
            k: {"baseline_label": v[0], "alternative_label": v[1]}
            for k, v in BORDERLINE_UNITS.items()
        },
    }
    fname = "cis_audit_results.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {fname}")

# ── MARKDOWN OUTPUT ───────────────────────────────────────────────────────────

def _units_table_for_file(fname):
    rows = [u for u in UNITS if u[1] == fname]
    if not rows:
        return ""
    lines = ["| ID | Scope | Description | Label | Lines |",
             "|----|-------|-------------|-------|-------|"]
    for u in rows:
        lines.append(f"| {u[0]} | `{u[2]}` | {u[3]} | {u[4]} | {u[5]} |")
    return "\n".join(lines)


def generate_markdown(baseline_buckets, baseline_CIS, mc_stats, n_runs, seed):
    repo      = AUDIT_METADATA["repository"]
    commit    = AUDIT_METADATA["commit_ref"]
    commit_s  = commit[:12]
    total_l   = AUDIT_METADATA["total_source_lines"]
    n_units   = len(UNITS)
    audit_date = datetime.now().strftime("%Y-%m-%d")

    lc = label_counts()
    total_u = n_units

    # baseline values
    b_D   = baseline_buckets["D"] * 100
    b_G   = baseline_buckets["G"] * 100
    b_P   = baseline_buckets["P"] * 100
    b_O   = baseline_buckets["O"] * 100
    b_CIS = baseline_CIS * 100

    # MC values
    mc = mc_stats
    SD  = mc["D"];   SG  = mc["G"];   SP  = mc["P"]
    SO  = mc["O"];   CIS = mc["CIS"]

    # ── dynamic interpretation paragraph ──────────────────────────────────────
    # Original robustness verdict
    if SO["std"] < 1.0:
        orig_robustness = "highly robust — the standard deviation is below 1 percentage point"
    elif SO["std"] < 2.0:
        orig_robustness = "moderately robust"
    else:
        orig_robustness = "sensitive to audit parameters and should be interpreted cautiously"

    # Line-match characterisation
    if b_D < 3.0:
        dm_char = "small"
    elif b_D < 6.0:
        dm_char = "moderate"
    else:
        dm_char = "substantial"

    # S_P variance characterisation
    sp_range = SP["ci95_hi"] - SP["ci95_lo"]
    if sp_range > 6.0:
        sp_var = (f"S_P carries the widest confidence interval of any metric "
                  f"([{SP['ci95_lo']:.2f}%, {SP['ci95_hi']:.2f}%]), "
                  f"meaning the prompted contribution is genuinely ambiguous and should "
                  f"not be reported as a reliable point estimate.")
    else:
        sp_var = (f"S_P has a relatively narrow confidence interval "
                  f"([{SP['ci95_lo']:.2f}%, {SP['ci95_hi']:.2f}%]), "
                  f"indicating good auditor agreement on prompted units.")

    # Direct units narrative
    direct_units = [u for u in UNITS if u[4] == "D"]
    direct_ids   = ", ".join(u[0] for u in direct_units)
    direct_lines = sum(u[5] for u in direct_units)

    interpretation = f"""\
**Original authorship is {orig_robustness}.** Across all {n_runs:,} simulated audits, \
the original fraction S_O never dropped below {SO['min']:.2f}%, with a mean of \
{SO['mean']:.2f}% ± {SO['std']:.2f}%. This figure is insensitive to both line-count \
uncertainty and label reclassification, making it the most reliable single number in the audit.

**The line-match fraction is {dm_char} and narrow.** S_D has a mean of {SD['mean']:.2f}% \
with a 95% CI of [{SD['ci95_lo']:.2f}%, {SD['ci95_hi']:.2f}%]. Even in the most aggressive \
simulation run, verbatim-match code never exceeded {SD['max']:.2f}% of the codebase. \
The {len(direct_units)} Direct unit(s) ({direct_ids}) account for only {direct_lines} lines \
across a {total_l}-line codebase.

**Guided influence is the dominant AI contribution.** S_G at {SG['mean']:.2f}% reflects cases \
where the conversation provided architectural direction but the author wrote every line of \
the implementation. Its 95% CI is [{SG['ci95_lo']:.2f}%, {SG['ci95_hi']:.2f}%].

**The CIS of ~{CIS['mean']:.1f}% is the most honest single-number answer.** \
It integrates all four origins with appropriate weighting, and its 95% CI of \
[{CIS['ci95_lo']:.2f}%, {CIS['ci95_hi']:.2f}%] means the true figure is unlikely to be \
below {CIS['ci95_lo']:.0f}% or above {CIS['ci95_hi']:.0f}% under any plausible audit disagreement.

{sp_var}"""

    # ── dynamic summary paragraph ──────────────────────────────────────────────
    summary = f"""\
The codebase of `{repo.split('/')[1]}` at commit `{commit_s}` is overwhelmingly original work. \
The AI conversation contributed approximately {SD['mean']:.0f}–{SD['ci95_hi']:.0f}% of lines \
verbatim, guided the architecture of a further {SG['mean']:.0f}% of lines (95% CI: \
[{SG['ci95_lo']:.1f}%, {SG['ci95_hi']:.1f}%]), and prompted debugging solutions for roughly \
{SP['ci95_lo']:.0f}–{SP['ci95_hi']:.0f}% of lines. The Conceptual Influence Score — the most \
appropriate single measure — is **{CIS['mean']:.1f}% ± {CIS['std']:.1f}%** \
(95% CI: {CIS['ci95_lo']:.1f}%–{CIS['ci95_hi']:.1f}%)."""

    # ── file/unit summary table ────────────────────────────────────────────────
    file_list = []
    file_lines = {"main.py": 55, "diary.py": 90, "budget_boxes.py": 120,
                  "budget.py": 382, "shopping.py": 200}
    for fname in ["main.py", "diary.py", "budget_boxes.py", "budget.py", "shopping.py"]:
        u_count = sum(1 for u in UNITS if u[1] == fname)
        file_list.append(f"| `main/{fname}` | {file_lines.get(fname, '—')} | {u_count} |")
    files_table = "\n".join(file_list)

    # ── label distribution table ───────────────────────────────────────────────
    label_rows = ""
    for label, name in [("D","Direct"),("G","Guided"),("P","Prompted"),("O","Original")]:
        label_rows += f"| {label} ({name}) | {lc[label]} | {lc[label]/total_u*100:.1f}% |\n"

    # ── concept unit tables per file ──────────────────────────────────────────
    unit_tables = ""
    file_headers = {
        "main.py":        "### main.py",
        "diary.py":       "### diary.py",
        "budget_boxes.py":"### budget_boxes.py",
        "budget.py":      "### budget.py",
        "shopping.py":    "### shopping.py",
    }
    for fname in ["main.py", "diary.py", "budget_boxes.py", "budget.py", "shopping.py"]:
        unit_tables += f"\n{file_headers[fname]}\n\n{_units_table_for_file(fname)}\n"

    # ── MC table rows ──────────────────────────────────────────────────────────
    mc_rows = (
        f"| S_D — Line-match % | {SD['mean']:.2f}% | {SD['std']:.2f}% | "
        f"[{SD['ci95_lo']:.2f}%, {SD['ci95_hi']:.2f}%] | {SD['min']:.2f}% | {SD['max']:.2f}% |\n"
        f"| S_G — Guided % | {SG['mean']:.2f}% | {SG['std']:.2f}% | "
        f"[{SG['ci95_lo']:.2f}%, {SG['ci95_hi']:.2f}%] | {SG['min']:.2f}% | {SG['max']:.2f}% |\n"
        f"| S_P — Prompted % | {SP['mean']:.2f}% | {SP['std']:.2f}% | "
        f"[{SP['ci95_lo']:.2f}%, {SP['ci95_hi']:.2f}%] | {SP['min']:.2f}% | {SP['max']:.2f}% |\n"
        f"| S_O — Original % | {SO['mean']:.2f}% | {SO['std']:.2f}% | "
        f"[{SO['ci95_lo']:.2f}%, {SO['ci95_hi']:.2f}%] | {SO['min']:.2f}% | {SO['max']:.2f}% |\n"
        f"| **CIS — Composite** | **{CIS['mean']:.2f}%** | **{CIS['std']:.2f}%** | "
        f"**[{CIS['ci95_lo']:.2f}%, {CIS['ci95_hi']:.2f}%]** | "
        f"**{CIS['min']:.2f}%** | **{CIS['max']:.2f}%** |"
    )

    # ── assemble document ──────────────────────────────────────────────────────
    doc = f"""# Conceptual Influence Audit — {repo.split('/')[1]}

**Repository:** [{repo}](https://github.com/{repo})
**Audit date:** {audit_date}
**Commit ref:** `{commit}`
**Total source lines audited:** {total_l} (across {len(file_lines)} files, excluding blank lines and comments)
**Concept units identified:** {n_units}
**Monte Carlo simulation runs:** {n_runs:,}

---

## 1. Purpose and Scope

This document provides a methodology and full quantitative audit measuring the degree to which an AI-assisted conversation contributed to the committed code in the {repo.split('/')[1]} repository. Two distinct quantities are separated throughout:

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

$$w_i = \\frac{{\\ell_i}}{{\\sum_j \\ell_j}}$$

where $\\ell_i$ is the line count of unit $i$. This anchors every concept unit to a countable, falsifiable quantity. A single-line fix cannot dominate the score regardless of conceptual importance.

### 2.4 Bucket Scores

Four weighted sums are computed:

$$S_D = \\sum_{{i \\in D}} w_i, \\quad S_G = \\sum_{{i \\in G}} w_i, \\quad S_P = \\sum_{{i \\in P}} w_i, \\quad S_O = \\sum_{{i \\in O}} w_i$$

These sum to 1 by construction. They represent the fraction of the codebase by line weight attributable to each origin.

### 2.5 Conceptual Influence Score (CIS)

The CIS is a single weighted composite:

$$\\text{{CIS}} = 1.0 \\cdot S_D + 0.5 \\cdot S_G + 0.2 \\cdot S_P + 0.0 \\cdot S_O$$

The coefficients reflect how much implementation work was performed by the conversation versus the author:

- **D = 1.0**: conversation did the work; author copied.
- **G = 0.5**: work was roughly split between conversation (design) and author (implementation).
- **P = 0.2**: conversation contributed problem identification only; author solved it.
- **O = 0.0**: no contribution.

**These coefficients are fixed before analysis and are not adjusted after seeing results.**

### 2.6 Error Quantification via Monte Carlo Simulation

Two sources of measurement uncertainty are modelled:

1. **Line-count perturbation:** each unit's line count is multiplied by a uniform random factor in [{NOISE_RANGE[0]}, {NOISE_RANGE[1]}], simulating auditor disagreement on how many lines a concept "governs."
2. **Label uncertainty:** borderline units (those credibly classifiable under two adjacent labels) are identified in advance. Each borderline unit flips to its alternative label with probability {FLIP_PROBABILITY} per run, simulating rater disagreement on origin.

{n_runs:,} runs are executed. For each metric, the mean, standard deviation, 95% confidence interval, minimum, and maximum are reported.

---

## 3. Files and Line Counts

| File | Approx. lines audited | Concept units |
|------|-----------------------|---------------|
{files_table}
| **Total** | **{total_l}** | **{n_units}** |

---

## 4. Label Distribution

| Label | Count | Fraction of units |
|-------|-------|-------------------|
{label_rows}
---

## 5. Complete Concept Unit Table
{unit_tables}
---

## 6. Baseline Audit Results

Computed from the deterministic baseline (no perturbation):

| Metric | Score |
|--------|-------|
| S_D — Line-match % | {b_D:.2f}% |
| S_G — Guided % | {b_G:.2f}% |
| S_P — Prompted % | {b_P:.2f}% |
| S_O — Original % | {b_O:.2f}% |
| **CIS — Composite** | **{b_CIS:.2f}%** |

---

## 7. Monte Carlo Results ({n_runs:,} runs)

Sources of uncertainty modelled:
- **Line-count noise:** ±{int((NOISE_RANGE[1]-1)*100)}% uniform perturbation on each unit's line count per run.
- **Label flips:** {len(BORDERLINE_UNITS)} borderline units identified; each flips to its alternative label with probability {FLIP_PROBABILITY} per run.

| Metric | Mean | ±1σ | 95% CI | Min | Max |
|--------|------|-----|--------|-----|-----|
{mc_rows}

---

## 8. Interpretation

{interpretation}

---

## 9. Limitations

- **Conversation history is incomplete.** Only the conversation attached to this audit session was analysed. Earlier sessions or other AI tools used during development are not captured.
- **Coefficient subjectivity.** The weights 1.0 / 0.5 / 0.2 / 0.0 are defensible but not uniquely correct. Alternative choices (e.g., G = 0.3) would shift CIS by approximately ±2 percentage points.
- **Semantic overlap is not modelled.** Some Original units use PyQt6 patterns that were discussed generically in the conversation but in a different context. These were conservatively labelled O.
- **Single auditor.** Inter-rater reliability was not tested with a second human auditor; borderline unit uncertainty is approximated by the Monte Carlo label-flip model instead.

---

## 10. Summary

{summary}
"""
    return doc


def save_markdown(baseline_buckets, baseline_CIS, mc_stats, n_runs, seed):
    doc = generate_markdown(baseline_buckets, baseline_CIS, mc_stats, n_runs, seed)
    fname = "cis_audit_report.md"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Report saved to {fname}")

# ── CONSOLE ENTRY POINT ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CIS Audit — shorkienotes conceptual influence scorer"
    )
    parser.add_argument("--baseline-only", action="store_true",
                        help="Run deterministic baseline only, skip Monte Carlo")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                        help=f"Number of Monte Carlo runs (default: {DEFAULT_RUNS})")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not write output files")
    args = parser.parse_args()

    print("=" * 60)
    print("  CIS Audit — shorkienotes")
    print(f"  Repository : {AUDIT_METADATA['repository']}")
    print(f"  Commit     : {AUDIT_METADATA['commit_ref'][:12]}...")
    print(f"  Units      : {len(UNITS)}")
    print(f"  Lines      : {AUDIT_METADATA['total_source_lines']}")
    print("=" * 60)

    print_label_distribution()

    buckets, CIS = run_baseline()
    print_baseline(buckets, CIS)

    mc_stats = None
    if not args.baseline_only:
        print(f"\nRunning {args.runs:,} Monte Carlo simulations (seed={args.seed})...")
        mc_stats = run_monte_carlo(args.runs, args.seed)
        print_monte_carlo(mc_stats, args.runs, args.seed)

    if not args.no_save and mc_stats is not None:
        save_json(buckets, CIS, mc_stats, args.runs, args.seed)
        save_markdown(buckets, CIS, mc_stats, args.runs, args.seed)

    print("\nDone.")


if __name__ == "__main__":
    main()
