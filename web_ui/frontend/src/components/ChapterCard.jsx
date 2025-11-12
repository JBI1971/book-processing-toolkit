import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import TranslateButton from './TranslateButton';

function ChapterCard({ chapter, onUpdate }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: chapter.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleSectionTypeChange = (e) => {
    if (onUpdate) {
      onUpdate(chapter.id, { section_type: e.target.value });
    }
  };

  const handleSpecialTypeChange = (e) => {
    if (onUpdate) {
      onUpdate(chapter.id, { special_section_type: e.target.value });
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`chapter-card ${isDragging ? 'dragging' : ''}`}
    >
      <div className="chapter-card-drag-handle" {...attributes} {...listeners}>
        ⋮⋮
      </div>

      <div className="chapter-card-content">
        <div className="chapter-card-header">
          <div className="chapter-title-section">
            <h4 className="chapter-title">
              {chapter.title || 'Untitled Chapter'}
            </h4>
            <TranslateButton text={chapter.title} />
          </div>
          {chapter.ordinal !== undefined && (
            <span className="chapter-ordinal">#{chapter.ordinal}</span>
          )}
        </div>

        <div className="chapter-card-body">
          <div className="chapter-info">
            <span className="chapter-id">{chapter.id}</span>
            {chapter.content_blocks && (
              <span className="block-count">
                {chapter.content_blocks.length} blocks
              </span>
            )}
          </div>

          <div className="chapter-controls">
            <div className="control-group">
              <label>Section:</label>
              <select
                value={chapter.section_type || 'body'}
                onChange={handleSectionTypeChange}
                className="section-type-select"
              >
                <option value="front_matter">Front Matter</option>
                <option value="body">Body</option>
                <option value="back_matter">Back Matter</option>
              </select>
            </div>

            <div className="control-group">
              <label>Type:</label>
              <select
                value={chapter.special_section_type || 'main_chapter'}
                onChange={handleSpecialTypeChange}
                className="special-type-select"
              >
                <option value="preface">Preface</option>
                <option value="introduction">Introduction</option>
                <option value="prologue">Prologue</option>
                <option value="main_chapter">Main Chapter</option>
                <option value="epilogue">Epilogue</option>
                <option value="afterword">Afterword</option>
                <option value="appendix">Appendix</option>
                <option value="author_note">Author Note</option>
                <option value="translator_note">Translator Note</option>
                <option value="character_list">Character List</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChapterCard;
