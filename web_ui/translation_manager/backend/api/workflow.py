#!/usr/bin/env python3
"""
Workflow API Endpoints

Provides REST API for Prefect workflow orchestration:
- Start/stop/pause workflows
- Query workflow status and progress
- Server-Sent Events (SSE) for real-time updates
- Workflow artifact retrieval (validation reports, logs)

Integrates Prefect with the existing translation_manager UI.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from prefect import get_client
from prefect.client.schemas.filters import FlowRunFilter, FlowFilter
from prefect.client.schemas.sorting import FlowRunSort

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/workflow", tags=["workflow"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class WorkflowStartRequest(BaseModel):
    """Request to start a new workflow"""
    work_id: str = Field(..., description="Work identifier (e.g., D1379)")
    volume: Optional[str] = Field(None, description="Optional volume identifier")
    config: Dict[str, Any] = Field(default_factory=dict, description="Workflow configuration")
    resume: bool = Field(False, description="Resume from checkpoint if available")


class WorkflowStageStatus(BaseModel):
    """Status of a single workflow stage"""
    stage_name: str
    stage_number: int
    status: str  # pending, running, completed, failed, skipped
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    items_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    progress_pct: float = 0.0
    validation_status: Optional[str] = None  # For quality gates


class WorkflowStatus(BaseModel):
    """Complete workflow status"""
    flow_run_id: str
    work_id: str
    volume: Optional[str] = None
    status: str  # scheduled, pending, running, completed, failed, cancelled
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    overall_progress_pct: float = 0.0
    current_stage: Optional[str] = None
    stages: List[WorkflowStageStatus] = Field(default_factory=list)
    error_message: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)  # Validation reports, logs


class WorkflowListItem(BaseModel):
    """Summary for workflow list"""
    flow_run_id: str
    work_id: str
    volume: Optional[str] = None
    status: str
    start_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    overall_progress_pct: float = 0.0


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def get_flow_deployment_id(flow_name: str = "translation-pipeline") -> Optional[str]:
    """Get deployment ID for a flow by name."""
    try:
        async with get_client() as client:
            deployments = await client.read_deployments(
                flow_filter=FlowFilter(name={"any_": [flow_name]})
            )
            if deployments:
                return str(deployments[0].id)
            return None
    except Exception as e:
        logger.error(f"Error getting deployment: {e}")
        return None


async def extract_workflow_status(flow_run) -> WorkflowStatus:
    """Extract workflow status from Prefect flow run."""

    # Calculate progress from task runs
    overall_progress = 0.0
    stages = []
    current_stage = None

    # Get task runs for this flow
    async with get_client() as client:
        task_runs = await client.read_task_runs(
            flow_run_filter=FlowRunFilter(id={"any_": [flow_run.id]})
        )

        # Group task runs by stage
        stage_tasks = {}
        for task_run in task_runs:
            task_name = task_run.name
            stage_tasks.setdefault(task_name, []).append(task_run)

        # Calculate stage status
        total_stages = len(stage_tasks) if stage_tasks else 7  # Default 7 stages
        completed_stages = 0

        for stage_num, (stage_name, tasks) in enumerate(stage_tasks.items(), 1):
            # Aggregate task status
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.state and t.state.is_completed())
            failed_tasks = sum(1 for t in tasks if t.state and t.state.is_failed())
            running_tasks = sum(1 for t in tasks if t.state and t.state.is_running())

            if failed_tasks > 0:
                stage_status = "failed"
            elif running_tasks > 0:
                stage_status = "running"
                current_stage = stage_name
            elif completed_tasks == total_tasks:
                stage_status = "completed"
                completed_stages += 1
            else:
                stage_status = "pending"

            stage_progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Get timing info
            start_times = [t.start_time for t in tasks if t.start_time]
            end_times = [t.end_time for t in tasks if t.end_time]

            stage_start = min(start_times).isoformat() if start_times else None
            stage_end = max(end_times).isoformat() if end_times else None

            duration = None
            if start_times and end_times:
                duration = (max(end_times) - min(start_times)).total_seconds()

            stages.append(WorkflowStageStatus(
                stage_name=stage_name,
                stage_number=stage_num,
                status=stage_status,
                start_time=stage_start,
                end_time=stage_end,
                duration_seconds=duration,
                items_processed=total_tasks,
                success_count=completed_tasks,
                error_count=failed_tasks,
                progress_pct=stage_progress
            ))

        overall_progress = (completed_stages / total_stages * 100) if total_stages > 0 else 0

    # Extract work_id from parameters
    work_id = "unknown"
    volume = None
    if flow_run.parameters:
        work_id = flow_run.parameters.get("work_id", "unknown")
        volume = flow_run.parameters.get("volume")

    # Calculate duration
    duration = None
    if flow_run.start_time:
        end = flow_run.end_time or datetime.now()
        duration = (end - flow_run.start_time).total_seconds()

    return WorkflowStatus(
        flow_run_id=str(flow_run.id),
        work_id=work_id,
        volume=volume,
        status=flow_run.state.name.lower() if flow_run.state else "unknown",
        start_time=flow_run.start_time.isoformat() if flow_run.start_time else None,
        end_time=flow_run.end_time.isoformat() if flow_run.end_time else None,
        duration_seconds=duration,
        overall_progress_pct=overall_progress,
        current_stage=current_stage,
        stages=stages,
        error_message=flow_run.state.message if flow_run.state and flow_run.state.is_failed() else None
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/start", response_model=WorkflowStatus)
async def start_workflow(request: WorkflowStartRequest):
    """
    Start a new translation workflow.

    Returns:
        Initial workflow status with flow_run_id for tracking
    """
    try:
        # Import workflow (avoid circular import at module level)
        from workflows.translation_flow import translation_workflow
        from scripts.orchestrate_translation_pipeline import OrchestrationConfig

        # Create config
        config = OrchestrationConfig(**request.config) if request.config else OrchestrationConfig()

        # Start workflow using Prefect's run_deployment or direct flow execution
        # Since we don't have a deployment, we'll use a background task
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        # Run the flow in the background using a thread pool
        executor = ThreadPoolExecutor(max_workers=1)

        def run_workflow_sync():
            """Run workflow synchronously - Prefect will track it"""
            try:
                result = translation_workflow(
                    work_id=request.work_id,
                    volume=request.volume,
                    config=config,
                    resume=request.resume
                )
                logger.info(f"Workflow completed for {request.work_id}")
                return result
            except Exception as e:
                logger.error(f"Workflow error for {request.work_id}: {e}", exc_info=True)
                raise

        # Submit to executor (non-blocking)
        future = executor.submit(run_workflow_sync)

        # Wait briefly to get the flow run ID
        await asyncio.sleep(0.5)

        # Get the most recent flow run for this work_id
        async with get_client() as client:
            # Query recent flow runs
            flow_runs = await client.read_flow_runs(
                flow_filter=FlowFilter(name={"any_": ["Translation Pipeline"]}),
                sort=FlowRunSort.START_TIME_DESC,
                limit=1
            )

            if not flow_runs:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to start workflow - no flow run created"
                )

            flow_run = flow_runs[0]
            logger.info(f"Started workflow {flow_run.id} for work {request.work_id}")

            # Return initial status
            return await extract_workflow_status(flow_run)

    except Exception as e:
        logger.error(f"Error starting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{flow_run_id}", response_model=WorkflowStatus)
async def get_workflow_status(flow_run_id: str):
    """
    Get current status of a workflow.

    Args:
        flow_run_id: Flow run identifier

    Returns:
        Complete workflow status with stage details
    """
    try:
        async with get_client() as client:
            flow_run = await client.read_flow_run(flow_run_id)
            return await extract_workflow_status(flow_run)

    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=404, detail=f"Workflow {flow_run_id} not found")


@router.get("/list", response_model=List[WorkflowListItem])
async def list_workflows(limit: int = 50, status: Optional[str] = None):
    """
    List recent workflows.

    Args:
        limit: Maximum number of workflows to return
        status: Filter by status (running, completed, failed, etc.)

    Returns:
        List of workflow summaries
    """
    try:
        async with get_client() as client:
            # Build filter
            flow_run_filter = None
            if status:
                flow_run_filter = FlowRunFilter(
                    state={"type": {"any_": [status.upper()]}}
                )

            # Query flow runs
            flow_runs = await client.read_flow_runs(
                flow_run_filter=flow_run_filter,
                limit=limit,
                sort=FlowRunSort.START_TIME_DESC
            )

            # Convert to list items
            items = []
            for flow_run in flow_runs:
                work_id = flow_run.parameters.get("work_id", "unknown") if flow_run.parameters else "unknown"
                volume = flow_run.parameters.get("volume") if flow_run.parameters else None

                duration = None
                if flow_run.start_time:
                    end = flow_run.end_time or datetime.now()
                    duration = (end - flow_run.start_time).total_seconds()

                items.append(WorkflowListItem(
                    flow_run_id=str(flow_run.id),
                    work_id=work_id,
                    volume=volume,
                    status=flow_run.state.name.lower() if flow_run.state else "unknown",
                    start_time=flow_run.start_time.isoformat() if flow_run.start_time else None,
                    duration_seconds=duration,
                    overall_progress_pct=0.0  # TODO: Calculate from tasks
                ))

            return items

    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{flow_run_id}")
async def cancel_workflow(flow_run_id: str):
    """
    Cancel a running workflow.

    Args:
        flow_run_id: Flow run identifier

    Returns:
        Cancellation confirmation
    """
    try:
        async with get_client() as client:
            # Cancel the flow run
            await client.set_flow_run_state(
                flow_run_id=flow_run_id,
                state=Failed(message="Cancelled by user"),
                force=True
            )

            logger.info(f"Cancelled workflow {flow_run_id}")
            return {"status": "cancelled", "flow_run_id": flow_run_id}

    except Exception as e:
        logger.error(f"Error cancelling workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/{flow_run_id}")
async def stream_workflow_progress(flow_run_id: str):
    """
    Server-Sent Events (SSE) stream for real-time workflow progress.

    Args:
        flow_run_id: Flow run identifier

    Returns:
        SSE stream with periodic status updates
    """
    async def event_generator():
        """Generate SSE events with workflow status."""
        try:
            while True:
                # Get current status
                async with get_client() as client:
                    flow_run = await client.read_flow_run(flow_run_id)
                    status = await extract_workflow_status(flow_run)

                    # Send status as SSE event
                    data = json.dumps(status.dict())
                    yield f"data: {data}\n\n"

                    # Stop streaming if workflow is complete
                    if status.status in ["completed", "failed", "cancelled"]:
                        break

                # Wait before next update
                await asyncio.sleep(2)  # Update every 2 seconds

        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/artifacts/{flow_run_id}")
async def get_workflow_artifacts(flow_run_id: str):
    """
    Get workflow artifacts (validation reports, logs, etc.).

    Args:
        flow_run_id: Flow run identifier

    Returns:
        List of artifacts with download links
    """
    try:
        async with get_client() as client:
            # Get artifacts for this flow run
            artifacts = await client.read_artifacts(
                flow_run_filter=FlowRunFilter(id={"any_": [flow_run_id]})
            )

            return [
                {
                    "key": artifact.key,
                    "type": artifact.type,
                    "description": artifact.description,
                    "created": artifact.created.isoformat(),
                    "data": artifact.data
                }
                for artifact in artifacts
            ]

    except Exception as e:
        logger.error(f"Error getting artifacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
