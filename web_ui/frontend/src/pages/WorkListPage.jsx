import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { worksAPI } from '../api/client';

function WorkListPage() {
  const [works, setWorks] = useState([]);
  const [filteredWorks, setFilteredWorks] = useState([]);
  const [search, setSearch] = useState('');
  const [volumeFilter, setVolumeFilter] = useState('all');
  const [showTranslated, setShowTranslated] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadWorks();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [works, search, volumeFilter]);

  const loadWorks = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await worksAPI.list();
      setWorks(data);
      setFilteredWorks(data);
    } catch (err) {
      setError(err.message || 'Failed to load works');
      console.error('Error loading works:', err);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = works;

    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(work => {
        const titleChinese = (work.title_chinese || work.title || '').toLowerCase();
        const titleEnglish = (work.title_english || '').toLowerCase();
        const authorChinese = (work.author_chinese || work.author || '').toLowerCase();
        const authorEnglish = (work.author_english || '').toLowerCase();
        const workNumber = (work.work_number || '').toLowerCase();
        const volume = (work.volume || '').toLowerCase();
        const directoryName = (work.directory_name || '').toLowerCase();

        return titleChinese.includes(searchLower) ||
               titleEnglish.includes(searchLower) ||
               authorChinese.includes(searchLower) ||
               authorEnglish.includes(searchLower) ||
               workNumber.includes(searchLower) ||
               volume.includes(searchLower) ||
               directoryName.includes(searchLower);
      });
    }

    // Apply volume filter
    if (volumeFilter !== 'all') {
      filtered = filtered.filter(work => {
        if (volumeFilter === 'none') {
          return !work.volume;
        }
        return work.volume === volumeFilter;
      });
    }

    // Sort by title (Chinese), then by volume
    filtered.sort((a, b) => {
      const titleA = a.title_chinese || a.title || '';
      const titleB = b.title_chinese || b.title || '';

      // First sort by title
      if (titleA !== titleB) {
        return titleA.localeCompare(titleB, 'zh-Hans-CN');
      }

      // Then sort by volume (treat missing as empty string)
      const volA = a.volume || '';
      const volB = b.volume || '';
      return volA.localeCompare(volB);
    });

    setFilteredWorks(filtered);
  };

  const handleWorkClick = (workId) => {
    navigate(`/work/${encodeURIComponent(workId)}`);
  };

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
  };

  const getUniqueVolumes = () => {
    const volumes = new Set();
    works.forEach(work => {
      if (work.volume) {
        volumes.add(work.volume);
      }
    });
    return Array.from(volumes).sort();
  };

  return (
    <div className="work-list-page">
      <div className="filters-section">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search by title, author, work number, or volume..."
            value={search}
            onChange={handleSearchChange}
            className="search-input"
          />
        </div>

        <div className="filter-controls">
          <div className="filter-group">
            <label>Volume:</label>
            <select
              value={volumeFilter}
              onChange={(e) => setVolumeFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Volumes</option>
              <option value="none">No Volume</option>
              {getUniqueVolumes().map(vol => (
                <option key={vol} value={vol}>Volume {vol}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>
              <input
                type="checkbox"
                checked={showTranslated}
                onChange={(e) => setShowTranslated(e.target.checked)}
              />
              Show English Translations
            </label>
          </div>

          <div className="results-count">
            {filteredWorks.length} of {works.length} works
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading">Loading works...</div>
      )}

      {error && (
        <div className="error">
          Error: {error}
          <button onClick={loadWorks} className="retry-button">Retry</button>
        </div>
      )}

      {!loading && !error && (
        <div className="works-grid">
          {filteredWorks.length === 0 ? (
            <div className="no-results">No works found</div>
          ) : (
            filteredWorks.map((work) => (
              <div
                key={work.work_id}
                className="work-card"
                onClick={() => handleWorkClick(work.work_id)}
              >
                <div className="work-card-header">
                  <div className="work-titles">
                    <h3 className="work-title-chinese">
                      {work.title_chinese || work.title}
                    </h3>
                    {showTranslated && work.title_english && (
                      <div className="work-title-english">
                        {work.title_english}
                      </div>
                    )}
                  </div>
                  <div className="work-badges">
                    {work.directory_name && (
                      <span className="work-directory">{work.directory_name}</span>
                    )}
                    {work.work_number && (
                      <span className="work-number">{work.work_number}</span>
                    )}
                    {work.volume && (
                      <span className="work-volume">Vol. {work.volume}</span>
                    )}
                  </div>
                </div>

                <div className="work-card-body">
                  {(work.author_chinese || work.author) && (
                    <div className="work-author-section">
                      <p className="work-author-chinese">
                        作者: {work.author_chinese || work.author}
                      </p>
                      {showTranslated && work.author_english && (
                        <p className="work-author-english">
                          Author: {work.author_english}
                        </p>
                      )}
                    </div>
                  )}
                  <p className="work-chapters">
                    {work.chapter_count} chapters
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default WorkListPage;
