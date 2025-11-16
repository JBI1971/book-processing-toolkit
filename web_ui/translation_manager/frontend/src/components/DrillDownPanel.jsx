import React, { useState, useEffect } from 'react';

/**
 * DrillDownPanel Component
 *
 * Displays detailed information for a selected workflow stage:
 * - Stage metrics and timing
 * - Validation reports (for quality gates)
 * - Error details (for failed stages)
 * - Artifacts (logs, reports)
 */
const DrillDownPanel = ({ stage, flowRunId, onClose }) => {
  const [artifacts, setArtifacts] = useState([]);
  const [loadingArtifacts, setLoadingArtifacts] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const {
    stage_name,
    stage_number,
    status,
    start_time,
    end_time,
    duration_seconds,
    items_processed,
    success_count,
    error_count,
    progress_pct,
    validation_status
  } = stage;

  // Fetch artifacts for this stage
  useEffect(() => {
    const fetchArtifacts = async () => {
      setLoadingArtifacts(true);
      try {
        const response = await fetch(`http://localhost:8000/api/workflow/artifacts/${flowRunId}`);
        if (response.ok) {
          const data = await response.json();
          // Filter artifacts for this stage
          const stageArtifacts = data.filter(artifact =>
            artifact.key && artifact.key.includes(stage_name)
          );
          setArtifacts(stageArtifacts);
        }
      } catch (err) {
        console.error('Error fetching artifacts:', err);
      } finally {
        setLoadingArtifacts(false);
      }
    };

    if (flowRunId) {
      fetchArtifacts();
    }
  }, [flowRunId, stage_name]);

  // Format timestamp
  const formatTime = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    if (mins > 0) return `${mins}m ${secs}s`;
    if (secs > 0) return `${secs}.${ms.toString().padStart(3, '0')}s`;
    return `${ms}ms`;
  };

  // Format stage name
  const formatStageName = (name) => {
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="drill-down-panel">
      <div className="panel-overlay" onClick={onClose}></div>

      <div className="panel-content">
        {/* Header */}
        <div className="panel-header">
          <h3>
            Stage {stage_number}: {formatStageName(stage_name)}
          </h3>
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="panel-tabs">
          <button
            className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={`tab ${activeTab === 'validation' ? 'active' : ''}`}
            onClick={() => setActiveTab('validation')}
            disabled={!validation_status && artifacts.length === 0}
          >
            Validation {artifacts.length > 0 && `(${artifacts.length})`}
          </button>
          <button
            className={`tab ${activeTab === 'errors' ? 'active' : ''}`}
            onClick={() => setActiveTab('errors')}
            disabled={error_count === 0}
          >
            Errors {error_count > 0 && `(${error_count})`}
          </button>
        </div>

        {/* Tab Content */}
        <div className="panel-body">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="overview-tab">
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">Status:</span>
                  <span className={`info-value status-${status}`}>
                    {status.toUpperCase()}
                  </span>
                </div>

                <div className="info-item">
                  <span className="info-label">Start Time:</span>
                  <span className="info-value">{formatTime(start_time)}</span>
                </div>

                <div className="info-item">
                  <span className="info-label">End Time:</span>
                  <span className="info-value">{formatTime(end_time)}</span>
                </div>

                <div className="info-item">
                  <span className="info-label">Duration:</span>
                  <span className="info-value">{formatDuration(duration_seconds)}</span>
                </div>

                <div className="info-item">
                  <span className="info-label">Items Processed:</span>
                  <span className="info-value">{items_processed}</span>
                </div>

                <div className="info-item">
                  <span className="info-label">Success Count:</span>
                  <span className="info-value success">{success_count}</span>
                </div>

                <div className="info-item">
                  <span className="info-label">Error Count:</span>
                  <span className="info-value error">{error_count}</span>
                </div>

                <div className="info-item">
                  <span className="info-label">Progress:</span>
                  <span className="info-value">{progress_pct.toFixed(1)}%</span>
                </div>
              </div>

              {validation_status && (
                <div className={`validation-summary validation-${validation_status}`}>
                  <h4>Validation Status</h4>
                  <p>
                    {validation_status === 'passed'
                      ? '✓ Quality gate passed - no issues detected'
                      : '✗ Quality gate failed - check validation tab for details'}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Validation Tab */}
          {activeTab === 'validation' && (
            <div className="validation-tab">
              {loadingArtifacts ? (
                <div className="loading">Loading validation reports...</div>
              ) : artifacts.length > 0 ? (
                <div className="artifacts-list">
                  {artifacts.map((artifact, index) => (
                    <div key={index} className="artifact-item">
                      <h4>{artifact.description || artifact.key}</h4>
                      <div className="artifact-meta">
                        <span>Type: {artifact.type}</span>
                        <span>Created: {formatTime(artifact.created)}</span>
                      </div>
                      {artifact.type === 'markdown' && artifact.data && (
                        <div
                          className="artifact-content markdown"
                          dangerouslySetInnerHTML={{ __html: artifact.data }}
                        />
                      )}
                      {artifact.type === 'json' && artifact.data && (
                        <pre className="artifact-content json">
                          {JSON.stringify(artifact.data, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <p>No validation reports available for this stage</p>
                </div>
              )}
            </div>
          )}

          {/* Errors Tab */}
          {activeTab === 'errors' && (
            <div className="errors-tab">
              {error_count > 0 ? (
                <div className="errors-list">
                  <div className="error-summary">
                    <p>
                      {error_count} error{error_count !== 1 ? 's' : ''} occurred during this stage
                    </p>
                  </div>
                  {/* TODO: Display actual error details from task runs */}
                  <div className="error-placeholder">
                    <p>Error details will be populated from task run logs</p>
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <p>No errors occurred in this stage</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DrillDownPanel;
