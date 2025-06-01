"""Database models and setup for podcast status persistence."""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import Column, DateTime, func

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


# Database connection setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///podcast_status.db")
engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Get a database session."""
    return Session(engine)

# Helper functions for JSON serialization
def serialize_to_json(data: Any) -> str:
    """Serialize Python object to JSON string."""
    if hasattr(data, 'dict'):
        data = data.dict()
    return json.dumps(data, default=str)

def deserialize_from_json(json_str: str) -> Any:
    """Deserialize JSON string to Python object."""
    return json.loads(json_str) if json_str else None
