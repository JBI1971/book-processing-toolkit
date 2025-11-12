# Translation Manager - Architecture Documentation

Technical architecture and design decisions for the Translation Management Interface.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Work Catalog │  │  Jobs Page   │  │Configuration │     │
│  │     Page     │  │              │  │     Page     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           │ HTTP/REST          │ WebSocket          │
           ▼                    ▼                    │
┌─────────────────────────────────────────────────────────────┐
│               Backend API (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Endpoints                            │  │
│  │  /api/works          - List/search works             │  │
│  │  /api/jobs           - Create/list/cancel jobs       │  │
│  │  /ws                 - Real-time updates             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Job Processing System                        │  │
│  │  - Async job queue                                    │  │
│  │  - Background worker                                  │  │
│  │  - WebSocket broadcaster                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  SQLite Catalog  │  │Translation Scripts│  │  OpenAI API      │
│  - Works         │  │- translate_work.py│  │  - GPT-4o        │
│  - Volumes       │  │- volume_manager   │  │  - GPT-4o-mini   │
│  - Metadata      │  │- config           │  │  - Translation   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Component Architecture

### Frontend (React)

```
frontend/src/
├── main.jsx                 # Application entry point
├── App.jsx                  # Main app with routing
├── index.css                # Global styles
│
├── pages/                   # Page components
│   ├── WorkListPage.jsx     # Browse and select works
│   ├── JobsPage.jsx         # Monitor translation jobs
│   └── ConfigPage.jsx       # System configuration
│
└── api/                     # Backend communication
    └── client.js            # API client + WebSocket
```

**Data Flow:**

```
User Action → Component State → API Call → Backend
     ↓                              ↓
Component Re-render  ←  WebSocket  ←  Job Updates
```

### Backend (FastAPI)

```
backend/
├── app.py                   # Main application
│   ├── API Endpoints        # REST endpoints
│   ├── WebSocket Handler    # Real-time updates
│   ├── Job Processor        # Background worker
│   └── Database Helpers     # SQLite queries
│
├── requirements.txt         # Python dependencies
└── .env                     # Configuration
```

**Request Flow:**

```
HTTP Request → FastAPI Router → Handler Function
                    ↓
            Database Query / Job Queue
                    ↓
            Response / WebSocket Broadcast
```

## Key Design Decisions

### 1. Technology Stack

**Backend: FastAPI**
- **Why**: Fast, async support, automatic API docs, WebSocket support
- **Alternatives considered**: Flask (no async/WebSocket), Django (too heavy)

**Frontend: React + Vite**
- **Why**: Fast dev experience, component-based, large ecosystem
- **Alternatives considered**: Vue (less familiar), Vanilla JS (too manual)

**Database: SQLite**
- **Why**: Already used in project, simple, no server needed
- **Alternatives considered**: PostgreSQL (overkill), JSON files (slow queries)

**Communication: REST + WebSocket**
- **Why**: REST for CRUD, WebSocket for real-time updates
- **Alternatives considered**: Server-Sent Events (browser support), polling (inefficient)

### 2. Job Processing Architecture

**Async Queue Pattern:**
```python
# Single queue for all jobs
job_queue = asyncio.Queue()

# Background processor
async def job_processor():
    while True:
        job = await job_queue.get()
        await process_job(job)

# Add jobs from API endpoints
await job_queue.put(job_data)
```

**Why this approach:**
- ✅ Simple to implement
- ✅ No external dependencies (Redis, RabbitMQ)
- ✅ Sufficient for internal use case
- ✅ Easy to extend with multiple workers

**Limitations:**
- ❌ Jobs lost on server restart
- ❌ No persistence between restarts
- ❌ Single process only

**Future improvements:**
- Use Celery + Redis for distributed processing
- Add job persistence with database storage
- Implement job priorities and scheduling

### 3. Real-time Updates

**WebSocket Implementation:**

```javascript
// Frontend: Automatic reconnection
class JobWebSocket {
  connect() {
    this.ws = new WebSocket(url);
    this.ws.onclose = () => {
      if (attempts < max) {
        setTimeout(() => this.connect(), 3000);
      }
    };
  }
}
```

**Backend: Connection Management:**

```python
# Broadcast to all connected clients
async def broadcast(message: dict):
    for connection in active_connections:
        await connection.send_json(message)
```

**Message Types:**
- `job_update`: Status changes (queued → running)
- `job_progress`: Progress percentage updates
- `job_complete`: Job finished (success/failure)

### 4. State Management

**Frontend State:**
- Component-local state with `useState`
- No global state management (Redux, etc.)
- WebSocket updates merge into local state

**Why this approach:**
- ✅ Simple for small application
- ✅ No boilerplate
- ✅ Easy to understand

**When to add global state:**
- Multiple pages need same data
- Complex state transitions
- Undo/redo functionality needed

### 5. Error Handling

**Backend Strategy:**

```python
# Try-catch with specific error messages
try:
    result = await process_job(job)
except FileNotFoundError as e:
    return {"error": f"Source file not found: {e}"}
except OpenAIError as e:
    return {"error": f"Translation API error: {e}"}
except Exception as e:
    return {"error": f"Unexpected error: {e}"}
```

**Frontend Strategy:**

```javascript
// Try-catch with user-friendly alerts
try {
  const data = await api.getWorks();
  setWorks(data);
} catch (error) {
  console.error('Failed to load works:', error);
  alert('Failed to load works. Check console for details.');
}
```

**Improvements needed:**
- Add error boundary components
- Show toast notifications instead of alerts
- Implement retry logic for network failures
- Add detailed error logging

### 6. Security Considerations

**Current State:**
- ❌ No authentication
- ❌ No authorization
- ❌ No rate limiting
- ✅ CORS configured
- ✅ Environment variables for secrets

**Why this is acceptable:**
- Designed for internal network use
- Single-user or small team
- No public internet exposure

**Required for production:**
- Add HTTP Basic Auth at minimum
- Use OAuth2 for multi-user
- Implement API rate limiting
- Add request validation
- Use HTTPS/SSL

## Data Models

### Work Summary

```typescript
interface WorkSummary {
  work_number: string;          // e.g., "D55"
  title_chinese: string;         // e.g., "射鵰英雄傳"
  title_english?: string;        // e.g., "The Legend of the Condor Heroes"
  author_chinese: string;        // e.g., "金庸"
  author_english?: string;       // e.g., "Jin Yong"
  total_volumes: number;         // e.g., 4
  translation_status: string;    // "not_started" | "in_progress" | "completed" | "failed"
}
```

### Translation Job

```typescript
interface TranslationJob {
  job_id: string;                // e.g., "job_20250110_143022"
  work_numbers: string[];        // ["D55", "D70"]
  status: string;                // "queued" | "running" | "paused" | "completed" | "failed"
  progress: number;              // 0-100
  current_work?: string;         // Currently processing work
  completed_works: string[];     // Successfully translated
  failed_works: string[];        // Failed to translate
  start_time?: string;           // ISO datetime
  end_time?: string;             // ISO datetime
  error_message?: string;        // If failed
  statistics: {
    total_chapters: number;
    total_blocks: number;
    successful_blocks: number;
    total_tokens: number;
    estimated_cost_usd: number;
  };
}
```

## API Design

### REST Endpoints

**List Works:**
```http
GET /api/works?search=金庸&limit=100
Response: WorkSummary[]
```

**Get Work Details:**
```http
GET /api/works/D55
Response: WorkDetail
```

**Create Job:**
```http
POST /api/jobs
Body: {
  work_numbers: ["D55", "D70"],
  model: "gpt-4o-mini",
  temperature: 0.3,
  max_retries: 3
}
Response: TranslationJob
```

**List Jobs:**
```http
GET /api/jobs
Response: TranslationJob[]
```

**Get Job Status:**
```http
GET /api/jobs/job_20250110_143022
Response: TranslationJob
```

**Cancel Job:**
```http
DELETE /api/jobs/job_20250110_143022
Response: { message: "Job cancelled" }
```

### WebSocket Protocol

**Connection:**
```
ws://localhost:8001/ws
```

**Client → Server:**
```json
"ping"
```

**Server → Client:**
```json
{
  "type": "job_update",
  "job_id": "job_20250110_143022",
  "status": "running",
  "start_time": "2025-01-10T14:30:22"
}

{
  "type": "job_progress",
  "job_id": "job_20250110_143022",
  "current_work": "D55",
  "progress": 45.5,
  "completed": 1,
  "total": 2
}

{
  "type": "job_complete",
  "job_id": "job_20250110_143022",
  "status": "completed",
  "end_time": "2025-01-10T15:45:30"
}
```

## Performance Characteristics

### Frontend

- **Initial Load**: ~500ms (development), ~200ms (production)
- **Page Navigation**: <50ms (client-side routing)
- **API Requests**: 100-500ms (depends on network/database)
- **WebSocket Latency**: <100ms (local network)

### Backend

- **Works List Query**: 50-200ms (100 works)
- **Job Creation**: <100ms
- **Translation Processing**:
  - Small work (1 volume): 5-10 minutes
  - Medium work (4 volumes): 20-40 minutes
  - Large work (10 volumes): 1-2 hours

### Scalability Limits

**Current Architecture:**
- Max concurrent jobs: 1 (sequential processing)
- Max works in catalog: ~1000 (before pagination needed)
- Max concurrent users: ~10 (with single backend)
- WebSocket connections: ~100 (before performance impact)

**Scaling Recommendations:**
- Add pagination for catalogs >1000 works
- Use job queue with multiple workers for concurrent processing
- Add load balancer for multiple backend instances
- Use Redis for WebSocket pub/sub at scale

## Testing Strategy

### Backend Testing

```python
# Unit tests
def test_get_works_from_db():
    works = get_works_from_db(search="金庸")
    assert len(works) > 0
    assert all(w.work_number for w in works)

# Integration tests
async def test_create_job_endpoint():
    response = await client.post("/api/jobs", json={
        "work_numbers": ["TEST001"],
        "model": "gpt-4o-mini"
    })
    assert response.status_code == 200
    assert "job_id" in response.json()
```

### Frontend Testing

```javascript
// Component tests
test('WorkListPage loads works', async () => {
  render(<WorkListPage />);
  await waitFor(() => {
    expect(screen.getByText(/works found/i)).toBeInTheDocument();
  });
});

// Integration tests
test('Creating a job navigates to jobs page', async () => {
  // Select works, create job, verify navigation
});
```

### End-to-End Testing

```bash
# Manual test checklist:
1. Start application
2. Browse works catalog
3. Search for a work
4. Select work and create job
5. Monitor job progress on jobs page
6. Verify WebSocket updates
7. Check output files created
8. Verify job completion status
```

## Monitoring and Observability

### Logging

```python
# Backend structured logging
logger.info(f"Job created", extra={
    "job_id": job_id,
    "work_count": len(work_numbers),
    "model": model
})

logger.error(f"Job failed", extra={
    "job_id": job_id,
    "error": str(e),
    "work_number": current_work
})
```

### Metrics to Track

- Job creation rate (jobs/hour)
- Job success rate (%)
- Average job duration (minutes)
- API error rate (%)
- WebSocket connection count
- Token usage per job
- Cost per translation

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": check_db_connection(),
        "queue_size": job_queue.qsize(),
        "active_jobs": count_running_jobs(),
        "websocket_connections": len(active_connections)
    }
```

## Future Enhancements

### High Priority

1. **Job Persistence**: Store jobs in database to survive restarts
2. **Authentication**: Add user login and access control
3. **Pagination**: Support large catalogs (1000+ works)
4. **Error Recovery**: Retry failed works automatically

### Medium Priority

5. **Preview Results**: View translations before finalizing
6. **Job Scheduling**: Schedule jobs for later execution
7. **Notifications**: Email/Slack alerts on job completion
8. **Batch Operations**: Process multiple jobs concurrently

### Low Priority

9. **Dark Mode**: UI theme toggle
10. **Export Reports**: Download job statistics as CSV
11. **Custom Workflows**: Configure pipeline stages
12. **API Rate Limiting**: Prevent abuse

## References

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **WebSocket Protocol**: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- **OpenAI API**: https://platform.openai.com/docs/api-reference

---

For implementation details, see:
- `backend/app.py` - Backend implementation
- `frontend/src/` - Frontend components
- `README.md` - User documentation
- `DEPLOYMENT.md` - Deployment guide
