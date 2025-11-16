# Footnote Processing Architecture - Explained

**Date**: 2025-11-16

---

## Key Understanding

**ALL footnote processing tools are created by agents** - but there are two different **usage patterns**:

###  Pattern 1: Agent Creates Scripts Once → Orchestrator Invokes Them (Stage 6a)

```
┌─────────────────────────────────────────────────────────────────┐
│ DEVELOPMENT TIME (Done once by agent)                          │
├─────────────────────────────────────────────────────────────────┤
│ 1. Invoke footnote-cleanup-optimizer agent                      │
│ 2. Agent generates implementation:                              │
│    - utils/cleanup_character_footnotes.py                       │
│    - cli/cleanup_character_footnotes.py                         │
│ 3. Scripts are integrated into pipeline:                        │
│    - CharacterFootnoteCleanupProcessor uses the utility         │
│ 4. Scripts are committed to repo                                │
└─────────────────────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────────┐
│ RUNTIME (Every translation)                                     │
├─────────────────────────────────────────────────────────────────┤
│ 1. User runs: python scripts/orchestrate_translation_pipeline.py│
│ 2. Orchestrator reaches Stage 6a                                │
│ 3. Orchestrator invokes CharacterFootnoteCleanupProcessor:      │
│    - Processor imports utils/cleanup_character_footnotes.py     │
│    - Runs cleanup on translated JSON                            │
│    - Removes character footnotes                                │
│    - Saves results                                              │
│ 4. NO user intervention required                                │
└─────────────────────────────────────────────────────────────────┘
```

**Example: Stage 6a - Character Footnote Cleanup**
- **Development**: `footnote-cleanup-optimizer` agent created `utils/cleanup_character_footnotes.py`
- **Runtime**: Orchestrator invokes it during every translation (no user action needed)

---

### Pattern 2: Agent Creates Scripts Each Time → User Runs Them Manually (Stage 6b)

```
┌─────────────────────────────────────────────────────────────────┐
│ EACH TIME USER NEEDS IT                                        │
├─────────────────────────────────────────────────────────────────┤
│ 1. User invokes footnote-deduplicator agent:                   │
│    > "Check for duplicate footnotes in work I1046"             │
│                                                                 │
│ 2. Agent analyzes THIS SPECIFIC work:                          │
│    - Scans all volumes                                         │
│    - Identifies duplicate patterns                             │
│    - Generates CUSTOM scripts for this work:                   │
│      • exact_match_deletion.py  (specific to I1046)            │
│      • candidate_analysis.py    (specific to I1046)            │
│      • ai_assisted_deletion.py  (specific to I1046)            │
│      • validation_suite.py                                      │
│                                                                 │
│ 3. User REVIEWS generated scripts                              │
│                                                                 │
│ 4. User MANUALLY runs scripts:                                 │
│    python exact_match_deletion.py --dry-run                    │
│    python exact_match_deletion.py                              │
│    python validation_suite.py                                  │
│                                                                 │
│ 5. Scripts modify work and generate reports                    │
│                                                                 │
│ 6. Scripts are NOT committed (work-specific, one-time use)     │
└─────────────────────────────────────────────────────────────────┘
```

**Example: Stage 6b - Duplicate Term Cleanup**
- **Each time**: User invokes `footnote-deduplicator` agent
- **Each time**: Agent creates fresh scripts specific to that work
- **Each time**: User reviews and runs scripts manually

---

## Comparison

| Aspect | Pattern 1 (Stage 6a) | Pattern 2 (Stage 6b) |
|--------|----------------------|----------------------|
| **Agent** | footnote-cleanup-optimizer | footnote-deduplicator |
| **Agent used** | Once (development time) | Each time needed |
| **Scripts location** | `utils/` (committed to repo) | Current directory (temporary) |
| **Scripts generated** | Once, reused forever | Fresh each invocation |
| **Integration** | Built into pipeline | Not integrated |
| **Invoked by** | Orchestrator (pipeline) | User (manual) |
| **Review** | Not needed (trusted) | Required (work-specific) |
| **Configuration** | CLI flags | Agent invocation |
| **Use case** | Every translation | Occasional, final QA |

---

## Complete Workflow Example

### Development Phase (Done Once)

```bash
# Developer uses agent to create character cleanup implementation
> Invoke footnote-cleanup-optimizer agent
> Agent creates:
    - utils/cleanup_character_footnotes.py
    - cli/cleanup_character_footnotes.py
> Developer integrates into pipeline:
    - Creates CharacterFootnoteCleanupProcessor
    - Registers in orchestrate_translation_pipeline.py
> Scripts committed to repository
```

### Translation Time (Every Book)

```bash
# User translates a book
python scripts/orchestrate_translation_pipeline.py D1379

# Pipeline automatically (no user action):
# - Stage 1-5: Translation with footnote generation
# - Stage 6a: Character cleanup (uses utils/cleanup_character_footnotes.py)
# - Stage 7: Validation

# Output: Translated book with ~50% footnote reduction
```

### Optional Additional Cleanup (When Needed)

```bash
# User wants additional cleanup for multi-volume work
> "Check for duplicate footnotes across all volumes of I1046"

# Agent analyzes I1046 and generates scripts:
# - exact_match_deletion.py
# - candidate_analysis.py
# - ai_assisted_deletion.py
# - validation_suite.py

# User reviews scripts
cat exact_match_deletion.py

# User runs scripts manually
python exact_match_deletion.py --dry-run  # Preview
python exact_match_deletion.py            # Execute
python validation_suite.py                # Verify

# Additional ~10-20% reduction
# Scripts are work-specific, not committed
```

---

## Why Two Patterns?

### Pattern 1 (Integrated) is used when:
- ✓ Cleanup logic is **consistent across all books**
- ✓ No manual review needed (trusted algorithm)
- ✓ Should be **invoked by orchestrator for every translation**
- ✓ Configuration via simple flags is sufficient
- ✓ Example: Removing character names (always the same logic)

### Pattern 2 (Script Generator) is used when:
- ✓ Cleanup is **work-specific** (different for each book)
- ✓ Manual review required (edge cases, ambiguity)
- ✓ **Optional** / occasional use (not every translation)
- ✓ Complex multi-phase logic (exact + AI-assisted)
- ✓ Need detailed audit trails
- ✓ Example: Duplicate terms (varies by book's annotation style)

---

## Future Substages

When adding new substages, choose the appropriate pattern:

### Use Pattern 1 (Integrated) for:
- **6c**: Cross-reference consolidation (if logic is consistent)
- **6d**: Redundant pinyin cleanup (deterministic rules)

### Use Pattern 2 (Script Generator) for:
- **6e**: Footnote length optimization (needs review per book)
- **6z**: Custom user-specific rules (work-specific)

---

## Key Takeaways

1. **Both patterns use agents** - agents create the code
2. **Pattern 1**: Agent creates scripts once → Orchestrator invokes them during pipeline
3. **Pattern 2**: Agent creates scripts each time → User manually invokes them
4. **Pattern 1 scripts**: Committed to repo, invoked by orchestrator
5. **Pattern 2 scripts**: Temporary, work-specific, invoked manually
6. **Choice of pattern**: Based on consistency vs. customization needs

---

**Status**: Both patterns production-ready and documented ✅
