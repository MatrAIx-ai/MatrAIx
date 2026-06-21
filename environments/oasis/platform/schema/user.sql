CREATE TABLE IF NOT EXISTS user (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER UNIQUE NOT NULL,
    user_name TEXT NOT NULL,
    name TEXT NOT NULL,
    bio TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    num_followings INTEGER DEFAULT 0,
    num_followers INTEGER DEFAULT 0
);
