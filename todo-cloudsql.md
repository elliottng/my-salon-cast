# MySalonCast Cloud SQL Migration Plan

## Overview
Migrate MySalonCast from SQLite to Cloud SQL PostgreSQL for reliable task persistence. Complete infrastructure replacement - no fallbacks. Fresh start with no data migration needed.

## Phase 1: Infrastructure Setup (Human - Windsurf IDE)

### 1.1 Create Cloud SQL Instance

```bash
# Set variables
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-west1"
export DB_INSTANCE_NAME="mysaloncast-db"
export DB_NAME="podcast_status"
export DB_USER="podcast_user"
export DB_PASSWORD=$(openssl rand -base64 32)

echo "Database password: $DB_PASSWORD" > db_password.txt

# Create PostgreSQL instance
gcloud sql instances create $DB_INSTANCE_NAME \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-type=SSD \
  --storage-size=10GB

# Create database and user
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE_NAME
gcloud sql users create $DB_USER --instance=$DB_INSTANCE_NAME --password=$DB_PASSWORD

# Enable automatic backups
gcloud sql instances patch $DB_INSTANCE_NAME \
  --backup-start-time=02:00 \
  --retained-backups-count=7 \
  --retained-transaction-log-days=7
```

### 1.2 Service Account and Permissions

```bash
# Create service account
gcloud iam service-accounts create mysaloncast-service \
  --display-name="MySalonCast Application"

export SERVICE_ACCOUNT_EMAIL="mysaloncast-service@$PROJECT_ID.iam.gserviceaccount.com"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"

# Generate credentials
gcloud iam service-accounts keys create ./gcp-credentials.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL
```

### 1.3 Storage Buckets

```bash
export AUDIO_BUCKET="$PROJECT_ID-mysaloncast-audio"

gsutil mb gs://$AUDIO_BUCKET
gsutil iam ch allUsers:objectViewer gs://$AUDIO_BUCKET
```

### 1.4 Cloud SQL Proxy Setup (for Local Docker Development)

```bash
# Download Cloud SQL Proxy for Docker
mkdir -p cloud-sql-proxy
cd cloud-sql-proxy

# Create Dockerfile for Cloud SQL Proxy
cat > Dockerfile << EOF
FROM gcr.io/cloud-sql-connectors/cloud-sql-proxy:latest
CMD ["/cloud-sql-proxy", "--address", "0.0.0.0", "--port", "5432", "$PROJECT_ID:$REGION:$DB_INSTANCE_NAME"]
EOF

# Build proxy image
docker build -t mysaloncast-sql-proxy .
cd ..
```

### 1.5 Create Environment Files

```bash
# For Cloud deployment
CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME"

cat > .env.cloud << EOF
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@/$DB_NAME?host=/cloudsql/$CONNECTION_NAME
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
PROJECT_ID=$PROJECT_ID
AUDIO_BUCKET=$AUDIO_BUCKET
GEMINI_API_KEY=your-actual-gemini-api-key-here
ENVIRONMENT=staging
EOF

# For local Docker development
cat > .env.local << EOF
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@cloud-sql-proxy:5432/$DB_NAME
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
PROJECT_ID=$PROJECT_ID
AUDIO_BUCKET=$AUDIO_BUCKET
GEMINI_API_KEY=your-actual-gemini-api-key-here
ENVIRONMENT=local
EOF
```

### 1.6 Update Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  cloud-sql-proxy:
    image: mysaloncast-sql-proxy
    volumes:
      - ./gcp-credentials.json:/config/gcp-credentials.json
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/config/gcp-credentials.json
    ports:
      - "5432:5432"
    networks:
      - mysaloncast-network

  app:
    build: .
    depends_on:
      - cloud-sql-proxy
    volumes:
      - ./gcp-credentials.json:/app/gcp-credentials.json
    env_file:
      - .env.local
    ports:
      - "8000:8000"
    networks:
      - mysaloncast-network

networks:
  mysaloncast-network:
    driver: bridge
```

### 1.7 Update Cloud Run Timeout

```bash
# If service exists
gcloud run services update mysaloncast-api --timeout=3600 --region=$REGION
```

### Phase 1 Checklist
- [x] Cloud SQL instance running with automatic backups
- [x] Database and user created
- [x] Service account with permissions created
- [x] `gcp-credentials.json` generated
- [x] Audio bucket created with public read
- [x] Cloud SQL Proxy Docker image built
- [x] `.env.cloud` and `.env.local` files created
- [x] `docker-compose.yml` updated
- [x] Gemini API key added to environment files
- [x] Cloud Run timeout updated

---

## Phase 2: Code Implementation (Codex Autonomous Agent)

### Required Files from Phase 1
- [ ] `gcp-credentials.json`
- [ ] `.env.local` for Docker development
- [ ] `.env.cloud` for cloud deployment
- [ ] Current MySalonCast codebase access

### 2.1 Dependencies Update

**Using UV dependency manager:**
- [ ] Run `uv add psycopg2-binary>=2.9.0`
- [ ] Run `uv add alembic>=1.13.0` (for future schema management)
- [ ] Verify dependencies in `pyproject.toml`

### 2.2 Database Configuration

**File: `app/database.py`**
- [ ] Replace SQLite logic with PostgreSQL
- [ ] Update `get_database_path()` to use `DATABASE_URL` environment variable
- [ ] Configure connection pooling based on environment:
  ```python
  if config.is_cloud_environment:
      # Cloud Run optimized settings
      engine = create_engine(
          DATABASE_URL,
          pool_size=1,
          max_overflow=0,
          pool_pre_ping=True,
          pool_recycle=300,
          connect_args={
              "connect_timeout": 10,
              "application_name": "mysaloncast",
          }
      )
  else:
      # Local development settings
      engine = create_engine(
          DATABASE_URL,
          pool_size=5,
          max_overflow=10,
          pool_pre_ping=True,
          pool_recycle=3600
      )
  ```
- [ ] Remove all `/tmp/` path references
- [ ] **Remove all backup-related code**:
  - Delete `get_storage_client()` function
  - Delete `download_database_backup()` function  
  - Delete `upload_database_backup()` function
  - Delete `cleanup_old_backups()` function
  - Remove backup logic from `init_db()`
  - Delete `DatabaseSession` class with auto_backup
  - Delete `get_session_with_backup()` function
  - Remove `DATABASE_BUCKET` references

**File: `app/config.py`**
- [ ] Update database configuration to load `DATABASE_URL`
- [ ] Remove SQLite-specific path logic
- [ ] Add PostgreSQL connection validation
- [ ] Remove `database_bucket` property
- [ ] Remove DATABASE_BUCKET from validation checks

### 2.3 Environment Handling

**File: `app/config.py`**
- [ ] Load `DATABASE_URL` from environment
- [ ] Validate required Cloud SQL environment variables
- [ ] Remove local database path generation
- [ ] Add logic to detect Docker vs Cloud Run environment

### 2.4 Error Handling

**All database modules:**
- [ ] Add PostgreSQL-specific error handling
- [ ] Handle connection pool exhaustion
- [ ] Handle Cloud SQL connection timeouts
- [ ] Replace SQLite error handling

### 2.5 Cloud Run Configuration

**Deployment files:**
- [ ] Set timeout to `3600s`
- [ ] Ensure `DATABASE_URL` in environment variables
- [ ] Ensure `GOOGLE_APPLICATION_CREDENTIALS` path correct
- [ ] Use Cloud SQL connection name for production and add `--add-cloudsql-instances=$PROJECT_ID:$REGION:$DB_INSTANCE_NAME` flag

### 2.6 Testing

**Required Tests:**
- [ ] Database connection with PostgreSQL works
- [ ] Task creation/update/retrieval with Cloud SQL
- [ ] Full podcast generation end-to-end
- [ ] Audio upload to Cloud Storage (no database backups)
- [ ] Container restart simulation (disconnect/reconnect DB)
- [ ] Concurrent database access
- [ ] Connection pool behavior under load

### 2.7 Code Changes Checklist

**Core Files to Modify:**
- [ ] `app/database.py` - PostgreSQL connection and remove backup code
- [ ] `app/config.py` - Environment variable handling, remove database_bucket
- [ ] `app/status_manager.py` - Verify no local file dependencies
- [ ] `pyproject.toml` - PostgreSQL dependencies via UV
- [ ] Deployment configuration - Update timeout and env vars

**Remove/Replace:**
- [ ] All SQLite file path logic
- [ ] `/tmp/` directory references
- [ ] **All database backup/restore functions**
- [ ] `get_database_path()` function logic
- [ ] DATABASE_BUCKET environment variable usage

### 2.8 Validation Checklist

- [ ] Application connects to Cloud SQL successfully
- [ ] Database schema created correctly
- [ ] Task CRUD operations work with PostgreSQL
- [ ] Audio files upload to Cloud Storage (only)
- [ ] End-to-end podcast generation completes
- [ ] Data persists after simulated app restart
- [ ] All tests pass with new configuration
- [ ] No references to SQLite or local files remain
- [ ] **No database backup code remains**

### Success Criteria
- [ ] Task status survives container restarts
- [ ] Audio files accessible via persistent URLs
- [ ] Multiple containers can access shared database
- [ ] Full podcast workflow works end-to-end
- [ ] No SQLite dependencies remain in codebase
- [ ] **Cloud SQL automatic backups handle data protection**