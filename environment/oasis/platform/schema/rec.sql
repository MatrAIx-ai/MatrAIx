CREATE TABLE IF NOT EXISTS rec (
    user_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    UNIQUE(user_id, post_id)
);
