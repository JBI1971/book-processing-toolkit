import React, { useState, useEffect, useCallback } from 'react';
import StageNode from './StageNode';
import DrillDownPanel from './DrillDownPanel';

/**
 * WorkflowProgress Component
 *
 * Displays real-time workflow progress with DAG visualization
 * Features:
 * - SSE connection for live updates
 * - Stage nodes with visual indicators (✓/✗/⏳/progress)
 * - Click to drill-down into logs/validation reports
 * - Overall progress tracking
 */
const WorkflowProgress = ({ flowRunId, onComplete }) => {
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [selectedStage, setSelectedStage] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch initial status
  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/workflow/status/${flowRunId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch workflow status: ${response.statusText}`);
      }
      const data = await response.json();
      setWorkflowStatus(data);
      setIsLoading(false);

      // Check if workflow is complete
      if (['completed', 'failed', 'cancelled'].includes(data.status) && onComplete) {
        onComplete(data);
      }
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  }, [flowRunId, onComplete]);

  // Set up SSE connection for real-time updates
  useEffect(() => {
    // Initial fetch
    fetchStatus();

    // Set up Server-Sent Events (SSE) stream
    const eventSource = new EventSource(`http://localhost:8000/api/workflow/stream/${flowRunId}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle error in stream
        if (data.error) {
          setError(data.error);
          return;
        }

        setWorkflowStatus(data);

        // Check if workflow is complete
        if (['completed', 'failed', 'cancelled'].includes(data.status) && onComplete) {
          onComplete(data);
        }
      } catch (err) {
        console.error('Error parsing SSE data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      eventSource.close();
      // Fall back to polling
      const pollInterval = setInterval(fetchStatus, 3000);
      return () => clearInterval(pollInterval);
    };

    // Cleanup on unmount
    return () => {
      eventSource.close();
    };
  }, [flowRunId, fetchStatus, onComplete]);

  // Handle stage click for drill-down
  const handleStageClick = (stage) => {
    setSelectedStage(stage);
  };

  // Close drill-down panel
  const handleCloseDrillDown = () => {
    setSelectedStage(null);
  };

  if (isLoading) {
    return (
      <div className="workflow-progress loading">
        <div className="loading-spinner"></div>
        <p>Loading workflow...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="workflow-progress error">
        <div className="error-icon">✗</div>
        <h3>Error Loading Workflow</h3>
        <p>{error}</p>
        <button onClick={fetchStatus}>Retry</button>
      </div>
    );
  }

  if (!workflowStatus) {
    return (
      <div className="workflow-progress empty">
        <p>No workflow data available</p>
      </div>
    );
  }

  const { work_id, volume, status, overall_progress_pct, current_stage, stages, duration_seconds } = workflowStatus;

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  // Get status icon and color
  const getStatusDisplay = (status) => {
    const displays = {
      pending: { icon: '⊙', color: '#999', text: 'Pending' },
      scheduled: { icon: '⊙', color: '#999', text: 'Scheduled' },
      running: { icon: '●', color: '#2196F3', text: 'Running' },
      completed: { icon: '✓', color: '#4CAF50', text: 'Completed' },
      failed: { icon: '✗', color: '#f44336', text: 'Failed' },
      cancelled: { icon: '⊘', color: '#FF9800', text: 'Cancelled' },
    };
    return displays[status] || displays.pending;
  };

  const statusDisplay = getStatusDisplay(status);

  return (
    <div className="workflow-progress">
      {/* Header */}
      <div className="workflow-header">
        <div className="workflow-title">
          <h2>
            <span className="status-icon" style={{ color: statusDisplay.color }}>
              {statusDisplay.icon}
            </span>
            Translation Workflow: {work_id}
            {volume && ` (Vol. ${volume})`}
          </h2>
          <span className={`status-badge status-${status}`}>
            {statusDisplay.text}
          </span>
        </div>

        <div className="workflow-meta">
          <div className="meta-item">
            <span className="meta-label">Progress:</span>
            <span className="meta-value">{overall_progress_pct.toFixed(1)}%</span>
          </div>
          {current_stage && (
            <div className="meta-item">
              <span className="meta-label">Current Stage:</span>
              <span className="meta-value">{current_stage}</span>
            </div>
          )}
          <div className="meta-item">
            <span className="meta-label">Duration:</span>
            <span className="meta-value">{formatDuration(duration_seconds)}</span>
          </div>
        </div>
      </div>

      {/* Overall Progress Bar */}
      <div className="overall-progress">
        <div className="progress-bar-container">
          <div
            className="progress-bar-fill"
            style={{
              width: `${overall_progress_pct}%`,
              backgroundColor: statusDisplay.color
            }}
          />
        </div>
        <span className="progress-label">{overall_progress_pct.toFixed(1)}%</span>
      </div>

      {/* Stage Nodes (DAG-style) */}
      <div className="workflow-stages">
        <div className="stages-container">
          {stages && stages.length > 0 ? (
            stages.map((stage, index) => (
              <React.Fragment key={stage.stage_name}>
                <StageNode
                  stage={stage}
                  onClick={() => handleStageClick(stage)}
                  isSelected={selectedStage?.stage_name === stage.stage_name}
                />
                {/* Arrow connector between stages */}
                {index < stages.length - 1 && (
                  <div className="stage-connector">→</div>
                )}
              </React.Fragment>
            ))
          ) : (
            <div className="no-stages">
              <p>No stages available yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Drill-down Panel */}
      {selectedStage && (
        <DrillDownPanel
          stage={selectedStage}
          flowRunId={flowRunId}
          onClose={handleCloseDrillDown}
        />
      )}
    </div>
  );
};

export default WorkflowProgress;
