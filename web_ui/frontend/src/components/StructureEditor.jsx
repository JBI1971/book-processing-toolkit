import { useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import ChapterCard from './ChapterCard';
import DroppableSection from './DroppableSection';
import './StructureEditor.css';

function StructureEditor({ book, onUpdate }) {
  const [activeId, setActiveId] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Extract all chapters from all sections
  const getAllChapters = () => {
    const structure = book?.structure || {};
    const frontMatter = structure.front_matter?.chapters || [];
    const body = structure.body?.chapters || [];
    const backMatter = structure.back_matter?.chapters || [];

    return {
      front_matter: frontMatter.map(ch => ({ ...ch, section: 'front_matter' })),
      body: body.map(ch => ({ ...ch, section: 'body' })),
      back_matter: backMatter.map(ch => ({ ...ch, section: 'back_matter' })),
    };
  };

  const [sections, setSections] = useState(getAllChapters());

  const findChapter = (id) => {
    for (const [sectionName, chapters] of Object.entries(sections)) {
      const chapter = chapters.find(ch => ch.id === id);
      if (chapter) {
        return { chapter, sectionName };
      }
    }
    return null;
  };

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragOver = (event) => {
    const { active, over } = event;

    if (!over) return;

    const activeData = findChapter(active.id);
    if (!activeData) return;

    const { chapter: activeChapter, sectionName: activeSection } = activeData;

    // Check if we're over a section container
    if (over.id.startsWith('section-')) {
      const targetSection = over.id.replace('section-', '');

      if (activeSection !== targetSection) {
        // Move chapter to different section
        setSections(prev => {
          const newSections = { ...prev };

          // Remove from old section
          newSections[activeSection] = newSections[activeSection].filter(
            ch => ch.id !== active.id
          );

          // Add to new section
          newSections[targetSection] = [
            ...newSections[targetSection],
            { ...activeChapter, section: targetSection }
          ];

          return newSections;
        });
      }
    } else {
      // Over another chapter - handle reordering within section
      const overData = findChapter(over.id);
      if (!overData) return;

      const { sectionName: overSection } = overData;

      if (activeSection === overSection && active.id !== over.id) {
        // Reorder within same section
        setSections(prev => {
          const newSections = { ...prev };
          const chapters = newSections[activeSection];

          const oldIndex = chapters.findIndex(ch => ch.id === active.id);
          const newIndex = chapters.findIndex(ch => ch.id === over.id);

          const reordered = [...chapters];
          const [removed] = reordered.splice(oldIndex, 1);
          reordered.splice(newIndex, 0, removed);

          newSections[activeSection] = reordered.map((ch, idx) => ({
            ...ch,
            ordinal: idx + 1
          }));

          return newSections;
        });
      } else if (activeSection !== overSection) {
        // Move to different section at specific position
        setSections(prev => {
          const newSections = { ...prev };

          // Remove from old section
          newSections[activeSection] = newSections[activeSection].filter(
            ch => ch.id !== active.id
          );

          // Add to new section at position
          const targetChapters = [...newSections[overSection]];
          const insertIndex = targetChapters.findIndex(ch => ch.id === over.id);
          targetChapters.splice(insertIndex, 0, {
            ...activeChapter,
            section: overSection
          });

          newSections[overSection] = targetChapters.map((ch, idx) => ({
            ...ch,
            ordinal: idx + 1
          }));

          return newSections;
        });
      }
    }
  };

  const handleDragEnd = () => {
    setActiveId(null);

    // Notify parent of changes
    if (onUpdate) {
      const updatedBook = {
        ...book,
        structure: {
          ...book.structure,
          front_matter: {
            ...book.structure.front_matter,
            chapters: sections.front_matter
          },
          body: {
            ...book.structure.body,
            chapters: sections.body
          },
          back_matter: {
            ...book.structure.back_matter,
            chapters: sections.back_matter
          }
        }
      };
      onUpdate(updatedBook);
    }
  };

  const handleChapterUpdate = (chapterId, updates) => {
    setSections(prev => {
      const newSections = { ...prev };

      for (const sectionName in newSections) {
        newSections[sectionName] = newSections[sectionName].map(ch =>
          ch.id === chapterId ? { ...ch, ...updates } : ch
        );
      }

      return newSections;
    });
  };

  const allChapterIds = [
    ...sections.front_matter.map(ch => ch.id),
    ...sections.body.map(ch => ch.id),
    ...sections.back_matter.map(ch => ch.id),
  ];

  const activeChapterData = activeId ? findChapter(activeId) : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="structure-editor">
        <div className="structure-hint">
          💡 Drag chapters between sections to restructure the book
        </div>

        <SortableContext items={allChapterIds} strategy={verticalListSortingStrategy}>
          <DroppableSection
            id="front_matter"
            title="Front Matter"
            description="Preface, introduction, foreword, etc."
            chapters={sections.front_matter}
            onChapterUpdate={handleChapterUpdate}
          />

          <DroppableSection
            id="body"
            title="Main Content"
            description="Story chapters"
            chapters={sections.body}
            onChapterUpdate={handleChapterUpdate}
          />

          <DroppableSection
            id="back_matter"
            title="Back Matter"
            description="Afterword, appendix, author notes, etc."
            chapters={sections.back_matter}
            onChapterUpdate={handleChapterUpdate}
          />
        </SortableContext>
      </div>

      <DragOverlay>
        {activeId && activeChapterData ? (
          <div className="drag-overlay">
            <ChapterCard
              chapter={activeChapterData.chapter}
              onUpdate={() => {}}
            />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export default StructureEditor;
