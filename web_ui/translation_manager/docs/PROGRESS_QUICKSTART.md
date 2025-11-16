# Progress Tracking - Quick Start Guide

## 5-Minute Integration Guide

Want to add progress tracking to your own translation workflow? Here's how:

## Backend Integration

### Step 1: Save Checkpoint Files

In your translator, save progress after each chapter:

```python
import json
from pathlib import Path

def save_checkpoint(work_number, volume, progress_data):
    """Save translation progress checkpoint"""
    checkpoint_dir = Path("./logs/checkpoints")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_file = checkpoint_dir / f"{work_number}_{volume}_checkpoint.json"

    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump({
            "work_number": work_number,
            "volume": volume,
            "total_chapters": progress_data['total_chapters'],
            "completed_chapters": progress_data['completed_chapters'],
            "current_chapter": {
                "chapter_id": progress_data['current_chapter_id'],
                "total_blocks": progress_data['current_chapter_blocks'],
                "completed_blocks": progress_data['current_chapter_completed']
            },
            "chapter_progress": progress_data['all_chapters'],
            "last_updated": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)
```

### Step 2: Call in Your Translation Loop

```python
from processors.book_translator import BookTranslator

translator = BookTranslator(config)

for i, chapter in enumerate(chapters):
    # Translate chapter
    translated_blocks = translator.translate_chapter(chapter)

    # Save checkpoint
    save_checkpoint(work_number, volume, {
        'total_chapters': len(chapters),
        'completed_chapters': i,
        'current_chapter_id': chapter['id'],
        'current_chapter_blocks': len(chapter['blocks']),
        'current_chapter_completed': len(translated_blocks),
        'all_chapters': chapter_progress_list
    })
```

### Step 3: Use in API (Already Implemented!)

The backend API automatically reads these checkpoints:

```python
# Already in app.py - just use it!
progress = get_detailed_progress(work_number, volume)
```

## Frontend Integration

### Step 1: Import Components

```jsx
import { MultiLevelProgress, ProgressBadge } from '../components/ProgressBar';
```

### Step 2: Fetch Progress

```jsx
import { jobsAPI, progressAPI } from '../api/client';

// For a running job
const progress = await jobsAPI.getDetailedProgress(job.job_id);

// For a specific work
const progress = await progressAPI.get('D55', '001');
```

### Step 3: Display Progress

```jsx
function MyJobView({ job }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    // Poll for progress
    const interval = setInterval(async () => {
      const data = await jobsAPI.getDetailedProgress(job.job_id);
      setProgress(data);
    }, 5000);

    return () => clearInterval(interval);
  }, [job.job_id]);

  return (
    <div>
      <h3>{job.job_id}</h3>
      <ProgressBadge percentage={job.progress} />

      <MultiLevelProgress
        detailedProgress={progress}
        workProgress={job.progress}
      />
    </div>
  );
}
```

## Testing Your Integration

### Create a Test Checkpoint

```bash
mkdir -p logs/checkpoints

cat > logs/checkpoints/TEST_001_checkpoint.json <<EOF
{
  "work_number": "TEST",
  "volume": "001",
  "total_chapters": 10,
  "completed_chapters": 3,
  "current_chapter": {
    "chapter_id": "chapter_0004",
    "total_blocks": 100,
    "completed_blocks": 45
  },
  "chapter_progress": []
}
EOF
```

### Test the API Endpoint

```bash
# Start the backend
cd web_ui/translation_manager/backend
python app.py

# In another terminal, test the endpoint
curl http://localhost:8001/api/progress/TEST?volume=001
```

Expected response:
```json
{
  "current_volume": "001",
  "current_chapter": "chapter_0004",
  "total_chapters": 10,
  "completed_chapters": 3,
  "total_blocks": 0,
  "completed_blocks": 0,
  "current_chapter_blocks": 100,
  "current_chapter_completed": 45
}
```

### Test the Frontend Component

```jsx
// Create a test page
import { ProgressBar } from '../components/ProgressBar';

function TestPage() {
  return (
    <div style={{ padding: '20px' }}>
      <h2>Progress Bar Test</h2>

      {/* Test different percentages */}
      <ProgressBar current={15} total={100} label="15% - Red" />
      <ProgressBar current={45} total={100} label="45% - Orange" />
      <ProgressBar current={75} total={100} label="75% - Blue" />
      <ProgressBar current={100} total={100} label="100% - Green" />

      {/* Test animated */}
      <ProgressBar
        current={50}
        total={100}
        label="Animated"
        animated={true}
      />
    </div>
  );
}
```

## Common Patterns

### Pattern 1: Show Progress in Job List

```jsx
{jobs.map(job => (
  <div key={job.job_id} className="job-card">
    <div className="job-header">
      <span>{job.job_id}</span>
      <ProgressBadge percentage={job.progress} />
    </div>
    <ProgressBar
      current={job.progress}
      total={100}
      showFraction={false}
      animated={job.status === 'running'}
    />
  </div>
))}
```

### Pattern 2: Show Detailed Progress on Click

```jsx
function JobDetails({ job }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    if (job.status === 'running') {
      const interval = setInterval(async () => {
        const data = await jobsAPI.getDetailedProgress(job.job_id);
        setProgress(data);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [job.job_id, job.status]);

  return (
    <div>
      <MultiLevelProgress
        detailedProgress={progress}
        workProgress={job.progress}
      />

      {progress && (
        <div className="stats">
          <p>Chapters: {progress.completed_chapters}/{progress.total_chapters}</p>
          <p>Blocks: {progress.completed_blocks}/{progress.total_blocks}</p>
        </div>
      )}
    </div>
  );
}
```

### Pattern 3: WebSocket Real-Time Updates

```jsx
import { JobWebSocket } from '../api/client';

function JobMonitor({ job }) {
  const [progress, setProgress] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    // Setup WebSocket
    wsRef.current = new JobWebSocket((message) => {
      if (message.type === 'progress_update' && message.job_id === job.job_id) {
        setProgress(message.detailed_progress);
      }
    });
    wsRef.current.connect();

    return () => wsRef.current?.disconnect();
  }, [job.job_id]);

  return (
    <MultiLevelProgress
      detailedProgress={progress}
      workProgress={job.progress}
    />
  );
}
```

## Customization

### Custom Colors

```jsx
// Modify ProgressBar component
function ProgressBar({ current, total, customColors }) {
  const percentage = (current / total) * 100;

  const getColor = () => {
    if (customColors) {
      if (percentage === 100) return customColors.complete;
      if (percentage >= 67) return customColors.almostDone;
      if (percentage >= 34) return customColors.inProgress;
      return customColors.started;
    }
    // Default colors...
  };

  // ...
}

// Usage
<ProgressBar
  current={50}
  total={100}
  customColors={{
    complete: '#2ecc71',
    almostDone: '#3498db',
    inProgress: '#f39c12',
    started: '#e74c3c'
  }}
/>
```

### Custom Thresholds

```jsx
function ProgressBar({ current, total, thresholds = [33, 67, 100] }) {
  const percentage = (current / total) * 100;

  const getColor = () => {
    if (percentage >= thresholds[2]) return '#27ae60'; // Green
    if (percentage >= thresholds[1]) return '#3498db'; // Blue
    if (percentage >= thresholds[0]) return '#f39c12'; // Orange
    return '#e74c3c'; // Red
  };

  // ...
}

// Usage - More granular thresholds
<ProgressBar
  current={50}
  total={100}
  thresholds={[25, 50, 75, 100]}
/>
```

### Custom Labels

```jsx
function ProgressBar({ current, total, labelFormatter }) {
  const percentage = (current / total) * 100;

  const defaultLabel = `${percentage.toFixed(1)}% (${current}/${total})`;
  const label = labelFormatter
    ? labelFormatter(current, total, percentage)
    : defaultLabel;

  return (
    <div className="progress-bar">
      <div className="progress-fill" style={{ width: `${percentage}%` }}>
        {label}
      </div>
    </div>
  );
}

// Usage
<ProgressBar
  current={1500}
  total={7230}
  labelFormatter={(current, total, pct) =>
    `${pct.toFixed(0)}% • ${current.toLocaleString()} blocks`
  }
/>
```

## Troubleshooting

### Progress Not Updating

**Check**: Is checkpoint file being created?
```bash
ls -la logs/checkpoints/
```

**Check**: Is WebSocket connected?
```javascript
// In browser console
console.log(wsRef.current?.ws?.readyState);
// 1 = OPEN, 0 = CONNECTING, 2 = CLOSING, 3 = CLOSED
```

**Check**: Is polling interval running?
```javascript
// In browser console
console.log('Polling active:', progressPollRef.current !== null);
```

### Colors Not Showing

**Check**: Are percentages calculated correctly?
```javascript
console.log('Percentage:', (current / total) * 100);
```

**Check**: Is CSS animation defined?
```css
/* Should be in index.css */
@keyframes progress-bar-stripes {
  /* ... */
}
```

### WebSocket Disconnects

**Check**: Backend WebSocket endpoint
```bash
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:8001/ws
```

**Check**: Reconnection logic
```javascript
// JobWebSocket class handles reconnection automatically
// Max 5 attempts, 3 seconds between attempts
```

## Performance Tips

1. **Debounce updates**: Don't update state on every WebSocket message
   ```javascript
   const debouncedUpdate = useCallback(
     debounce((progress) => setProgress(progress), 500),
     []
   );
   ```

2. **Memoize progress components**: Avoid unnecessary re-renders
   ```javascript
   const MemoizedProgress = React.memo(MultiLevelProgress);
   ```

3. **Lazy load progress**: Only fetch when job is visible
   ```javascript
   const { ref, inView } = useInView({ threshold: 0.1 });

   useEffect(() => {
     if (inView && job.status === 'running') {
       loadProgress();
     }
   }, [inView, job.status]);
   ```

4. **Batch updates**: Combine multiple state updates
   ```javascript
   setJobState(prev => ({
     ...prev,
     progress: message.progress,
     detailedProgress: message.detailed_progress
   }));
   ```

## Next Steps

1. **Customize colors** to match your brand
2. **Add notifications** on milestones (25%, 50%, 75%, 100%)
3. **Calculate ETA** using historical translation speed
4. **Export progress** reports for analysis
5. **Add progress history** graph for trend visualization

## Resources

- Full documentation: `/PROGRESS_TRACKING.md`
- Visual guide: `/docs/PROGRESS_UI_GUIDE.md`
- Implementation summary: `/PROGRESS_IMPLEMENTATION_SUMMARY.md`
- Component source: `/frontend/src/components/ProgressBar.jsx`
- API source: `/backend/app.py` (search for `DetailedProgress`)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review browser console for errors
3. Check backend logs for exceptions
4. Verify checkpoint files are being created
5. Test with the example checkpoint file provided

Happy tracking!
