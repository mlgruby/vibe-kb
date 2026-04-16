---
name: kb:compile
description: Compile raw sources into wiki (MVP: manual guidance)
---

# kb:compile

## Purpose

This skill compiles raw source materials into wiki articles with wikilinks and backlinks. For MVP, this is a guided manual process - full automation comes in future phases.

## Prerequisites

- A knowledge base with sources in `raw/` directories
- The `kb` CLI tool installed
- Access to Claude for summarization and wikilink generation

## Workflow

### 1. Identify Knowledge Base and Sources

Ask which KB to compile, then scan for new sources:

```bash
# List raw sources that haven't been compiled yet
ls -la "/Users/satyasheel/Insync/satyasheel@ymail.com/Dropbox/obsidian-satya/knowledge-bases/<kb_name>/raw/"
```

Check each subdirectory (books/, videos/, papers/, articles/) for unprocessed sources.

### 2. Process Each Source

For each uncompiled source:

**A. Read the source content**
```bash
# Read the markdown content
cat "raw/<type>/<filename>.md"

# Read the metadata
cat "raw/<type>/<filename>.meta.json"
```

**B. Generate summary using template**

Read the template:
```bash
cat "wiki/.templates/<type>-summary.md"
```

Use the template to generate a summary that:
- Provides a 250-500 word overview
- Identifies key concepts and creates [[wikilinks]] for them
- Extracts notable quotes/insights
- Suggests related work
- Raises questions for further exploration

**C. Write summary to wiki**

Save the summary to:
```
wiki/summaries/<type>/<filename-summary>.md
```

Use the template format with proper frontmatter:
```yaml
---
type: summary
source_type: book|video|paper|article
source_url: <original_url_or_path>
added: YYYY-MM-DD
authors: <author_names>
---
```

**D. Update indices**

Update `wiki/_sources.md` with:
- Link to the summary: `[[<filename-summary>]]`
- Date added
- Source type
- Brief description

### 3. Create Concept Articles (Optional)

For major concepts mentioned in summaries:

**A. Check if concept article exists**
```bash
# Search for existing concept
kb search <kb_name> "[[concept-name]]"
```

**B. If new concept, create article**

Use the concept template:
```bash
cat "wiki/.templates/concept-article.md"
```

Write to:
```
wiki/concepts/<concept-name>.md
```

**C. Link concept to sources**

In the concept article, list sources that mention this concept in the "Sources" section.

### 4. Commit Changes

After compiling, commit the wiki changes:

```bash
cd "/Users/satyasheel/Insync/satyasheel@ymail.com/Dropbox/obsidian-satya/knowledge-bases/<kb_name>"
git add wiki/
git commit -m "Compile: Add <source-name> summary and concepts"
```

### 5. Report Completion

Tell the user:
- How many sources were compiled
- How many summaries were created
- How many new concept articles were added
- What wikilinks were created

## Examples

### Example 1: Compiling a book
```
User: "Compile the sources in my ML knowledge base"
Assistant: "I found 1 uncompiled book: 'Deep Learning by Ian Goodfellow'. Let me process it..."

[Reads book content, generates summary, creates wikilinks for concepts like [[neural-networks]], [[backpropagation]], [[convolutional-networks]]]

"Created summary: wiki/summaries/books/deep-learning-ian-goodfellow-summary.md
Created 3 new concept articles: [[neural-networks]], [[backpropagation]], [[convolutional-networks]]
Updated wiki/_sources.md"
```

### Example 2: Compiling a YouTube video
```
User: "Compile the new video"
Assistant: [Reads transcript, generates summary, creates wikilinks]

"Compiled video 'Transformers Explained':
- Summary: wiki/summaries/videos/transformers-explained-summary.md
- New concepts: [[attention-mechanism]], [[self-attention]], [[transformer-architecture]]
- Linked to existing concept: [[neural-networks]]"
```

## Notes

### MVP Limitations
- No automatic backlink intelligence (manual wikilink creation)
- No structural wiki changes (no automatic reorganization)
- No conflict detection (assumes clean compilation)
- No batch compilation optimization
- No inter-source connection detection

### Future Enhancements
- Automatic backlink generation and validation
- Concept clustering and wiki restructuring
- Duplicate concept detection and merging
- Cross-source citation linking
- Automatic index generation
- Wiki health checks and maintenance

### Best Practices
- Compile sources in small batches (1-3 at a time)
- Review summaries before committing
- Check for duplicate concepts before creating new ones
- Use consistent naming for wikilinks (lowercase, hyphenated)
- Link liberally - more connections are better
