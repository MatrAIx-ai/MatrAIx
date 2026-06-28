CREATE TABLE IF NOT EXISTS group_members (
    group_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    joined_at TEXT NOT NULL,
    UNIQUE(group_id, agent_id)
);
