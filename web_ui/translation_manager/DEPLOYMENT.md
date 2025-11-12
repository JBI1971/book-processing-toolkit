# Translation Manager - Deployment Guide

Production deployment guide for the Translation Management Interface.

## Overview

This guide covers deployment options for the Translation Manager in production environments.

⚠️ **Important**: This tool is designed for internal use. Do not expose to public internet without proper security measures.

## Deployment Options

### Option 1: Local Development (Current Setup)

**Use Case**: Single user, development/testing
**Pros**: Easy setup, no infrastructure required
**Cons**: Only accessible from local machine

Already configured and ready to use:
```bash
./start.sh
```

### Option 2: Internal Network Deployment

**Use Case**: Multiple users on same network
**Pros**: Accessible to team members, simple setup
**Cons**: Limited to local network

#### Setup

1. **Update Backend to Accept External Connections**

```python
# backend/app.py - Change uvicorn.run:
if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", "8001"))
    uvicorn.run(
        app,
        host="0.0.0.0",  # Changed from localhost
        port=port,
        log_level="info"
    )
```

2. **Update CORS to Allow Network Access**

```python
# backend/app.py - Add your network IP range:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://192.168.1.*",  # Your network range
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Configure Frontend to Use Server IP**

```bash
# frontend/.env
VITE_API_BASE_URL=http://192.168.1.100:8001  # Your server IP
```

4. **Start and Access**

```bash
# On server
./start.sh

# Access from any computer on network
http://192.168.1.100:5174  # Frontend
http://192.168.1.100:8001  # Backend
```

### Option 3: Docker Deployment

**Use Case**: Isolated environment, easy deployment
**Pros**: Consistent environment, easy updates
**Cons**: Requires Docker knowledge

#### Dockerfile for Backend

```dockerfile
# backend/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8001

# Run application
CMD ["python", "app.py"]
```

#### Dockerfile for Frontend

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json .
RUN npm ci

# Build application
COPY . .
RUN npm run build

# Production image
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - CATALOG_DB_PATH=/data/wuxia_catalog.db
      - SOURCE_DIR=/data/wuxia_individual_files
      - OUTPUT_DIR=/data/translations
    volumes:
      - /Users/jacki/project_files/translation_project:/data
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

**Usage:**
```bash
docker-compose up -d
```

### Option 4: Production Server Deployment

**Use Case**: Production environment with monitoring
**Pros**: Scalable, reliable, monitored
**Cons**: Complex setup, requires server management

#### Using Nginx + Gunicorn/Uvicorn

**1. Install System Dependencies**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-venv nginx nodejs npm
```

**2. Setup Backend with Systemd**

```ini
# /etc/systemd/system/translation-backend.service
[Unit]
Description=Translation Manager Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/translation_manager/backend
Environment="PATH=/opt/translation_manager/backend/venv/bin"
ExecStart=/opt/translation_manager/backend/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable translation-backend
sudo systemctl start translation-backend
sudo systemctl status translation-backend
```

**3. Setup Frontend with Nginx**

```nginx
# /etc/nginx/sites-available/translation-manager
server {
    listen 80;
    server_name translation.yourdomain.com;

    # Frontend
    location / {
        root /opt/translation_manager/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/translation-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**4. Build Frontend**

```bash
cd /opt/translation_manager/frontend
npm install
npm run build
```

## Security Considerations

### Authentication

Add user authentication before deploying to production:

```python
# Example: Basic authentication
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("ADMIN_USERNAME", "admin")
    correct_password = os.getenv("ADMIN_PASSWORD", "changeme")

    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Apply to all endpoints
@app.get("/api/works", dependencies=[Depends(authenticate)])
async def list_works(...):
    ...
```

### HTTPS/SSL

Use Let's Encrypt for free SSL certificates:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d translation.yourdomain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

### Environment Variables

Never commit sensitive data. Use environment variables:

```bash
# /opt/translation_manager/backend/.env
CATALOG_DB_PATH=/data/wuxia_catalog.db
SOURCE_DIR=/data/wuxia_individual_files
OUTPUT_DIR=/data/translations
OPENAI_API_KEY=sk-...
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password_here
```

Set proper permissions:
```bash
chmod 600 /opt/translation_manager/backend/.env
chown ubuntu:ubuntu /opt/translation_manager/backend/.env
```

### Firewall Rules

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Block direct access to backend
sudo ufw deny 8001/tcp
```

## Monitoring

### Log Management

```bash
# Backend logs
journalctl -u translation-backend -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Application logs
tail -f /opt/translation_manager/logs/backend.log
```

### Process Monitoring

```bash
# Check backend status
systemctl status translation-backend

# Check Nginx status
systemctl status nginx

# Check resource usage
htop
```

### Automated Monitoring (Optional)

Use tools like:
- **Prometheus + Grafana**: Metrics and dashboards
- **ELK Stack**: Log aggregation and search
- **Uptime Robot**: Uptime monitoring
- **Sentry**: Error tracking

## Backup

### Critical Data to Backup

1. **Catalog Database**
```bash
# Backup catalog
cp /path/to/wuxia_catalog.db /backup/wuxia_catalog_$(date +%Y%m%d).db

# Automated daily backup
echo "0 2 * * * cp /path/to/wuxia_catalog.db /backup/wuxia_catalog_\$(date +\%Y\%m\%d).db" | crontab -
```

2. **Configuration Files**
```bash
tar -czf /backup/config_$(date +%Y%m%d).tar.gz \
    /opt/translation_manager/backend/.env \
    /etc/nginx/sites-available/translation-manager \
    /etc/systemd/system/translation-backend.service
```

3. **Translation Outputs**
```bash
rsync -av --progress /path/to/translations/ /backup/translations/
```

## Scaling

### Horizontal Scaling

Run multiple backend instances:

```bash
# Start multiple workers
# backend1.service on port 8001
# backend2.service on port 8002
# backend3.service on port 8003

# Nginx load balancing
upstream translation_backend {
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

location /api {
    proxy_pass http://translation_backend;
}
```

### Database Optimization

For large catalogs (1000+ works):

```sql
-- Add indexes for faster queries
CREATE INDEX idx_work_number ON works(work_number);
CREATE INDEX idx_title_chinese ON works(title_chinese);
CREATE INDEX idx_author_chinese ON works(author_chinese);
```

## Updates and Maintenance

### Updating the Application

```bash
# Pull latest code
cd /opt/translation_manager
git pull

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart translation-backend

# Update frontend
cd ../frontend
npm install
npm run build
sudo systemctl reload nginx
```

### Database Migrations

```bash
# Backup first
cp /path/to/wuxia_catalog.db /backup/before_migration.db

# Apply migrations
sqlite3 /path/to/wuxia_catalog.db < migrations/001_add_indexes.sql
```

## Troubleshooting Production Issues

### Backend Not Responding

```bash
# Check if service is running
systemctl status translation-backend

# Check logs
journalctl -u translation-backend -n 100 --no-pager

# Restart service
sudo systemctl restart translation-backend
```

### High Memory Usage

```bash
# Check memory usage
free -h

# Check process memory
ps aux | grep python | sort -nrk 4 | head

# Restart backend to clear memory
sudo systemctl restart translation-backend
```

### WebSocket Connection Issues

```bash
# Check Nginx WebSocket configuration
sudo nginx -t

# Check firewall rules
sudo ufw status

# Test WebSocket directly
wscat -c ws://localhost:8001/ws
```

## Performance Tuning

### Backend Optimization

```python
# Increase uvicorn workers
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8001,
    workers=4,  # CPU cores
    log_level="info"
)
```

### Frontend Optimization

```bash
# Build with production optimizations
npm run build

# Serve with compression
# In nginx config:
gzip on;
gzip_types text/css application/javascript application/json;
```

### Database Optimization

```bash
# Vacuum database
sqlite3 /path/to/wuxia_catalog.db "VACUUM;"

# Analyze for query optimization
sqlite3 /path/to/wuxia_catalog.db "ANALYZE;"
```

## Cost Estimation

### OpenAI API Costs

Approximate costs based on GPT-4o-mini:
- **Input**: $0.15 per 1M tokens
- **Output**: $0.60 per 1M tokens

Example translation costs:
- Small work (50k tokens): ~$0.04
- Medium work (200k tokens): ~$0.15
- Large work (500k tokens): ~$0.38

Monitor usage:
```python
# Track in job statistics
total_tokens = job.statistics.get('total_tokens', 0)
estimated_cost = (total_tokens * 0.00015) / 1000
print(f"Estimated cost: ${estimated_cost:.2f}")
```

## Support and Maintenance

Regular maintenance tasks:

- **Daily**: Check logs for errors
- **Weekly**: Review job success rates, backup database
- **Monthly**: Update dependencies, review disk usage
- **Quarterly**: Update SSL certificates, security audit

---

For questions or issues with deployment, consult:
- README.md for application details
- SETUP.md for installation steps
- Project CLAUDE.md for pipeline details
