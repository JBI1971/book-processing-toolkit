"""
Prefect Workflows for Book Processing

Provides production-grade workflow orchestration with:
- DAG-based dependency resolution
- Parallel execution
- Quality gates
- Real-time progress tracking
- Web UI integration
"""

from .translation_flow import translation_workflow

__all__ = ["translation_workflow"]

