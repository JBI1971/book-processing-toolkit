# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Book JSON Cleaner** - Transforms raw book JSON files into clean, structured formats with discrete content blocks for EPUB generation.

Two-tier architecture:
1. **Pure Python cleaner** (`clean_input_json.py`) - No API required, instant processing
2. **AI-powered structuring** (`content_structuring_processor.py`) - Optional OpenAI-based semantic analysis

## Development Commands

### Environment Setup
```bash
make venv      # Create virtual environment
make install   # Install dependencies from ~/PycharmProjects/requirements_base.txt
```

### Testing
```bash
make test      # Run pytest (currently minimal test coverage)
pytest tests/test_sanity.py  # Run single test file
```

### Running Tools
```bash
# Main JSON cleaner (no API needed)
python clean_input_json.py --input book.json --output cleaned.json --language zh-Hant

# AI-powered structuring (requires OPENAI_API_KEY)
python content_structuring_processor.py --input novel.txt --output structured.json

# Batch processing with AI
python content_structuring_processor.py --input ./novels/ --output ./output/ --max-workers 5

# Assistant manager CLI
python translation_assistant_manager.py list
python translation_assistant_manager.py create --name my-assistant --instructions file.md
```

### Demo & Cleanup
```bash
make run    # Run template_pkg.main (checks env vars)
make clean  # Remove build artifacts
```

## Architecture

### Data Flow Pipeline
```
Raw JSON → clean_input_json.py → Discrete Blocks → (Optional) content_structuring_processor.py → Semantically Tagged Blocks
```

### Core Components

**1. clean_input_json.py** - Standalone JSON transformer
- Input: `{chapters: [{title, content}]}` in various formats (string, HTML-like objects, nested structures)
- Recursively extracts text from nested nodes
- Creates discrete blocks: `{id, type, content, epub_id}`
- Block types: `heading_1` through `heading_6`, `paragraph`, `text`, `list_ul/ol`, `list_item`
- Auto-detects TOC based on title keywords (目錄, contents) or structure patterns
- Output: `{meta, structure: {front_matter, body: {chapters}, back_matter}}`

**2. content_structuring_processor.py** - AI-powered semantic analysis
- Uses OpenAI Assistants API via threads
- Chunks large texts (>4000 chars) with 200-char overlap
- Semantic block types: `narrative`, `dialogue`, `verse`, `document`, `thought`, `descriptive`, `chapter_title`
- Processing modes: STRICT, FLEXIBLE (default), BEST_EFFORT
- Retry logic: 3 attempts with 2s delay, 300s timeout per request
- Batch processing: ThreadPoolExecutor with 3 workers default
- Schema validation against `assistant_configs/schemas/structuring_schema.json`

**3. translation_assistant_manager.py** - OpenAI Assistant lifecycle management
- Stores configs in `.assistants/` directory (JSON files)
- Versioning: supports semantic versions (v1, v2) and "latest" keyword
- CRUD operations: create, get, list, update, delete, export, import
- Tracks: assistant_id, instructions, schema, model, temperature, metadata, timestamps

### Template Package (src/template_pkg/)

Reusable utilities for other projects:
- **clients/openai_client.py**: `get_client()`, `quick_chat(prompt)` - Uses OPENAI_API_KEY env var
- **clients/anthropic_client.py**: `get_client()`, `quick_chat(prompt)` - Uses ANTHROPIC_API_KEY env var
- **scraping/http.py**: HTTP client with retry logic (3 attempts, exponential backoff)
- **scraping/parse.py**: BeautifulSoup-based HTML parsing

## Key Data Structures

### Input JSON (Multiple Formats Accepted)
```json
{
  "title": "Book Title",
  "chapters": [
    {
      "title": "Chapter 1",
      "content": "string" // OR array of {tag, content} objects
    }
  ]
}
```

### Output JSON (Standardized Format)
```json
{
  "meta": {
    "title": "Book Title",
    "language": "zh-Hant",
    "schema_version": "2.0.0",
    "source": "cleaned-input",
    "original_file": "book.json"
  },
  "structure": {
    "front_matter": {
      "toc": [{"id": "toc_0000", "title": "...", "content": "..."}]
    },
    "body": {
      "chapters": [
        {
          "id": "chapter_0001",
          "title": "Chapter Title",
          "ordinal": 1,
          "content_blocks": [
            {
              "id": "block_0000",
              "type": "heading_3",
              "content": "...",
              "epub_id": "heading_0",
              "level": 3
            }
          ],
          "source_reference": "/chapters/0"
        }
      ]
    },
    "back_matter": {}
  }
}
```

### Block ID Generation
- Sequential numbering: `block_0000`, `block_0001`, etc.
- EPUB IDs: `heading_0`, `para_1`, `text_2`, `list_3`, `li_4`
- Chunk IDs (AI processing): `chunk_001`, `chunk_002`, etc.

## Important Implementation Details

### Block Extraction Logic (clean_input_json.py)

The recursive `extract_blocks_from_nodes()` function handles:
- String nodes → text blocks
- HTML-like tags (h1-h6, p, div, section, ul, ol, li) → typed blocks
- Nested structures → recursive descent
- Sentence-boundary splitting for paragraphs (\\n\\n delimiter)

### Text Chunking Strategy (content_structuring_processor.py)

When text exceeds 4000 chars:
1. Split at max_chunk_size (4000)
2. Search backwards up to 200 chars for sentence boundary (。！？\\n)
3. If found, break there; otherwise break at max_chunk_size
4. Add 200-char overlap between chunks
5. Track chunk metadata: `chunk_id`, `start_char`, `end_char`

### TOC Detection Heuristics

Identifies table of contents by:
1. **Title matching**: "目錄", "目录", "contents", "table of contents", "toc"
2. **Structure pattern** (first chapter only): ≥5 lines with 70%+ having ≤15 characters

### OpenAI Assistant Thread Pattern

```python
thread = client.beta.threads.create()
client.beta.threads.messages.create(thread_id=thread.id, role="user", content=text)
run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)
# Poll run.status until 'completed' or 'failed' (max 300s)
messages = client.beta.threads.messages.list(thread_id=thread.id)
# Extract assistant response and parse JSON
```

### Language Detection

Simple heuristic in `detect_language()`:
- Checks first 100 characters for Chinese unicode range (\\u4e00-\\u9fff)
- Returns "zh" if found, "en" otherwise

## Configuration & Environment

### Required Environment Variables
- `OPENAI_API_KEY` - For content_structuring_processor.py and translation_assistant_manager.py
- `ANTHROPIC_API_KEY` - For src/template_pkg/clients/anthropic_client.py (optional)

### Default Paths
- Input: `./input/book.json` (clean_input_json.py)
- Output: `./output/cleaned_book.json`
- Assistants: `.assistants/` directory for OpenAI configs
- Schemas: `assistant_configs/schemas/` (if using AI structuring)

### Processing Configurations

**content_structuring_processor.py defaults**:
- max_retries: 3
- retry_delay: 2.0s
- rate_limit_delay: 0.5s
- timeout: 300s (5 minutes)
- max_workers: 3 (batch processing)
- max_chunk_size: 4000 chars
- chunk_overlap: 200 chars

## Dependencies

Core Python 3.10+ with:
- `openai` - OpenAI API client
- `anthropic` - Anthropic API client (optional)
- `httpx` - Async HTTP client
- `tenacity` - Retry logic
- `beautifulsoup4` + `lxml` - HTML parsing
- `tqdm` - Progress bars (optional)
- `pytest` - Testing

Note: Dependencies installed from `~/PycharmProjects/requirements_base.txt` via `make install`

## Error Handling Patterns

### Retry Strategy (content_structuring_processor.py)
- Automatic retry on: JSON parse errors, validation failures, API failures
- Max 3 attempts with 2s delay between
- Mode-dependent: FLEXIBLE retries most errors, STRICT fails fast
- Timeout per request: 300s

### Schema Validation
Validates AI output has:
- `content_blocks` array (non-empty)
- Each block: `id`, `type`, `content`, `metadata` fields
- Valid block types from predefined list
- IDs start with `block_`
- Non-empty content

### Batch Processing Resilience
- ThreadPoolExecutor catches individual file failures
- Continues processing remaining files (unless STRICT mode)
- Returns status dict: `{file: {status: "success|failed", result|error}}`

## Common Workflows

### Add New Block Type
1. Update valid_types in `SchemaValidator.validate()` (content_structuring_processor.py)
2. Update assistant instructions to recognize new type
3. Update schema file if using schema validation

### Process Large Book
```bash
# Use chunking (automatically enabled for >4000 chars)
python content_structuring_processor.py --input large_novel.txt --output result.json

# Or disable chunking (may hit token limits)
python content_structuring_processor.py --input novel.txt --no-chunking
```

### Debug AI Assistant
```bash
# List all assistants
python translation_assistant_manager.py list

# View specific assistant config
python translation_assistant_manager.py export --name structuring --version latest

# Compare versions
python translation_assistant_manager.py compare --name structuring --version1 v1 --version2 v2
```

### Batch Process Multiple Files
```bash
# Process all .txt files in directory
python content_structuring_processor.py --input ./books/ --output ./results/ --max-workers 5
```

## Testing Notes

Current test coverage is minimal (`tests/test_sanity.py` only).

When adding tests, consider:
- Block extraction correctness (various input formats)
- TOC detection accuracy
- Language detection edge cases
- Chunking boundary conditions
- Schema validation rules
- Batch processing concurrency
- Retry logic behavior
- JSON output structure validation
