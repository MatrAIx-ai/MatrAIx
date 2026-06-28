CREATE TABLE IF NOT EXISTS mute (
    mute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    muter_id INTEGER NOT NULL,
    mutee_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(muter_id, mutee_id),
    FOREIGN KEY (muter_id) REFERENCES user(user_id),
    FOREIGN KEY (mutee_id) REFERENCES user(user_id)
);
