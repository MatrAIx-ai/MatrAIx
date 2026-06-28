CREATE TABLE IF NOT EXISTS follow (
    follow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id INTEGER NOT NULL,
    followee_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(follower_id, followee_id),
    FOREIGN KEY (follower_id) REFERENCES user(user_id),
    FOREIGN KEY (followee_id) REFERENCES user(user_id)
);
