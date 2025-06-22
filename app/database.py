"""Database models and setup for podcast status persistence."""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Any
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import Column, DateTime, func

from .config import get_config

# Database models using SQLModel
class PodcastStatusDB(SQLModel, table=True):
    """Database model for storing podcast generation status."""

    __tablename__ = "podcast_status"

    task_id: str = Field(primary_key=True, description="Unique task identifier")
    status: str = Field(description="Current status of the task")
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")
    status_description: str = Field(default="", description="Human-readable status description")

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=False), server_default=func.now()),
        description="When the task was created",
    )
    last_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now()),
        description="Last update timestamp",
    )

    request_data: str = Field(description="JSON-serialized PodcastRequest")
    result_episode: Optional[str] = Field(default=None, description="JSON-serialized PodcastEpisode")

    error_message: Optional[str] = Field(default=None, description="User-friendly error message")
    error_details: Optional[str] = Field(default=None, description="Technical error details")

    artifacts: str = Field(default="{}", description="JSON-serialized artifact availability")
    logs: str = Field(default="[]", description="JSON-serialized list of log entries")


config = get_config()
DATABASE_URL = config.database_url

# Configure SQLAlchemy engine with environment-aware pooling
if config.is_cloud_environment:
    engine = create_engine(
        DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 10, "application_name": "mysaloncast"},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


def init_db() -> None:
    """Create tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a database session."""
    return Session(engine)


# Helper functions for JSON serialization

def serialize_to_json(data: Any) -> str:
    if hasattr(data, "dict"):
        data = data.dict()
    return json.dumps(data, default=str)


def deserialize_from_json(json_str: str) -> Any:
    return json.loads(json_str) if json_str else None
