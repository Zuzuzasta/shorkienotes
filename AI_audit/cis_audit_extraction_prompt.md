# CIS Audit — Concept Unit Extraction Prompt

## Purpose

This prompt is designed to be given to an AI assistant alongside a GitHub
repository link. Its output is a Python-ready `UNITS` list and
`BORDERLINE_UNITS` dict that can be pasted directly into `cis_audit.py`.

---

## How to use

1. Open a fresh conversation with an AI assistant.
2. Paste this entire prompt.
3. Provide the repository link and the conversation history link (or paste
   the conversation text directly).
4. The assistant returns a ready-to-paste Python block.

---

## The Prompt

---

You are performing a Conceptual Influence Audit on a Python codebase.
Your task has two parts: construct the `UNITS` table and the
`BORDERLINE_UNITS` dict for use in `cis_audit.py`.

### Inputs you will receive

1. **Repository link** — the GitHub repository to audit.
2. **Conversation history** — the AI-assisted chat session(s) that
   accompanied development of the code. Provide this as a link, a
   pasted transcript, or describe which topics were discussed if the
   full log is unavailable.

---

### Step 1 — Read the code first, before looking at the conversation

Ignore the code in AI_Audit folder (cis_audit.py).

For every other Python source file in the repository:

a. Read the file completely.
b. Identify every **decision point** — a place where the code could
   have been written differently. A decision point is one concept unit.
c. Write each unit as a short declarative statement in the form:
   *"[what the code does] [why this specific approach was chosen if
   apparent]"*
   Examples of well-formed descriptions:
   - "QDoubleValidator on QLineEdit for numeric input validation"
   - "itertools.count(1) loop to find first unused numbered filename"
   - "Duck-typed parent.spendings[key] with no isinstance guard"
   Bad descriptions (too vague):
   - "validates input" — does not say how
   - "saves data" — does not say how or where

d. Count the lines of code that exist **because** of that decision.
   Include all lines in the block, not just the key line. Blank lines
   and comments inside the block count; blank lines between blocks
   do not.

Do **not** look at the conversation history yet.

---

### Step 2 — Assign origin labels

Now read the conversation history. For each unit, assign one label:

| Label | Assign when |
|-------|-------------|
| **D** | The conversation contained working code for this unit and the repository code matches it near-verbatim (same structure, same API calls, same variable names or clearly renamed). Threshold: >70% structural similarity. |
| **G** | The conversation described the approach, pattern, or API in prose or pseudocode, but the author wrote the actual implementation. The conversation is the source of the *idea*; the author is the source of the *code*. |
| **P** | The conversation identified a bug, error message, or incorrect behaviour. The author then solved it independently. The conversation contributed problem identification only. |
| **O** | No related discussion found in the conversation history. The unit is entirely author-originated. When in doubt between O and G, assign O. |

**Tie-breaking rules:**
- If a concept was mentioned in passing (one sentence) but not
  explained, assign O.
- If the same concept appears in multiple conversation turns with
  increasing detail, assign G.
- If the conversation gave complete code and the author used a
  different but clearly inspired implementation, assign G, not D.
- Assign D only when you could plausibly argue plagiarism in a
  strict academic sense.

---

### Step 3 — Identify borderline units

After all labels are assigned, review the full list and flag any unit
where a reasonable second auditor could assign a different label.
Specifically, flag a unit as borderline if it meets any of these
criteria:

- It is labelled D but the conversation code and repository code
  differ in more than variable names.
- It is labelled G but the conversation only gave a one-line hint
  rather than a full explanation.
- It is labelled P but the conversation's debugging answer was
  detailed enough that it could be considered G.
- It is labelled O but the same general pattern was discussed
  somewhere in the conversation, even in a different context.

For each borderline unit, identify the most plausible alternative
label (the one a second auditor would most likely assign).

---

### Step 4 — Output format

Return **only** the following Python block. No prose, no explanation,
no markdown — just the raw Python that can be pasted into `cis_audit.py`.

```python
# Audited repository : <repo URL>
# Audited commit     : <full commit SHA or branch@date>
# Conversation scope : <brief description of what conversation covered>
# Auditor            : <AI model name and version>
# Audit date         : <YYYY-MM-DD>
# Total units        : <N>
# Total lines        : <N>

UNITS = [
    # ── <filename> ──────────────────────────────────────────
    # schema: (id, file, scope, description, label, lines_governed)
    ("X1", "filename.py", "ClassName.method", "description", "O", 5),
    ...
]

BORDERLINE_UNITS = {
    # schema: unit_id: (baseline_label, alternative_label)
    "X1": ("G", "D"),
    ...
}

# Update AUDIT_METADATA in cis_audit.py:
# "repository"         : "<owner/repo>"
# "commit_ref"         : "<full SHA>"
# "audited_files"      : [<list of relative paths>]
# "total_source_lines" : <N>
```

**ID convention:** use a two-letter file prefix + integer, e.g.
`M1`–`MN` for `main.py`, `D1`–`DN` for `diary.py`, etc.
For repositories with many files, use three letters.

**One unit per row.** Do not group multiple decisions into one unit.
Do not split one decision across multiple units.

**Lines governed:** count lines in the block controlled by this
decision. Do not count blank lines between blocks. Minimum 1.

---

### Quality checks before returning output

- Every file has at least one unit.
- No two units have the same ID.
- All labels are one of: D, G, P, O.
- All BORDERLINE_UNITS entries reference IDs present in UNITS.
- The baseline label in each BORDERLINE_UNITS entry matches the
  label assigned in UNITS.
- Total units > 10 for any non-trivial file (>100 lines).
- No unit description is shorter than 5 words.
- D units are fewer than 15% of total units for a typical
  AI-assisted project. If D exceeds 15%, re-examine your
  threshold — you are likely being too generous with D.

---

