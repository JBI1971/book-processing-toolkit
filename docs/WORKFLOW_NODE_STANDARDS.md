# Workflow Node Standards & Best Practices

**Version**: 1.0.0
**Status**: Active Standard
**Applies To**: All workflow nodes in the translation pipeline

---

## Table of Contents

1. [Overview](#overview)
2. [Node Manifest Standard](#node-manifest-standard)
3. [Business Rules Format](#business-rules-format)
4. [API Contract Standard](#api-contract-standard)
5. [Logging Standard](#logging-standard)
6. [Validation Report Standard](#validation-report-standard)
7. [Error Handling Standard](#error-handling-standard)
8. [Documentation Standard](#documentation-standard)
9. [Testing Standard](#testing-standard)
10. [Reference Implementation](#reference-implementation)

---

## Overview

### Purpose

This document defines **mandatory standards** for all workflow nodes to ensure:

- **Consistency**: Uniform patterns across simple and complex nodes
- **Discoverability**: Nodes self-describe capabilities via manifests
- **Observability**: Structured logging and metrics
- **Reliability**: Standardized error handling and validation
- **Maintainability**: Clear documentation and testing requirements
- **Composability**: Support for hierarchical node composition with aggregatable results

### Scope

These standards apply to all workflow nodes including:
- **Top-level nodes** (workflow stages: translate volume, validate work)
- **Mid-level nodes** (translate metadata, TOC, headings, body, special sections)
- **Leaf nodes** (translate chapter, translate block, validate footnote)
- **Validation stages** (pre/post checks, quality gates)
- **Cleanup stages** (footnote processing, formatting)
- **Utility nodes** (file I/O, manifest generation)

### Node Hierarchy

Nodes form a **composition hierarchy** where:

```
Translate Volume (top-level aggregator)
├─ Translate Metadata (simple node)
├─ Translate TOC (simple node)
├─ Translate Body (composite node with parallelization)
│  ├─ Translate Chapter [parallel: 5 workers] (composite node)
│  │  └─ Translate Block [parallel per chapter] (ATOMIC - one worker handles one block)
│  └─ Aggregate Chapter Results
├─ Renumber Footnotes (sequential - NOT atomic, needs coordination)
└─ Generate Volume Manifest (aggregation)

Note: "Translate Block" is ATOMIC because:
- One worker can translate one block independently
- No coordination needed with other workers
- Can safely run 50 blocks in parallel (5 workers × 10 blocks each)
```

**Key principles**:
1. **Atomic units** - Leaf nodes perform operations that can be handled by **one worker independently**
   - Examples: translate single block, validate single footnote, cleanup block footnotes
   - Atomic = "can be parallelized without coordination between workers"
2. **Aggregation** - Parent nodes collect and summarize child results
3. **Cascading validation** - Failures propagate up with context
4. **Manifest chaining** - Child manifests linked to parent manifest

### Atomic Unit Definition

**Atomic node** = smallest work unit that can be processed by a single worker without coordination.

**Guidelines for determining atomic level**:

✅ **IS atomic** if:
- One worker can complete it independently
- No need to coordinate with other workers during execution
- Can be safely parallelized (N workers process N items simultaneously)
- Examples:
  - Translate single content block
  - Validate single footnote marker
  - Clean footnotes within a single block
  - Generate footnote for a single term

❌ **NOT atomic** if:
- Requires coordination between workers (e.g., shared state, sequence dependencies)
- Must access results from other parallel operations
- Examples:
  - Renumber footnotes across entire chapter (needs sequential numbering)
  - Deduplicate footnotes across work (needs to see all footnotes)
  - Cross-reference validation (needs to check relationships)

**Atomic granularity examples**:

| Operation | Atomic Unit | Reason |
|-----------|-------------|--------|
| Translate content | **Content block** | Each block translates independently |
| Generate cultural footnotes | **Content block** | Footnotes for block don't depend on other blocks |
| Validate footnote markers | **Content block** | Check markers within block match definitions |
| Clean character footnotes | **Content block** | Remove character footnotes from single block |
| Renumber footnotes | **Chapter or Work** | Sequential numbering requires coordination (NOT atomic) |
| Deduplicate footnotes | **Work** | Must see all footnotes to find duplicates (NOT atomic) |
| Translate chapter title | **Chapter** | Single indivisible string |

**Key insight**: The atomic level determines **parallelization boundaries**.
- Atomic operations → can fan out to parallel workers
- Non-atomic operations → must run sequentially or with coordination

### Compliance

**All new nodes MUST**:
1. Provide a Node Manifest (`node_manifest.json`)
2. Implement standard contracts (`StageInput` → `StageOutput`)
3. Follow logging standard (structured JSON + human-readable)
4. Generate validation reports in standard format
5. Use standard error handling patterns
6. Include documentation per template
7. Meet testing requirements (>80% coverage)

**Existing nodes SHOULD** migrate incrementally to these standards.

---

## Hierarchical Node Composition

### Overview

Workflow nodes support **hierarchical composition** where:
- **Leaf nodes** perform atomic operations (e.g., translate single block)
- **Composite nodes** orchestrate multiple sub-nodes (e.g., translate chapter calls translate blocks)
- **Aggregator nodes** collect and summarize results (e.g., translate volume aggregates chapter results)

### Composition Patterns

#### Pattern 1: Sequential Composition

Parent node calls sub-nodes in sequence, aggregating results.

```python
# Example: Translate Chapter (mid-level composite)
class TranslateChapterNode:
    def execute(self, chapter_input: StageInput) -> StageOutput:
        # Initialize aggregator
        aggregator = ResultAggregator(node_id="translate_chapter")

        chapter_data = chapter_input.data
        blocks = chapter_data.get("content_blocks", [])

        # Call leaf node for each block
        for block in blocks:
            block_input = StageInput(
                work_id=chapter_input.work_id,
                volume=chapter_input.volume,
                data={"block": block},
                config=chapter_input.config
            )

            # Call atomic translation node
            block_result = TranslateBlockNode().execute(block_input)

            # Aggregate result
            aggregator.add_result(block_result)

            # Stop on critical failure
            if not block_result.success and self.halt_on_error:
                break

        # Generate aggregated output
        return aggregator.to_stage_output(
            success=aggregator.all_successful(),
            data=chapter_data  # With translated blocks
        )
```

#### Pattern 2: Parallel Composition

Parent node fans out to sub-nodes in parallel, collecting results.

```python
# Example: Translate Body (complex composite with parallelization)
class TranslateBodyNode:
    def execute(self, body_input: StageInput) -> StageOutput:
        aggregator = ResultAggregator(node_id="translate_body")
        chapters = body_input.data.get("chapters", [])

        # Fan out to parallel workers
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    TranslateChapterNode().execute,
                    StageInput(work_id=body_input.work_id, data={"chapter": ch})
                ): ch
                for ch in chapters
            }

            # Collect results as they complete
            for future in as_completed(futures):
                chapter_result = future.result()
                aggregator.add_result(chapter_result)

        return aggregator.to_stage_output(
            success=aggregator.all_successful(),
            data=body_input.data  # With all translated chapters
        )
```

#### Pattern 3: Hierarchical Aggregation

Top-level node aggregates results from multiple mid-level nodes.

```python
# Example: Translate Volume (top-level aggregator)
class TranslateVolumeNode:
    def execute(self, volume_input: StageInput) -> StageOutput:
        aggregator = ResultAggregator(node_id="translate_volume")

        # Call each major section
        sections = [
            ("metadata", TranslateMetadataNode()),
            ("toc", TranslateTOCNode()),
            ("headings", TranslateHeadingsNode()),
            ("body", TranslateBodyNode()),
            ("special", TranslateSpecialSectionsNode())
        ]

        for section_name, node in sections:
            result = node.execute(volume_input)
            aggregator.add_result(result, section_name=section_name)

            if not result.success and self.halt_on_section_failure:
                break

        # Generate volume-level manifest
        return aggregator.to_stage_output(
            success=aggregator.all_successful(),
            data=volume_input.data,
            rollup_manifests=True  # Include all child manifests
        )
```

### Result Aggregation

#### ResultAggregator Class

```python
# utils/result_aggregator.py

from typing import List, Dict, Any, Optional
from contracts.node_standards import StageOutput, ExecutionManifest
from datetime import datetime

class ResultAggregator:
    """
    Aggregates results from sub-nodes.

    Responsibilities:
    - Collect StageOutput from multiple sub-nodes
    - Aggregate metrics (sum counters, average scores, etc.)
    - Roll up manifests (link child manifests to parent)
    - Determine overall success/failure
    - Generate aggregated validation report
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.results: List[StageOutput] = []
        self.section_names: List[str] = []
        self.start_time = datetime.now()

    def add_result(
        self,
        result: StageOutput,
        section_name: Optional[str] = None
    ):
        """Add a sub-node result"""
        self.results.append(result)
        self.section_names.append(section_name or f"item_{len(self.results)}")

    def all_successful(self) -> bool:
        """Check if all sub-nodes succeeded"""
        return all(r.success for r in self.results)

    def aggregate_metrics(self) -> Dict[str, Any]:
        """
        Aggregate metrics from sub-nodes.

        Aggregation rules:
        - Counters: SUM (e.g., total_blocks = sum of all block counts)
        - Timers: SUM for totals, AVG for averages
        - Gauges: LAST value or AVG depending on metric
        - Quality scores: WEIGHTED AVERAGE
        """
        aggregated = {
            # Counters (sum)
            "total_items_processed": sum(r.metrics.get("items_processed", 0) for r in self.results),
            "total_success_count": sum(r.metrics.get("success_count", 0) for r in self.results),
            "total_error_count": sum(r.metrics.get("error_count", 0) for r in self.results),
            "total_warning_count": sum(r.metrics.get("warning_count", 0) for r in self.results),

            # Timers (sum for total duration)
            "total_duration_seconds": sum(r.metrics.get("duration_seconds", 0) for r in self.results),

            # Quality scores (weighted average)
            "overall_quality_score": self._weighted_average_quality(),

            # Sub-node tracking
            "sub_nodes_executed": len(self.results),
            "sub_nodes_successful": sum(1 for r in self.results if r.success),
            "sub_nodes_failed": sum(1 for r in self.results if not r.success),

            # Section breakdown
            "sections": {
                name: {
                    "success": result.success,
                    "items": result.metrics.get("items_processed", 0),
                    "quality": result.metrics.get("quality_score", 0)
                }
                for name, result in zip(self.section_names, self.results)
            }
        }

        return aggregated

    def _weighted_average_quality(self) -> float:
        """
        Calculate weighted average quality score.

        Weight by items_processed (more items = more weight)
        """
        total_items = 0
        weighted_sum = 0.0

        for result in self.results:
            items = result.metrics.get("items_processed", 1)  # Default weight 1
            quality = result.metrics.get("quality_score", 0.0)

            total_items += items
            weighted_sum += quality * items

        if total_items == 0:
            return 0.0

        return weighted_sum / total_items

    def rollup_manifests(self) -> Dict[str, Any]:
        """
        Create parent manifest with links to child manifests.

        Returns:
            {
                "parent_manifest": ExecutionManifest,
                "child_manifests": [
                    {"section": "metadata", "manifest": {...}},
                    {"section": "body", "manifest": {...}}
                ]
            }
        """
        end_time = datetime.now()

        parent_manifest = {
            "stage_name": self.node_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - self.start_time).total_seconds(),

            # Aggregated metrics
            "items_processed": sum(r.manifest.get("items_processed", 0) for r in self.results),
            "success_count": sum(r.manifest.get("success_count", 0) for r in self.results),
            "error_count": sum(r.manifest.get("error_count", 0) for r in self.results),
            "quality_score": self._weighted_average_quality(),

            # Validation rollup
            "validation_passed": all(
                r.manifest.get("validation_passed", False) for r in self.results
            ),

            # Child tracking
            "child_nodes": len(self.results),
            "child_nodes_successful": sum(1 for r in self.results if r.success),
        }

        child_manifests = [
            {
                "section": name,
                "manifest": result.manifest,
                "success": result.success
            }
            for name, result in zip(self.section_names, self.results)
        ]

        return {
            "parent_manifest": parent_manifest,
            "child_manifests": child_manifests
        }

    def aggregate_validation_reports(self) -> Dict[str, Any]:
        """
        Aggregate validation reports from sub-nodes.

        Combines:
        - All errors from all sub-nodes
        - All warnings from all sub-nodes
        - Overall validation status (all must pass)
        """
        all_errors = []
        all_warnings = []
        all_info = []

        for section, result in zip(self.section_names, self.results):
            if result.validation_report:
                vr = result.validation_report

                # Prefix errors/warnings with section name
                all_errors.extend([f"[{section}] {e}" for e in vr.get("errors", [])])
                all_warnings.extend([f"[{section}] {w}" for w in vr.get("warnings", [])])
                all_info.extend([f"[{section}] {i}" for i in vr.get("info", [])])

        return {
            "is_valid": all(
                r.validation_report.get("is_valid", True) if r.validation_report else True
                for r in self.results
            ),
            "errors": all_errors,
            "warnings": all_warnings,
            "info": all_info,
            "sections_validated": len(self.results),
            "sections_passed": sum(
                1 for r in self.results
                if r.validation_report and r.validation_report.get("is_valid", False)
            )
        }

    def to_stage_output(
        self,
        success: bool,
        data: Dict[str, Any],
        rollup_manifests: bool = True
    ) -> StageOutput:
        """
        Convert aggregated results to StageOutput.

        Args:
            success: Overall success (usually all_successful())
            data: Processed data (with all sub-node modifications)
            rollup_manifests: Include child manifests in output
        """
        aggregated_metrics = self.aggregate_metrics()

        if rollup_manifests:
            manifest_data = self.rollup_manifests()
            manifest = manifest_data["parent_manifest"]
            manifest["child_manifests"] = manifest_data["child_manifests"]
        else:
            manifest = {
                "stage_name": self.node_id,
                "duration_seconds": (datetime.now() - self.start_time).total_seconds()
            }

        # Collect all warnings from sub-nodes
        all_warnings = []
        for result in self.results:
            all_warnings.extend(result.warnings)

        # Collect error details if any sub-node failed
        error_details = None
        if not success:
            failed_sections = [
                {
                    "section": name,
                    "error": result.error_details
                }
                for name, result in zip(self.section_names, self.results)
                if not result.success
            ]
            error_details = {
                "failed_sections": failed_sections,
                "total_failures": len(failed_sections)
            }

        return StageOutput(
            success=success,
            data=data,
            manifest=manifest,
            metrics=aggregated_metrics,
            validation_report=self.aggregate_validation_reports(),
            error_details=error_details,
            warnings=all_warnings
        )
```

### Manifest Hierarchy Example

When a composite node completes, its manifest includes child manifests:

```json
{
  "parent_manifest": {
    "stage_name": "translate_volume",
    "duration_seconds": 245.67,
    "items_processed": 1523,
    "success_count": 1520,
    "error_count": 3,
    "quality_score": 94.5,
    "child_nodes": 5,
    "child_nodes_successful": 5
  },
  "child_manifests": [
    {
      "section": "metadata",
      "success": true,
      "manifest": {
        "stage_name": "translate_metadata",
        "duration_seconds": 2.34,
        "items_processed": 3,
        "quality_score": 95.0
      }
    },
    {
      "section": "body",
      "success": true,
      "manifest": {
        "stage_name": "translate_body",
        "duration_seconds": 230.12,
        "items_processed": 1500,
        "quality_score": 94.2,
        "child_nodes": 50,
        "child_manifests": [
          {
            "section": "chapter_1",
            "manifest": {
              "stage_name": "translate_chapter",
              "items_processed": 30,
              "quality_score": 95.5
            }
          }
          // ... more chapters
        ]
      }
    }
  ]
}
```

### Cascading Validation

Validation failures cascade up the hierarchy with context:

```python
# Leaf node validation failure
block_validation = ValidationReport(
    is_valid=False,
    errors=["Footnote marker [5] has no definition"],
    context={"block_id": "block_0123", "chapter": 5}
)

# Mid-level node aggregates
chapter_validation = {
    "is_valid": False,
    "errors": [
        "[block_0123] Footnote marker [5] has no definition"
    ],
    "context": {"chapter": 5, "failed_blocks": 1, "total_blocks": 30}
}

# Top-level node aggregates
volume_validation = {
    "is_valid": False,
    "errors": [
        "[body/chapter_5/block_0123] Footnote marker [5] has no definition"
    ],
    "context": {
        "failed_chapters": 1,
        "total_chapters": 50,
        "failed_sections": ["body"]
    }
}
```

This allows you to trace exactly where the error occurred: Volume → Body → Chapter 5 → Block 0123.

---

## Node Manifest Standard

### Overview

Every node MUST provide a **manifest file** (`node_manifest.json`) describing its capabilities, requirements, and configuration.

### Schema

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "node_id",
    "node_name",
    "version",
    "complexity",
    "inputs",
    "outputs",
    "business_rules"
  ],
  "properties": {
    "node_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$",
      "description": "Unique identifier (snake_case)"
    },
    "node_name": {
      "type": "string",
      "description": "Human-readable name"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version"
    },
    "complexity": {
      "type": "string",
      "enum": ["simple", "moderate", "complex"],
      "description": "Node complexity level"
    },
    "description": {
      "type": "string",
      "description": "Detailed description of what this node does"
    },
    "inputs": {
      "type": "object",
      "description": "Input schema definition",
      "required": ["schema", "required_fields"],
      "properties": {
        "schema": {"type": "string"},
        "required_fields": {"type": "array", "items": {"type": "string"}},
        "optional_fields": {"type": "array", "items": {"type": "string"}}
      }
    },
    "outputs": {
      "type": "object",
      "description": "Output schema definition",
      "required": ["schema", "guarantees"],
      "properties": {
        "schema": {"type": "string"},
        "guarantees": {"type": "array", "items": {"type": "string"}}
      }
    },
    "business_rules": {
      "type": "array",
      "description": "Declarative business rules",
      "items": {
        "type": "object",
        "required": ["rule_id", "severity", "description"],
        "properties": {
          "rule_id": {"type": "string"},
          "severity": {"type": "string", "enum": ["error", "warning", "info"]},
          "description": {"type": "string"},
          "check": {"type": "string"},
          "auto_fix": {"type": "boolean"}
        }
      }
    },
    "dependencies": {
      "type": "object",
      "description": "External dependencies",
      "properties": {
        "apis": {"type": "array", "items": {"type": "string"}},
        "files": {"type": "array", "items": {"type": "string"}},
        "environment": {"type": "array", "items": {"type": "string"}}
      }
    },
    "parallelization": {
      "type": "object",
      "description": "Parallel execution configuration (complex nodes)",
      "properties": {
        "strategy": {"type": "string", "enum": ["fan_out", "pipeline", "none"]},
        "max_workers": {"type": "integer"},
        "partition_by": {"type": "string"}
      }
    },
    "checkpointing": {
      "type": "object",
      "description": "Checkpoint/resume configuration",
      "properties": {
        "enabled": {"type": "boolean"},
        "granularity": {"type": "string", "enum": ["none", "stage", "item"]},
        "storage_path": {"type": "string"}
      }
    },
    "metrics": {
      "type": "object",
      "description": "Metrics this node reports",
      "properties": {
        "counters": {"type": "array", "items": {"type": "string"}},
        "timers": {"type": "array", "items": {"type": "string"}},
        "gauges": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
}
```

### Example: Simple Node (Metadata Translation)

```json
{
  "node_id": "metadata_translation",
  "node_name": "Metadata Translation",
  "version": "1.0.0",
  "complexity": "simple",
  "description": "Translates book metadata (title, author, publisher) from Chinese to English without adding footnotes",

  "inputs": {
    "schema": "StageInput",
    "required_fields": ["work_id", "data.meta.title_chinese"],
    "optional_fields": ["data.meta.author_chinese", "data.meta.publisher_chinese"]
  },

  "outputs": {
    "schema": "StageOutput",
    "guarantees": [
      "data.meta.title_english populated",
      "No footnotes in metadata fields",
      "Validation report included"
    ]
  },

  "business_rules": [
    {
      "rule_id": "title_required",
      "severity": "error",
      "description": "Chinese title must exist",
      "check": "data.meta.title_chinese is not None and len(data.meta.title_chinese) > 0"
    },
    {
      "rule_id": "translation_not_empty",
      "severity": "error",
      "description": "English translation must not be empty",
      "check": "data.meta.title_english is not None and len(data.meta.title_english) > 0"
    },
    {
      "rule_id": "translation_different",
      "severity": "warning",
      "description": "English should differ from Chinese",
      "check": "data.meta.title_english != data.meta.title_chinese"
    }
  ],

  "dependencies": {
    "apis": ["OpenAI GPT-4.1-nano"],
    "files": [],
    "environment": ["OPENAI_API_KEY"]
  },

  "parallelization": {
    "strategy": "none"
  },

  "checkpointing": {
    "enabled": false
  },

  "metrics": {
    "counters": ["fields_translated", "api_calls"],
    "timers": ["translation_duration"],
    "gauges": ["character_count_chinese", "character_count_english"]
  }
}
```

### Example: Complex Node (Body Translation)

```json
{
  "node_id": "body_translation",
  "node_name": "Body Translation (Parallel)",
  "version": "1.0.0",
  "complexity": "complex",
  "description": "Translates main story chapters in parallel with cultural footnote generation",

  "inputs": {
    "schema": "StageInput",
    "required_fields": ["work_id", "data.structure.body.chapters"],
    "optional_fields": ["config.max_workers", "config.checkpoint_path"]
  },

  "outputs": {
    "schema": "StageOutput",
    "guarantees": [
      "All chapters translated with English content",
      "Cultural footnotes added where appropriate",
      "Footnote markers balanced (all markers have definitions)",
      "Validation report with footnote integrity check"
    ]
  },

  "business_rules": [
    {
      "rule_id": "has_chapters",
      "severity": "error",
      "description": "Body must have at least one chapter",
      "check": "len(data.structure.body.chapters) > 0"
    },
    {
      "rule_id": "footnote_markers_balanced",
      "severity": "error",
      "description": "All footnote markers must have corresponding definitions",
      "check": "footnote_integrity_validator.validate(data).is_valid"
    },
    {
      "rule_id": "minimum_translation_length",
      "severity": "warning",
      "description": "Translated text should be at least 50% of original length",
      "check": "len(english_text) >= 0.5 * len(chinese_text)"
    },
    {
      "rule_id": "no_untranslated_blocks",
      "severity": "error",
      "description": "All content blocks must be translated",
      "check": "all(block.get('content_english') for block in all_blocks)"
    }
  ],

  "dependencies": {
    "apis": ["OpenAI GPT-4.1-nano"],
    "files": ["wuxia_glossary.json"],
    "environment": ["OPENAI_API_KEY"]
  },

  "parallelization": {
    "strategy": "fan_out",
    "max_workers": 5,
    "partition_by": "chapter"
  },

  "checkpointing": {
    "enabled": true,
    "granularity": "item",
    "storage_path": "wip/stage_4_body/{work_id}_checkpoint.json"
  },

  "metrics": {
    "counters": [
      "chapters_translated",
      "blocks_translated",
      "footnotes_generated",
      "api_calls_total"
    ],
    "timers": [
      "total_translation_duration",
      "avg_chapter_duration",
      "avg_api_latency"
    ],
    "gauges": [
      "chinese_character_count",
      "english_word_count",
      "footnote_count",
      "parallel_workers_active"
    ]
  }
}
```

---

## Business Rules Format

### Overview

Business rules are declared in **node manifests** and evaluated programmatically by the `BusinessRuleEngine`.

### Rule Definition

```python
# contracts/node_standards.py

from pydantic import BaseModel
from typing import Callable, Optional, Any

class BusinessRule(BaseModel):
    """Declarative business rule definition"""

    rule_id: str  # Unique identifier (e.g., "title_required")
    severity: str  # "error", "warning", "info"
    description: str  # Human-readable description
    check: str  # Python expression or function reference
    auto_fix: Optional[bool] = False  # Can this be auto-fixed?
    fix_function: Optional[str] = None  # Function to auto-fix

    class Config:
        # Allow function references
        arbitrary_types_allowed = True
```

### Rule Evaluation

```python
# utils/business_rules.py

class BusinessRuleEngine:
    """Evaluate business rules for workflow nodes"""

    def __init__(self):
        self.rules: Dict[str, List[BusinessRule]] = {}

    def register_rules_from_manifest(self, manifest: NodeManifest):
        """Load rules from node manifest"""
        for rule_dict in manifest.business_rules:
            rule = BusinessRule(**rule_dict)
            self.register_rule(manifest.node_id, rule)

    def evaluate(
        self,
        node_id: str,
        data: Any,
        context: Optional[Dict] = None
    ) -> RuleEvaluationResult:
        """
        Evaluate all rules for a node.

        Returns:
            RuleEvaluationResult with:
            - passed_rules: List[str]
            - failed_rules: List[Dict[str, Any]]
            - severity_counts: {"error": 0, "warning": 2, "info": 0}
            - can_auto_fix: bool
            - suggested_fixes: List[str]
        """
        result = RuleEvaluationResult()

        for rule in self.rules.get(node_id, []):
            try:
                # Evaluate rule check
                passed = self._evaluate_check(rule.check, data, context)

                if passed:
                    result.passed_rules.append(rule.rule_id)
                else:
                    result.failed_rules.append({
                        "rule_id": rule.rule_id,
                        "severity": rule.severity,
                        "description": rule.description,
                        "auto_fix_available": rule.auto_fix
                    })
                    result.severity_counts[rule.severity] += 1

                    if rule.auto_fix:
                        result.suggested_fixes.append(
                            f"Auto-fix available: {rule.fix_function}"
                        )
            except Exception as e:
                # Rule evaluation failed (bad check expression)
                result.failed_rules.append({
                    "rule_id": rule.rule_id,
                    "severity": "error",
                    "description": f"Rule evaluation error: {str(e)}"
                })

        result.can_auto_fix = any(
            r.get("auto_fix_available") for r in result.failed_rules
        )

        return result

    def _evaluate_check(
        self,
        check: str,
        data: Any,
        context: Optional[Dict]
    ) -> bool:
        """
        Evaluate a rule check expression.

        Supports:
        - Simple expressions: "data.meta.title_chinese is not None"
        - Function calls: "footnote_integrity_validator.validate(data).is_valid"
        """
        # Build evaluation context
        eval_context = {
            "data": data,
            "len": len,
            "all": all,
            "any": any,
            **(context or {})
        }

        # Safely evaluate
        try:
            return eval(check, {"__builtins__": {}}, eval_context)
        except Exception as e:
            raise ValueError(f"Rule check evaluation failed: {check}") from e
```

### Rule Categories

**Error Rules** (severity="error"):
- MUST pass for workflow to continue
- Failed error rules halt stage execution
- Examples: required fields missing, data corruption, invalid state

**Warning Rules** (severity="warning"):
- SHOULD pass but workflow continues
- Logged for review and improvement
- Examples: quality concerns, suspicious patterns, optimization suggestions

**Info Rules** (severity="info"):
- Informational checks
- Tracked for metrics and analysis
- Examples: translation length ratios, API usage patterns

---

## API Contract Standard

### Overview

All workflow nodes communicate via **standardized contracts** defined with Pydantic models.

### Base Contracts

```python
# contracts/node_standards.py

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class StageInput(BaseModel):
    """Standard input for all workflow nodes"""

    work_id: str = Field(..., description="Work identifier (e.g., D1379)")
    volume: Optional[str] = Field(None, description="Volume identifier")
    data: Dict[str, Any] = Field(..., description="Input data (book JSON)")

    # Optional fields
    checkpoint_path: Optional[str] = Field(None, description="Path to checkpoint file")
    previous_stage_manifest: Optional[Dict] = Field(None, description="Manifest from previous stage")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Node configuration")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

class StageOutput(BaseModel):
    """Standard output from all workflow nodes"""

    success: bool = Field(..., description="Whether stage completed successfully")
    data: Dict[str, Any] = Field(..., description="Output data (modified book JSON)")
    manifest: Dict[str, Any] = Field(..., description="Stage execution manifest")
    metrics: Dict[str, Any] = Field(..., description="Stage metrics")

    # Optional fields
    validation_report: Optional[Dict] = Field(None, description="Validation results")
    error_details: Optional[Dict] = Field(None, description="Error context if failed")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated artifacts")
```

### Execution Manifest

```python
class ExecutionManifest(BaseModel):
    """Manifest tracking stage execution"""

    # Identity
    stage_name: str
    stage_version: str
    work_id: str
    volume: Optional[str]

    # Inputs
    input_hash: str = Field(..., description="SHA256 hash of input data")
    input_metadata: Dict[str, Any]

    # Outputs
    output_hash: str = Field(..., description="SHA256 hash of output data")
    output_metadata: Dict[str, Any]

    # Timing
    start_time: datetime
    end_time: datetime
    duration_seconds: float

    # Quality
    items_processed: int
    success_count: int
    error_count: int
    warning_count: int
    quality_score: float = Field(..., ge=0.0, le=100.0)

    # Validation
    validation_passed: bool
    validation_details: Dict[str, Any]
    business_rules_evaluated: int
    business_rules_passed: int
    business_rules_failed: int

    # Dependencies
    dependencies_used: List[str] = Field(default_factory=list)
    checkpoints_created: List[str] = Field(default_factory=list)
    artifacts_generated: List[str] = Field(default_factory=list)

    # Lineage
    previous_stage: Optional[str] = None
    next_stage: Optional[str] = None
```

---

## Logging Standard

### Overview

All nodes MUST use **structured logging** with dual output:
1. **JSON logs** - Machine-readable for analysis
2. **Human-readable logs** - For debugging and monitoring

### Log Entry Schema

```python
class LogEntry(BaseModel):
    """Standard log entry format"""

    timestamp: datetime
    level: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    event: str  # Event type (e.g., "stage_start", "validation_failed")

    # Context
    node_id: str
    work_id: str
    volume: Optional[str]

    # Message
    message: str

    # Additional data
    data: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    # Trace
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
```

### Standard Events

All nodes MUST log these events:

1. **`stage_start`** - Stage begins execution
2. **`stage_complete`** - Stage finishes successfully
3. **`stage_error`** - Stage encounters error
4. **`validation_start`** - Validation begins
5. **`validation_complete`** - Validation finishes
6. **`business_rule_failed`** - Business rule fails
7. **`checkpoint_created`** - Checkpoint saved
8. **`artifact_generated`** - Artifact created

### Example Usage

```python
from utils.workflow_logger import WorkflowLogger

# Initialize logger
logger = WorkflowLogger(
    node_id="metadata_translation",
    work_id="D1379",
    log_dir=Path("logs")
)

# Log stage start
logger.log_stage_start(
    input_data=stage_input.data,
    config=config
)

# Log validation
logger.log_validation(
    validation_report=validation_result,
    passed=validation_result.is_valid
)

# Log completion
logger.log_stage_complete(
    output_data=output.data,
    metrics=output.metrics,
    duration=elapsed_time
)
```

**Output (JSON)**:
```json
{
  "timestamp": "2025-11-16T14:30:00.000Z",
  "level": "INFO",
  "event": "stage_complete",
  "node_id": "metadata_translation",
  "work_id": "D1379",
  "volume": null,
  "message": "Metadata translation completed successfully",
  "data": {
    "fields_translated": 3,
    "quality_score": 95.0
  },
  "metrics": {
    "duration_seconds": 2.34,
    "api_calls": 3,
    "chinese_chars": 45,
    "english_chars": 52
  }
}
```

---

## Validation Report Standard

### Overview

All nodes that perform validation MUST return reports in this standardized format.

### Schema

```python
class ValidationReport(BaseModel):
    """Standard validation report format"""

    # Overall result
    is_valid: bool
    confidence_score: float = Field(..., ge=0.0, le=100.0)

    # Validation types
    schema_valid: bool
    business_rules_passed: bool
    data_quality_score: float = Field(..., ge=0.0, le=100.0)

    # Details
    checks_passed: List[str] = Field(default_factory=list)
    checks_failed: List[Dict[str, Any]] = Field(default_factory=list)

    # Issues
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    info: List[str] = Field(default_factory=list)

    # Recommendations
    suggested_fixes: List[str] = Field(default_factory=list)
    auto_fixable: bool = False

    # Metadata
    validator_version: str
    validation_timestamp: datetime
    validation_duration_seconds: float
```

### Example

```python
ValidationReport(
    is_valid=False,
    confidence_score=75.0,

    schema_valid=True,
    business_rules_passed=False,
    data_quality_score=80.0,

    checks_passed=[
        "title_required",
        "schema_structure_valid"
    ],

    checks_failed=[
        {
            "check": "translation_different",
            "severity": "warning",
            "message": "English title identical to Chinese (possible translation failure)",
            "data": {
                "title_chinese": "金庸作品集",
                "title_english": "金庸作品集"
            }
        }
    ],

    errors=[],
    warnings=["Title translation may have failed - review recommended"],
    info=["Translation completed in 2.3 seconds"],

    suggested_fixes=[
        "Re-translate title with explicit English instruction",
        "Check OpenAI API response for errors"
    ],
    auto_fixable=True,

    validator_version="1.0.0",
    validation_timestamp=datetime.now(),
    validation_duration_seconds=0.05
)
```

---

## Error Handling Standard

### Exception Hierarchy

```python
# contracts/exceptions.py

class WorkflowNodeError(Exception):
    """Base exception for all workflow node errors"""

    def __init__(
        self,
        message: str,
        error_code: str,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.recoverable = recoverable

class InputValidationError(WorkflowNodeError):
    """Input data failed validation"""
    pass

class BusinessRuleViolationError(WorkflowNodeError):
    """Business rule failed (severity=error)"""
    pass

class ExternalDependencyError(WorkflowNodeError):
    """External API/file dependency failed"""
    pass

class DataQualityError(WorkflowNodeError):
    """Output quality below acceptable threshold"""
    pass

class CheckpointError(WorkflowNodeError):
    """Checkpoint save/load failed"""
    pass
```

### Error Codes

Standard error codes follow pattern: `<NODE>_<CATEGORY>_<SPECIFIC>`

Examples:
- `META_INPUT_MISSING_TITLE` - Metadata translation: missing title
- `BODY_RULE_FOOTNOTE_UNBALANCED` - Body translation: footnote markers don't match
- `TOC_API_RATE_LIMIT` - TOC translation: OpenAI rate limit hit
- `VALID_DQ_LOW_QUALITY` - Validation: data quality score too low

### Error Context

All errors MUST include context:

```python
raise InputValidationError(
    message="Required field 'title_chinese' not found in metadata",
    error_code="META_INPUT_MISSING_TITLE",
    context={
        "work_id": "D1379",
        "stage": "metadata_translation",
        "available_fields": list(meta.keys()),
        "required_fields": ["title_chinese"]
    },
    recoverable=False  # Cannot continue without title
)
```

---

## Documentation Standard

### Required Sections

Every workflow node MUST include documentation with these sections:

#### 1. Overview
- What the node does (1-2 sentences)
- When it runs in the pipeline
- Typical execution time

#### 2. Inputs
- Required fields in `StageInput.data`
- Optional fields
- Configuration parameters
- Example input

#### 3. Outputs
- Guaranteed fields in `StageOutput.data`
- Output modifications
- Example output

#### 4. Business Rules
- List of all rules (reference manifest)
- Rule rationale (why each rule exists)
- Failure scenarios

#### 5. Dependencies
- APIs required (with fallback behavior)
- Files required (with location)
- Environment variables

#### 6. Error Handling
- Common errors
- Recovery strategies
- When to retry vs fail

#### 7. Performance
- Typical execution time
- Resource usage (memory, API calls)
- Scaling characteristics

#### 8. Examples
- Minimal example
- Real-world example
- Edge cases

### Template

```markdown
# {Node Name}

**Node ID**: `{node_id}`
**Version**: `{version}`
**Complexity**: `{simple|moderate|complex}`

## Overview

{What this node does - 1-2 sentences}

**Pipeline Position**: Stage {N} of 7
**Typical Duration**: {X} seconds
**Parallelizable**: {Yes|No}

## Inputs

### Required Fields
- `data.{field_path}` - {description}

### Optional Fields
- `data.{field_path}` - {description}

### Configuration
```python
config = {
    "parameter": "value"  # Description
}
```

### Example Input
```json
{example}
```

## Outputs

### Guarantees
- `data.{field_path}` will be populated
- Validation report included

### Example Output
```json
{example}
```

## Business Rules

| Rule ID | Severity | Description |
|---------|----------|-------------|
| {rule_id} | {error|warning} | {description} |

**Rationale**: {Why these rules exist}

## Dependencies

- **APIs**: {list}
- **Files**: {list}
- **Environment**: {list}

## Error Handling

| Error Code | Description | Recovery |
|------------|-------------|----------|
| {code} | {description} | {strategy} |

## Performance

- **Typical Time**: {X}s
- **API Calls**: {N} per execution
- **Memory**: {X}MB peak

## Examples

{Provide 2-3 examples}
```

---

## Testing Standard

### Requirements

All workflow nodes MUST have:

1. **Unit Tests** (>80% coverage)
   - Test each business rule independently
   - Test validation logic
   - Test error handling
   - Mock external dependencies

2. **Integration Tests**
   - Test with real data samples
   - Test with previous stage output
   - Test checkpoint/resume
   - Test parallel execution (if applicable)

3. **Contract Tests**
   - Validate `StageInput` schema compliance
   - Validate `StageOutput` schema compliance
   - Validate manifest format

### Test Structure

```
tests/
└── nodes/
    └── test_{node_id}/
        ├── test_unit.py           # Unit tests
        ├── test_integration.py    # Integration tests
        ├── test_contracts.py      # Contract validation
        ├── test_business_rules.py # Rule evaluation
        └── fixtures/
            ├── input_valid.json
            ├── input_invalid.json
            └── expected_output.json
```

### Example Test

```python
# tests/nodes/test_metadata_translation/test_unit.py

import pytest
from wrappers.metadata_translation_wrapper import MetadataTranslationWrapper
from contracts.node_standards import StageInput, StageOutput

def test_translate_title_success():
    """Test successful title translation"""
    wrapper = MetadataTranslationWrapper(config={
        "model": "gpt-4.1-nano",
        "temperature": 0.3
    })

    input_data = StageInput(
        work_id="D1379",
        data={
            "meta": {
                "title_chinese": "偷拳"
            }
        }
    )

    result: StageOutput = wrapper.execute(input_data)

    assert result.success
    assert result.data["meta"]["title_english"] is not None
    assert len(result.data["meta"]["title_english"]) > 0
    assert result.manifest["validation_passed"]

def test_missing_title_fails():
    """Test error handling when title is missing"""
    wrapper = MetadataTranslationWrapper(config={})

    input_data = StageInput(
        work_id="D1379",
        data={"meta": {}}  # Missing title
    )

    result: StageOutput = wrapper.execute(input_data)

    assert not result.success
    assert result.error_details is not None
    assert "title_chinese" in str(result.error_details)

def test_business_rule_evaluation():
    """Test business rules are evaluated correctly"""
    wrapper = MetadataTranslationWrapper(config={})

    # Test data that violates "translation_different" rule
    data = {
        "meta": {
            "title_chinese": "Test Title",
            "title_english": "Test Title"  # Same as Chinese - should warn
        }
    }

    validation = wrapper.validate_output(data)

    assert validation.is_valid  # Still valid (warning, not error)
    assert len(validation.warnings) > 0
    assert any("translation_different" in str(w) for w in validation.warnings)
```

---

## Reference Implementation

### Simple Node Example

See: `templates/simple_node_template.py`

**Characteristics**:
- Straightforward logic
- No parallelization
- Few business rules
- Fast execution (<5s)

**Example**: Metadata Translation
- Translates 3-4 fields
- Simple validation
- No checkpointing needed

### Complex Node Example

See: `templates/complex_node_template.py`

**Characteristics**:
- Parallel execution
- Many business rules
- Checkpointing required
- Long execution (minutes)

**Example**: Body Translation
- Translates 100+ chapters
- Fan-out parallelization
- Cultural footnote generation
- Checkpoint after each chapter
- Complex validation (footnote integrity)

---

## Enforcement

### Programmatic Validation

Use the `NodeValidator` tool to check compliance:

```bash
# Validate single node
python utils/node_validator.py --node wrappers/metadata_translation_wrapper.py

# Validate all nodes
python utils/node_validator.py --all

# Generate compliance report
python utils/node_validator.py --all --report compliance_report.json
```

**Checks**:
- ✅ Manifest file exists and valid
- ✅ Implements required contracts
- ✅ Logging standards followed
- ✅ Documentation sections complete
- ✅ Test coverage >80%
- ✅ Business rules declared

### CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/validate_nodes.yml
- name: Validate Workflow Nodes
  run: |
    python utils/node_validator.py --all --strict
    # Fails build if any node is non-compliant
```

---

## Migration Guide

### For Existing Nodes

1. **Create manifest** - Start with minimal manifest, expand incrementally
2. **Adopt contracts** - Wrap existing code with `StageInput`/`StageOutput`
3. **Add logging** - Use `WorkflowLogger` for structured logs
4. **Document rules** - Extract implicit rules to manifest
5. **Add tests** - Achieve >80% coverage
6. **Update docs** - Follow documentation template

### For New Nodes

1. Copy template (`simple_node_template.py` or `complex_node_template.py`)
2. Fill in manifest
3. Implement business logic
4. Write tests
5. Document per standard
6. Validate with `NodeValidator`

---

## Version History

- **1.0.0** (2025-11-16) - Initial standard
