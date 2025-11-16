import React, { useState, useEffect, useRef } from 'react';
import { jobsAPI, JobWebSocket } from '../api/client';
import { MultiLevelProgress, ProgressBadge } from '../components/ProgressBar';
import WorkflowProgress from '../components/WorkflowProgress';
import '../components/WorkflowProgress.css';

function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [detailedProgress, setDetailedProgress] = useState(null);
  const [activeWorkflow, setActiveWorkflow] = useState(null); // { flowRunId, workId, volume }
  const [showWorkflowView, setShowWorkflowView] = useState(false);
  const wsRef = useRef(null);
  const progressPollRef = useRef(null);

  useEffect(() => {
    loadJobs();

    // Setup WebSocket connection
    wsRef.current = new JobWebSocket(handleWebSocketMessage);
    wsRef.current.connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
      if (progressPollRef.current) {
        clearInterval(progressPollRef.current);
      }
    };
  }, []);

  // Poll for detailed progress when a running job is selected
  useEffect(() => {
    if (selectedJob && selectedJob.status === 'running' && selectedJob.current_work) {
      // Initial load
      loadDetailedProgress(selectedJob.job_id);

      // Poll every 5 seconds
      progressPollRef.current = setInterval(() => {
        loadDetailedProgress(selectedJob.job_id);
      }, 5000);

      return () => {
        if (progressPollRef.current) {
          clearInterval(progressPollRef.current);
        }
      };
    } else {
      setDetailedProgress(null);
      if (progressPollRef.current) {
        clearInterval(progressPollRef.current);
      }
    }
  }, [selectedJob?.job_id, selectedJob?.status, selectedJob?.current_work]);

  const loadJobs = async () => {
    try {
      setLoading(true);
      const data = await jobsAPI.list();
      setJobs(data);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDetailedProgress = async (jobId) => {
    try {
      const progress = await jobsAPI.getDetailedProgress(jobId);
      setDetailedProgress(progress);
    } catch (error) {
      // Not all jobs will have detailed progress (e.g., queued jobs)
      console.debug('No detailed progress available:', error);
      setDetailedProgress(null);
    }
  };

  const handleWebSocketMessage = (message) => {
    console.log('WebSocket message:', message);

    // Update jobs list based on message type
    if (message.type === 'job_update' || message.type === 'job_progress' || message.type === 'job_complete') {
      setJobs(prevJobs => {
        return prevJobs.map(job => {
          if (job.job_id === message.job_id) {
            return {
              ...job,
              ...message,
            };
          }
          return job;
        });
      });

      // Update selected job if it's the one being updated
      if (selectedJob && selectedJob.job_id === message.job_id) {
        setSelectedJob(prev => ({ ...prev, ...message }));
      }

      // Update detailed progress if included
      if (message.detailed_progress) {
        setDetailedProgress(message.detailed_progress);
      }
    }

    // Handle real-time progress updates
    if (message.type === 'progress_update' && selectedJob && selectedJob.job_id === message.job_id) {
      if (message.detailed_progress) {
        setDetailedProgress(message.detailed_progress);
      }
    }

    // Handle work completion
    if (message.type === 'work_complete' && selectedJob && selectedJob.job_id === message.job_id) {
      if (message.detailed_progress) {
        setDetailedProgress(message.detailed_progress);
      }
    }
  };

  const cancelJob = async (jobId) => {
    if (!confirm('Are you sure you want to cancel this job?')) {
      return;
    }

    try {
      await jobsAPI.cancel(jobId);
      alert('Job cancellation requested');
      loadJobs();
    } catch (error) {
      console.error('Failed to cancel job:', error);
      alert('Failed to cancel job');
    }
  };

  const refreshJobs = () => {
    loadJobs();
  };

  const startWorkflow = async (workId, volume = null) => {
    try {
      const response = await fetch('http://localhost:8000/api/workflow/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          work_id: workId,
          volume: volume,
          config: {},
          resume: false
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to start workflow: ${response.statusText}`);
      }

      const data = await response.json();

      setActiveWorkflow({
        flowRunId: data.flow_run_id,
        workId: workId,
        volume: volume
      });
      setShowWorkflowView(true);

      alert(`Workflow started successfully!\nFlow Run ID: ${data.flow_run_id}`);
    } catch (error) {
      console.error('Error starting workflow:', error);
      alert(`Failed to start workflow: ${error.message}`);
    }
  };

  const handleWorkflowComplete = (status) => {
    console.log('Workflow completed:', status);
    alert(`Workflow completed with status: ${status.status}`);

    // Refresh jobs list
    loadJobs();

    // Optionally close workflow view
    // setShowWorkflowView(false);
  };

  if (loading) {
    return (
      <div className="empty-state">
        <div className="spinner"></div>
        <p>Loading translation jobs...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex-between mb-2">
        <h2>Translation Jobs</h2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            className="btn btn-success"
            onClick={() => {
              const workId = prompt('Enter Work ID (e.g., D1379):');
              if (workId) {
                const volume = prompt('Enter Volume (optional, leave blank for all):');
                startWorkflow(workId, volume || null);
              }
            }}
          >
            ⚡ Start New Workflow
          </button>
          {showWorkflowView && (
            <button
              className="btn btn-secondary"
              onClick={() => setShowWorkflowView(!showWorkflowView)}
            >
              {showWorkflowView ? '📋 Show Jobs' : '📊 Show Workflow'}
            </button>
          )}
          <button className="btn btn-primary" onClick={refreshJobs}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Workflow View */}
      {showWorkflowView && activeWorkflow && (
        <div style={{ marginBottom: '24px' }}>
          <WorkflowProgress
            flowRunId={activeWorkflow.flowRunId}
            onComplete={handleWorkflowComplete}
          />
        </div>
      )}

      {/* Jobs List View */}
      {!showWorkflowView && (
        jobs.length === 0 ? (
          <div className="empty-state">
            <h3>No translation jobs yet</h3>
            <p>Go to Works Catalog to create your first translation job</p>
          </div>
        ) : (
          <div className="grid grid-2">
          {/* Jobs List */}
          <div>
            {jobs.map(job => (
              <div
                key={job.job_id}
                className="card mb-2"
                style={{
                  cursor: 'pointer',
                  border: selectedJob?.job_id === job.job_id ? '2px solid #3498db' : 'none'
                }}
                onClick={() => setSelectedJob(job)}
              >
                <div className="flex-between mb-1">
                  <div>
                    <strong>{job.job_id}</strong>
                    <div className="text-sm text-muted">
                      {job.work_numbers.length} work(s)
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <ProgressBadge percentage={job.progress || 0} />
                    <span className={`badge badge-${getJobStatusColor(job.status)}`}>
                      {getJobStatusLabel(job.status)}
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                {(job.status === 'running' || job.status === 'queued') && (
                  <div className="progress-bar mt-1">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${job.progress || 0}%`,
                        backgroundColor: getProgressColor(job.progress || 0)
                      }}
                    >
                      {job.progress ? `${job.progress.toFixed(0)}%` : 'Queued'}
                    </div>
                  </div>
                )}

                {/* Current Work */}
                {job.current_work && (
                  <div className="text-sm mt-1">
                    Currently: <strong>{job.current_work}</strong>
                  </div>
                )}

                {/* Summary */}
                <div className="flex flex-gap mt-1 text-sm">
                  <span className="badge badge-success">
                    ✓ {job.completed_works?.length || 0}
                  </span>
                  <span className="badge badge-danger">
                    ✗ {job.failed_works?.length || 0}
                  </span>
                </div>

                {/* Actions */}
                {job.status === 'running' && (
                  <div className="mt-1">
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        cancelJob(job.job_id);
                      }}
                    >
                      ⏸ Pause
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Job Details */}
          <div>
            {selectedJob ? (
              <div className="card" style={{ position: 'sticky', top: '20px' }}>
                <h3>Job Details</h3>

                <div className="form-group">
                  <label>Job ID</label>
                  <div className="text-muted">{selectedJob.job_id}</div>
                </div>

                <div className="form-group">
                  <label>Status</label>
                  <span className={`badge badge-${getJobStatusColor(selectedJob.status)}`}>
                    {getJobStatusLabel(selectedJob.status)}
                  </span>
                </div>

                <div className="form-group">
                  <label>Progress</label>
                  <MultiLevelProgress
                    detailedProgress={detailedProgress}
                    workProgress={selectedJob.progress || 0}
                  />
                </div>

                {/* Detailed Progress Info */}
                {detailedProgress && (
                  <div className="form-group">
                    <label>Translation Details</label>
                    <div style={{
                      padding: '12px',
                      background: '#f8f9fa',
                      borderRadius: '4px',
                      fontSize: '13px'
                    }}>
                      {detailedProgress.current_volume && (
                        <div style={{ marginBottom: '8px' }}>
                          <strong>Current Volume:</strong> {detailedProgress.current_volume}
                        </div>
                      )}
                      {detailedProgress.current_chapter && (
                        <div style={{ marginBottom: '8px' }}>
                          <strong>Current Chapter:</strong> {detailedProgress.current_chapter}
                        </div>
                      )}
                      {detailedProgress.total_chapters > 0 && (
                        <div style={{ marginBottom: '4px' }}>
                          Chapters: {detailedProgress.completed_chapters}/{detailedProgress.total_chapters}
                          ({((detailedProgress.completed_chapters / detailedProgress.total_chapters) * 100).toFixed(1)}%)
                        </div>
                      )}
                      {detailedProgress.total_blocks > 0 && (
                        <div>
                          Blocks: {detailedProgress.completed_blocks}/{detailedProgress.total_blocks}
                          ({((detailedProgress.completed_blocks / detailedProgress.total_blocks) * 100).toFixed(1)}%)
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="form-group">
                  <label>Works ({selectedJob.work_numbers.length})</label>
                  <div style={{ maxHeight: '150px', overflow: 'auto', padding: '10px', background: '#f8f9fa', borderRadius: '4px' }}>
                    {selectedJob.work_numbers.map(workNum => (
                      <div key={workNum} style={{ padding: '2px 0' }}>
                        {selectedJob.completed_works?.includes(workNum) && '✓ '}
                        {selectedJob.failed_works?.includes(workNum) && '✗ '}
                        {selectedJob.current_work === workNum && '⚙️ '}
                        {workNum}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="form-group">
                  <label>Completed Works</label>
                  <div className="text-lg">
                    <span className="badge badge-success">
                      {selectedJob.completed_works?.length || 0}
                    </span>
                  </div>
                </div>

                <div className="form-group">
                  <label>Failed Works</label>
                  <div className="text-lg">
                    <span className="badge badge-danger">
                      {selectedJob.failed_works?.length || 0}
                    </span>
                  </div>
                </div>

                {selectedJob.start_time && (
                  <div className="form-group">
                    <label>Start Time</label>
                    <div className="text-muted text-sm">
                      {new Date(selectedJob.start_time).toLocaleString()}
                    </div>
                  </div>
                )}

                {selectedJob.end_time && (
                  <div className="form-group">
                    <label>End Time</label>
                    <div className="text-muted text-sm">
                      {new Date(selectedJob.end_time).toLocaleString()}
                    </div>
                  </div>
                )}

                {selectedJob.error_message && (
                  <div className="form-group">
                    <label>Error</label>
                    <div style={{ padding: '10px', background: '#fadbd8', borderRadius: '4px', fontSize: '14px' }}>
                      {selectedJob.error_message}
                    </div>
                  </div>
                )}

                {selectedJob.statistics && Object.keys(selectedJob.statistics).length > 0 && (
                  <div className="form-group">
                    <label>Statistics</label>
                    <div style={{ padding: '10px', background: '#f8f9fa', borderRadius: '4px', fontSize: '12px' }}>
                      <pre>{JSON.stringify(selectedJob.statistics, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="card empty-state">
                <p>Select a job to view details</p>
              </div>
            )}
          </div>
        </div>
        )
      )}
    </div>
  );
}

function getJobStatusColor(status) {
  switch (status) {
    case 'completed': return 'success';
    case 'running': return 'warning';
    case 'failed': return 'danger';
    case 'paused': return 'secondary';
    default: return 'info';
  }
}

function getJobStatusLabel(status) {
  switch (status) {
    case 'completed': return '✓ Completed';
    case 'running': return '⚙️ Running';
    case 'failed': return '✗ Failed';
    case 'paused': return '⏸ Paused';
    case 'queued': return '⏳ Queued';
    default: return status;
  }
}

function getProgressColor(percentage) {
  if (percentage === 100) return '#27ae60'; // Green - complete
  if (percentage >= 67) return '#3498db'; // Blue - almost done
  if (percentage >= 34) return '#f39c12'; // Yellow/orange - in progress
  return '#e74c3c'; // Red - just started
}

export default JobsPage;
