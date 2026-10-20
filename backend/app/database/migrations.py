from app.database.connection import db
from app.core.logging import logger

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    model TEXT NOT NULL,
    system_prompt TEXT DEFAULT '',
    temperature REAL DEFAULT 0.7,
    context_length INTEGER DEFAULT 8192,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    images_json TEXT DEFAULT '[]',
    tool_calls_json TEXT DEFAULT '[]',
    tool_call_id TEXT DEFAULT NULL,
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tools_log (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    result_json TEXT,
    status TEXT NOT NULL,
    error TEXT,
    execution_time_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coding_tasks (
    id TEXT PRIMARY KEY,
    workspace_path TEXT NOT NULL,
    task_description TEXT NOT NULL,
    status TEXT NOT NULL,
    plan TEXT,
    affected_files_json TEXT DEFAULT '[]',
    diff_content TEXT,
    command_logs_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    steps_json TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    timeout_seconds INTEGER DEFAULT 300,
    max_iterations INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    triggered_by TEXT DEFAULT 'user',
    logs_json TEXT DEFAULT '[]',
    result_json TEXT DEFAULT '{}',
    error TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_history (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    negative_prompt TEXT DEFAULT '',
    model_checkpoint TEXT DEFAULT '',
    seed INTEGER DEFAULT -1,
    width INTEGER DEFAULT 512,
    height INTEGER DEFAULT 512,
    image_filename TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    cwd TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    stdout TEXT,
    stderr TEXT,
    duration_ms INTEGER NOT NULL,
    approved INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_memory (
    workspace_path TEXT PRIMARY KEY,
    instructions TEXT DEFAULT '',
    context_summary TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_memories (
    id TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    content TEXT NOT NULL,
    source_tool TEXT DEFAULT 'custom',
    category TEXT DEFAULT 'general',
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tools_log_conversation ON tools_log(conversation_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
"""

async def run_migrations() -> None:
    logger.info("Initializing database schema and running migrations...")
    await db.executescript(SCHEMA_SQL)
    # Perform column migrations for user_memories
    try:
        await db.execute("ALTER TABLE user_memories ADD COLUMN source_tool TEXT DEFAULT 'custom'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE user_memories ADD COLUMN category TEXT DEFAULT 'general'")
    except Exception:
        pass
    logger.info("Database schema initialized successfully.")
