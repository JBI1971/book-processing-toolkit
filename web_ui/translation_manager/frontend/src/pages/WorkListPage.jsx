import React, { useState, useEffect } from 'react';
import { worksAPI, jobsAPI } from '../api/client';

function WorkListPage() {
  const [works, setWorks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedWorks, setSelectedWorks] = useState(new Set());
  const [showModal, setShowModal] = useState(false);
  const [jobConfig, setJobConfig] = useState({
    model: 'gpt-4o-mini',
    temperature: 0.3,
    max_retries: 3,
  });
  const [creating, setCreating] = useState(false);
  const [sortBy, setSortBy] = useState('directory_name');
  const [sortDirection, setSortDirection] = useState('asc');

  useEffect(() => {
    loadWorks();
  }, []);

  const loadWorks = async () => {
    try {
      setLoading(true);
      const data = await worksAPI.list(search);
      setWorks(data);
    } catch (error) {
      console.error('Failed to load works:', error);
      alert('Failed to load works catalog. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadWorks();
  };

  const toggleWorkSelection = (workNumber) => {
    const newSelection = new Set(selectedWorks);
    if (newSelection.has(workNumber)) {
      newSelection.delete(workNumber);
    } else {
      newSelection.add(workNumber);
    }
    setSelectedWorks(newSelection);
  };

  const selectAll = () => {
    setSelectedWorks(new Set(works.map(w => w.work_number)));
  };

  const clearSelection = () => {
    setSelectedWorks(new Set());
  };

  const formatCount = (count) => {
    if (!count) return '-';
    if (count < 1000) return count.toString();
    if (count < 1000000) return `${(count / 1000).toFixed(0)}K`;
    return `${(count / 1000000).toFixed(1)}M`;
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to ascending
      setSortBy(column);
      setSortDirection('asc');
    }
  };

  const getSortedWorks = () => {
    const sorted = [...works].sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];

      // Handle null/undefined values
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';

      // Convert to string for consistent comparison
      if (typeof aVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      // String comparison
      const comparison = aVal.toString().localeCompare(bVal.toString(), 'zh-CN');
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return sorted;
  };

  const SortableHeader = ({ column, children, align }) => (
    <th
      style={{ cursor: 'pointer', textAlign: align, userSelect: 'none' }}
      onClick={() => handleSort(column)}
    >
      {children}
      {sortBy === column && (
        <span style={{ marginLeft: '5px' }}>
          {sortDirection === 'asc' ? '▲' : '▼'}
        </span>
      )}
    </th>
  );

  const createTranslationJob = async () => {
    if (selectedWorks.size === 0) {
      alert('Please select at least one work to translate');
      return;
    }

    try {
      setCreating(true);
      const workNumbers = Array.from(selectedWorks);
      const job = await jobsAPI.create(workNumbers, jobConfig);
      alert(`Translation job created: ${job.job_id}\n\nGo to Jobs page to monitor progress.`);
      clearSelection();
      setShowModal(false);
    } catch (error) {
      console.error('Failed to create job:', error);
      alert('Failed to create translation job. Check console for details.');
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="empty-state">
        <div className="spinner"></div>
        <p>Loading works catalog...</p>
      </div>
    );
  }

  return (
    <div>
      {/* Search and Actions */}
      <div className="card mb-2">
        <form onSubmit={handleSearch} className="flex-between">
          <div className="flex flex-gap" style={{ flex: 1 }}>
            <input
              type="text"
              className="input"
              placeholder="Search by title, author, or work number..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn-primary">Search</button>
          </div>
        </form>
      </div>

      {/* Selection Actions */}
      {selectedWorks.size > 0 && (
        <div className="card mb-2" style={{ background: '#e8f4f8' }}>
          <div className="flex-between">
            <div>
              <strong>{selectedWorks.size}</strong> work(s) selected
            </div>
            <div className="flex flex-gap">
              <button className="btn btn-secondary" onClick={clearSelection}>
                Clear Selection
              </button>
              <button className="btn btn-success" onClick={() => setShowModal(true)}>
                ▶️ Start Translation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Actions */}
      <div className="flex-between mb-2">
        <div className="text-muted">
          {works.length} works found
        </div>
        <button className="btn btn-secondary" onClick={selectAll}>
          Select All
        </button>
      </div>

      {/* Works Table */}
      {works.length === 0 ? (
        <div className="empty-state">
          <h3>No works found</h3>
          <p>Try adjusting your search query</p>
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}>
                  <input
                    type="checkbox"
                    checked={selectedWorks.size === works.length && works.length > 0}
                    onChange={() => selectedWorks.size === works.length ? clearSelection() : selectAll()}
                  />
                </th>
                <SortableHeader column="directory_name">Directory</SortableHeader>
                <SortableHeader column="work_number">Work #</SortableHeader>
                <SortableHeader column="title_chinese">Title (Chinese)</SortableHeader>
                <SortableHeader column="title_english">Title (English)</SortableHeader>
                <SortableHeader column="author_chinese">Author (Chinese)</SortableHeader>
                <SortableHeader column="author_english">Author (English)</SortableHeader>
                <SortableHeader column="total_volumes" align="center">Volumes</SortableHeader>
                <SortableHeader column="character_count" align="right">Characters</SortableHeader>
                <SortableHeader column="word_count" align="right">Words</SortableHeader>
                <SortableHeader column="estimated_tokens" align="right">Est. Tokens</SortableHeader>
                <SortableHeader column="translation_status">Status</SortableHeader>
              </tr>
            </thead>
            <tbody>
              {getSortedWorks().map((work) => (
                <tr key={work.work_number} onClick={() => toggleWorkSelection(work.work_number)}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedWorks.has(work.work_number)}
                      onChange={() => toggleWorkSelection(work.work_number)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                  <td className="text-muted"><small>{work.directory_name || '-'}</small></td>
                  <td><strong>{work.work_number}</strong></td>
                  <td>{work.title_chinese}</td>
                  <td className="text-muted">{work.title_english || '-'}</td>
                  <td>{work.author_chinese}</td>
                  <td className="text-muted">{work.author_english || '-'}</td>
                  <td style={{ textAlign: 'center' }}>
                    <span className="badge badge-info">{work.total_volumes}</span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <small className="text-muted">{formatCount(work.character_count)}</small>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <small className="text-muted">{formatCount(work.word_count)}</small>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <small className="text-muted">{formatCount(work.estimated_tokens)}</small>
                  </td>
                  <td>
                    <span className={`badge badge-${getStatusColor(work.translation_status)}`}>
                      {getStatusLabel(work.translation_status)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Job Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Translation Job</h2>

            <div className="form-group">
              <label>Selected Works ({selectedWorks.size})</label>
              <div style={{ maxHeight: '150px', overflow: 'auto', padding: '10px', background: '#f8f9fa', borderRadius: '4px' }}>
                {Array.from(selectedWorks).map(workNum => {
                  const work = works.find(w => w.work_number === workNum);
                  return (
                    <div key={workNum} style={{ padding: '5px 0' }}>
                      <strong>{workNum}</strong>: {work?.title_chinese}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="form-group">
              <label>Translation Model</label>
              <select
                className="select"
                value={jobConfig.model}
                onChange={(e) => setJobConfig({ ...jobConfig, model: e.target.value })}
                style={{ width: '100%' }}
              >
                <option value="gpt-4o-mini">GPT-4o Mini (Fast, Cost-Effective)</option>
                <option value="gpt-4o">GPT-4o (Best Quality)</option>
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
              </select>
            </div>

            <div className="form-group">
              <label>Temperature</label>
              <input
                type="number"
                className="input"
                min="0"
                max="1"
                step="0.1"
                value={jobConfig.temperature}
                onChange={(e) => setJobConfig({ ...jobConfig, temperature: parseFloat(e.target.value) })}
              />
              <span className="help-text">Lower = more consistent, Higher = more creative</span>
            </div>

            <div className="form-group">
              <label>Max Retries</label>
              <input
                type="number"
                className="input"
                min="1"
                max="10"
                value={jobConfig.max_retries}
                onChange={(e) => setJobConfig({ ...jobConfig, max_retries: parseInt(e.target.value) })}
              />
              <span className="help-text">Number of retry attempts for failed translations</span>
            </div>

            <div className="flex flex-gap mt-2">
              <button
                className="btn btn-success"
                onClick={createTranslationJob}
                disabled={creating}
                style={{ flex: 1 }}
              >
                {creating ? 'Creating...' : '▶️ Start Translation'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setShowModal(false)}
                disabled={creating}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getStatusColor(status) {
  switch (status) {
    case 'completed': return 'success';
    case 'in_progress': return 'warning';
    case 'failed': return 'danger';
    default: return 'secondary';
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'completed': return '✓ Completed';
    case 'in_progress': return '⚙️ In Progress';
    case 'failed': return '✗ Failed';
    default: return '○ Not Started';
  }
}

export default WorkListPage;
