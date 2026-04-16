---
name: kb:create
description: Initialize a new knowledge base with conversational flow
---

# kb:create

## Purpose

This skill guides you through creating a new knowledge base in your Obsidian vault. It sets up the directory structure, templates, and configuration needed to start collecting and organizing research materials.

## Prerequisites

- Obsidian vault at: `~/obsidian-vault/`
- The `kb` CLI tool installed and available

## Workflow

### 1. Gather Information

Ask the user:
- What should the knowledge base be named? (e.g., "ml-research", "quantum-computing")
- What is the research topic? (e.g., "Machine Learning", "Quantum Computing")
- Do they have existing sources to import immediately? (yes/no)

### 2. Create the Knowledge Base

Run the create command:

```bash
kb create <name> \
  --vault-path $HOME/obsidian-vault/ \
  --topic "<Research Topic>"
```

The command will create:
- `knowledge-bases/<name>/raw/` - Storage for source materials (books, papers, videos, articles)
- `knowledge-bases/<name>/wiki/` - LLM-compiled wiki articles
- `knowledge-bases/<name>/outputs/` - Research outputs and Q&A results

### 3. Import Initial Sources (Optional)

If the user has sources to add, ask for each source:
- What type? (epub, youtube)
- What is the ePub path or YouTube URL?

For each source, call the appropriate `kb add` command:

**For ePub books:**
```bash
kb add <name> --epub "/path/to/book.epub" \
  --vault-path $HOME/obsidian-vault/
```

**For YouTube videos:**
```bash
kb add <name> --youtube "https://youtube.com/watch?v=..." \
  --vault-path $HOME/obsidian-vault/
```

### 4. Explain the Structure

Tell the user:

> Your knowledge base is ready! Here's how it's organized:
> 
> **raw/** - This is where source materials live:
> - `raw/books/` - ePub books converted to markdown
> - `raw/videos/` - YouTube video transcripts
> - `raw/papers/` - Academic papers
> - `raw/articles/` - Web articles
> 
> **wiki/** - This is where the LLM-compiled wiki lives:
> - `wiki/concepts/` - Concept articles with wikilinks
> - `wiki/summaries/` - Summaries of source materials
> - `wiki/topics/` - Topic overviews
> 
> **outputs/** - Research outputs, Q&A results, generated reports

### 5. Suggest Next Steps

Recommend:
1. Add more sources: `/kb:add-source` skill
2. Compile sources into wiki: `/kb:compile` skill (once you have sources)
3. Start researching: `/kb:research` skill (once wiki is populated)

## Examples

### Example 1: Simple creation
```
User: "Create a knowledge base for machine learning"
Assistant: "I'll create a knowledge base called 'ml-research' for Machine Learning. Do you have any sources to import right now?"
User: "Not yet"
Assistant: [runs kb create command, explains structure, suggests adding sources]
```

### Example 2: Creation with sources
```
User: "Create a KB for quantum computing and add this book"
Assistant: "What should I name the knowledge base?"
User: "quantum-kb"
Assistant: [creates KB, adds book, explains structure]
```

## Notes

- The vault path is hardcoded for this user's Obsidian setup
- Knowledge bases are stored in `knowledge-bases/` within the vault
- Each KB is isolated - sources and wiki are separate per KB
- Templates are automatically created in `wiki/.templates/`
- The CLI is AI-free - compilation and Q&A happen through skills
