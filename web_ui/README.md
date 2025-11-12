# Book Review Interface

Web-based interface for reviewing and editing processed book JSON files with drag-and-drop reordering, on-demand translation, and structure management.

## 🎯 Features

- **Filterable Works List** - Search and browse all processed books
- **Structure Editing** - View and edit book structure, TOC, chapters
- **Drag & Drop** - Reorder chapters with intuitive drag-and-drop
- **On-Demand Translation** - Click to translate Chinese text to English via OpenAI
- **Category Management** - Change section types (front_matter/body/back_matter) and special types (preface/afterword/etc.)
- **Review Workflow** - Save edited versions to separate review directory

## 📁 Architecture

```
web_ui/
├── backend/               # FastAPI server
│   ├── app.py            # Main application
│   ├── api/              # API endpoints
│   │   ├── works.py      # List/get works
│   │   ├── translate.py  # OpenAI translation
│   │   └── edit.py       # Save/reorder/update
│   ├── models/           # Pydantic models
│   │   └── book.py       # Data structures
│   ├── requirements.txt  # Python dependencies
│   └── .env.example      # Environment template
├── frontend/             # React + Vite
│   ├── src/
│   │   ├── api/          # API client layer
│   │   ├── components/   # React components [TO IMPLEMENT]
│   │   ├── pages/        # Page components [TO IMPLEMENT]
│   │   └── utils/        # Utilities [TO IMPLEMENT]
│   └── package.json      # Node dependencies
└── start.sh              # Startup script

## ✅ Backend Status: COMPLETE

The FastAPI backend is fully implemented with:

- ✅ Works listing with search/filtering
- ✅ Full work retrieval with structure
- ✅ On-demand translation via OpenAI (gpt-4o-mini)
- ✅ Chapter reordering
- ✅ Chapter metadata updates (section/special types)
- ✅ Save to review directory with edit history
- ✅ CORS middleware for frontend access
- ✅ Pydantic models for validation
- ✅ Environment configuration

### Backend Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/works` | GET | List all works (with optional search) |
| `/api/works/{work_id}` | GET | Get complete work data |
| `/api/works/{work_id}/save` | POST | Save modifications to review directory |
| `/api/works/{work_id}/chapters/{chapter_id}` | PUT | Update chapter metadata |
| `/api/works/{work_id}/reorder` | POST | Reorder chapter position |
| `/api/translate` | POST | Translate text via OpenAI |
| `/docs` | GET | Interactive API documentation |

## 🚧 Frontend Status: STARTED

The React frontend is initialized with dependencies installed. **Implementation needed:**

### Required React Components

#### 1. `src/pages/WorkListPage.jsx`
**Purpose:** Main landing page with filterable works list

**Features:**
- Search bar for filtering works by title/author/work_number
- Grid or list view of work summaries
- Click to navigate to work detail page

**Key State:**
- `works` - array of WorkSummary objects from API
- `search` - search filter string
- `loading` - loading state

**API Call:**
```javascript
import { worksAPI } from '../api/client';
const works = await worksAPI.list(searchQuery);
```

#### 2. `src/pages/WorkDetailPage.jsx`
**Purpose:** Main editing interface for a single work

**Features:**
- Display book metadata (title, author, work_number, volume)
- Show TOC structure
- Display chapters with drag-and-drop reordering
- Save button to commit changes

**Key State:**
- `book` - complete Book object from API
- `modified` - boolean flag if changes made
- `saving` - saving state

**API Calls:**
```javascript
const book = await worksAPI.get(workId);
await worksAPI.save(workId, book, commitMessage);
```

#### 3. `src/components/ChapterCard.jsx`
**Purpose:** Individual draggable chapter card

**Features:**
- Display chapter title (Chinese + translated)
- Drag handle for reordering
- Dropdown for section_type (front_matter/body/back_matter)
- Dropdown for special_type (preface/main_chapter/afterword/etc.)
- Translation button
- Ordinal display

**Props:**
- `chapter` - Chapter object
- `onUpdate` - callback when metadata changes
- `onTranslate` - callback to translate title

**Drag-and-Drop Integration:**
```javascript
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
  id: chapter.id
});

const style = {
  transform: CSS.Transform.toString(transform),
  transition,
};
```

#### 4. `src/components/TranslateButton.jsx`
**Purpose:** Button to translate text on demand

**Features:**
- Click to translate
- Loading spinner during translation
- Toggle between original and translated
- Cache translations to avoid re-translating

**State:**
- `translated` - translated text (null if not yet translated)
- `loading` - translation in progress
- `showTranslated` - boolean toggle

**API Call:**
```javascript
const result = await translateAPI.translate(text, 'zh', 'en');
setTranslated(result.translated);
```

#### 5. `src/components/TOCViewer.jsx`
**Purpose:** Display table of contents

**Features:**
- List all TOC entries
- Show chapter numbering and titles
- Highlight mismatches between TOC and actual chapters
- Click to scroll to chapter

#### 6. `src/App.jsx`
**Purpose:** Main application with routing

**Required:**
```javascript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import WorkListPage from './pages/WorkListPage';
import WorkDetailPage from './pages/WorkDetailPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<WorkListPage />} />
        <Route path="/work/:workId" element={<WorkDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### Drag-and-Drop Implementation

Using `@dnd-kit` (already installed):

```javascript
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';

function ChapterList({ chapters, onReorder }) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event) => {
    const { active, over } = event;

    if (active.id !== over.id) {
      const oldIndex = chapters.findIndex((c) => c.id === active.id);
      const newIndex = chapters.findIndex((c) => c.id === over.id);
      const reordered = arrayMove(chapters, oldIndex, newIndex);
      onReorder(reordered, active.id, newIndex);
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={chapters.map((c) => c.id)}
        strategy={verticalListSortingStrategy}
      >
        {chapters.map((chapter) => (
          <ChapterCard key={chapter.id} chapter={chapter} />
        ))}
      </SortableContext>
    </DndContext>
  );
}
```

## 🚀 Quick Start

### 1. Backend Setup

```bash
# From web_ui/backend directory
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Start Both Servers

```bash
# From web_ui directory
./start.sh
```

This will start:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

### 3. Manual Start (Alternative)

**Backend:**
```bash
cd backend
source venv/bin/activate
python app.py
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## 🔧 Environment Configuration

### Backend `.env`

```bash
# Required
OPENAI_API_KEY=your_key_here

# Paths (adjust to your setup)
CLEANED_JSON_DIR=/Users/jacki/project_files/translation_project/01_clean_json
REVIEWED_JSON_DIR=/Users/jacki/project_files/translation_project/02_reviewed_json

# Optional
BACKEND_PORT=8000
```

### Frontend `.env` (create if needed)

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## 📊 Data Flow

```
User Action
   ↓
React Component
   ↓
API Client (axios)
   ↓
FastAPI Endpoint
   ↓
Load/Modify JSON
   ↓
Return Response
   ↓
Update React State
   ↓
Re-render UI
```

### Save Workflow

```
1. User edits work in UI
2. Modified book data stored in React state
3. Click "Save"
4. POST /api/works/{work_id}/save with full book data
5. Backend saves to REVIEWED_JSON_DIR
6. Filename: cleaned_*.json → reviewed_*.json
7. Edit history appended to JSON
8. Success message returned
```

## 🎨 Styling Recommendations

The frontend uses React + Vite (no styling framework installed yet). Recommend adding:

**Option 1: Tailwind CSS** (utility-first)
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Option 2: Material-UI** (component library)
```bash
npm install @mui/material @emotion/react @emotion/styled
```

**Option 3: Plain CSS** (already works)
- Style in `src/index.css`
- Component-specific CSS modules

## 📝 Development Notes

### Testing the Backend

```bash
# List works
curl http://localhost:8000/api/works

# Get specific work
curl http://localhost:8000/api/works/wuxia_0001/cleaned_D55a_射鵰英雄傳一_金庸.json

# Translate text
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "第一章", "source_lang": "zh", "target_lang": "en"}'
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

## 🐛 Troubleshooting

**Backend won't start:**
- Check `.env` file exists
- Verify OPENAI_API_KEY is set
- Check paths in .env point to actual directories

**Frontend can't connect to backend:**
- Ensure backend is running on port 8000
- Check CORS settings in backend/app.py
- Verify VITE_API_BASE_URL in frontend

**Translation fails:**
- Verify OPENAI_API_KEY is valid
- Check OpenAI account has credits
- Review error in backend logs

## 📦 Dependencies

### Backend (Python)
- fastapi >=0.104.0
- uvicorn[standard] >=0.24.0
- pydantic >=2.4.0
- openai >=1.3.0
- python-dotenv >=1.0.0

### Frontend (Node)
- react ^18.3.1
- react-dom ^18.3.1
- react-router-dom (installed)
- axios (installed)
- @dnd-kit/core (installed)
- @dnd-kit/sortable (installed)
- @dnd-kit/utilities (installed)
- vite ^7.1.12

## 🎯 Next Steps

1. **Implement React Components** - Complete the frontend components listed above
2. **Add Styling** - Choose and implement a styling solution
3. **Error Handling** - Add user-friendly error messages
4. **Loading States** - Add spinners/skeletons for async operations
5. **Undo/Redo** - Implement change history within editing session
6. **Validation Warnings** - Show warnings for structural issues
7. **Batch Operations** - Allow multi-select and bulk editing

## 📄 License

Part of the Book Processing Toolkit project.
