CREATE TABLE IF NOT EXISTS comment_like (
    comment_like_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    comment_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, comment_id)
);
