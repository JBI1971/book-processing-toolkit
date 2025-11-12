import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import ChapterCard from './ChapterCard';

function DroppableSection({ id, title, description, chapters, onChapterUpdate }) {
  const { setNodeRef, isOver } = useDroppable({
    id: `section-${id}`,
  });

  return (
    <div
      ref={setNodeRef}
      className={`droppable-section ${isOver ? 'drag-over' : ''}`}
    >
      <div className="section-header">
        <div className="section-title-group">
          <h3>{title}</h3>
          <span className="section-count">
            {chapters.length} chapter{chapters.length !== 1 ? 's' : ''}
          </span>
        </div>
        <p className="section-description">{description}</p>
      </div>

      <div className="section-content">
        {chapters.length === 0 ? (
          <div className="empty-section">
            Drop chapters here or use the Section dropdown in chapter cards
          </div>
        ) : (
          <SortableContext
            items={chapters.map(ch => ch.id)}
            strategy={verticalListSortingStrategy}
          >
            {chapters.map((chapter) => (
              <ChapterCard
                key={chapter.id}
                chapter={chapter}
                onUpdate={onChapterUpdate}
              />
            ))}
          </SortableContext>
        )}
      </div>
    </div>
  );
}

export default DroppableSection;
