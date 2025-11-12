import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { worksAPI } from '../api/client';
import TOCViewer from '../components/TOCViewer';
import AnalysisPanel from '../components/AnalysisPanel';
import StructureEditor from '../components/StructureEditor';

function WorkDetailPage() {
  const { workId } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState(null);
  const [originalBook, setOriginalBook] = useState(null);
  const [modified, setModified] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');
  const chapterRefs = useRef({});

  useEffect(() => {
    loadWork();
  }, [workId]);

  const loadWork = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await worksAPI.get(decodeURIComponent(workId));
      setBook(data);
      setOriginalBook(JSON.parse(JSON.stringify(data))); // Deep copy
      setModified(false);
    } catch (err) {
      setError(err.message || 'Failed to load work');
      console.error('Error loading work:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStructureUpdate = (updatedBook) => {
    setBook(updatedBook);
    setModified(true);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const commitMessage = saveMessage || 'Manual edit via web interface';

      await worksAPI.save(workId, book, commitMessage);

      setModified(false);
      setSaveMessage('');
      alert('Work saved successfully!');
    } catch (err) {
      setError(err.message || 'Failed to save work');
      console.error('Error saving work:', err);
      alert('Failed to save: ' + (err.message || 'Unknown error'));
    } finally {
      setSaving(false);
    }
  };

  const handleAccept = () => {
    if (!modified) {
      alert('No changes to accept');
      return;
    }

    // Accept current state as new baseline
    setOriginalBook(JSON.parse(JSON.stringify(book)));
    setModified(false);
    alert('Changes accepted! Use "Save" to persist to file.');
  };

  const handleUndo = () => {
    if (!modified) {
      alert('No changes to undo');
      return;
    }

    if (confirm('Discard all changes and revert to original?')) {
      setBook(JSON.parse(JSON.stringify(originalBook)));
      setModified(false);
      alert('Changes reverted');
    }
  };

  const scrollToChapter = (chapterId) => {
    const element = chapterRefs.current[chapterId];
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  if (loading) {
    return <div className="loading">Loading work...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <p>Error: {error}</p>
        <button onClick={loadWork}>Retry</button>
        <button onClick={() => navigate('/')}>Back to List</button>
      </div>
    );
  }

  if (!book) {
    return <div className="error">Work not found</div>;
  }

  return (
    <div className="work-detail-page">
      <div className="work-detail-header">
        <button onClick={() => navigate('/')} className="back-button">
          ← Back to List
        </button>

        <div className="work-metadata">
          <h2>{book.meta?.title_chinese || book.meta?.title || 'Untitled'}</h2>
          {book.meta?.author && <p className="author">作者: {book.meta.author}</p>}
          {book.meta?.work_number && (
            <p className="work-number">Work: {book.meta.work_number}</p>
          )}
          {book.meta?.volume && <p className="volume">Vol: {book.meta.volume}</p>}
        </div>

        <div className="save-controls">
          <input
            type="text"
            placeholder="Commit message (optional)"
            value={saveMessage}
            onChange={(e) => setSaveMessage(e.target.value)}
            className="save-message-input"
            disabled={saving}
          />
          <button
            onClick={handleUndo}
            disabled={!modified || saving}
            className="undo-button"
          >
            Undo
          </button>
          <button
            onClick={handleAccept}
            disabled={!modified || saving}
            className="accept-button"
          >
            Accept
          </button>
          <button
            onClick={handleSave}
            disabled={!modified || saving}
            className="save-button"
          >
            {saving ? 'Saving...' : modified ? 'Save to File' : 'No Changes'}
          </button>
        </div>
      </div>

      <div className="work-detail-body">
        <aside className="toc-sidebar">
          <TOCViewer
            toc={book.structure?.front_matter?.toc}
            chapters={book.structure?.body?.chapters || []}
            onChapterClick={scrollToChapter}
          />
        </aside>

        <main className="chapters-main">
          {/* Lazy-loaded analysis panel */}
          <AnalysisPanel workId={workId} />

          {modified && (
            <div className="modified-indicator">
              ⚠️ You have unsaved changes
            </div>
          )}

          <StructureEditor book={book} onUpdate={handleStructureUpdate} />
        </main>
      </div>
    </div>
  );
}

export default WorkDetailPage;
