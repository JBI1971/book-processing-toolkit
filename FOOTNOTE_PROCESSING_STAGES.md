# Footnote Processing Stages - Extensible Framework

**Date**: 2025-11-16
**Status**: Framework established for multiple footnote processing stages

---

## Overview

Footnote processing is organized into **substages** under Stage 6 of the translation pipeline. Each substage processes footnotes sequentially, maintaining work-level processing requirements for consistent renumbering.

**Stage 6 Architecture**:
```
Stage 6: FOOTNOTE PROCESSING
├── 6a: Character Footnote Cleanup (INTEGRATED - automatic)
├── 6b: Duplicate Term Cleanup (SCRIPT GENERATOR - manual)
├── 6c: [RESERVED FOR FUTURE USE]
├── 6d: [RESERVED FOR FUTURE USE]
├── 6e: [RESERVED FOR FUTURE USE]
└── 6z: [RESERVED FOR CUSTOM/USER STAGES]
```

---

## Processing Requirements (ALL Substages)

### Work-Level Processing Mandatory

**Why**: Footnote markers must be numbered sequentially across the entire work

```
✓ Correct:   Entire work → [1], [2], [3], [4], [5]...
✗ Incorrect: Per chapter → Ch1: [1], [2] | Ch2: [1], [2] (duplicates!)
```

### Sequential Execution

Substages must run **in order** as each depends on the output of the previous:

```
Raw footnotes (3,876)
    ↓
[6a] Character cleanup → 1,822 footnotes (remove character names)
    ↓
[6b] Duplicate cleanup → 1,600 footnotes (remove duplicate terms)
    ↓
[6c] Future stage → N footnotes (additional cleanup)
    ↓
Final footnotes (optimized)
```

### Renumbering After Each Stage

Each substage **must renumber** footnotes after modifications:
- Remove footnotes
- Renumber remaining footnotes sequentially
- Update all reference markers in content
- Validate no orphaned references

---

## Substage Types

### Type 1: Integrated Processors (Automatic)

**Characteristics**:
- Implementation scripts built into `utils/` (created via agent initially)
- Used automatically by `orchestrate_translation_pipeline.py`
- Runs during translation without user intervention
- Configurable via CLI flags
- No manual review required per execution
- Fast execution (minutes)

**Development Pattern**:
1. Agent generates implementation scripts once (e.g., `utils/cleanup_character_footnotes.py`)
2. Scripts are integrated into pipeline processor
3. Pipeline uses scripts automatically for every translation

**Current Examples**:
- **6a**: Character Footnote Cleanup
  - Agent: `footnote-cleanup-optimizer` (created scripts)
  - Scripts: `utils/cleanup_character_footnotes.py`
  - Integration: `CharacterFootnoteCleanupProcessor` in pipeline
  - Usage: Runs automatically, no user action needed

**Template for Adding New Integrated Stage**:

```python
class NewFootnoteCleanupProcessor(StageProcessor):
    """Stage 6x: Description of cleanup type

    NOTE: Processes ENTIRE WORK for consistent numbering
    """

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        # 1. Check if cleanup is disabled
        if not self.config.enable_new_cleanup:
            # Log skip and return

        # 2. Extract footnotes from entire work
        # 3. Apply cleanup logic
        # 4. Remove identified footnotes
        # 5. Renumber remaining footnotes sequentially
        # 6. Update reference markers
        # 7. Validate integrity
        # 8. Save WIP and log
        return data
```

### Type 2: One-Time Script Generators (Manual Review)

**Characteristics**:
- Invoked via specialized agents each time needed
- Generates Python scripts per invocation (doesn't execute)
- Requires user review and approval before running
- Creates detailed audit trails
- Includes dry-run and validation
- Multi-phase processing (exact + AI-assisted)

**Usage Pattern**:
1. User invokes agent when needed
2. Agent analyzes the specific work
3. Agent generates custom scripts for that work
4. User reviews generated scripts
5. User manually runs scripts
6. Scripts modify work and create reports

**Current Examples**:
- **6b**: Duplicate Term Cleanup
  - Agent: `footnote-deduplicator` (invoked each time)
  - Generates: `exact_match_deletion.py`, `candidate_analysis.py`, etc.
  - Usage: User reviews and runs scripts manually

**Template for Adding New Script Generator Agent**:

```markdown
---
name: footnote-[type]-cleaner
description: Use this agent to generate scripts for [specific cleanup type]
model: sonnet
---

You generate Python scripts to:
1. Analyze footnotes for [specific pattern]
2. Identify candidates for removal
3. Create deletion scripts with validation
4. Generate detailed reports

Output artifacts:
- analysis.py - Identify candidates
- deletion.py - Remove identified footnotes
- validation.py - Verify integrity
- REPORT.md - Summary and audit trail
```

---

## Currently Implemented Substages

### Stage 6a: Character Footnote Cleanup ✅

**Type**: Integrated (automatic)
**Status**: Production-ready
**File**: `scripts/orchestrate_translation_pipeline.py` (CharacterFootnoteCleanupProcessor)

**Purpose**: Remove redundant fictional character name footnotes

**What it removes**:
- Fictional character names (魯世雄, 完顏長之, 柳元宗)

**What it preserves**:
- Historical figures (康熙帝, 孔子, 李白, 成吉思汗)
- Legendary personages (關羽, 觀音, 玉皇大帝, 孫悟空)
- Cultural concepts (氣, 內功, 輕功, 金國, 王爺)

**Configuration**:
```bash
--skip-character-footnote-cleanup        # Disable this substage
--character-footnote-batch-size 25       # AI batch size
--no-preserve-historical                 # Remove historical figures
--no-preserve-legendary                  # Remove legendary personages
--no-preserve-cultural                   # Remove cultural concepts
```

**Metrics**:
- Reduction: ~50-60% of total footnotes
- Processing time: ~15-20 minutes for 3,876 footnotes
- Cost: ~$0.50-$1.00 per 4,000 footnotes (GPT-4.1-nano)

---

### Stage 6b: Duplicate Term Cleanup 🛠️

**Type**: Script generator (manual)
**Status**: Agent available (`.claude/agents/footnote-deduplicator.md`)
**Invocation**: Via Claude Code agent interface

**Purpose**: Remove duplicate cultural term and concept explanations

**What it removes**:
- Exact duplicate footnotes (same ideogram explained multiple times)
- Similar footnotes (AI-evaluated semantic duplicates)
- Variant spellings or characters
- Abbreviated vs. full explanations

**Generated Scripts**:
1. `exact_match_deletion.py` - Remove exact duplicates
2. `candidate_analysis.py` - Find potential duplicates via regex
3. `ai_assisted_deletion.py` - AI evaluation of edge cases
4. `validation_suite.py` - Comprehensive validation
5. `DEDUPLICATION_REPORT.md` - Detailed audit trail

**Workflow**:
```bash
# 1. Invoke agent via Claude Code
> "Check for duplicate footnotes across all volumes of I1046"

# 2. Review generated scripts
ls -la exact_match_deletion.py candidate_analysis.py

# 3. Preview changes
python exact_match_deletion.py --dry-run

# 4. Execute if satisfied
python exact_match_deletion.py

# 5. Validate
python validation_suite.py
```

**Metrics**:
- Reduction: Additional ~10-20% of remaining footnotes
- Processing time: Variable (depends on manual review)
- Review: Required before execution

---

## Future Substages (Reserved)

### Stage 6c: Cross-Reference Consolidation [PLANNED]

**Purpose**: Merge related footnotes that cross-reference each other

**Example**:
```
Before:
  [1] 氣 (qì): Vital energy. See also 內功[3]
  [3] 內功 (nèi gōng): Internal energy cultivation using 氣[1]

After:
  [1] 氣 (qì) and 內功 (nèi gōng): Vital energy and internal energy
      cultivation practice. The two concepts are closely related...
```

**Type**: TBD (integrated or script generator)

---

### Stage 6d: Redundant Pinyin Cleanup [PLANNED]

**Purpose**: Remove pinyin when the same term was already shown with pinyin earlier

**Example**:
```
Before:
  Chapter 1: "He practiced 氣功 (qì gōng)[1]..."
  Chapter 5: "The 氣功 (qì gōng)[15] technique..."

After:
  Chapter 1: "He practiced 氣功 (qì gōng)[1]..."
  Chapter 5: "The 氣功[1] technique..."  (reference to first footnote)
```

**Type**: TBD (likely integrated for consistency)

---

### Stage 6e: Footnote Length Optimization [PLANNED]

**Purpose**: Condense verbose explanations while preserving key information

**Example**:
```
Before:
  [1] 武當山 (Wǔdāng Shān): Mount Wudang is a mountain range located in
      northwestern Hubei Province, China. It is famous for its Taoist
      temples and practices, and is considered one of the sacred mountains
      of Taoism. The mountain has been a center of Taoist study and martial
      arts training for centuries...

After:
  [1] 武當山 (Wǔdāng Shān): Sacred Taoist mountain in Hubei Province,
      famous for temples and martial arts training.
```

**Type**: TBD (likely AI-assisted script generator)

---

### Stage 6z: Custom User Stages [RESERVED]

Reserved for project-specific or user-defined cleanup rules that don't fit standard patterns.

---

## Adding a New Integrated Substage

### Step 1: Define Configuration

Add to `OrchestrationConfig` in `orchestrate_translation_pipeline.py`:

```python
# Footnote cleanup settings
enable_character_cleanup: bool = True        # 6a
enable_duplicate_cleanup: bool = True        # 6b (future)
enable_crossref_cleanup: bool = True         # 6c (future)
enable_pinyin_cleanup: bool = True           # 6d (future)
enable_length_optimization: bool = True      # 6e (future)
```

### Step 2: Create Processor Class

```python
class NewFootnoteProcessor(StageProcessor):
    """Stage 6x: [Description]"""

    def process(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        # Implementation
        pass
```

### Step 3: Add CLI Arguments

```python
parser.add_argument(
    '--skip-[new-type]-footnote-cleanup',
    dest='skip_new_cleanup',
    action='store_true',
    help='Skip [new type] footnote cleanup (Stage 6x)'
)
```

### Step 4: Register Processor

```python
self.processors = {
    PipelineStage.CLEANUP_CHARACTER: CharacterFootnoteCleanupProcessor(...),
    PipelineStage.CLEANUP_NEW: NewFootnoteProcessor(...),  # Add here
}
```

### Step 5: Update Pipeline Enum

```python
class PipelineStage(Enum):
    # ...
    CLEANUP_CHARACTER = (6, "cleanup_character", "...")
    CLEANUP_NEW = (7, "cleanup_new", "...")  # Increment stage numbers
    VALIDATION = (8, "validation", "...")    # Update downstream stages
```

### Step 6: Document

- Update CLAUDE.md with new substage description
- Add CLI examples
- Document expected reduction metrics

---

## Adding a New Script Generator Agent

### Step 1: Create Agent Definition

File: `.claude/agents/footnote-[type]-cleaner.md`

```markdown
---
name: footnote-[type]-cleaner
description: Generates scripts to remove [specific type] footnotes
model: sonnet
---

[Agent instructions for generating cleanup scripts]
```

### Step 2: Define Output Artifacts

Specify scripts the agent should generate:
- `[type]_analysis.py` - Identify candidates
- `[type]_deletion.py` - Remove footnotes
- `[type]_validation.py` - Verify integrity
- `[TYPE]_CLEANUP_REPORT.md` - Audit trail

### Step 3: Document Usage

- Update CLAUDE.md with agent invocation examples
- Add to footnote processing workflow
- Document expected reduction metrics

---

## Validation Requirements

ALL footnote processing substages **must** implement:

### Pre-Processing Validation
- Verify footnote structure integrity
- Count total footnotes
- Catalog all unique ideograms

### Post-Processing Validation
- Verify sequential numbering [1], [2], [3]...
- Confirm all reference markers point to valid footnotes
- Check for orphaned references or footnotes
- Validate JSON schema compliance
- Count reduction metrics

### Multi-Pass Validation
- Run validation at least 3 times with different algorithms
- Cross-validate results
- Flag discrepancies for manual review

---

## Best Practices

### For Integrated Substages:
1. **Conservative by default**: Prefer false negatives over false positives
2. **Make configurable**: Allow users to disable or configure behavior
3. **Log extensively**: Detailed logs for debugging
4. **Create backups**: WIP files before modifications
5. **Validate thoroughly**: Multiple validation passes

### For Script Generator Agents:
1. **Generate, don't execute**: Scripts must be reviewed before running
2. **Include dry-run**: Always provide preview mode
3. **Create backups**: Automatic backup before modifications
4. **Detailed reporting**: Comprehensive audit trails
5. **Rollback capability**: Provide mechanism to undo changes

---

## Summary

This framework provides a structured, extensible approach to footnote processing with:

- ✅ Clear substage organization (6a, 6b, 6c...)
- ✅ Two processing types (integrated vs script generator)
- ✅ Work-level processing enforced for all substages
- ✅ Sequential execution with renumbering
- ✅ Reserved slots for future expansion (6c-6z)
- ✅ Consistent validation requirements
- ✅ Templates for adding new substages

**Current Status**:
- 6a: Character Footnote Cleanup - ✅ Production-ready
- 6b: Duplicate Term Cleanup - 🛠️ Agent available
- 6c-6z: Reserved for future use

---

**Last Updated**: 2025-11-16
