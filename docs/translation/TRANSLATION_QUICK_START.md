# Translation Pipeline - Quick Start Guide

## Prerequisites

1. **API Key**: Ensure `OPENAI_API_KEY` is set in `env_creds.yml`
2. **Cleaned JSON**: Books processed through restructuring pipeline
3. **Catalog Database**: `wuxia_catalog.db` with work metadata

## 5-Minute Quick Start

### Step 1: Discover Works

```bash
# List all multi-volume works
python scripts/list_works.py --multi-volume

# Find Jin Yong's works
python scripts/list_works.py --author 金庸 --by-author

# Show details for specific work
python scripts/list_works.py D55 --details
```

### Step 2: Translate a Single Volume (Test Run)

Start with a single volume to test the pipeline:

```bash
# Translate just Volume 1 of Legend of the Condor Heroes
python scripts/translate_work.py D55 --volume 001
```

**Expected Output:**
- Translated JSON in: `/Users/jacki/project_files/translation_project/translated_books/D55/`
- Log file: `logs/translation/D55_001_translation.log`
- Report: `logs/translation/D55_translation_report.json`

**Duration**: ~15-30 minutes for 10 chapters
**Cost**: ~$0.50-0.75 USD

### Step 3: Review Translation Quality

Check a few chapters in the output JSON:

```bash
# View output file
cat /Users/jacki/project_files/translation_project/translated_books/D55/translated_D55a_射鵰英雄傳一_金庸.json | jq '.structure.body.chapters[0].content_blocks[0]'
```

Look for:
- ✓ `translated_content` field present
- ✓ `footnotes` array with cultural notes
- ✓ `original_content` preserved

### Step 4: Translate Complete Work

Once satisfied with quality, translate all volumes:

```bash
# Translate all 4 volumes of D55
python scripts/translate_work.py D55

# Or with resume support
python scripts/translate_work.py D55 --resume
```

**Duration**: ~1-2 hours for 40 chapters (4 volumes)
**Cost**: ~$2-3 USD

### Step 5: Batch Translate Multiple Works

```bash
# Translate Jin Yong's major works
python scripts/batch_translate_works.py D55 D56 D57

# Or translate all works with 4 volumes
python scripts/batch_translate_works.py --all-multi-volume --min-volumes 4 --max-volumes 4
```

## Common Workflows

### Test on Small Work First

```bash
# Find shortest multi-volume works
python scripts/list_works.py --multi-volume --min-volumes 2 --max-volumes 2

# Translate a 2-volume work for testing
python scripts/translate_work.py <work_number>
```

### Translate Jin Yong Collection

```bash
# Step 1: Export Jin Yong's multi-volume works to file
python scripts/list_works.py --author 金庸 --multi-volume --export jin_yong_works.txt

# Step 2: Batch translate
python scripts/batch_translate_works.py --file jin_yong_works.txt
```

### Monitor Long-Running Translation

```bash
# Terminal 1: Start translation
python scripts/translate_work.py D191  # 8 volumes, ~3-4 hours

# Terminal 2: Monitor progress
watch tail -20 logs/translation/D191_translation.log

# Terminal 3: Check token usage
watch "grep 'Tokens used' logs/translation/D191_*.log | tail -5"
```

### Resume Interrupted Translation

```bash
# If translation is interrupted (network, API limit, etc.)
python scripts/translate_work.py D55 --resume

# The system will:
# 1. Load checkpoint
# 2. Skip completed chapters
# 3. Continue from last position
```

## Output Structure

```
/Users/jacki/project_files/translation_project/translated_books/
├── D55/                                           # Work directory
│   ├── translated_D55a_射鵰英雄傳一_金庸.json     # Volume 1
│   ├── translated_D55b_射鵰英雄傳二_金庸.json     # Volume 2
│   ├── translated_D55c_射鵰英雄傳三_金庸.json     # Volume 3
│   └── translated_D55d_射鵰英雄傳四_金庸.json     # Volume 4
├── D56/
│   └── ...
└── logs/
    └── translation/
        ├── D55_001_translation.log               # Volume logs
        ├── D55_translation_report.json           # Work report
        └── checkpoints/
            ├── D55_001_checkpoint.json           # Resume data
            └── ...
```

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

```bash
# Check env_creds.yml
cat env_creds.yml | grep OPENAI_API_KEY

# Verify key works
python scripts/verify_api_key.py
```

### "No volumes found for work"

```bash
# Check if work exists in catalog
python scripts/list_works.py <work_number> --details

# Verify source files
ls -la /Users/jacki/project_files/translation_project/test_cleaned_json_v2/COMPLETE_ALL_BOOKS/wuxia_*/
```

### Rate Limit Errors

```bash
# Use slower rate
python scripts/translate_work.py D55 --model gpt-4o-mini

# Edit translation_config.py:
# rate_limit_delay: 2.0  # Increase to 2 seconds
```

### Low Quality Translations

```bash
# Try lower temperature for more consistency
# Edit translation_config.py:
# temperature: 0.1  # Lower = more deterministic
```

## Cost Estimates

Based on GPT-4o-mini pricing ($0.150 per 1M tokens):

| Work Type | Volumes | Chapters | Est. Tokens | Est. Cost |
|-----------|---------|----------|-------------|-----------|
| Small     | 2       | 20       | 5-7M        | $0.75-1.00 |
| Medium    | 4       | 40       | 15-20M      | $2.25-3.00 |
| Large     | 6-8     | 60-80    | 30-40M      | $4.50-6.00 |

**Note**: Actual costs vary based on:
- Chapter length and complexity
- Number of footnotes generated
- Retry attempts for quality

## Next Steps

1. **Test with single volume** to verify quality
2. **Review output** for footnote accuracy
3. **Adjust configuration** if needed (temperature, model)
4. **Run batch translation** on curated work list
5. **Monitor progress** and costs

## Advanced Features

### Custom Configuration

Create a custom config:

```python
from processors.translation_config import TranslationConfig

config = TranslationConfig(
    model="gpt-4o-mini",
    temperature=0.2,
    rate_limit_delay=1.5,
    max_retries=5,
    output_dir="/custom/path"
)
```

### Programmatic Usage

```python
from processors.book_translator import BookTranslator
from processors.translation_config import TranslationConfig

config = TranslationConfig()
translator = BookTranslator(config)

report = translator.translate_book(
    input_path="cleaned_book.json",
    output_path="translated_book.json",
    work_number="D55",
    volume="001"
)

print(f"Success rate: {report['success_rate']:.1f}%")
```

## Support

For detailed documentation, see:
- `TRANSLATION_PIPELINE_README.md` - Complete documentation
- `CLAUDE.md` - Project architecture
- `logs/translation/` - Detailed logs and reports

Happy translating! 📚🌏→🇬🇧
