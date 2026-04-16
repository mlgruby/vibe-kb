---
name: kb:health-check
description: Audit a knowledge base for structural issues and suggest fixes
---

# kb:health-check

## Purpose

This skill runs a health audit of a knowledge base wiki. It detects dead links,
orphaned articles, unindexed sources, missing metadata, and template drift, then
reports findings by severity and offers to auto-fix the easy ones.

## Prerequisites

- A knowledge base created with `kb create`
- The `kb` CLI installed
- Vault path: `~/obsidian-vault/` (default)

---

## Workflow

### 1. Identify which KB to check

Ask: "Which knowledge base should I check? (or check all?)"

If "all", list KBs:
```bash
ls ~/obsidian-vault/knowledge-bases/
```
Run the check against each directory in sequence.

### 2. Get basic counts with the CLI

```bash
kb stats <kb_name> --vault-path ~/obsidian-vault/
```

Note the article count, source count, and last compile date before proceeding.

### 3. Scan the wiki structure

Read the directory tree to understand what is present:
```bash
ls ~/obsidian-vault/knowledge-bases/<kb_name>/wiki/
ls ~/obsidian-vault/knowledge-bases/<kb_name>/wiki/concepts/
ls ~/obsidian-vault/knowledge-bases/<kb_name>/wiki/summaries/
ls ~/obsidian-vault/knowledge-bases/<kb_name>/raw/
```

### 4. Run each health check

Perform the following checks by reading files directly. For each issue found,
record: severity (critical / warning / suggestion), check name, affected file,
and details.

#### 4a. Dead links

Scan every non-hidden, non-template `.md` file under `wiki/` for `[[wikilink]]`
patterns. For each target, check whether a `.md` file with that stem exists
anywhere under `wiki/`.

- Skip self-references (file links to itself).
- Skip `[[_index]]`, `[[_sources]]`, `[[_concepts]]`.
- Flag missing targets as **warning / dead_links**.

Example: `wiki/article.md` contains `[[TransformerArchitecture]]` but
`wiki/concepts/TransformerArchitecture.md` does not exist → dead link.

#### 4b. Orphaned articles

List all non-hidden, non-index `.md` files under `wiki/`. For each file, count
how many other files contain `[[<stem>]]` as a wikilink target. Files with zero
incoming references are **suggestion / orphaned_articles**.

Skip `_index.md`, `_sources.md`, `_concepts.md` from orphan checks.

#### 4c. Unindexed sources

List all `.md`, `.pdf`, and `.epub` files under `raw/`. For each, derive the
slug by stripping a leading `YYYY-MM-DD-` date prefix and the file extension.
Check whether any file under `wiki/summaries/` contains that slug in its name.
Sources with no matching summary are **warning / unindexed_sources**.

#### 4d. Missing metadata

Check every non-hidden, non-template `.md` file under `wiki/` for a YAML
frontmatter block (file begins with `---`). Files missing frontmatter are
**suggestion / missing_metadata**.

#### 4e. Template drift

Check `wiki/concepts/*.md` files for required sections:
`## Overview`, `## Key Ideas`, `## Sources`

Check `wiki/summaries/**/*.md` files for:
`## Summary`, `## Key Concepts`

Missing required sections are **suggestion / template_drift**.

### 5. Present findings by severity

Report in this order: critical → warnings → suggestions.

Format:
```
== HEALTH CHECK: <kb_name> ==
Checked: <timestamp>

Stats
  Articles : <n>
  Sources  : <n>
  Concepts : <n>
  Wikilinks: <n>

CRITICAL (n)
  [none] / [list issues]

WARNINGS (n)
  ⚠ dead_links: [[DeadPage]] in wiki/article.md
  ⚠ unindexed_sources: raw/my-paper.md has no wiki summary

SUGGESTIONS (n)
  · orphaned_articles: wiki/concepts/old-concept.md – no incoming links
  · missing_metadata: wiki/topics/overview.md – add frontmatter
  · template_drift: wiki/concepts/ml.md – missing ## Overview, ## Sources
```

If there are no issues: "No issues found. Knowledge base looks healthy."

### 6. Offer auto-fixes

After presenting findings, offer to fix the simple cases:

**Dead links** – For each dead link `[[Target]]`:
> "Create a stub article `wiki/concepts/Target.md`? (yes / no / skip all)"
If yes, create a minimal stub:
```markdown
---
type: concept
created: <today>
---

# Target

## Overview
_Stub article — fill in definition._

## Key Ideas
-

## Sources
-
```

**Unindexed sources** – For each unindexed source:
> "Add `raw/<file>` to the compile queue? This will remind you to run kb:compile."
If yes, append a note to `wiki/_sources.md` (or create it if missing):
```
- [ ] Compile: [[<slug>]] — raw/<file>
```

**Missing metadata** – For each article without frontmatter:
> "Generate frontmatter for `wiki/<file>`?"
If yes, read the file title (first `# Heading`) and prepend:
```yaml
---
type: concept
created: <today>
tags: []
---
```

Do not auto-fix: orphaned articles, template drift, or inconsistent data.
Those require human judgment — list them for review instead.

### 7. Concept gap detection

After checking, scan all summary files for `[[wikilinks]]`. If a link target
appears in 3 or more summaries but has no concept article under
`wiki/concepts/`, suggest creating one:

> "The concept '[[AttentionMechanism]]' appears in 4 summaries but has no
> concept article. Create it?"

### 8. Show final stats

After all fixes are applied (or declined), print a summary:

```
Health check complete.
  Issues resolved : <n>
  Issues remaining: <n>
  Next step: run /kb:compile to process unindexed sources
```

---

## Examples

### Example 1: Clean KB
```
User: /kb:health-check
Assistant: Which KB? "ml-research"

[scans wiki, runs all checks]

== HEALTH CHECK: ml-research ==
Stats: 24 articles, 8 sources, 12 concepts, 87 wikilinks

No issues found. Knowledge base looks healthy.
```

### Example 2: KB with issues
```
User: /kb:health-check
Assistant: Which KB? "quantum-research"

[scans wiki]

WARNINGS (2)
  ⚠ dead_links: [[QuantumEntanglement]] in wiki/summaries/papers/bell-theorem.md
  ⚠ unindexed_sources: raw/papers/2024-03-10-shor-algorithm.pdf has no wiki summary

SUGGESTIONS (3)
  · orphaned_articles: wiki/concepts/old-qubits.md – no incoming links
  · missing_metadata: wiki/topics/overview.md – add frontmatter
  · template_drift: wiki/concepts/superposition.md – missing ## Sources

Create stub for [[QuantumEntanglement]]? yes
→ Created wiki/concepts/QuantumEntanglement.md

Add raw/papers/2024-03-10-shor-algorithm.pdf to compile queue? yes
→ Added to wiki/_sources.md

Generate frontmatter for wiki/topics/overview.md? yes
→ Added frontmatter block

Health check complete.
  Issues resolved : 3
  Issues remaining: 2 (orphaned article, template drift — review manually)
```

---

## Notes

- This skill reads files directly; it does not call `run_health_check()` at
  runtime (the Python module is for programmatic use; the skill does the same
  logic via file inspection).
- Skip symlinks in all file traversal — they are a security risk.
- Skip files and directories beginning with `.` or `_` (templates, index files).
- Always use UTF-8 encoding when reading or writing files.
- Do not auto-fix orphaned articles or template drift without user confirmation.
- When in doubt, list an issue rather than silently skipping it.
