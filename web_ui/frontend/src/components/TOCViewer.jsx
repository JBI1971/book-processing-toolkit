import TranslateButton from './TranslateButton';

function TOCViewer({ toc, chapters, onChapterClick }) {
  // Validate TOC entries against actual chapters
  const validateTOC = () => {
    if (!toc || !chapters) return { valid: [], invalid: [] };

    const chapterIds = new Set(chapters.map(ch => ch.id));
    const valid = [];
    const invalid = [];

    toc.forEach(entry => {
      if (entry.chapter_id && chapterIds.has(entry.chapter_id)) {
        valid.push(entry);
      } else {
        invalid.push(entry);
      }
    });

    return { valid, invalid };
  };

  const { valid, invalid } = validateTOC();

  const handleEntryClick = (entry) => {
    if (entry.chapter_id && onChapterClick) {
      onChapterClick(entry.chapter_id);
    }
  };

  if (!toc || toc.length === 0) {
    return (
      <div className="toc-viewer empty">
        <p>No table of contents available</p>
      </div>
    );
  }

  return (
    <div className="toc-viewer">
      <h3>Table of Contents</h3>

      {invalid.length > 0 && (
        <div className="toc-warning">
          ⚠️ {invalid.length} TOC {invalid.length === 1 ? 'entry' : 'entries'} don't match actual chapters
        </div>
      )}

      <div className="toc-entries">
        {valid.map((entry, index) => (
          <div
            key={index}
            className="toc-entry"
            onClick={() => handleEntryClick(entry)}
            style={{ cursor: entry.chapter_id ? 'pointer' : 'default' }}
          >
            <div className="toc-entry-header">
              {entry.chapter_number && (
                <span className="toc-chapter-number">
                  Ch. {entry.chapter_number}
                </span>
              )}
              <span className="toc-title">
                {entry.chapter_title || entry.full_title}
              </span>
              {entry.chapter_title && (
                <TranslateButton text={entry.chapter_title} />
              )}
            </div>
            {entry.chapter_id && (
              <span className="toc-chapter-id">{entry.chapter_id}</span>
            )}
          </div>
        ))}

        {invalid.length > 0 && (
          <>
            <div className="toc-section-header">Invalid Entries</div>
            {invalid.map((entry, index) => (
              <div key={`invalid-${index}`} className="toc-entry invalid">
                <div className="toc-entry-header">
                  {entry.chapter_number && (
                    <span className="toc-chapter-number">
                      Ch. {entry.chapter_number}
                    </span>
                  )}
                  <span className="toc-title">
                    {entry.chapter_title || entry.full_title}
                  </span>
                </div>
                <span className="toc-error">
                  Chapter not found: {entry.chapter_id || 'N/A'}
                </span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export default TOCViewer;
