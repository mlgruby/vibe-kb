---
name: kb:add-source
description: Add source material with conversational interface
---

# kb:add-source

## Purpose

This skill provides a conversational interface for adding source materials (books, videos, articles, papers) to a knowledge base. It handles different source types and optionally triggers compilation.

## Prerequisites

- At least one knowledge base already created
- The `kb` CLI tool installed
- Obsidian vault at: `/Users/satyasheel/Insync/satyasheel@ymail.com/Dropbox/obsidian-satya/`

## Workflow

### 1. Identify the Knowledge Base

Ask the user which KB to add to:
- "Which knowledge base should I add this to?"
- If user doesn't know, list available KBs by checking the vault path

### 2. Determine Source Type

Ask what type of source:
- ePub book (.epub file)
- YouTube video (URL)
- PDF paper (not yet implemented in MVP)
- Web article (not yet implemented in MVP)

### 3. Get Source Details

Based on type, ask for:

**For ePub:**
- Full path to the .epub file
- Example: `/Users/satyasheel/Downloads/book.epub`

**For YouTube:**
- Full YouTube URL
- Example: `https://youtube.com/watch?v=dQw4w9WgXcQ`

### 4. Add the Source

Run the appropriate command:

**For ePub books:**
```bash
kb add <kb_name> --epub "<path_to_epub>" \
  --vault-path "/Users/satyasheel/Insync/satyasheel@ymail.com/Dropbox/obsidian-satya/"
```

**For YouTube videos:**
```bash
kb add <kb_name> --youtube "<video_url>" \
  --vault-path "/Users/satyasheel/Insync/satyasheel@ymail.com/Dropbox/obsidian-satya/"
```

### 5. Confirm What Was Added

Report to the user:
- Title of the source
- Where it was saved (raw/books/, raw/videos/, etc.)
- Metadata (author, chapter count, duration, etc.)

### 6. Offer to Compile

Ask: "Would you like me to compile this source into your wiki now?"

If yes:
- Invoke the `/kb:compile` skill to process the new source

If no:
- Explain they can compile later with `/kb:compile`

## Examples

### Example 1: Adding an ePub book
```
User: "Add this book to my ML knowledge base"
Assistant: "What's the path to the .epub file?"
User: "/Users/satyasheel/Downloads/deep-learning.epub"
Assistant: [runs kb add command]
✓ Added book: Deep Learning by Ian Goodfellow
  Location: raw/books/deep-learning-ian-goodfellow.md
  Chapters: 20

"Would you like me to compile this into your wiki now?"
```

### Example 2: Adding a YouTube video
```
User: "Add a YouTube video"
Assistant: "Which knowledge base?"
User: "ml-research"
Assistant: "What's the YouTube URL?"
User: "https://youtube.com/watch?v=abc123"
Assistant: [runs kb add command]
✓ Added video: Transformers Explained
  Channel: AI Academy
  Location: raw/videos/transformers-explained-ai-academy.md

"Would you like me to compile this into your wiki now?"
```

### Example 3: Batch adding
```
User: "Add these 3 books to quantum-kb"
Assistant: [loops through each book, adds them]
"All 3 books added. Would you like me to compile them into your wiki?"
```

## Notes

- Sources are stored in `raw/<type>/` directories as markdown files
- Each source gets a `.meta.json` file with metadata
- Filenames are auto-generated from titles (slugified)
- The CLI validates file formats and URLs
- Compilation is optional - sources can be added in batches then compiled together
- Future: Support for PDFs, web scraping, arXiv papers, GitHub repos
