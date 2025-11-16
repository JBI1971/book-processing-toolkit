# Translation and Annotation Pipeline

Complete orchestration system for translating multi-volume wuxia works with cultural annotations and scholarly footnotes.

## Overview

This pipeline translates cleaned JSON books (post-restructuring) into English with comprehensive cultural/historical annotations. It handles:

- **Multi-volume works** - Coordinates translation across all volumes of a work
- **Cultural annotations** - Adds footnotes for historical references, martial arts terminology, character names
- **Progress tracking** - Checkpoint/resume functionality for long-running translations
- **Error recovery** - Robust retry logic and detailed error reporting
- **Cost tracking** - Token usage and cost estimation

## Architecture

```
Translation Pipeline
├── translation_config.py       - Configuration and dataclasses
├── volume_manager.py           - Multi-volume work coordination
├── book_translator.py          - Single volume translation
├── translator.py               - Core translation service with AI
│
Scripts
├── translate_work.py           - Translate all volumes of one work
├── batch_translate_works.py    - Batch process multiple works
└── list_works.py               - Discover and explore works
```

## Quick Start

### 1. List Available Works

```bash
# List all multi-volume works
python scripts/list_works.py --multi-volume

# List works by specific author
python scripts/list_works.py --author 金庸

# Show detailed info for a work
python scripts/list_works.py D55 --details
```

### 2. Translate a Single Work

```bash
# Translate all volumes of Legend of the Condor Heroes (射鵰英雄傳)
python scripts/translate_work.py D55

# Translate specific volume only
python scripts/translate_work.py D55 --volume 001

# Resume from checkpoint
python scripts/translate_work.py D55 --resume
```

### 3. Batch Translate Multiple Works

```bash
# Translate specific works
python scripts/batch_translate_works.py D55 D70 D81

# Translate all works with 4-8 volumes
python scripts/batch_translate_works.py --all-multi-volume --min-volumes 4 --max-volumes 8

# Translate from file
python scripts/batch_translate_works.py --file works_to_translate.txt
```

## Configuration

Edit `/Users/jacki/PycharmProjects/agentic_test_project/processors/translation_config.py` to customize:

```python
@dataclass
class TranslationConfig:
    # API Configuration
    model: str = "gpt-4.1-nano"
    temperature: float = 0.3
    max_retries: int = 3
    timeout: int = 120

    # Rate Limiting
    rate_limit_delay: float = 1.0  # Seconds between API calls

    # Input/Output Paths
    source_dir: Path = Path("/path/to/cleaned_json")
    output_dir: Path = Path("/path/to/translated_books")
    catalog_path: Path = Path("/path/to/wuxia_catalog.db")

    # Processing Options
    skip_completed: bool = True  # Resume functionality
    save_checkpoints: bool = True  # Save progress after each chapter
```

### Default Paths

- **Source**: `/Users/jacki/project_files/translation_project/test_cleaned_json_v2/COMPLETE_ALL_BOOKS/`
- **Output**: `/Users/jacki/project_files/translation_project/translated_books/`
- **Catalog**: `/Users/jacki/project_files/translation_project/wuxia_catalog.db`
- **Logs**: `./logs/translation/`

## Input/Output Formats

### Input: Cleaned JSON

Expected structure from restructuring pipeline:

```json
{
  "meta": {
    "title": "射鵰英雄傳",
    "author": "金庸",
    "work_number": "D55",
    "volume": "001",
    "language": "zh-Hant"
  },
  "structure": {
    "front_matter": {"toc": [...]},
    "body": {
      "chapters": [
        {
          "id": "chapter_0001",
          "title": "第一回　風雪驚變",
          "chapter_number": 1,
          "content_blocks": [
            {
              "id": "block_0000",
              "type": "text",
              "content": "正是嚴冬天氣，彤云密佈，朔風漸起，卻早紛紛揚揚捲下一場大雪來。",
              "epub_id": "para_1"
            }
          ]
        }
      ]
    }
  }
}
```

### Output: Translated JSON with Annotations

```json
{
  "meta": {
    "title": "射鵰英雄傳 (上卷)",
    "author": "金庸",
    "work_number": "D55",
    "volume": "001",
    "language": "zh-Hant",
    "translation": {
      "target_language": "en",
      "translator": "AI (OpenAI GPT-4o-mini)",
      "translation_date": "2025-11-10T12:00:00",
      "total_tokens": 150000,
      "chapters_translated": 10
    }
  },
  "structure": {
    "body": {
      "chapters": [
        {
          "id": "chapter_0001",
          "title": "第一回　風雪驚變",
          "content_blocks": [
            {
              "id": "block_0000",
              "type": "text",
              "original_content": "正是嚴冬天氣，彤云密佈，朔風漸起...",
              "translated_content": "It was the depth of winter[1], clouds heavy with snow[2]...",
              "footnotes": [
                {
                  "key": 1,
                  "ideogram": "嚴冬",
                  "pinyin": "yán dōng",
                  "explanation": "Severe winter; the coldest period of winter..."
                }
              ],
              "content_type": "narrative"
            }
          ]
        }
      ]
    }
  }
}
```

## Translation Features

### Cultural Annotations

The translator automatically adds footnotes for:

- **Historical references** - Dynasties, events, figures
- **Cultural concepts** - Confucian values, social customs
- **Martial arts terminology** - 內功 (nèi gōng), 輕功 (qīng gōng)
- **Character names** - With pinyin and meaning
- **Place names** - Historical/geographical context
- **Literary allusions** - Classical poetry, proverbs

### Footnote Format

Each footnote includes:
- **Ideogram**: Original Chinese characters
- **Pinyin**: Romanized pronunciation (Hanyu Pinyin)
- **Explanation**: Cultural/historical context

### Content Type Classification

Blocks are classified as:
- `narrative` - Storytelling, action sequences
- `dialogue` - Character speech
- `verse` - Poetry, songs
- `document` - Letters, proclamations
- `descriptive` - Pure description
- `thought` - Internal monologue

## Progress Tracking and Resumption

### Checkpoints

The pipeline automatically saves checkpoints after each chapter:

```
logs/translation/checkpoints/
  D55_001_checkpoint.json
  D55_002_checkpoint.json
```

### Resume Translation

```bash
# Resume interrupted translation
python scripts/translate_work.py D55 --resume
```

The system will:
1. Load checkpoint file
2. Skip already-translated chapters
3. Continue from last incomplete chapter

## Error Handling

### Retry Logic

- **Automatic retries**: 3 attempts per API call
- **Exponential backoff**: 2-second delay between retries
- **Validation**: Two-pass translation with quality checks

### Error Reports

Detailed error logs saved to:
```
logs/translation/
  D55_001_translation.log
  D55_translation_report.json
```

Report includes:
- Failed chapters and blocks
- Error types and messages
- Token usage statistics
- Success/failure rates

## Cost Estimation

### Token Usage

The pipeline tracks token usage and provides cost estimates:

```
GPT-4o-mini pricing (as of 2025):
- Input: $0.150 per 1M tokens
- Output: $0.600 per 1M tokens
- Average: ~$0.150 per 1M tokens (combined)
```

### Example Costs

Typical wuxia novel (4 volumes, ~40 chapters/volume, ~200 blocks/chapter):
- **Blocks**: ~32,000
- **Tokens**: ~15-20M tokens
- **Estimated cost**: $2.25 - $3.00

## CLI Reference

### translate_work.py

Translate all volumes of a single work.

```bash
python scripts/translate_work.py <work_number> [options]

Options:
  --volume VOLUME       Translate specific volume only
  --resume              Resume from checkpoint
  --dry-run             Preview without writing files
  --output-dir PATH     Custom output directory
  --model MODEL         OpenAI model (default: gpt-4.1-nano)
  --max-workers N       Concurrent chapters (default: 3)
  --verbose             Enable debug logging

Examples:
  python scripts/translate_work.py D55
  python scripts/translate_work.py D55 --volume 001
  python scripts/translate_work.py D55 --resume --verbose
```

### batch_translate_works.py

Batch process multiple works.

```bash
python scripts/batch_translate_works.py [work_numbers...] [options]

Options:
  --file FILE           File with work numbers (one per line)
  --all-multi-volume    Translate all multi-volume works
  --min-volumes N       Filter: minimum volumes
  --max-volumes N       Filter: maximum volumes
  --list-only           Preview without translating
  --dry-run             Dry run mode
  --model MODEL         OpenAI model
  --verbose             Enable debug logging

Examples:
  python scripts/batch_translate_works.py D55 D70 D81
  python scripts/batch_translate_works.py --file works.txt
  python scripts/batch_translate_works.py --all-multi-volume --min-volumes 4
  python scripts/batch_translate_works.py --all-multi-volume --list-only
```

### list_works.py

Discover and explore available works.

```bash
python scripts/list_works.py [work_numbers...] [options]

Options:
  --multi-volume        List only multi-volume works
  --author AUTHOR       Filter by author (Chinese or English)
  --category CATEGORY   Filter by category
  --min-volumes N       Minimum volumes filter
  --max-volumes N       Maximum volumes filter
  --details             Show detailed information
  --show-details        More details in list view
  --export FILE         Export work numbers to file
  --by-author           Group results by author

Examples:
  python scripts/list_works.py --multi-volume
  python scripts/list_works.py --author 金庸
  python scripts/list_works.py D55 --details
  python scripts/list_works.py --multi-volume --export works.txt
  python scripts/list_works.py --author 金庸 --by-author
```

## Multi-Volume Works

### Top Multi-Volume Works in Database

```
D191 - 8 volumes
D70  - 7 volumes
J090908 - 6 volumes
D81  - 6 volumes
D69  - 6 volumes
D423 - 6 volumes
D65  - 5 volumes
D57  - 4 volumes
D56  - 4 volumes
D55  - 4 volumes (射鵰英雄傳 - Legend of the Condor Heroes)
```

### Volume Naming Convention

Volumes are stored as:
- **Database**: Letters (a, b, c, d...)
- **Filenames**: Letters (D55a, D55b, D55c...)
- **Internal**: Numbers (001, 002, 003...)

## Integration with Existing Pipeline

### Prerequisites

1. **Cleaned JSON files** - Must be processed through restructuring pipeline
2. **Catalog database** - `wuxia_catalog.db` with work metadata
3. **API credentials** - OpenAI API key in `env_creds.yml`

### Pipeline Flow

```
Raw JSON (EPUB extraction)
    ↓
[Stage 1-6] Restructuring Pipeline
    ↓
Cleaned JSON (discrete blocks)
    ↓
[Translation Pipeline] ← YOU ARE HERE
    ↓
Translated JSON (with annotations)
    ↓
[Future] EPUB Builder
    ↓
Final EPUB with translations
```

## Troubleshooting

### API Key Issues

```bash
# Verify API key
python scripts/verify_api_key.py

# Check env_creds.yml
cat env_creds.yml | grep OPENAI_API_KEY
```

### Missing Files

```bash
# Verify volume integrity
python scripts/list_works.py D55 --details

# Check source directory
ls -la /Users/jacki/project_files/translation_project/test_cleaned_json_v2/COMPLETE_ALL_BOOKS/wuxia_0001/
```

### Rate Limit Errors

Adjust rate limiting in config:

```python
config = TranslationConfig(
    rate_limit_delay=2.0,  # Increase to 2 seconds
    max_retries=5          # More retries
)
```

### Low Quality Translations

- Lower temperature for more deterministic output: `temperature=0.1`
- Use higher-quality model: `model="gpt-4o"` (more expensive)
- Check validation scores in logs

## Performance Optimization

### Concurrent Processing

```bash
# Increase concurrent chapters (use with caution)
python scripts/translate_work.py D55 --max-workers 5
```

**Note**: Higher concurrency = faster but higher API costs and rate limit risks.

### Batch Size

Adjust in config:
```python
config = TranslationConfig(
    batch_size=20  # Process more blocks per API call
)
```

### Resume Strategy

For very large works, translate in stages:

```bash
# Translate volume by volume
python scripts/translate_work.py D55 --volume 001
python scripts/translate_work.py D55 --volume 002
python scripts/translate_work.py D55 --volume 003
python scripts/translate_work.py D55 --volume 004
```

## Monitoring and Reports

### Real-time Monitoring

```bash
# Watch log file
tail -f logs/translation/D55_001_translation.log

# Monitor checkpoints
watch ls -lh logs/translation/checkpoints/
```

### Post-Translation Reports

Reports are saved to:
```
logs/translation/
  D55_translation_report.json           - Work-level report
  D55_001_translation.log               - Volume-level logs
  batch_translation_20251110_120000.json - Batch report
```

### Report Contents

```json
{
  "work_number": "D55",
  "work_title": "射鵰英雄傳",
  "volumes": {
    "total": 4,
    "completed": 4,
    "completion_percentage": 100.0
  },
  "statistics": {
    "total_chapters": 160,
    "total_blocks": 8000,
    "successful_blocks": 7950,
    "success_rate": 99.4,
    "total_tokens": 15000000,
    "estimated_cost_usd": 2.25
  },
  "duration_formatted": "180.5 minutes"
}
```

## Best Practices

### 1. Start Small

Test on single volumes first:
```bash
python scripts/translate_work.py D55 --volume 001
```

### 2. Monitor Costs

Check token usage regularly:
```bash
grep "total_tokens" logs/translation/*_report.json
```

### 3. Use Dry Run

Preview before committing:
```bash
python scripts/translate_work.py D55 --dry-run
```

### 4. Checkpoint Regularly

Enable checkpoints (default on):
```python
config = TranslationConfig(save_checkpoints=True)
```

### 5. Validate Output

Review a few chapters manually before batch processing.

## Future Enhancements

Planned features:

- [ ] Glossary management for consistent terminology
- [ ] Custom footnote styles (Chicago, MLA, inline)
- [ ] Translation memory for repeated phrases
- [ ] Parallel translation with multiple models
- [ ] Interactive editing interface
- [ ] Export to Markdown/HTML for review
- [ ] Integration with EPUB builder

## Support and Feedback

For issues or questions:

1. Check logs in `logs/translation/`
2. Review error reports (JSON)
3. Verify API key and rate limits
4. Test with single volume first

## License

Part of the Book Processing Toolkit (v0.2.0)
