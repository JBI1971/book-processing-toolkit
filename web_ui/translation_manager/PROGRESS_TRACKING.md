# Progress Tracking Feature

## Overview

The Translation Manager UI now includes comprehensive, multi-level progress tracking with real-time updates for translation jobs. This feature provides visibility into work-level, volume-level, chapter-level, and block-level progress with color-coded visual indicators.

## Features

### 1. Multi-Level Progress Display

Progress is tracked and displayed at three hierarchical levels:

- **Work-Level Progress**: Overall completion across all volumes (0-100%)
- **Chapter-Level Progress**: Number of completed chapters vs. total chapters
- **Block-Level Progress**: Number of translated blocks vs. total blocks
- **Current Chapter Progress**: Real-time progress within the active chapter

### 2. Color-Coded Progress Indicators

Progress bars and badges use intuitive color coding:

| Percentage | Color | Meaning |
|------------|-------|---------|
| 0-33% | Red (#e74c3c) | Just started / Warning |
| 34-66% | Yellow/Orange (#f39c12) | In progress |
| 67-99% | Blue (#3498db) | Almost done |
| 100% | Green (#27ae60) | Complete |

### 3. Real-Time Updates

Progress updates are delivered via WebSocket, providing:

- Live chapter/block progress every 5 seconds
- Immediate updates on work completion
- Animated progress bars for active translations
- No page refresh required

## Architecture

### Backend Components

#### 1. Progress Data Model (`DetailedProgress`)

```python
class DetailedProgress(BaseModel):
    current_volume: Optional[str]
    current_chapter: Optional[str]
    total_chapters: int
    completed_chapters: int
    total_blocks: int
    completed_blocks: int
    current_chapter_blocks: int
    current_chapter_completed: int
```

#### 2. Progress Calculation (`get_detailed_progress()`)

Reads progress from two sources:

1. **Checkpoint files** (primary source): `/logs/checkpoints/{work_number}_{volume}_checkpoint.json`
   - Contains real-time progress during active translation
   - Includes current chapter information
   - Updated by the translator as it processes blocks

2. **Translated output files** (fallback): `/translations/{work_number}/translated_{work_number}_{volume}.json`
   - Used when checkpoint doesn't exist
   - Counts completed chapters/blocks from final output
   - Provides static progress for completed works

#### 3. API Endpoints

- `GET /api/progress/{work_number}?volume={volume}`: Get detailed progress for a work/volume
- `GET /api/jobs/{job_id}/progress`: Get detailed progress for the current work in a job

#### 4. WebSocket Progress Updates

Three message types broadcast progress:

```javascript
// Initial work progress
{
  type: 'job_progress',
  job_id: 'job_20231113_120000',
  current_work: 'D55',
  progress: 25.0,
  detailed_progress: {...}
}

// Periodic updates during translation
{
  type: 'progress_update',
  job_id: 'job_20231113_120000',
  work_number: 'D55',
  detailed_progress: {...}
}

// Work completion
{
  type: 'work_complete',
  job_id: 'job_20231113_120000',
  work_number: 'D55',
  detailed_progress: {...}
}
```

### Frontend Components

#### 1. ProgressBar Component

Reusable progress bar with configurable options:

```jsx
<ProgressBar
  current={50}
  total={100}
  label="Chapter Progress"
  showPercentage={true}
  showFraction={true}
  height="24px"
  animated={true}
/>
```

Features:
- Color-coded background based on percentage
- Optional animation for active progress
- Flexible display options (percentage, fraction, both)
- Automatic label positioning (inside or outside bar)

#### 2. MultiLevelProgress Component

Hierarchical progress display showing all levels:

```jsx
<MultiLevelProgress
  detailedProgress={detailedProgress}
  workProgress={75.5}
/>
```

Displays:
- Overall work progress bar
- Chapter progress with count
- Current chapter progress with chapter ID
- Total block progress

#### 3. ProgressBadge Component

Compact percentage badge with color coding:

```jsx
<ProgressBadge percentage={85.5} />
```

Perfect for:
- Job list cards
- Work catalog status indicators
- Compact UI spaces

## Usage Examples

### Display Job Progress

```jsx
import { MultiLevelProgress, ProgressBadge } from '../components/ProgressBar';

function JobDetails({ job, detailedProgress }) {
  return (
    <div>
      <h3>{job.job_id}</h3>
      <ProgressBadge percentage={job.progress} />

      <MultiLevelProgress
        detailedProgress={detailedProgress}
        workProgress={job.progress}
      />
    </div>
  );
}
```

### Poll for Progress Updates

```jsx
import { jobsAPI } from '../api/client';

// Poll every 5 seconds for active jobs
useEffect(() => {
  const interval = setInterval(async () => {
    if (selectedJob?.status === 'running') {
      const progress = await jobsAPI.getDetailedProgress(selectedJob.job_id);
      setDetailedProgress(progress);
    }
  }, 5000);

  return () => clearInterval(interval);
}, [selectedJob]);
```

### Handle WebSocket Progress Updates

```jsx
const handleWebSocketMessage = (message) => {
  if (message.type === 'progress_update') {
    setDetailedProgress(message.detailed_progress);
  }

  if (message.type === 'work_complete') {
    setDetailedProgress(message.detailed_progress);
    notifyUser('Work completed!');
  }
};
```

## Checkpoint File Format

The translator saves checkpoint files during processing:

```json
{
  "work_number": "D55",
  "volume": "001",
  "total_chapters": 45,
  "completed_chapters": 12,
  "current_chapter": {
    "chapter_id": "chapter_0013",
    "chapter_number": 13,
    "title": "第十三章",
    "total_blocks": 164,
    "completed_blocks": 87
  },
  "chapter_progress": [
    {
      "chapter_id": "chapter_0001",
      "chapter_number": 1,
      "title": "第一章",
      "total_blocks": 142,
      "completed_blocks": 142,
      "token_usage": 15234,
      "is_complete": true,
      "completion_percentage": 100.0
    },
    // ... more chapters
  ],
  "last_updated": "2023-11-13T12:34:56"
}
```

## Performance Considerations

### Backend

- **Checkpoint reads**: O(1) file read, parsed JSON (~50KB typical)
- **Progress calculation**: O(n) where n = number of chapters
- **WebSocket broadcast**: Async, non-blocking
- **Periodic updates**: Every 5 seconds (configurable)

### Frontend

- **Polling**: Disabled when job is not running
- **WebSocket**: Single connection shared across all updates
- **Re-renders**: Optimized with React hooks and memoization
- **Progress bar animations**: CSS-based, no JS performance cost

## Troubleshooting

### Progress Not Updating

**Problem**: Progress stays at 0% even though translation is running

**Solutions**:
1. Check if checkpoint file exists: `/logs/checkpoints/{work_number}_{volume}_checkpoint.json`
2. Verify WebSocket connection in browser console
3. Check backend logs for errors in `get_detailed_progress()`
4. Ensure `save_checkpoints` is `True` in `TranslationConfig`

### Inconsistent Progress

**Problem**: Progress jumps or goes backwards

**Solutions**:
1. Verify checkpoint file is being updated atomically
2. Check for race conditions in file writes
3. Ensure unique work/volume identifiers
4. Clear old checkpoint files before starting new job

### WebSocket Disconnects

**Problem**: Progress stops updating after a few minutes

**Solutions**:
1. Check WebSocket ping/pong mechanism (30s interval)
2. Verify backend keepalive settings
3. Check for proxy/load balancer timeouts
4. Enable WebSocket reconnection logic (built-in, max 5 attempts)

## Future Enhancements

- [ ] Estimated time remaining (ETA) based on historical data
- [ ] Token usage tracking in progress display
- [ ] Pause/resume at chapter boundaries
- [ ] Progress history graph (time series visualization)
- [ ] Export progress reports as JSON/CSV
- [ ] Mobile-optimized progress view
- [ ] Browser notifications on milestones (25%, 50%, 75%, 100%)

## API Reference

### Backend Endpoints

#### GET /api/progress/{work_number}

Get detailed progress for a work.

**Parameters**:
- `work_number` (path): Work number (e.g., "D55")
- `volume` (query, optional): Volume number (e.g., "001")

**Response**: `DetailedProgress` object

**Example**:
```bash
curl http://localhost:8001/api/progress/D55?volume=001
```

#### GET /api/jobs/{job_id}/progress

Get detailed progress for the current work in a job.

**Parameters**:
- `job_id` (path): Job ID

**Response**: `DetailedProgress` object

**Errors**:
- 404: Job not found or no active work

### Frontend API

#### jobsAPI.getDetailedProgress(jobId)

```javascript
const progress = await jobsAPI.getDetailedProgress('job_20231113_120000');
console.log(progress.completed_chapters, '/', progress.total_chapters);
```

#### progressAPI.get(workNumber, volume)

```javascript
const progress = await progressAPI.get('D55', '001');
console.log(progress.block_progress_pct); // Calculated percentage
```

## Testing

### Manual Testing Checklist

- [ ] Start a translation job
- [ ] Verify progress updates in real-time
- [ ] Check color changes at 33%, 67%, 100%
- [ ] Test with multiple concurrent jobs
- [ ] Verify WebSocket reconnection
- [ ] Test pause/resume behavior
- [ ] Check progress persistence after refresh

### Example Test Data

Create a mock checkpoint file for testing:

```bash
mkdir -p logs/checkpoints
cat > logs/checkpoints/TEST_001_checkpoint.json <<EOF
{
  "work_number": "TEST",
  "volume": "001",
  "total_chapters": 10,
  "completed_chapters": 7,
  "current_chapter": {
    "chapter_id": "chapter_0008",
    "total_blocks": 100,
    "completed_blocks": 45
  },
  "chapter_progress": []
}
EOF
```

Then test the endpoint:
```bash
curl http://localhost:8001/api/progress/TEST?volume=001
```

## Configuration

### Backend Settings

```python
# In translation_config.py
class TranslationConfig:
    save_checkpoints: bool = True  # Enable checkpoint saving
    log_dir: Path = Path("./logs/translation")  # Checkpoint location
```

### Frontend Settings

```javascript
// In JobsPage.jsx
const PROGRESS_POLL_INTERVAL = 5000; // Poll every 5 seconds
const WEBSOCKET_RECONNECT_ATTEMPTS = 5; // Max reconnection attempts
```

## Dependencies

### Backend
- FastAPI (async WebSocket support)
- Pydantic (data validation)
- Python 3.8+ (async/await)

### Frontend
- React 18+ (hooks)
- Axios (HTTP client)
- WebSocket API (browser native)

## License

Same as parent project.
