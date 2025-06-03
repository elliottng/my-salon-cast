"""Database models and setup for podcast status persistence."""

import os
import json
import shutil
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import Column, DateTime, func

# Import Google Cloud Storage client (optional for local development)
try:
    from google.cloud import storage
    CLOUD_STORAGE_AVAILABLE = True
except ImportError:
    CLOUD_STORAGE_AVAILABLE = False
    logging.warning("Google Cloud Storage not available. Running in local mode.")

# Database models using SQLModel
class PodcastStatusDB(SQLModel, table=True):
    """Database model for storing podcast generation status."""
    
    __tablename__ = "podcast_status"
    
    # Primary key
    task_id: str = Field(primary_key=True, description="Unique task identifier")
    
    # Status fields
    status: str = Field(description="Current status of the task")
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")
    status_description: str = Field(default="", description="Human-readable status description")
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=False), server_default=func.now()),
        description="When the task was created"
    )
    last_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now()),
        description="Last update timestamp"
    )
    
    # Request and result data (stored as JSON strings)
    request_data: str = Field(description="JSON-serialized PodcastRequest")
    result_episode: Optional[str] = Field(default=None, description="JSON-serialized PodcastEpisode")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="User-friendly error message")
    error_details: Optional[str] = Field(default=None, description="Technical error details")
    
    # Artifacts tracking (stored as JSON string)
    artifacts: str = Field(default="{}", description="JSON-serialized artifact availability")
    
    # Logs (stored as JSON array)
    logs: str = Field(default="[]", description="JSON-serialized list of log entries")


# Database connection setup with cloud-aware configuration
def get_database_path() -> str:
    """Get the appropriate database path for the environment."""
    environment = os.getenv("ENVIRONMENT", "local")
    
    if environment in ["staging", "production"]:
        # Use a local path in Cloud Run container
        db_dir = "/tmp/database"
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "podcast_status.db")
    else:
        # Local development
        return "podcast_status.db"

DATABASE_PATH = get_database_path()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
engine = create_engine(DATABASE_URL, echo=False)

# Cloud Storage backup configuration
PROJECT_ID = os.getenv("PROJECT_ID")
DATABASE_BUCKET = os.getenv("DATABASE_BUCKET")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

def get_storage_client():
    """Get Google Cloud Storage client if available."""
    if not CLOUD_STORAGE_AVAILABLE or not PROJECT_ID:
        return None
    
    try:
        return storage.Client(project=PROJECT_ID)
    except Exception as e:
        logging.warning(f"Failed to initialize Cloud Storage client: {e}")
        return None

def download_database_backup():
    """Download the latest database backup from Cloud Storage."""
    if ENVIRONMENT == "local" or not DATABASE_BUCKET:
        logging.info("Skipping database backup download in local environment")
        return
    
    client = get_storage_client()
    if not client:
        logging.warning("Cloud Storage not available. Starting with empty database.")
        return
    
    try:
        bucket = client.bucket(DATABASE_BUCKET)
        blob_name = f"{ENVIRONMENT}/podcast_status.db"
        blob = bucket.blob(blob_name)
        
        if blob.exists():
            logging.info(f"Downloading database backup from gs://{DATABASE_BUCKET}/{blob_name}")
            blob.download_to_filename(DATABASE_PATH)
            logging.info("Database backup downloaded successfully")
        else:
            logging.info("No existing database backup found. Starting with fresh database.")
    
    except Exception as e:
        logging.error(f"Failed to download database backup: {e}")
        logging.info("Starting with fresh database.")

def upload_database_backup():
    """Upload database backup to Cloud Storage."""
    if ENVIRONMENT == "local" or not DATABASE_BUCKET:
        logging.debug("Skipping database backup upload in local environment")
        return
    
    client = get_storage_client()
    if not client:
        logging.warning("Cloud Storage not available. Cannot backup database.")
        return
    
    try:
        if not os.path.exists(DATABASE_PATH):
            logging.warning("Database file does not exist. Cannot backup.")
            return
        
        bucket = client.bucket(DATABASE_BUCKET)
        blob_name = f"{ENVIRONMENT}/podcast_status.db"
        blob = bucket.blob(blob_name)
        
        # Create a backup with timestamp
        timestamp_blob_name = f"{ENVIRONMENT}/backups/podcast_status_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
        timestamp_blob = bucket.blob(timestamp_blob_name)
        
        # Upload current backup (overwrites)
        blob.upload_from_filename(DATABASE_PATH)
        logging.info(f"Database backed up to gs://{DATABASE_BUCKET}/{blob_name}")
        
        # Upload timestamped backup
        timestamp_blob.upload_from_filename(DATABASE_PATH)
        logging.info(f"Timestamped backup created: gs://{DATABASE_BUCKET}/{timestamp_blob_name}")
        
    except Exception as e:
        logging.error(f"Failed to upload database backup: {e}")

def cleanup_old_backups(days_to_keep: int = 7):
    """Clean up old timestamped backups to save storage costs."""
    if ENVIRONMENT == "local" or not DATABASE_BUCKET:
        return
    
    client = get_storage_client()
    if not client:
        return
    
    try:
        bucket = client.bucket(DATABASE_BUCKET)
        prefix = f"{ENVIRONMENT}/backups/"
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        blobs_to_delete = []
        for blob in bucket.list_blobs(prefix=prefix):
            if blob.time_created < cutoff_date.replace(tzinfo=blob.time_created.tzinfo):
                blobs_to_delete.append(blob)
        
        for blob in blobs_to_delete:
            blob.delete()
            logging.info(f"Deleted old backup: {blob.name}")
            
        if blobs_to_delete:
            logging.info(f"Cleaned up {len(blobs_to_delete)} old backups")
    
    except Exception as e:
        logging.error(f"Failed to cleanup old backups: {e}")

def init_db():
    """Initialize database tables with cloud backup support."""
    # Download latest backup before initializing
    download_database_backup()
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    logging.info("Database initialized successfully")

# Enhanced session management with backup hooks
class DatabaseSession:
    """Context manager for database sessions with automatic backup."""
    
    def __init__(self, auto_backup: bool = False):
        self.session = Session(engine)
        self.auto_backup = auto_backup
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.session.commit()
                if self.auto_backup:
                    upload_database_backup()
            else:
                self.session.rollback()
        finally:
            self.session.close()

def get_session():
    """Get a database session."""
    return Session(engine)

def get_session_with_backup():
    """Get a database session that automatically backs up on successful commit."""
    return DatabaseSession(auto_backup=True)

# Helper functions for JSON serialization
def serialize_to_json(data: Any) -> str:
    """Serialize Python object to JSON string."""
    if hasattr(data, 'dict'):
        data = data.dict()
    return json.dumps(data, default=str)

def deserialize_from_json(json_str: str) -> Any:
    """Deserialize JSON string to Python object."""
    return json.loads(json_str) if json_str else None
