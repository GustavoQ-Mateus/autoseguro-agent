CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    sender_role TEXT NOT NULL,
    message_type TEXT NOT NULL,
    body TEXT NOT NULL,
    response_body TEXT,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id);

CREATE TABLE IF NOT EXISTS conversation_state (
    conversation_id TEXT PRIMARY KEY,
    slots TEXT NOT NULL,
    stagnation_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'em_andamento',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quote_attempts (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,
    motivo TEXT,
    http_status INTEGER,
    latencia_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quote_attempts_conversation ON quote_attempts (conversation_id);

CREATE TABLE IF NOT EXISTS escalations (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    motivo TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_escalations_conversation ON escalations (conversation_id);
