CREATE TABLE IF NOT EXISTS podcast_status (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0,
    status_description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    request_data TEXT NOT NULL,
    result_episode TEXT,
    error_message TEXT,
    error_details TEXT,
    artifacts TEXT DEFAULT '{}',
    logs TEXT DEFAULT '[]'
);
