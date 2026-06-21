CREATE TABLE IF NOT EXISTS post (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    original_post_id INTEGER DEFAULT NULL,
    quote_content TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    num_likes INTEGER DEFAULT 0,
    num_dislikes INTEGER DEFAULT 0,
    num_shares INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    num_reports INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);
