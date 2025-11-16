# Character Footnote Cleanup Tool

## Overview

The Character Footnote Cleanup Tool is a production-quality Python script that intelligently removes fictional character name footnotes from translated wuxia novels while preserving historical figures, legendary personages, and cultural/historical concepts.

**Key Features:**
- AI-powered footnote classification (OpenAI GPT-4.1-nano)
- Heuristic fallback when API unavailable
- Removes ALL fictional character footnotes (no threshold)
- Preserves historical figures and legendary personages
- Deduplicates footnotes within chapters
- Renumbers footnotes for sequential consistency
- Generates detailed classification logs

## Files

- **Utility**: `/Users/jacki/PycharmProjects/agentic_test_project/utils/cleanup_character_footnotes.py`
- **CLI**: `/Users/jacki/PycharmProjects/agentic_test_project/cli/cleanup_character_footnotes.py`

## Usage

### Basic Usage

```bash
python cli/cleanup_character_footnotes.py \
  --input /path/to/translated_book.json \
  --output-dir /path/to/output
```

### Full Options

```bash
python cli/cleanup_character_footnotes.py \
  --input /path/to/translated_book.json \              # Required
  --output /path/to/cleaned_book.json \               # Optional, auto-generated if not provided
  --output-dir /path/to/output_directory \            # Default: ./character_footnotes_cleaned
  --log-dir /path/to/logs \                           # Default: ./logs
  --model gpt-4.1-nano \                              # OpenAI model (default: gpt-4.1-nano)
  --batch-size 20 \                                   # Footnotes per API call (default: 25)
  --temperature 0.1 \                                 # API temperature (default: 0.1)
  --preserve-historical \                             # Keep historical figures (default: True)
  --preserve-legendary \                              # Keep legendary personages (default: True)
  --preserve-cultural \                               # Keep cultural footnotes (default: True)
  --no-backup \                                       # Skip creating backup file
  --dry-run \                                         # Preview changes without writing
  --verbose                                           # Enable verbose logging
```

### Example Run

```bash
# Process a translated wuxia novel
python cli/cleanup_character_footnotes.py \
  --input /Users/jacki/project_files/translation_project/refactor_test/I1046/translated_I1046_飛鳳潛龍_梁羽生.json \
  --output-dir /Users/jacki/project_files/translation_project/character_footnotes_cleaned \
  --log-dir ./logs \
  --batch-size 20 \
  --verbose
```

## Footnote Classification Types

The script classifies footnotes into four categories:

### 1. FICTIONAL_CHARACTER (REMOVED)
- Fictional characters in the story
- Named individuals created by the author
- Examples: 魯世雄, 完顏長之, 柳元宗
- **Action**: All instances removed

### 2. HISTORICAL_FIGURE (PRESERVED)
- Real historical persons
- Documented historical figures
- Examples: 康熙帝, 孔子, 李白, 成吉思汗
- **Action**: Preserved (configurable)

### 3. LEGENDARY_PERSONAGE (PRESERVED)
- Mythological or legendary figures
- Religious deities
- Folk heroes from traditional legends
- Examples: 關羽, 觀音, 玉皇大帝, 孫悟空
- **Action**: Preserved (configurable)

### 4. CULTURAL (PRESERVED)
- Cultural concepts, places, events
- Martial arts terminology (氣, 內功, 輕功)
- Historical dynasties and places
- Idioms and literary references
- Objects, titles, customs
- Examples: 金國, 氣, 王爺, 白玉堂
- **Action**: Preserved (configurable)

## Processing Pipeline

The script follows a 5-stage pipeline:

### Stage 1: Catalog Footnotes
- Extracts all footnotes from content_blocks
- Tracks: chapter, block, ideogram, explanation
- Builds occurrence catalog

### Stage 2: Classify Footnotes (AI-Powered)
- Batch processing (configurable batch size)
- Uses OpenAI GPT-4.1-nano for classification
- Falls back to heuristic mode if API unavailable
- Temperature: 0.1 for consistency

### Stage 3: Remove Fictional Characters
- Removes ALL fictional character footnotes
- No occurrence threshold (all instances removed)
- Preserves other categories based on config

### Stage 4: Deduplicate Footnotes
- Removes duplicate footnotes within each chapter
- Based on exact ideogram matching
- Keeps first occurrence per chapter

### Stage 5: Renumber Footnotes
- Renumbers footnotes sequentially (1, 2, 3...)
- Maintains consistency within each content_block

## Output Files

### 1. Cleaned JSON
- Location: `{output-dir}/{input_filename}`
- Format: Same as input with reduced footnotes
- Backup: `{input_file}.backup` (unless --no-backup)

### 2. Detailed Log
- Location: `{log-dir}/{input_filename}_character_cleanup_log.json`
- Contains:
  - Summary statistics
  - Classification details for each footnote
  - Removed vs. preserved breakdown
  - Configuration used
  - Timestamp

## Log File Structure

```json
{
  "timestamp": "2025-11-15T10:02:39.146Z",
  "summary": {
    "total_footnotes": 3876,
    "total_unique_ideograms": 1710,
    "fictional_characters": 151,
    "historical_figures": 85,
    "legendary_personages": 18,
    "cultural_footnotes": 1456,
    "removed_count": 991,
    "preserved_count": 2885,
    "deduplicated_count": 1063,
    "api_calls": 86
  },
  "configuration": {
    "model": "gpt-4.1-nano",
    "batch_size": 20,
    "temperature": 0.1,
    "preserve_historical": true,
    "preserve_legendary": true,
    "preserve_cultural": true
  },
  "removed_footnotes": {
    "fictional_character": [...]
  },
  "preserved_footnotes": {
    "historical_figure": [...],
    "legendary_personage": [...],
    "cultural": [...]
  },
  "classifications": [...]
}
```

## Example Results

### Test Work: I1046 飛鳳潛龍 (梁羽生)

**Input Statistics:**
- Total footnotes: 3,876
- Unique ideograms: 1,710

**Classification Results:**
- Fictional characters: 151 (removed)
- Historical figures: 85 (preserved)
- Legendary personages: 18 (preserved)
- Cultural footnotes: 1,456 (preserved)

**Final Results:**
- Removed: 2,054 footnotes (53.0% reduction)
- Output footnotes: 1,822
- Deduplicated: 1,063 additional footnotes

**Character Examples Removed:**
- 魯世雄 (404 occurrences)
- 完顏長之 (160 occurrences)
- 柳元宗 (5 occurrences)
- 德充符 (3 occurrences)

**Cultural Terms Preserved:**
- 氣 (vital energy/qi)
- 金國 (Jin Dynasty)
- 王爺 (noble title)
- 白玉堂 (Baiyu Hall)

## Heuristic Fallback Mode

When OpenAI API is unavailable, the script automatically falls back to heuristic classification using keyword matching:

**Character Keywords:**
- character, protagonist, hero, heroine, villain
- young man, young woman, warrior, martial artist
- the name of, personal name, given name

**Historical Keywords:**
- emperor, dynasty, historical, reign
- kangxi, confucius, documented

**Legendary Keywords:**
- deity, god, goddess, buddha
- mythological, legendary, immortal

**Default:**
- Everything else classified as CULTURAL

## Environment Setup

### Required Dependencies
```bash
pip install openai tqdm tenacity
```

### API Key (Optional)
The script will use heuristic mode if no API key is available.

To use AI classification:
```bash
# Set environment variable
export OPENAI_API_KEY=your-key-here

# Or create env_creds.yml in project root
OPENAI_API_KEY: your-key-here
```

## Best Practices

1. **Always run with --dry-run first** to preview changes
2. **Review the log file** to verify classifications
3. **Use --verbose** during testing to see detailed processing
4. **Keep backups enabled** (default) for safety
5. **Adjust batch-size** based on API rate limits
6. **Lower temperature** (0.0-0.2) for more consistent classification

## Error Handling

The script includes comprehensive error handling:

- **Input validation**: Checks JSON schema before processing
- **API retry logic**: 3 attempts with exponential backoff
- **Graceful degradation**: Falls back to heuristic mode
- **Backup creation**: Automatic backup before modification
- **Output validation**: Verifies JSON structure before saving

## Integration with Translation Pipeline

This tool is designed to work as a post-processing step after translation:

```
Raw JSON → Clean → Structure → Translate → Footnote Cleanup → EPUB
```

**Recommended Workflow:**
1. Translate book with footnotes using translation pipeline
2. Run character footnote cleanup to remove repetitive names
3. Verify results using log file
4. Proceed to EPUB generation

## Troubleshooting

### Issue: API key errors
**Solution**: Script will automatically fall back to heuristic mode

### Issue: Too many footnotes removed
**Solution**: Review log file classifications, adjust heuristics if needed

### Issue: Important characters preserved
**Solution**: This is intentional - the heuristic errs on the side of preserving ambiguous footnotes as CULTURAL

### Issue: Slow processing
**Solution**: Increase --batch-size (but watch API rate limits)

## Future Improvements

- Support for custom classification rules
- Machine learning model for better heuristics
- Confidence threshold filtering
- Multi-language support
- Batch processing for multiple files

## Contact

For issues or questions, refer to the main project documentation.
