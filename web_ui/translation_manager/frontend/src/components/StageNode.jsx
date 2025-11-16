import React from 'react';

/**
 * StageNode Component
 *
 * Displays a single workflow stage with visual status indicators
 * States: pending (⊙), running (● + progress), completed (✓), failed (✗)
 */
const StageNode = ({ stage, onClick, isSelected }) => {
  const {
    stage_name,
    stage_number,
    status,
    progress_pct,
    duration_seconds,
    success_count,
    error_count,
    validation_status
  } = stage;

  // Get status display properties
  const getStatusDisplay = () => {
    switch (status) {
      case 'pending':
        return {
          icon: '⊙',
          color: '#999',
          bgColor: '#f5f5f5',
          borderColor: '#ddd'
        };
      case 'running':
        return {
          icon: '●',
          color: '#2196F3',
          bgColor: '#E3F2FD',
          borderColor: '#2196F3'
        };
      case 'completed':
        return {
          icon: '✓',
          color: '#4CAF50',
          bgColor: '#E8F5E9',
          borderColor: '#4CAF50'
        };
      case 'failed':
        return {
          icon: '✗',
          color: '#f44336',
          bgColor: '#FFEBEE',
          borderColor: '#f44336'
        };
      case 'skipped':
        return {
          icon: '⊘',
          color: '#FF9800',
          bgColor: '#FFF3E0',
          borderColor: '#FF9800'
        };
      default:
        return {
          icon: '?',
          color: '#999',
          bgColor: '#f5f5f5',
          borderColor: '#ddd'
        };
    }
  };

  const statusDisplay = getStatusDisplay();

  // Format stage name for display
  const formatStageName = (name) => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  return (
    <div
      className={`stage-node ${isSelected ? 'selected' : ''} status-${status}`}
      onClick={onClick}
      style={{
        backgroundColor: statusDisplay.bgColor,
        borderColor: statusDisplay.borderColor,
        cursor: 'pointer'
      }}
    >
      {/* Stage Number Badge */}
      <div className="stage-number" style={{ backgroundColor: statusDisplay.color }}>
        {stage_number}
      </div>

      {/* Status Icon */}
      <div className="stage-icon" style={{ color: statusDisplay.color }}>
        {statusDisplay.icon}
      </div>

      {/* Stage Name */}
      <div className="stage-name">
        {formatStageName(stage_name)}
      </div>

      {/* Progress Bar (for running stages) */}
      {status === 'running' && (
        <div className="stage-progress">
          <div className="progress-bar-mini">
            <div
              className="progress-fill-mini"
              style={{
                width: `${progress_pct}%`,
                backgroundColor: statusDisplay.color
              }}
            />
          </div>
          <span className="progress-text">{progress_pct.toFixed(0)}%</span>
        </div>
      )}

      {/* Metrics (for completed stages) */}
      {status === 'completed' && (
        <div className="stage-metrics">
          {duration_seconds && (
            <span className="metric-item">
              ⏱ {formatDuration(duration_seconds)}
            </span>
          )}
          {success_count > 0 && (
            <span className="metric-item">
              ✓ {success_count}
            </span>
          )}
        </div>
      )}

      {/* Error Indicator (for failed stages) */}
      {status === 'failed' && error_count > 0 && (
        <div className="stage-errors">
          <span className="error-badge">
            {error_count} error{error_count !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Validation Status (for quality gates) */}
      {validation_status && (
        <div className={`validation-badge validation-${validation_status}`}>
          {validation_status === 'passed' ? '✓ Validated' : '✗ Failed'}
        </div>
      )}
    </div>
  );
};

export default StageNode;
