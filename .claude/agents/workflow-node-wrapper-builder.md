# Workflow Node Wrapper Builder Agent

## Purpose

Design and implement **wrapper scripts** that provide clean, workflow-ready interfaces around existing translation utilities. These wrappers handle:

- **Business rules** and success criteria
- **Data quality validation** (pre/post checks)
- **Manifest generation** (input/output tracking, metadata)
- **Structured logging** (JSON logs, progress reports)
- **Error handling** with retry policies
- **Checkpoint/resume** support
- **Contract validation** (input/output schemas)

## Core Responsibilities

### 1. Analyze Existing Utilities

Before building wrappers, understand what utilities exist:
- `processors/json_cleaner.py`
- `processors/content_structurer.py`
- `processors/book_translator.py`
- `utils/footnote_generator.py`
- `utils/cleanup_character_footnotes.py`
- `utils/validation/footnote_integrity_validator.py`

Document:
- Input requirements (file paths, data structures, config)
- Output formats (modified data, reports, artifacts)
- Error conditions and failure modes
- Performance characteristics (fast vs slow, API-dependent)

### 2. Design Wrapper Architecture

Create a **consistent wrapper pattern** for all utilities:

```python
# Standard wrapper interface
class TranslationStageWrapper:
    """
    Base class for workflow stage wrappers.

    Responsibilities:
    - Input validation (schema, file existence, prerequisites)
    - Business rule evaluation (success criteria)
    - Manifest generation (tracking inputs/outputs)
    - Structured logging (JSON + human-readable)
    - Data quality checks (pre/post processing)
    - Error handling with context
    """

    def __init__(self, config: WrapperConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.manifest = Manifest()

    def validate_input(self, data: Any) -> ValidationResult:
        """Validate input against schema and business rules"""
        pass

    def execute(self, input_data: Any) -> StageResult:
        """
        Main execution method called by workflow.

        Returns StageResult with:
        - success: bool
        - output_data: Any
        - manifest: Manifest (inputs, outputs, metadata)
        - metrics: Dict (timing, counts, quality scores)
        - logs: List[LogEntry]
        - validation_report: Optional[ValidationReport]
        """
        pass

    def validate_output(self, data: Any) -> ValidationResult:
        """Validate output against quality criteria"""
        pass
```

### 3. Define Data Contracts

Create **strict contracts** between workflow stages:

```python
# contracts/translation_contracts.py

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class StageInput(BaseModel):
    """Input contract for workflow stages"""
    work_id: str
    volume: Optional[str]
    data: Dict[str, Any]
    checkpoint_path: Optional[str] = None
    previous_stage_manifest: Optional[Dict] = None

class StageOutput(BaseModel):
    """Output contract from workflow stages"""
    success: bool
    data: Dict[str, Any]
    manifest: Dict[str, Any]  # See Manifest schema below
    metrics: Dict[str, Any]
    validation_report: Optional[Dict] = None
    error_details: Optional[Dict] = None

class Manifest(BaseModel):
    """Manifest tracking all stage I/O"""
    stage_name: str
    work_id: str
    volume: Optional[str]

    # Inputs
    input_file: Optional[str]
    input_hash: str
    input_metadata: Dict[str, Any]

    # Outputs
    output_file: Optional[str]
    output_hash: str
    output_metadata: Dict[str, Any]

    # Processing
    start_time: datetime
    end_time: datetime
    duration_seconds: float

    # Quality metrics
    items_processed: int
    success_count: int
    error_count: int
    quality_score: float  # 0-100

    # Validation
    validation_passed: bool
    validation_details: Dict[str, Any]

    # Dependencies
    dependencies: List[str]  # Files/resources used
    checkpoints: List[str]   # Checkpoint files created

class ValidationReport(BaseModel):
    """Comprehensive validation report"""
    is_valid: bool
    confidence_score: float  # 0-100

    # Rule-based checks
    schema_valid: bool
    business_rules_passed: bool
    data_quality_score: float

    # Specific checks
    checks_passed: List[str]
    checks_failed: List[Dict[str, Any]]

    # Recommendations
    warnings: List[str]
    errors: List[str]
    suggested_fixes: List[str]
```

### 4. Implement Business Rules Engine

Create a **declarative business rules system**:

```python
# utils/business_rules.py

from typing import Callable, List
from dataclasses import dataclass

@dataclass
class BusinessRule:
    """Single business rule definition"""
    name: str
    description: str
    check_function: Callable[[Any], bool]
    error_message: str
    severity: str  # "error", "warning", "info"
    auto_fix: Optional[Callable[[Any], Any]] = None

class BusinessRuleEngine:
    """Evaluate business rules for workflow stages"""

    def __init__(self):
        self.rules = {}

    def register_rule(self, stage: str, rule: BusinessRule):
        """Register a rule for a specific stage"""
        if stage not in self.rules:
            self.rules[stage] = []
        self.rules[stage].append(rule)

    def evaluate(self, stage: str, data: Any) -> RuleEvaluationResult:
        """
        Evaluate all rules for a stage.

        Returns:
            RuleEvaluationResult with passed/failed rules,
            severity counts, auto-fix suggestions
        """
        pass

# Example rules for translation stages
TRANSLATION_RULES = {
    "body_translation": [
        BusinessRule(
            name="has_chapters",
            description="Body must have at least one chapter",
            check_function=lambda data: len(data.get("structure", {}).get("body", {}).get("chapters", [])) > 0,
            error_message="No chapters found in body",
            severity="error"
        ),
        BusinessRule(
            name="footnote_markers_balanced",
            description="All footnote markers must have corresponding definitions",
            check_function=lambda data: validate_footnote_balance(data),
            error_message="Unbalanced footnote markers detected",
            severity="error"
        ),
        BusinessRule(
            name="minimum_translation_length",
            description="Translated text should be at least 50% of original length",
            check_function=lambda data: check_translation_length_ratio(data) >= 0.5,
            error_message="Translation appears truncated or incomplete",
            severity="warning"
        )
    ]
}
```

### 5. Create Wrapper Scripts

Build **individual wrappers** for each workflow stage:

#### Example: Metadata Translation Wrapper
```python
# wrappers/metadata_translation_wrapper.py

from typing import Dict, Any
from pathlib import Path
import hashlib
import json
from datetime import datetime

from processors.book_translator import BookTranslator
from utils.business_rules import BusinessRuleEngine
from contracts.translation_contracts import (
    StageInput, StageOutput, Manifest, ValidationReport
)

class MetadataTranslationWrapper:
    """
    Wrapper for metadata translation stage.

    Responsibilities:
    - Validate input has required metadata fields
    - Translate title, author, publisher (NO footnotes)
    - Verify translation quality (not empty, reasonable length)
    - Generate manifest with metadata tracking
    - Log all operations with structured JSON
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.translator = BookTranslator(
            model=config.get("model", "gpt-4.1-nano"),
            temperature=config.get("temperature", 0.3)
        )
        self.rule_engine = BusinessRuleEngine()
        self._register_rules()

    def _register_rules(self):
        """Register business rules for metadata translation"""
        # Must have Chinese title
        # Translated title must not be empty
        # Translated title must be different from Chinese
        # etc.
        pass

    def execute(self, stage_input: StageInput) -> StageOutput:
        """
        Execute metadata translation with full tracking.

        Workflow:
        1. Validate input (has meta.title_chinese, etc.)
        2. Translate metadata fields (title, author, publisher)
        3. Validate output (translations not empty, quality checks)
        4. Generate manifest
        5. Return StageOutput
        """
        start_time = datetime.now()

        # 1. Input validation
        validation = self.validate_input(stage_input.data)
        if not validation.is_valid:
            return StageOutput(
                success=False,
                data=stage_input.data,
                manifest={},
                metrics={},
                error_details={"validation_errors": validation.errors}
            )

        # 2. Execute translation
        try:
            translated_data = self._translate_metadata(stage_input.data)
        except Exception as e:
            return self._handle_error(e, stage_input, start_time)

        # 3. Validate output
        output_validation = self.validate_output(translated_data)

        # 4. Generate manifest
        end_time = datetime.now()
        manifest = self._generate_manifest(
            stage_input, translated_data, start_time, end_time
        )

        # 5. Return result
        return StageOutput(
            success=output_validation.is_valid,
            data=translated_data,
            manifest=manifest.dict(),
            metrics=self._calculate_metrics(translated_data),
            validation_report=output_validation.dict() if output_validation else None
        )

    def _translate_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Actual translation logic"""
        meta = data.get("meta", {})

        # Translate title (if not already translated)
        if not meta.get("title_english") and meta.get("title_chinese"):
            meta["title_english"] = self.translator.translate_text(
                meta["title_chinese"],
                context="book title",
                add_footnotes=False
            )

        # Translate author
        if not meta.get("author_english") and meta.get("author_chinese"):
            meta["author_english"] = self.translator.translate_text(
                meta["author_chinese"],
                context="author name",
                add_footnotes=False
            )

        # Translate publisher
        if not meta.get("publisher_english") and meta.get("publisher_chinese"):
            meta["publisher_english"] = self.translator.translate_text(
                meta["publisher_chinese"],
                context="publisher name",
                add_footnotes=False
            )

        data["meta"] = meta
        return data

    def validate_input(self, data: Dict[str, Any]) -> ValidationReport:
        """Validate input has required fields"""
        errors = []

        if "meta" not in data:
            errors.append("Missing 'meta' field")
        else:
            meta = data["meta"]
            if not meta.get("title_chinese"):
                errors.append("Missing title_chinese in meta")

        return ValidationReport(
            is_valid=len(errors) == 0,
            confidence_score=100.0 if len(errors) == 0 else 0.0,
            schema_valid=len(errors) == 0,
            business_rules_passed=True,
            data_quality_score=100.0,
            checks_passed=[],
            checks_failed=[{"check": e} for e in errors],
            warnings=[],
            errors=errors,
            suggested_fixes=[]
        )

    def validate_output(self, data: Dict[str, Any]) -> ValidationReport:
        """Validate translation quality"""
        warnings = []
        errors = []

        meta = data.get("meta", {})

        # Check English fields populated
        if not meta.get("title_english"):
            errors.append("title_english not populated")

        # Check not same as Chinese (bad translation)
        if meta.get("title_english") == meta.get("title_chinese"):
            warnings.append("English title same as Chinese (possible translation failure)")

        # Check reasonable length
        if meta.get("title_english") and len(meta["title_english"]) > 200:
            warnings.append("Title suspiciously long (>200 chars)")

        return ValidationReport(
            is_valid=len(errors) == 0,
            confidence_score=95.0 if len(errors) == 0 else 50.0,
            schema_valid=True,
            business_rules_passed=len(errors) == 0,
            data_quality_score=100.0 - (len(warnings) * 10),
            checks_passed=["title_populated", "author_populated"],
            checks_failed=[{"check": e} for e in errors],
            warnings=warnings,
            errors=errors,
            suggested_fixes=[]
        )

    def _generate_manifest(
        self,
        stage_input: StageInput,
        output_data: Dict[str, Any],
        start_time: datetime,
        end_time: datetime
    ) -> Manifest:
        """Generate comprehensive manifest"""
        return Manifest(
            stage_name="metadata_translation",
            work_id=stage_input.work_id,
            volume=stage_input.volume,

            input_file=None,
            input_hash=self._hash_data(stage_input.data),
            input_metadata=stage_input.data.get("meta", {}),

            output_file=None,
            output_hash=self._hash_data(output_data),
            output_metadata=output_data.get("meta", {}),

            start_time=start_time,
            end_time=end_time,
            duration_seconds=(end_time - start_time).total_seconds(),

            items_processed=3,  # title, author, publisher
            success_count=3,
            error_count=0,
            quality_score=95.0,

            validation_passed=True,
            validation_details={},

            dependencies=[],
            checkpoints=[]
        )

    def _hash_data(self, data: Dict[str, Any]) -> str:
        """Generate hash of data for tracking"""
        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()[:16]

    def _calculate_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate stage-specific metrics"""
        meta = data.get("meta", {})
        return {
            "fields_translated": sum([
                1 for field in ["title_english", "author_english", "publisher_english"]
                if meta.get(field)
            ]),
            "chinese_char_count": sum([
                len(meta.get(field, ""))
                for field in ["title_chinese", "author_chinese", "publisher_chinese"]
            ]),
            "english_char_count": sum([
                len(meta.get(field, ""))
                for field in ["title_english", "author_english", "publisher_english"]
            ])
        }
```

### 6. Implement Manifest Management

Create a **manifest tracker** for the entire workflow:

```python
# utils/manifest_manager.py

from typing import List, Dict, Any
from pathlib import Path
import json
from datetime import datetime

class ManifestManager:
    """
    Tracks manifests across all workflow stages.

    Responsibilities:
    - Collect manifests from each stage
    - Generate workflow-level summary
    - Identify data lineage (input → stage1 → stage2 → output)
    - Detect missing dependencies
    - Create audit trail
    """

    def __init__(self, workflow_id: str, output_dir: Path):
        self.workflow_id = workflow_id
        self.output_dir = Path(output_dir)
        self.stages: List[Manifest] = []

    def add_stage_manifest(self, manifest: Manifest):
        """Add manifest from completed stage"""
        self.stages.append(manifest)

    def generate_workflow_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive workflow manifest.

        Returns:
            {
                "workflow_id": "...",
                "work_id": "D1379",
                "total_stages": 7,
                "completed_stages": 7,
                "overall_duration": 123.45,
                "total_items_processed": 1234,
                "quality_score": 95.5,
                "data_lineage": [...],
                "stage_manifests": [...]
            }
        """
        pass

    def save_to_file(self, path: Path):
        """Save complete manifest to JSON file"""
        pass

    def validate_lineage(self) -> bool:
        """Verify data lineage is complete (no broken chains)"""
        pass
```

### 7. Create Logging Infrastructure

Implement **structured logging** for all wrappers:

```python
# utils/workflow_logger.py

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

class WorkflowLogger:
    """
    Structured logger for workflow stages.

    Logs to:
    1. JSON file (machine-readable, for analysis)
    2. Human-readable file (debugging)
    3. Console (real-time monitoring)
    """

    def __init__(self, stage_name: str, work_id: str, log_dir: Path):
        self.stage_name = stage_name
        self.work_id = work_id
        self.log_dir = Path(log_dir)

        # Setup dual logging
        self.json_logger = self._setup_json_logger()
        self.text_logger = self._setup_text_logger()

    def log_stage_start(self, input_data: Dict[str, Any]):
        """Log stage start with input summary"""
        self._log_json({
            "event": "stage_start",
            "stage": self.stage_name,
            "work_id": self.work_id,
            "timestamp": datetime.now().isoformat(),
            "input_summary": self._summarize_data(input_data)
        })

    def log_stage_complete(self, output_data: Dict[str, Any], metrics: Dict[str, Any]):
        """Log stage completion with metrics"""
        self._log_json({
            "event": "stage_complete",
            "stage": self.stage_name,
            "work_id": self.work_id,
            "timestamp": datetime.now().isoformat(),
            "output_summary": self._summarize_data(output_data),
            "metrics": metrics
        })

    def log_validation(self, validation_report: ValidationReport):
        """Log validation results"""
        self._log_json({
            "event": "validation",
            "stage": self.stage_name,
            "work_id": self.work_id,
            "timestamp": datetime.now().isoformat(),
            "validation": validation_report.dict()
        })

    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log error with full context"""
        self._log_json({
            "event": "error",
            "stage": self.stage_name,
            "work_id": self.work_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        })
```

## Implementation Strategy

### Phase 1: Design Contracts (2-3 hours)
1. Define Pydantic models for all contracts
2. Document input/output schemas for each stage
3. Define business rules for each stage
4. Create validation criteria

### Phase 2: Build Base Infrastructure (3-4 hours)
1. Implement `TranslationStageWrapper` base class
2. Create `BusinessRuleEngine`
3. Build `ManifestManager`
4. Implement `WorkflowLogger`

### Phase 3: Create Stage Wrappers (8-10 hours)
Build wrappers for each of the 7 stages:
1. Metadata Translation Wrapper
2. TOC Translation Wrapper
3. Headings Translation Wrapper
4. Body Translation Wrapper (with footnotes)
5. Special Sections Wrapper
6. Footnote Cleanup Wrapper
7. Final Validation Wrapper

Each wrapper should be fully tested standalone before integration.

### Phase 4: Integration Testing (2-3 hours)
1. Test each wrapper independently
2. Test wrapper chain (stage 1 → stage 2 → stage 3...)
3. Verify manifests are generated correctly
4. Validate logs are structured and complete

### Phase 5: Workflow Integration (2-3 hours)
1. Update `workflows/translation_flow.py` to call wrappers
2. Wire up manifest collection
3. Connect logging infrastructure
4. Test complete workflow with real data

## Example Usage

Once wrappers are built, the workflow tasks become simple:

```python
# In workflows/translation_flow.py

from wrappers.metadata_translation_wrapper import MetadataTranslationWrapper
from contracts.translation_contracts import StageInput, StageOutput

@task(name="Translate Metadata", retries=2)
def translate_metadata(
    data: Dict[str, Any],
    config: OrchestrationConfig,
    work_id: str
) -> Dict[str, Any]:
    """Translate metadata - now uses wrapper with full tracking"""

    # Create wrapper
    wrapper = MetadataTranslationWrapper(config.__dict__)

    # Create input
    stage_input = StageInput(
        work_id=work_id,
        volume=None,
        data=data
    )

    # Execute with full tracking
    result: StageOutput = wrapper.execute(stage_input)

    # Check success
    if not result.success:
        raise ValueError(f"Metadata translation failed: {result.error_details}")

    # Store manifest (will be collected by ManifestManager)
    create_json_artifact(
        key=f"manifest-metadata-{work_id}",
        data=result.manifest
    )

    # Return translated data
    return result.data
```

## Success Criteria

A wrapper is considered complete when it:

1. ✅ Validates input against schema and business rules
2. ✅ Executes underlying utility correctly
3. ✅ Validates output quality
4. ✅ Generates comprehensive manifest
5. ✅ Logs all operations with structured JSON
6. ✅ Handles errors gracefully with context
7. ✅ Returns standardized `StageOutput`
8. ✅ Can run standalone (outside workflow)
9. ✅ Has unit tests with >80% coverage
10. ✅ Documents all business rules

## Agent Behavior

When invoked, this agent should:

1. **Analyze existing utilities** in the codebase
2. **Ask clarifying questions** about business rules and success criteria
3. **Design contracts** (Pydantic models) for each stage
4. **Propose business rules** for validation
5. **Implement wrappers** one at a time, testing each
6. **Generate documentation** for each wrapper
7. **Create integration guide** for connecting to workflow

The agent should work incrementally, building one wrapper at a time and testing it before moving to the next.

## Tools and Libraries

- **Pydantic**: Data validation and contracts
- **jsonschema**: JSON schema validation
- **hashlib**: Data fingerprinting for manifests
- **logging**: Structured logging
- **pathlib**: File management
- **json**: Manifest serialization

## Output Structure

```
wrappers/
├── __init__.py
├── base_wrapper.py                    # TranslationStageWrapper base class
├── metadata_translation_wrapper.py
├── toc_translation_wrapper.py
├── headings_translation_wrapper.py
├── body_translation_wrapper.py
├── special_sections_wrapper.py
├── footnote_cleanup_wrapper.py
└── final_validation_wrapper.py

contracts/
├── __init__.py
└── translation_contracts.py           # All Pydantic models

utils/
├── business_rules.py                  # BusinessRuleEngine
├── manifest_manager.py                # ManifestManager
└── workflow_logger.py                 # WorkflowLogger

tests/
└── wrappers/
    ├── test_metadata_wrapper.py
    ├── test_toc_wrapper.py
    └── ...
```

## Notes

- Wrappers should be **thin** - delegate actual work to existing utilities
- Focus on **contracts and validation** - not reimplementing business logic
- Make wrappers **testable standalone** - don't require full workflow
- Use **dependency injection** for utilities (easier to mock in tests)
- Generate **comprehensive manifests** - the audit trail is critical
- Keep **business rules declarative** - easy to modify without code changes