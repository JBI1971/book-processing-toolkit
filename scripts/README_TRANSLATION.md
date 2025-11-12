# Translation Pipeline Scripts

## Quick Reference

### Available Scripts

| Script | Purpose | Example |
|--------|---------|---------|
| `list_works.py` | Discover works | `python scripts/list_works.py --multi-volume` |
| `test_translation_pipeline.py` | System test | `python scripts/test_translation_pipeline.py` |
| `translate_work.py` | Translate one work | `python scripts/translate_work.py D55` |
| `batch_translate_works.py` | Batch translate | `python scripts/batch_translate_works.py D55 D56` |

### Common Commands

```bash
# Test system is ready
python scripts/test_translation_pipeline.py

# List Jin Yong's works
python scripts/list_works.py --author 金庸 --by-author

# Show work details
python scripts/list_works.py D55 --details

# Translate single volume (test)
python scripts/translate_work.py D55 --volume 001

# Translate complete work
python scripts/translate_work.py D55

# Batch translate
python scripts/batch_translate_works.py D55 D56 D57
```

## Documentation

- **`TRANSLATION_QUICK_START.md`** - 5-minute getting started guide
- **`TRANSLATION_PIPELINE_README.md`** - Complete documentation
- **`TRANSLATION_PIPELINE_SUMMARY.md`** - Implementation overview

## File Locations

### Scripts
- `/Users/jacki/PycharmProjects/agentic_test_project/scripts/`

### Processors
- `/Users/jacki/PycharmProjects/agentic_test_project/processors/`

### Source Data
- `/Users/jacki/project_files/translation_project/test_cleaned_json_v2/COMPLETE_ALL_BOOKS/`

### Output
- `/Users/jacki/project_files/translation_project/translated_books/`

### Logs
- `./logs/translation/`

## Status

✅ **System tested and ready**

All 6 tests passed:
- Configuration
- Catalog Database
- Volume Manager
- JSON Structure
- API Credentials
- Multi-Volume Discovery

## Next Steps

1. **Test**: `python scripts/translate_work.py D55 --volume 001`
2. **Review**: Check output quality
3. **Scale**: Batch translate curated works

Ready to translate! 🚀
