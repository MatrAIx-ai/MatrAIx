CREATE TABLE IF NOT EXISTS trace (
    trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    info TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);
