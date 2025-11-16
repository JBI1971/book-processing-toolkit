#!/usr/bin/env python3
"""
Workflow Node Standards - Pydantic Schemas

Defines standard contracts for all workflow nodes per WORKFLOW_NODE_STANDARDS.md
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMERATIONS
# =============================================================================

class Severity(str, Enum):
    """Business rule severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Complexity(str, Enum):
    """Node complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class ParallelizationStrategy(str, Enum):
    """Parallelization strategies"""
    NONE = "none"
    FAN_OUT = "fan_out"
    PIPELINE = "pipeline"


class CheckpointGranularity(str, Enum):
    """Checkpoint granularity levels"""
    NONE = "none"
    STAGE = "stage"
    ITEM = "item"


# =============================================================================
# BUSINESS RULES
# =============================================================================

class BusinessRule(BaseModel):
    """
    Declarative business rule definition.

    Business rules are evaluated by BusinessRuleEngine to validate
    data quality and enforce business logic.
    """

    rule_id: str = Field(..., description="Unique identifier (snake_case)")
    severity: Severity = Field(..., description="Error, warning, or info")
    description: str = Field(..., description="Human-readable description")
    check: str = Field(..., description="Python expression to evaluate")
    auto_fix: bool = Field(False, description="Can this be auto-fixed?")
    fix_function: Optional[str] = Field(None, description="Function reference for auto-fix")

    @validator("rule_id")
    def validate_rule_id(cls, v):
        """Ensure rule_id is snake_case"""
        if not v.replace("_", "").isalnum():
            raise ValueError(f"rule_id must be snake_case: {v}")
        return v


class RuleEvaluationResult(BaseModel):
    """Result from evaluating business rules"""

    passed_rules: List[str] = Field(default_factory=list)
    failed_rules: List[Dict[str, Any]] = Field(default_factory=list)

    severity_counts: Dict[str, int] = Field(
        default_factory=lambda: {"error": 0, "warning": 0, "info": 0}
    )

    can_auto_fix: bool = Field(False)
    suggested_fixes: List[str] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any error-level rules failed"""
        return self.severity_counts.get("error", 0) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warning-level rules failed"""
        return self.severity_counts.get("warning", 0) > 0


# =============================================================================
# VALIDATION REPORTS
# =============================================================================

class ValidationReport(BaseModel):
    """
    Standard validation report format.

    All nodes that perform validation must return this format.
    """

    # Overall result
    is_valid: bool = Field(..., description="Whether validation passed")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Confidence in validation (0-100)")

    # Validation types
    schema_valid: bool = Field(..., description="Schema validation passed")
    business_rules_passed: bool = Field(..., description="All business rules passed")
    data_quality_score: float = Field(..., ge=0.0, le=100.0, description="Data quality score (0-100)")

    # Details
    checks_passed: List[str] = Field(default_factory=list, description="List of passed checks")
    checks_failed: List[Dict[str, Any]] = Field(default_factory=list, description="List of failed checks with details")

    # Issues
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    info: List[str] = Field(default_factory=list, description="Informational messages")

    # Recommendations
    suggested_fixes: List[str] = Field(default_factory=list, description="Suggested fixes for issues")
    auto_fixable: bool = Field(False, description="Can issues be auto-fixed?")

    # Metadata
    validator_version: str = Field(..., description="Version of validator")
    validation_timestamp: datetime = Field(default_factory=datetime.now)
    validation_duration_seconds: float = Field(..., ge=0.0)


# =============================================================================
# STAGE CONTRACTS
# =============================================================================

class StageInput(BaseModel):
    """
    Standard input contract for all workflow nodes.

    All nodes receive this structure from the workflow engine.
    """

    work_id: str = Field(..., description="Work identifier (e.g., D1379)")
    volume: Optional[str] = Field(None, description="Volume identifier (e.g., 'a', 'b')")
    data: Dict[str, Any] = Field(..., description="Input data (book JSON structure)")

    # Optional fields
    checkpoint_path: Optional[str] = Field(None, description="Path to checkpoint file for resume")
    previous_stage_manifest: Optional[Dict[str, Any]] = Field(None, description="Manifest from previous stage")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node-specific configuration")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context (e.g., trace_id)")

    class Config:
        # Allow extra fields for extensibility
        extra = "allow"


class StageOutput(BaseModel):
    """
    Standard output contract for all workflow nodes.

    All nodes must return this structure to the workflow engine.
    """

    success: bool = Field(..., description="Whether stage completed successfully")
    data: Dict[str, Any] = Field(..., description="Output data (modified book JSON)")
    manifest: Dict[str, Any] = Field(..., description="Execution manifest (see ExecutionManifest)")
    metrics: Dict[str, Any] = Field(..., description="Stage-specific metrics")

    # Optional fields
    validation_report: Optional[Dict[str, Any]] = Field(None, description="Validation results (if applicable)")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Error context if failed")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated artifacts")

    class Config:
        extra = "allow"


# =============================================================================
# EXECUTION MANIFEST
# =============================================================================

class ExecutionManifest(BaseModel):
    """
    Manifest tracking stage execution.

    Generated by each node to provide audit trail and lineage tracking.
    """

    # Identity
    stage_name: str = Field(..., description="Stage identifier")
    stage_version: str = Field(..., description="Stage version (semver)")
    work_id: str = Field(..., description="Work being processed")
    volume: Optional[str] = Field(None, description="Volume identifier")

    # Inputs
    input_hash: str = Field(..., description="SHA256 hash of input data (first 16 chars)")
    input_metadata: Dict[str, Any] = Field(default_factory=dict, description="Input summary")

    # Outputs
    output_hash: str = Field(..., description="SHA256 hash of output data (first 16 chars)")
    output_metadata: Dict[str, Any] = Field(default_factory=dict, description="Output summary")

    # Timing
    start_time: datetime = Field(..., description="Stage start timestamp")
    end_time: datetime = Field(..., description="Stage end timestamp")
    duration_seconds: float = Field(..., ge=0.0, description="Execution duration")

    # Quality
    items_processed: int = Field(0, ge=0, description="Number of items processed")
    success_count: int = Field(0, ge=0, description="Number of successful items")
    error_count: int = Field(0, ge=0, description="Number of failed items")
    warning_count: int = Field(0, ge=0, description="Number of warnings")
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall quality score")

    # Validation
    validation_passed: bool = Field(..., description="Validation passed")
    validation_details: Dict[str, Any] = Field(default_factory=dict)
    business_rules_evaluated: int = Field(0, ge=0)
    business_rules_passed: int = Field(0, ge=0)
    business_rules_failed: int = Field(0, ge=0)

    # Dependencies
    dependencies_used: List[str] = Field(default_factory=list, description="APIs, files used")
    checkpoints_created: List[str] = Field(default_factory=list, description="Checkpoint file paths")
    artifacts_generated: List[str] = Field(default_factory=list, description="Artifact file paths")

    # Lineage
    previous_stage: Optional[str] = Field(None, description="Previous stage in pipeline")
    next_stage: Optional[str] = Field(None, description="Next stage in pipeline")


# =============================================================================
# NODE MANIFEST
# =============================================================================

class NodeInputSchema(BaseModel):
    """Input schema definition for node manifest"""

    schema: str = Field(..., description="Schema reference (e.g., 'StageInput')")
    required_fields: List[str] = Field(..., description="Required fields in data")
    optional_fields: List[str] = Field(default_factory=list, description="Optional fields")


class NodeOutputSchema(BaseModel):
    """Output schema definition for node manifest"""

    schema: str = Field(..., description="Schema reference (e.g., 'StageOutput')")
    guarantees: List[str] = Field(..., description="Guaranteed output fields/conditions")


class NodeDependencies(BaseModel):
    """External dependencies required by node"""

    apis: List[str] = Field(default_factory=list, description="External APIs (e.g., 'OpenAI GPT-4.1-nano')")
    files: List[str] = Field(default_factory=list, description="Required files (e.g., 'wuxia_glossary.json')")
    environment: List[str] = Field(default_factory=list, description="Environment variables (e.g., 'OPENAI_API_KEY')")


class ParallelizationConfig(BaseModel):
    """Parallelization configuration for complex nodes"""

    strategy: ParallelizationStrategy = Field(ParallelizationStrategy.NONE)
    max_workers: Optional[int] = Field(None, ge=1, description="Maximum parallel workers")
    partition_by: Optional[str] = Field(None, description="How to partition work (e.g., 'chapter')")


class CheckpointConfig(BaseModel):
    """Checkpoint/resume configuration"""

    enabled: bool = Field(False)
    granularity: CheckpointGranularity = Field(CheckpointGranularity.NONE)
    storage_path: Optional[str] = Field(None, description="Path template for checkpoints")


class NodeMetrics(BaseModel):
    """Metrics reported by node"""

    counters: List[str] = Field(default_factory=list, description="Counter metric names")
    timers: List[str] = Field(default_factory=list, description="Timer metric names")
    gauges: List[str] = Field(default_factory=list, description="Gauge metric names")


class NodeManifest(BaseModel):
    """
    Complete node manifest.

    Every workflow node MUST provide a manifest file describing
    its capabilities, requirements, and configuration.
    """

    # Identity
    node_id: str = Field(..., description="Unique node identifier (snake_case)")
    node_name: str = Field(..., description="Human-readable name")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    complexity: Complexity = Field(..., description="Node complexity level")
    description: str = Field(..., description="Detailed description")

    # Contracts
    inputs: NodeInputSchema = Field(..., description="Input schema definition")
    outputs: NodeOutputSchema = Field(..., description="Output schema definition")

    # Business Logic
    business_rules: List[Dict[str, Any]] = Field(..., description="Business rules (BusinessRule schema)")

    # Dependencies
    dependencies: NodeDependencies = Field(default_factory=NodeDependencies)

    # Advanced Features
    parallelization: ParallelizationConfig = Field(default_factory=ParallelizationConfig)
    checkpointing: CheckpointConfig = Field(default_factory=CheckpointConfig)
    metrics: NodeMetrics = Field(default_factory=NodeMetrics)

    @validator("node_id")
    def validate_node_id(cls, v):
        """Ensure node_id is snake_case"""
        if not v.replace("_", "").islower():
            raise ValueError(f"node_id must be lowercase snake_case: {v}")
        return v

    @validator("version")
    def validate_version(cls, v):
        """Ensure version is semver format"""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(f"version must be semver (X.Y.Z): {v}")
        if not all(p.isdigit() for p in parts):
            raise ValueError(f"version parts must be numeric: {v}")
        return v


# =============================================================================
# LOGGING
# =============================================================================

class LogEntry(BaseModel):
    """Standard log entry format for structured logging"""

    timestamp: datetime = Field(default_factory=datetime.now)
    level: str = Field(..., description="DEBUG, INFO, WARNING, ERROR, CRITICAL")
    event: str = Field(..., description="Event type (e.g., 'stage_start')")

    # Context
    node_id: str = Field(..., description="Node generating the log")
    work_id: str = Field(..., description="Work being processed")
    volume: Optional[str] = Field(None)

    # Message
    message: str = Field(..., description="Human-readable message")

    # Additional data
    data: Optional[Dict[str, Any]] = Field(None, description="Structured event data")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Metrics data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")

    # Trace
    trace_id: Optional[str] = Field(None, description="Distributed trace ID")
    span_id: Optional[str] = Field(None, description="Span ID within trace")


# =============================================================================
# EXCEPTIONS
# =============================================================================

class WorkflowNodeError(Exception):
    """
    Base exception for all workflow node errors.

    All node exceptions should inherit from this to enable
    consistent error handling and reporting.
    """

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "recoverable": self.recoverable
        }


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
