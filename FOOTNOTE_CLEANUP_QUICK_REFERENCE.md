# Footnote Processing - Quick Reference Guide

**Date**: 2025-11-16
**Framework**: Extensible substage architecture (Stage 6a-6z)

---

## Footnote Processing Substages

**Stage 6: FOOTNOTE PROCESSING** - Multiple sequential cleanup substages

Current substages:
- **6a**: Character Footnote Cleanup (integrated - automatic)
- **6b**: Duplicate Term Cleanup (script generator - manual)
- **6c-6z**: Reserved for future use

**All substages require work-level processing** (entire work at once)

---

## Currently Available Substages

### 1. Character Footnote Cleanup (Stage 6) - AUTOMATIC ✅

**Type**: Integrated into translation pipeline  
**Runs**: Automatically  
**Purpose**: Remove redundant character name footnotes

```bash
# Runs automatically as part of translation
python scripts/orchestrate_translation_pipeline.py D1379

# Skip if needed
python scripts/orchestrate_translation_pipeline.py D1379 \
  --skip-character-footnote-cleanup
```

**What it removes**:
- ❌ Fictional character names (魯世雄, 完顏長之)
- ✅ Preserves historical figures (康熙帝, 孔子)
- ✅ Preserves legendary personages (關羽, 觀音)
- ✅ Preserves cultural concepts (氣, 內功, 金國)

**Results**: ~50-60% footnote reduction

---

### 2. Footnote Deduplicator Agent (Stage 6b) - SCRIPT GENERATOR 🛠️

**Type**: Script generator (creates tools, doesn't execute)  
**Runs**: Manually invoked via agent  
**Purpose**: Generate scripts to remove duplicate cultural/term footnotes

**How to use**:

```
1. Invoke agent via Claude Code interface
2. Agent analyzes your work and generates scripts:
   - exact_match_deletion.py
   - candidate_analysis.py
   - ai_assisted_deletion.py
   - validation_suite.py
   
3. Review generated scripts

4. Run scripts manually:
   python exact_match_deletion.py --dry-run  # Preview
   python exact_match_deletion.py            # Execute
   python validation_suite.py                # Verify
```

**What it removes**:
- Duplicate cultural term explanations (江湖 explained 5 times → 1 time)
- Repeated concept footnotes across volumes
- Exact match duplicates across entire work
- AI-evaluated potential duplicates

**Results**: Additional ~10-20% reduction

---

## When to Use Each

### Use Character Cleanup (Automatic)
- ✓ Every translation run
- ✓ Remove character names
- ✓ No manual review needed
- ✓ Part of standard workflow

### Use Deduplicator Agent (Manual)
- ✓ Multi-volume works with duplicate terms
- ✓ Final QA before EPUB generation
- ✓ Need detailed audit trail
- ✓ Edge cases requiring manual review
- ✓ Want to preview changes before applying

---

## Complete Workflow Example

```bash
# Step 1: Translate with automatic character cleanup
python scripts/orchestrate_translation_pipeline.py I1046

# Output: Translation complete, ~50% footnote reduction from character cleanup

# Step 2 (Optional): Generate deduplication scripts
# Via Claude Code:
# > "Check for duplicate footnotes across all volumes of I1046"
# Agent generates scripts in current directory

# Step 3 (Optional): Review and run generated scripts
ls -la exact_match_deletion.py candidate_analysis.py

python exact_match_deletion.py --dry-run  # Preview changes
# Review output...

python exact_match_deletion.py  # Execute if satisfied
# Backup created: work_backup_20251116.json
# Removed 50 exact duplicate footnotes
# Renumbered 200 remaining footnotes

python validation_suite.py  # Verify integrity
# ✓ All footnote references valid
# ✓ Sequential numbering verified
# ✓ No orphaned references
# ✓ JSON schema valid

# Final result: ~60-70% total footnote reduction
```

---

## CLI Arguments (Character Cleanup)

```bash
# Skip character footnote cleanup
--skip-character-footnote-cleanup

# Custom batch size for AI classification
--character-footnote-batch-size 50

# Remove historical figures (default: preserve)
--no-preserve-historical

# Remove legendary personages (default: preserve)
--no-preserve-legendary

# Remove cultural concepts (default: preserve)
--no-preserve-cultural
```

---

## Processing Requirements

**Both cleanup types require**:
- ✓ Work-level processing (entire work at once)
- ✓ Cannot batch individual chapters
- ✓ Footnote renumbering must be consistent across work

**Batch processing**:
- ✓ Can process multiple WORKS in parallel
- ✗ Cannot process CHAPTERS in parallel within a work

---

## Output Locations

### Character Cleanup (Automatic)
```
/Users/jacki/project_files/translation_project/
├── wip/stage_6_cleanup/
│   └── work_name.json                          # After cleanup
├── translation_data/logs/
│   └── work_name_stage_6_cleanup.json          # Cleanup log
└── translation_data/
    └── translated_work_name.json               # Final output
```

### Deduplicator Scripts (Manual)
```
/path/to/working/directory/
├── exact_match_deletion.py                     # Generated script
├── candidate_analysis.py                       # Generated script
├── ai_assisted_deletion.py                     # Generated script
├── validation_suite.py                         # Generated script
├── DEDUPLICATION_REPORT.md                     # Analysis report
└── work_backup_YYYYMMDD.json                   # Auto-created backup
```

---

## Summary

| Feature | Character Cleanup | Deduplicator Agent |
|---------|-------------------|-------------------|
| Type | Integrated processor | Script generator |
| Execution | Automatic | Manual |
| Target | Character names | Duplicate terms |
| Configuration | CLI flags | Agent invocation |
| Review | Not needed | Required |
| Reduction | ~50-60% | ~10-20% additional |
| Use case | Every translation | Final QA, multi-volume |

**Best Practice**: Run character cleanup automatically during translation, then optionally use deduplicator agent for final quality assurance before EPUB generation.

---

**Status**: Both tools production-ready ✅
