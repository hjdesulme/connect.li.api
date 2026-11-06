import json
import sqlite3
from pathlib import Path
from src.db.seed import seed_db


def test_seed_database(tmp_path: Path):
    # Setup paths in temporary directory
    db_path = tmp_path / "test.db"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    schema_path = Path("src/db/schema.sql")

    # 1. Mock topics.json
    topics = [
        {"id": 1, "slug": "leadership", "label": "Leadership", "domain": "content"},
        {
            "id": 2,
            "slug": "public-speaking",
            "label": "Public Speaking",
            "domain": "content",
        },
    ]
    with open(data_dir / "topics.json", "w") as f:
        json.dump(topics, f)

    # 2. Mock users.json
    users = [
        {
            "id": 42,
            "first_name": "Test",
            "last_name": "User",
            "industry": "Tech",
            "topic_interests": ["leadership", "invalid-topic"],
        }
    ]
    with open(data_dir / "users.json", "w") as f:
        json.dump(users, f)

    # 3. Mock circles.json
    circles = [
        {
            "id": 1,
            "name": "Women Who Lead",
            "access": "public",
            "join_policy": "open",
            "topic": "leadership",
            "tags": ["public-speaking", "unrecognized-tag"],
            "feed_posts_30d": 10,
            "chat_messages_30d": 5,
        }
    ]
    with open(data_dir / "circles.json", "w") as f:
        json.dump(circles, f)

    # 4. Mock memberships.json
    memberships = [{"user_id": 42, "circle_id": 1, "role": "member"}]
    with open(data_dir / "memberships.json", "w") as f:
        json.dump(memberships, f)

    # Run the ETL script
    seed_db(db_path=db_path, data_dir=data_dir, schema_path=schema_path)

    # Verify the results in the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verify Topics
    cursor.execute("SELECT * FROM topics")
    db_topics = cursor.fetchall()
    assert len(db_topics) == 2
    assert db_topics[0]["slug"] == "leadership"

    # Verify Users
    cursor.execute("SELECT * FROM users")
    db_users = cursor.fetchall()
    assert len(db_users) == 1
    assert db_users[0]["id"] == 42
    assert db_users[0]["industry"] == "Tech"

    # Verify User Topics
    cursor.execute("SELECT topic_slug FROM user_topics WHERE user_id = 42")
    db_user_topics = cursor.fetchall()
    user_topic_slugs = [r["topic_slug"] for r in db_user_topics]
    assert "leadership" in user_topic_slugs

    # Verify Circles (member_count should be exactly 1 via our SQLite trigger)
    cursor.execute("SELECT * FROM circles WHERE id = 1")
    db_circle = cursor.fetchone()
    assert db_circle is not None
    assert db_circle["member_count"] == 1
    assert db_circle["feed_posts_30d"] == 10

    # Verify Circle Topics Normalization
    cursor.execute("SELECT topic_slug FROM circle_topics WHERE circle_id = 1")
    db_circle_topics = cursor.fetchall()
    circle_topic_slugs = {r["topic_slug"] for r in db_circle_topics}

    # "leadership" (from topic), "public-speaking" (from tags) -> both valid
    # "unrecognized-tag" -> invalid taxonomy, should be filtered out safely
    assert "leadership" in circle_topic_slugs
    assert "public-speaking" in circle_topic_slugs
    assert "unrecognized-tag" not in circle_topic_slugs
    assert len(circle_topic_slugs) == 2

    conn.close()
