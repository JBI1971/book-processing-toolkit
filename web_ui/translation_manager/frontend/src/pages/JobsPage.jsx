import React, { useState, useEffect, useRef } from 'react';
import { jobsAPI, JobWebSocket } from '../api/client';

function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    loadJobs();

    // Setup WebSocket connection
    wsRef.current = new JobWebSocket(handleWebSocketMessage);
    wsRef.current.connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, []);

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
        <button className="btn btn-primary" onClick={refreshJobs}>
          🔄 Refresh
        </button>
      </div>

      {jobs.length === 0 ? (
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
                  <span className={`badge badge-${getJobStatusColor(job.status)}`}>
                    {getJobStatusLabel(job.status)}
                  </span>
                </div>

                {/* Progress Bar */}
                {(job.status === 'running' || job.status === 'queued') && (
                  <div className="progress-bar mt-1">
                    <div className="progress-fill" style={{ width: `${job.progress || 0}%` }}>
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
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${selectedJob.progress || 0}%` }}>
                      {selectedJob.progress ? `${selectedJob.progress.toFixed(1)}%` : '0%'}
                    </div>
                  </div>
                </div>

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

export default JobsPage;
