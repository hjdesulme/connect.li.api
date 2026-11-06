CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    industry TEXT,
    location TEXT,
    joined_at DATETIME
);

CREATE TABLE IF NOT EXISTS circles (
    id INTEGER PRIMARY KEY,
    name TEXT,
    slug TEXT,
    description TEXT,
    format TEXT,
    access TEXT NOT NULL,
    join_policy TEXT NOT NULL,
    max_members INTEGER,
    member_count INTEGER NOT NULL DEFAULT 0,
    last_activity_at DATETIME,
    feed_posts_30d INTEGER NOT NULL DEFAULT 0,
    chat_messages_30d INTEGER NOT NULL DEFAULT 0,
    engagement_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS topics (
    slug TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    domain TEXT
);

CREATE TABLE IF NOT EXISTS user_topics (
    user_id INTEGER NOT NULL,
    topic_slug TEXT NOT NULL,
    PRIMARY KEY (user_id, topic_slug),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (topic_slug) REFERENCES topics (slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS circle_topics (
    circle_id INTEGER NOT NULL,
    topic_slug TEXT NOT NULL,
    PRIMARY KEY (circle_id, topic_slug),
    FOREIGN KEY (circle_id) REFERENCES circles (id) ON DELETE CASCADE,
    FOREIGN KEY (topic_slug) REFERENCES topics (slug) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memberships (
    user_id INTEGER NOT NULL,
    circle_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (user_id, circle_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (circle_id) REFERENCES circles (id) ON DELETE CASCADE
);

-- Triggers for keeping member_count synced automatically

CREATE TRIGGER IF NOT EXISTS trg_increment_member_count
AFTER INSERT ON memberships
FOR EACH ROW
BEGIN
    UPDATE circles 
    SET member_count = member_count + 1 
    WHERE id = NEW.circle_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_decrement_member_count
AFTER DELETE ON memberships
FOR EACH ROW
BEGIN
    UPDATE circles 
    SET member_count = member_count - 1 
    WHERE id = OLD.circle_id;
END;
