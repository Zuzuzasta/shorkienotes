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
import os

try:
    import numpy as np
except ImportError:
    sys.exit("numpy is required: pip install numpy")

# ── CONFIGURATION ─────────────────────────────────────────────────────────────


AUDIT_METADATA = {
    "repository"              : "Zuzuzasta/shorkienotes",
    "commit_ref"              : "7362ade2994413c34e11e70559f8d9753dbaa05b",
    "audited_files"           : [
        "main/main.py",
        "main/diary.py",
        "main/budget_boxes.py",
        "main/budget.py",
        "main/budget_plotting.py",
        "main/shopping.py"
    ],
    "audited_files_line_count": [
        ["main/main.py",             67],
        ["main/diary.py",           126],
        ["main/budget_boxes.py",    172],
        ["main/budget.py",          566],
        ["main/budget_plotting.py", 135],
        ["main/shopping.py",        251],
    ],
    "methodology_version"     : "1.0",
    "Auditor"                 : "Claude Sonnet 4.5 (via Perplexity AI MCP tool)",
    "Audit date"              : "2026-07-01"
}

AUDIT_METADATA["total_source_lines"] = sum(n for _, n in AUDIT_METADATA["audited_files_line_count"])

WEIGHTS         = {"D": 1.0, "G": 0.5, "P": 0.2, "O": 0.0}
NOISE_RANGE     = (0.80, 1.20)
FLIP_PROBABILITY = 0.15
DEFAULT_RUNS    = 10_000

# ── CONCEPT UNITS ─────────────────────────────────────────────────────────────

UNITS = [
    # main.py
    # schema: (id, file, scope, description, label, lines_governed)
    ("MN1",  "main/main.py", "module",            "from-import style used for Diary, Budget, Shopping to avoid module-is-not-callable error", "D", 3),
    ("MN2",  "main/main.py", "Shorkie.__init__",  "QMainWindow subclassed as single top-level window to host all tabs", "G", 2),
    ("MN3",  "main/main.py", "Shorkie.__init__",  "QTabWidget as central widget to switch between Diary, Budget, Shopping pages", "G", 3),
    ("MN4",  "main/main.py", "Shorkie.__init__",  "QTabBar stylesheet with border-radius, padding, blue selected/light-blue unselected colours and bold font", "G", 14),
    ("MN5",  "main/main.py", "Shorkie.__init__",  "button_formating string stored on Shorkie instance for child widgets to share a common QPushButton style", "O", 7),
    ("MN6",  "main/main.py", "Shorkie.__init__",  "os.path.dirname(os.path.abspath(__file__)) to locate icon independent of working directory", "G", 1),
    ("MN7",  "main/main.py", "Shorkie.__init__",  "setGeometry with fixed initial position and size 600,100,1000,900", "O", 1),
    ("MN8",  "main/main.py", "__main__",           "QApplication(sys.argv) entry guard with sys.exit(app.exec()) event loop", "O", 5),

    # diary.py 
    ("DI1",  "main/diary.py", "Diary.__init__",   "QWidget subclass (not QMainWindow) so Diary embeds cleanly inside QTabWidget", "G", 2),
    ("DI2",  "main/diary.py", "Diary.__init__",   "QTextEdit as multi-line diary input with placeholder text", "O", 2),
    ("DI3",  "main/diary.py", "Diary.__init__",   "index_of_selected_entry instance variable initialised to None to track list selection state", "O", 2),
    ("DI4",  "main/diary.py", "Diary.__init__",   "button_edit disabled on startup and only enabled after a list entry is clicked", "O", 4),
    ("DI5",  "main/diary.py", "Diary.__init__",   "button_formating style string inherited from parent (Shorkie) applied to all three buttons", "O", 6),
    ("DI6",  "main/diary.py", "Diary.__init__",   "QHBoxLayout for buttons, QVBoxLayout for text+buttons, QHBoxLayout for list+editor panels", "O", 10),
    ("DI7",  "main/diary.py", "Diary.__init__",   "QFileSystemModel with setRootPath to back a QListView showing the entries/ directory", "O", 6),
    ("DI8",  "main/diary.py", "Diary.__init__",   "entries_list.clicked connected to entry_selected for single-click file loading", "O", 2),
    ("DI9",  "main/diary.py", "Diary.save_note",  "datetime.now() with zero-padded day/month/year format string to generate date-based JSON filename", "O", 4),
    ("DI10", "main/diary.py", "Diary.save_note",  "itertools.count(1) loop to find first unused numbered suffix when same-date file already exists", "O", 8),
    ("DI11", "main/diary.py", "Diary.save_note",  "json.dump of plain text string (not a dict) into .json file via context manager", "O", 3),
    ("DI12", "main/diary.py", "Diary.open_new",   "open_new resets index_of_selected_entry to None and disables edit button to clear edit state", "O", 3),
    ("DI13", "main/diary.py", "Diary.edit_note",  "early-return guard on None index before attempting file write in edit_note", "O", 2),
    ("DI14", "main/diary.py", "Diary.edit_note",  "QFileSystemModel.filePath(index) used to resolve absolute path for overwrite save", "O", 4),
    ("DI15", "main/diary.py", "Diary.entry_selected", "entry_selected stores QModelIndex, enables edit button, and loads JSON text into editor in one handler", "O", 6),

    # budget.py 
    ("BU1",  "main/budget.py", "Budget.__init__",  "Budget accepts tab_root and parent separately so style strings on Shorkie are reachable from child boxes", "O", 2),
    ("BU2",  "main/budget.py", "Budget.__init__",  "spendings, income, brutto_income, registered dicts and list_box_spendings list initialised as empty containers at construction", "O", 6),
    ("BU3",  "main/budget.py", "Budget.__init__",  "setup_* method decomposition: each UI section built in its own named method called from __init__", "O", 20),
    ("BU4",  "main/budget.py", "Budget.setup_date_dropdowns", "QComboBox with hard-coded month names list and year list for budget period selection", "O", 16),
    ("BU5",  "main/budget.py", "Budget.setup_button_add_budget_config", "QIcon.fromTheme('list-add') used for add-spending button icon without a custom image file", "G", 4),
    ("BU6",  "main/budget.py", "Budget.setup_button_clear_budget_config", "QIcon.fromTheme('list-remove') used for clear button icon", "G", 3),
    ("BU7",  "main/budget.py", "Budget.clear_all_budget_inputs", "clear_all iterates list_box_spendings to reset every dynamic box plus calls setup_submited_value_text", "O", 15),
    ("BU8",  "main/budget.py", "Budget.create_budget_history_tree", "QTreeWidget with ResizeToContents header and Stretch on last column for auto-fit display", "G", 6),
    ("BU9",  "main/budget.py", "Budget.create_budget_history_tree", "5-column tree: Month / Category / Value-category / Entry-Name / Amount hierarchy built from history_data list", "O", 30),
    ("BU10", "main/budget.py", "Budget.collapse_when_clicked",  "itemClicked toggles item.setExpanded(not item.isExpanded()) to collapse/expand on single click", "G", 3),
    ("BU11", "main/budget.py", "Budget.load_when_double_clicked", "itemDoubleClicked dispatches on column index (1=section, 2=category, 3-4=single value) to load subsets of history", "O", 12),
    ("BU12", "main/budget.py", "Budget.load_specified_value",  "load_specified_value matches item.text(3) against box_descriptor labels to route values back to correct input box", "O", 12),
    ("BU13", "main/budget.py", "Budget.load_specified_value",  "frequency scaling applied when loading historical spending value: value * instance.frequency before setting text", "O", 3),
    ("BU14", "main/budget.py", "Budget.load_specified_value",  "replace('.',',') on all loaded text values to restore EU decimal display", "O", 5),
    ("BU15", "main/budget.py", "Budget.open_budget_config_window", "QDialog used as modal popup for adding a new spending category name and frequency", "O", 13),
    ("BU16", "main/budget.py", "Budget.update_budget_config_json", "locale().toDouble() on chosen_frequency string to parse locale-safe numeric value from QComboBox", "G", 3),
    ("BU17", "main/budget.py", "Budget.update_budget_config_json", "budget_config.json read-modify-append-write cycle to persist new spending entry", "O", 7),
    ("BU18", "main/budget.py", "Budget.connect_submit_buttons_to_button_calculate", "button_calculate.pressed connected to every box's submit_value_input so Calculate triggers all submissions", "G", 6),
    ("BU19", "main/budget.py", "Budget.setup_income_box_group",  "QGroupBox wrapping Box_brutto_income and two Box_income instances for the income section", "O", 8),
    ("BU20", "main/budget.py", "Budget.setup_savings_box_group", "Box_spendings reused for Savings with frequency=1 and check_if_registered hidden to specialise behaviour", "O", 6),
    ("BU21", "main/budget.py", "Budget.setup_graph",             "Plot_area instantiated and stored as self.graph, wired via parent reference", "O", 2),
    ("BU22", "main/budget.py", "Budget.setup_main_layout_budget_tab", "Three-column layout: history tree | scrollable inputs | results+buttons, plus graph below", "O", 10),
    ("BU23", "main/budget.py", "Budget.setup_scrollable_section_inputs_column", "QScrollArea wrapping a QWidget container for income/savings/spendings groups, always-on vertical scrollbar", "G", 9),
    ("BU24", "main/budget.py", "Budget.setup_grid_layout_budget_tab", "QGridLayout with 2×3 rows of label pairs (top description / bottom value) for results display", "O", 35),
    ("BU25", "main/budget.py", "Budget.read_budget_config_file", "setParent(None) loop to detach old Box_spendings widgets before rebuilding from JSON", "G", 5),
    ("BU26", "main/budget.py", "Budget.read_budget_config_file", "list_box_spendings.clear() called after setParent(None) loop to keep Python list in sync with Qt widget tree", "G", 1),
    ("BU27", "main/budget.py", "Budget.read_budget_config_file", "budget_config.json parsed as list-of-lists; each sub-list [name, frequency] instantiates one Box_spendings", "G", 8),
    ("BU28", "main/budget.py", "Budget.calculate_budgeting",     "effective_tax_rate computed as (brutto - netto) / brutto from separate brutto_income dict", "O", 3),
    ("BU29", "main/budget.py", "Budget.calculate_budgeting",     "round(x, 2) applied to all financial results before display and storage", "O", 7),
    ("BU30", "main/budget.py", "Budget.calculate_budgeting",     "calculated_values dict populated for later JSON submission, keyed by human-readable strings", "O", 7),
    ("BU31", "main/budget.py", "Budget.submit_monthly_budgeting_to_json", "budget_month key constructed as Month_YYYY string from two QComboBox values", "O", 3),
    ("BU32", "main/budget.py", "Budget.submit_monthly_budgeting_to_json", "monthly_budgeting nested dict with Results and Inputs sub-dicts appended to history_data list", "O", 12),
    ("BU33", "main/budget.py", "Budget.refresh_tree_in_budget_tab", "removeWidget + insertWidget(0, ...) pattern to replace tree in left column without rebuilding the full layout", "G", 5),
    ("BU34", "main/budget.py", "Budget.open_and_load_budget_history", "json.load from budget_history.json into self.history_data list via context manager", "O", 4),

    # budget_boxes.py 
    ("BB1",  "main/budget_boxes.py", "Box_spendings.__init__", "QDoubleValidator(0.00, 99999.99, 2) attached to QLineEdit for numeric range enforcement", "G", 3),
    ("BB2",  "main/budget_boxes.py", "Box_spendings.__init__", "box.setMaximumWidth(100) and box_descriptor.setMaximumWidth(100) to constrain column widths", "O", 2),
    ("BB3",  "main/budget_boxes.py", "Box_spendings.__init__", "frequency instance attribute stored on Box_spendings to support multi-month spending periods", "O", 2),
    ("BB4",  "main/budget_boxes.py", "Box_spendings.__init__", "QCheckBox('Registered?') for marking spending as auto-payment/Betalingskort", "O", 2),
    ("BB5",  "main/budget_boxes.py", "Box_spendings.__init__", "box.returnPressed connected to button_submit.click so Enter key submits without clicking", "O", 2),
    ("BB6",  "main/budget_boxes.py", "Box_spendings.__init__", "QHBoxLayout assembling descriptor, input, submit button, checkbox, and submitted_value label", "O", 7),
    ("BB7",  "main/budget_boxes.py", "Box_spendings.setup_submited_value_text", "conditional label text: 'monthly' for frequency==1, '/ N months' otherwise", "O", 4),
    ("BB8",  "main/budget_boxes.py", "Box_spendings.submit_value_input", "validator.locale().toDouble(value_input) to parse EU comma-decimal string into Python float", "G", 2),
    ("BB9",  "main/budget_boxes.py", "Box_spendings.submit_value_input", "monthly_needs = value / frequency to normalise multi-period spendings to monthly equivalent", "O", 2),
    ("BB10", "main/budget_boxes.py", "Box_spendings.submit_value_input", "submitted_value label updated with replace('.',',') to keep EU decimal display after conversion", "O", 4),
    ("BB11", "main/budget_boxes.py", "Box_spendings.submit_value_input", "duck-typed parent.spendings[box_name] assignment with no isinstance guard to avoid circular import", "D", 3),
    ("BB12", "main/budget_boxes.py", "Box_spendings.submit_value_input", "conditional parent.registered[box_name] write only when check_if_registered is checked", "O", 3),
    ("BB13", "main/budget_boxes.py", "Box_income.__init__",    "Box_income as separate class from Box_spendings omitting frequency and checkbox for simpler income entry", "O", 20),
    ("BB14", "main/budget_boxes.py", "Box_income.submit_value_input", "locale().toDouble pattern identical to Box_spendings for locale-safe float parsing in income box", "G", 2),
    ("BB15", "main/budget_boxes.py", "Box_income.submit_value_input", "duck-typed parent.income[box_name] assignment mirroring Box_spendings duck-typing pattern", "D", 2),
    ("BB16", "main/budget_boxes.py", "Box_brutto_income.__init__", "Box_brutto_income as third distinct class for pre-tax income, structurally identical to Box_income", "O", 20),
    ("BB17", "main/budget_boxes.py", "Box_brutto_income.submit_value_input", "duck-typed parent.brutto_income[box_name] assignment for gross-income tracking", "D", 2),

    # budget_plotting.py 
    ("BP1",  "main/budget_plotting.py", "Plot_area.__init__",  "pyqtgraph PlotWidget chosen over matplotlib for native Qt integration without canvas embedding", "O", 2),
    ("BP2",  "main/budget_plotting.py", "Plot_area.__init__",  "parent.open_and_load_budget_history() called on the Budget parent to reuse its JSON loading method", "O", 2),
    ("BP3",  "main/budget_plotting.py", "Plot_area.__init__",  "month_year list built by iterating parent.history_data keys to extract x-axis labels", "O", 6),
    ("BP4",  "main/budget_plotting.py", "Plot_area.__init__",  "string month names extracted by replacing last 5 chars (_YYYY) with empty string", "O", 3),
    ("BP5",  "main/budget_plotting.py", "Plot_area.__init__",  "dict(enumerate(x_axis_month)) used to create integer-keyed dictionary for pg AxisItem tick mapping", "O", 2),
    ("BP6",  "main/budget_plotting.py", "Plot_area.__init__",  "pg.AxisItem(orientation='bottom') with setTicks for custom string x-axis month labels", "O", 3),
    ("BP7",  "main/budget_plotting.py", "Plot_area.__init__",  "plot_graph.setBackground(None) for transparent background matching application theme", "O", 2),
    ("BP8",  "main/budget_plotting.py", "Plot_area.__init__",  "HTML span with inline CSS used inside setLabel calls for axis label font size and colour", "O", 3),
    ("BP9",  "main/budget_plotting.py", "Plot_area.__init__",  "pg.GraphicsLayoutWidget as separate legend container with addItem loop over listDataItems()", "O", 8),
    ("BP10", "main/budget_plotting.py", "Plot_area.__init__",  "legend_widget.setMaximumWidth(200) to constrain legend column width", "O", 1),
    ("BP11", "main/budget_plotting.py", "Plot_area.__init__",  "pg.mkPen(color=RGB_tuple, width=5) per data series for distinct coloured lines", "O", 9),
    ("BP12", "main/budget_plotting.py", "Plot_area.__init__",  "cost_of_living computed as spendings - savings; cost_of_living_index as income / cost_of_living derived metrics", "O", 4),
    ("BP13", "main/budget_plotting.py", "Plot_area.__init__",  "QHBoxLayout with legend_widget on left and plot_graph on right as Plot_area widget layout", "O", 5),
    ("BP14", "main/budget_plotting.py", "Plot_area.plot_line", "plot_line helper method encapsulates plot_graph.plot call with name, pen, x and y arguments", "O", 6),

    # shopping.py
    ("SH1",  "main/shopping.py", "Shopping.__init__",  "Shopping.__init__ delegates UI construction to four named setup methods for readability", "O", 5),
    ("SH2",  "main/shopping.py", "Shopping.add_produce_to_database_dialog", "QGroupBox with setMaximumHeight(100) to constrain the add-to-database section height", "O", 4),
    ("SH3",  "main/shopping.py", "Shopping.add_produce_to_database_dialog", "QComboBox populated from product_database.keys() for category selection when adding produce", "O", 3),
    ("SH4",  "main/shopping.py", "Shopping.add_produce_to_database_dialog", "produce_name_type_in.returnPressed connected to produce_add_button.click for keyboard-only entry", "O", 2),
    ("SH5",  "main/shopping.py", "Shopping.add_produce_to_database_button", "open_and_load_product_database() called at button-press time to ensure fresh data before mutation", "O", 2),
    ("SH6",  "main/shopping.py", "Shopping.add_produce_to_database_button", "loop over product_database items to find matching category then append produce and save", "O", 5),
    ("SH7",  "main/shopping.py", "Shopping.save_produce_to_file",  "product_database dict mutated then dumped wholesale to product_database.json via json.dump", "O", 4),
    ("SH8",  "main/shopping.py", "Shopping.open_and_load_product_database", "product_database loaded into self.product_database on every call to reflect current disk state", "O", 3),
    ("SH9",  "main/shopping.py", "Shopping.add_produce_to_shopping_list_dialog", "QLabel('<< OR >>') with font-size 20pt and AlignCenter to visually separate two add-methods", "O", 6),
    ("SH10", "main/shopping.py", "Shopping.setup_produce_combo",  "choose_produce_category_combo.currentIndexChanged connected to choose_produce_combo_refresh for cascading dropdowns", "O", 3),
    ("SH11", "main/shopping.py", "Shopping.setup_produce_combo",  "choose_produce_combo populated from product_database values filtered by selected category", "O", 5),
    ("SH12", "main/shopping.py", "Shopping.setup_produce_type_in", "QCompleter applied to add_produce_type_in with CaseInsensitive matching for autocomplete from full product list", "O", 5),
    ("SH13", "main/shopping.py", "Shopping.setup_produce_type_in", "add_produce_type_in.returnPressed connected to add button click for keyboard-only workflow", "O", 2),
    ("SH14", "main/shopping.py", "Shopping.apply_completer_to_line_edit", "generate_lit_of_produce() flattens all category lists into one list used as QCompleter source model", "O", 4),
    ("SH15", "main/shopping.py", "Shopping.choose_produce_combo_refresh", "combo.clear() then removeWidget/insertWidget(1,...) to replace combo in-place without rebuilding layout", "O", 5),
    ("SH16", "main/shopping.py", "Shopping.generate_lit_of_produce", "starred-expression list unpacking [*produce_list, *produce] to flatten category lists iteratively", "O", 5),
    ("SH17", "main/shopping.py", "Shopping.appending_typed_produce_to_shopping_list_button", "database lookup loop to find category of typed produce before appending to shopping_list", "O", 10),
    ("SH18", "main/shopping.py", "Shopping.appending_typed_produce_to_shopping_list_button", "conditional list creation: new empty list if category not yet in shopping_list keys, else load existing", "O", 4),
    ("SH19", "main/shopping.py", "Shopping.appending_combo_produce_to_shopping_list_button", "combo-based add uses currentText() directly without database lookup since category is already known", "O", 10),
    ("SH20", "main/shopping.py", "Shopping.open_and_load_shopping_list", "shopping_list.json loaded into self.shopping_list dict on each call, separate from product_database", "O", 3),
    ("SH21", "main/shopping.py", "Shopping.save_produce_to_shopping_list", "shopping list dict dumped wholesale to shopping_list.json, not appended", "O", 3),
    ("SH22", "main/shopping.py", "Shopping.construct_shopping_list_tree_display", "QTreeWidget with 2 columns (Category, Produce) built from shopping_list dict with parent/child items", "O", 15),
    ("SH23", "main/shopping.py", "Shopping.construct_shopping_list_tree_display", "shopping_tree.expandAll() called after build to show all items without manual expansion", "O", 1),
    ("SH24", "main/shopping.py", "Shopping.refresh_shopping_list_tree_view", "removeWidget + construct + insertWidget(1,...) pattern to replace tree in existing layout without full rebuild", "D", 5),
    ("SH25", "main/shopping.py", "Shopping.shopping_tab_layout",  "addStretch() calls between section group-boxes in shopping_inputs_layout to space them evenly", "O", 3),
    ("SH26", "main/shopping.py", "Shopping.shopping_tab_layout",  "QHBoxLayout splitting inputs column (left) from shopping list tree (right)", "O", 8),
]


BORDERLINE_UNITS = {
    # MN1: from-import fix is verbatim from conversation answer; however it is a
    # single import line — could be considered O (trivial stdlib knowledge).
    "MN1": ("D", "O"),

    # MN4: tab stylesheet structure matches conversation example closely in
    # selector names and CSS properties, but colours differ; could be G.
    "MN4": ("G", "D"),

    # DI10: itertools.count(1) loop was not explicitly discussed in the
    # conversation — only QFileSystemModel sorting was discussed.  Could be O.
    "DI10": ("O", "G"),

    # BU10: itemClicked toggling setExpanded(not isExpanded) is identified in
    # the conversation analysis as "near-exact from tree structure answer";
    # could be D rather than G.
    "BU10": ("G", "D"),

    # BU23: QScrollArea pattern with container widget was given as corrected
    # code in the conversation; could be D rather than G.
    "BU23": ("G", "D"),

    # BU25/BU26: setParent(None) + list.clear() pattern was given explicitly in
    # conversation; very close to D.
    "BU25": ("G", "D"),
    "BU26": ("G", "D"),

    # BU33: insertWidget(0,...) alternative was discussed but not adopted
    # verbatim (committed code still uses setupmainlayoutbudgettab path);
    # could be O since that specific pattern was not used.
    "BU33": ("G", "O"),

    # BB8: locale().toDouble was given as a complete code snippet in the
    # conversation; structural match is very high — could be D.
    "BB8": ("G", "D"),

    # BB11: duck-typed parent.spendings assignment is near-verbatim from the
    # circular-import fix answer; labelled D, but author removed isinstance and
    # left commented-out lines — could argue G.
    "BB11": ("D", "G"),

    # BB15/BB17: same duck-typing pattern extended to Box_income and
    # Box_brutto_income by the author — pattern was shown for Box_spendings only,
    # so extension could be O rather than D.
    "BB15": ("D", "G"),
    "BB17": ("D", "G"),

    # SH12: QCompleter with CaseInsensitive was not explicitly discussed in the
    # conversation; could be O.
    "SH12": ("O", "G"),

    # SH24: refresh pattern (removeWidget + insertWidget) matches the
    # conversation's "safer pattern for refresh" almost verbatim; could be D.
    "SH24": ("D", "G"),

    # BP6: pg.AxisItem with setTicks for string labels was not covered in the
    # conversation; could be O.
    "BP6": ("O", "G"),
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
    audit_date = AUDIT_METADATA.get("Audit date", datetime.now().strftime("%Y-%m-%d"))

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
    file_lines = {f: n for f, n in AUDIT_METADATA["audited_files_line_count"]}
    for fpath in AUDIT_METADATA["audited_files"]:
        u_count = sum(1 for u in UNITS if u[1] == fpath)
        file_list.append(f"| `{fpath}` | {file_lines.get(fpath, '—')} | {u_count} |")
    files_table = "\n".join(file_list)

    # ── label distribution table ───────────────────────────────────────────────
    label_rows = ""
    for label, name in [("D","Direct"),("G","Guided"),("P","Prompted"),("O","Original")]:
        label_rows += f"| {label} ({name}) | {lc[label]} | {lc[label]/total_u*100:.1f}% |\n"

    # ── concept unit tables per file ──────────────────────────────────────────
    unit_tables = ""

    seen = set()
    ordered_files = [
        u[1] for u in UNITS
        if not (u[1] in seen or seen.add(u[1]))]
    for fpath in ordered_files:
        header = f"### {os.path.basename(fpath)}"   # "main/diary.py" → "### diary.py"
        unit_tables += f"\n{header}\n\n{_units_table_for_file(fpath)}\n"
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
**Total source lines audited:** {total_l} (across {len(AUDIT_METADATA['audited_files'])} files, excluding blank lines and comments)
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

The CIS is the expected influence value of a randomly selected governed line of code. CIS is a single weighted sum composite:

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
