import { useState, useEffect } from 'react';
import { analysisAPI } from '../api/client';
import PropTypes from 'prop-types';
import './AnalysisPanel.css';

function AnalysisPanel({ workId }) {
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (!workId) return;

    // Start analysis
    startAnalysis();
  }, [workId]);

  const startAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);

      // Start the analysis
      await analysisAPI.startAnalysis(workId);

      // Poll for status
      pollStatus();
    } catch (err) {
      console.error('Error starting analysis:', err);
      setError(err.message || 'Failed to start analysis');
      setLoading(false);
    }
  };

  const pollStatus = async () => {
    const maxAttempts = 60; // Poll for up to 2 minutes (60 * 2s)
    let attempts = 0;

    const poll = async () => {
      try {
        const statusData = await analysisAPI.getStatus(workId);
        setStatus(statusData);

        if (statusData.status === 'completed') {
          // Fetch the full result
          const resultData = await analysisAPI.getResult(workId);
          setResult(resultData);
          setLoading(false);
        } else if (statusData.status === 'failed') {
          setError(statusData.error || 'Analysis failed');
          setLoading(false);
        } else if (attempts < maxAttempts) {
          // Continue polling
          attempts++;
          setTimeout(poll, 2000); // Poll every 2 seconds
        } else {
          setError('Analysis timed out');
          setLoading(false);
        }
      } catch (err) {
        // If we get 404, analysis hasn't started yet, keep polling
        if (err.response?.status === 404 && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 2000);
        } else if (err.response?.status === 202) {
          // Still processing
          attempts++;
          setTimeout(poll, 2000);
        } else {
          console.error('Error polling status:', err);
          setError(err.message || 'Failed to get analysis status');
          setLoading(false);
        }
      }
    };

    poll();
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'error':
        return 'red';
      case 'warning':
        return 'orange';
      case 'info':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const renderProgressBar = () => {
    if (!status || status.status === 'completed') return null;

    return (
      <div className="analysis-progress">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${status.progress || 0}%` }}
          />
        </div>
        <span className="progress-text">
          {status.current_stage || 'Processing'} - {status.progress || 0}%
        </span>
      </div>
    );
  };

  const renderIssues = (issues, title) => {
    if (!issues || issues.length === 0) return null;

    return (
      <div className="issues-section">
        <h4>{title} ({issues.length})</h4>
        <ul className="issues-list">
          {issues.map((issue, idx) => (
            <li key={idx} className={`issue-item severity-${issue.severity}`}>
              <span className="issue-type" style={{ color: getSeverityColor(issue.severity) }}>
                [{issue.severity?.toUpperCase()}]
              </span>
              <span className="issue-details">
                {issue.chapter_title && <strong>{issue.chapter_title}</strong>}
                {issue.details && <span> - {issue.details}</span>}
                {issue.toc_entry && (
                  <span>
                    TOC: "{issue.toc_entry}" vs Chapter: "{issue.chapter_title}"
                  </span>
                )}
                {issue.suggested_fix && (
                  <span className="suggested-fix"> → {issue.suggested_fix}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  if (!workId) return null;

  if (error) {
    return (
      <div className="analysis-panel error">
        <div className="panel-header">
          <h3>Analysis Failed</h3>
        </div>
        <div className="panel-body">
          <p className="error-message">{error}</p>
          <button onClick={startAnalysis}>Retry</button>
        </div>
      </div>
    );
  }

  if (loading && !result) {
    return (
      <div className="analysis-panel loading">
        <div className="panel-header">
          <h3>Analyzing Work...</h3>
          <button onClick={() => setExpanded(!expanded)}>
            {expanded ? '▼' : '▶'}
          </button>
        </div>
        {expanded && (
          <div className="panel-body">
            {renderProgressBar()}
            <p className="loading-text">
              Validating chapter sequences and TOC alignment...
            </p>
          </div>
        )}
      </div>
    );
  }

  if (!result) return null;

  const hasIssues = result.total_issues > 0;
  const allClear = !hasIssues;

  return (
    <div className={`analysis-panel ${hasIssues ? 'has-issues' : 'all-clear'}`}>
      <div className="panel-header">
        <h3>
          Structure Analysis
          {allClear && <span className="badge success">✓ All Clear</span>}
          {hasIssues && (
            <span className="badge warning">
              ⚠ {result.total_issues} Issue{result.total_issues !== 1 ? 's' : ''}
            </span>
          )}
        </h3>
        <button onClick={() => setExpanded(!expanded)}>
          {expanded ? '▼' : '▶'}
        </button>
      </div>

      {expanded && (
        <div className="panel-body">
          <div className="analysis-summary">
            <div className="summary-item">
              <span className="label">Chapters:</span>
              <span className="value">{result.total_chapters}</span>
            </div>
            <div className="summary-item">
              <span className="label">Critical Issues:</span>
              <span className={`value ${result.critical_issues > 0 ? 'error' : 'success'}`}>
                {result.critical_issues}
              </span>
            </div>
            <div className="summary-item">
              <span className="label">Warnings:</span>
              <span className={`value ${result.warnings > 0 ? 'warning' : 'success'}`}>
                {result.warnings}
              </span>
            </div>
            {result.toc_confidence_score > 0 && (
              <div className="summary-item">
                <span className="label">TOC Confidence:</span>
                <span className="value">{result.toc_confidence_score.toFixed(1)}%</span>
              </div>
            )}
          </div>

          {allClear && (
            <div className="all-clear-message">
              <p>No issues found. Chapter sequences and TOC alignment look good!</p>
            </div>
          )}

          {renderIssues(result.sequence_issues, 'Chapter Sequence Issues')}
          {renderIssues(result.toc_issues, 'TOC Alignment Issues')}

          {result.sequence_summary && (
            <div className="summary-section">
              <h4>Sequence Summary</h4>
              <p>{result.sequence_summary}</p>
            </div>
          )}

          {result.toc_summary && (
            <div className="summary-section">
              <h4>TOC Summary</h4>
              <p>{result.toc_summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

AnalysisPanel.propTypes = {
  workId: PropTypes.string.isRequired,
};

export default AnalysisPanel;
