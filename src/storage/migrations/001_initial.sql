CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    category        TEXT NOT NULL,
    transcript      TEXT NOT NULL,
    summary         TEXT NOT NULL,
    urgency_score   INTEGER DEFAULT 5,
    speaker_count   INTEGER DEFAULT 1,
    audio_duration  REAL,
    raw_audio_path  TEXT,
    telegram_msg_id INTEGER NOT NULL,
    key_topics      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS action_items (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    description     TEXT NOT NULL,
    deadline        TEXT,
    priority        TEXT NOT NULL DEFAULT 'medium',
    assigned_to     TEXT,
    category        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    snoozed_until   TEXT,
    duplicate_of    TEXT REFERENCES action_items(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items(status);
CREATE INDEX IF NOT EXISTS idx_action_items_deadline ON action_items(deadline);
CREATE INDEX IF NOT EXISTS idx_action_items_conversation ON action_items(conversation_id);

CREATE TABLE IF NOT EXISTS calendar_events (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    google_event_id TEXT NOT NULL,
    google_event_link TEXT,
    title           TEXT NOT NULL,
    start_time      TEXT NOT NULL,
    end_time        TEXT,
    category        TEXT NOT NULL,
    calendar_id     TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS commitments (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    description     TEXT NOT NULL,
    made_by         TEXT NOT NULL,
    made_to         TEXT NOT NULL,
    deadline        TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS people (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    mention_count   INTEGER DEFAULT 1,
    role            TEXT,
    category        TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_people_normalized ON people(normalized_name);

CREATE TABLE IF NOT EXISTS person_mentions (
    id              TEXT PRIMARY KEY,
    person_id       TEXT NOT NULL REFERENCES people(id),
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    context         TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    UNIQUE(person_id, conversation_id)
);
CREATE INDEX IF NOT EXISTS idx_mentions_person ON person_mentions(person_id);
CREATE INDEX IF NOT EXISTS idx_mentions_conversation ON person_mentions(conversation_id);
