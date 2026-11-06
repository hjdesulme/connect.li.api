import json
import sqlite3
from pathlib import Path


def seed_db(db_path: Path, data_dir: Path, schema_path: Path):
    """
    Parses JSON seeds, normalizes relationships, and populates the SQLite database.
    Idempotent: removes the existing database file before running.
    """
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Execute Schema
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # 2. Seed Topics
    topics_file = data_dir / "topics.json"
    if topics_file.exists():
        with open(topics_file, "r", encoding="utf-8") as f:
            topics = json.load(f)
            for t in topics:
                cursor.execute(
                    "INSERT INTO topics (slug, label, domain) VALUES (?, ?, ?)",
                    (t.get("slug"), t.get("label"), t.get("domain")),
                )

    # 3. Seed Users and User Topics
    users_file = data_dir / "users.json"
    if users_file.exists():
        with open(users_file, "r", encoding="utf-8") as f:
            users = json.load(f)
            for u in users:
                cursor.execute(
                    """
                    INSERT INTO users (id, first_name, last_name, industry, location, joined_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        u.get("id"),
                        u.get("first_name"),
                        u.get("last_name"),
                        u.get("industry"),
                        u.get("location"),
                        u.get("joined_at"),
                    ),
                )
                for slug in u.get("topic_interests", []):
                    cursor.execute(
                        "INSERT OR IGNORE INTO user_topics (user_id, topic_slug) VALUES (?, ?)",
                        (u.get("id"), slug),
                    )

    # Load valid topics for normalization checks
    cursor.execute("SELECT slug FROM topics")
    valid_topics = {row["slug"] for row in cursor.fetchall()}

    # 4. Seed Circles and Normalize Circle Topics
    circles_file = data_dir / "circles.json"
    if circles_file.exists():
        with open(circles_file, "r", encoding="utf-8") as f:
            circles = json.load(f)
            for c in circles:
                # Base circle insertion. member_count defaults to 0.
                cursor.execute(
                    """
                    INSERT INTO circles (
                        id, name, slug, description, format, access, join_policy, 
                        max_members, member_count, last_activity_at, feed_posts_30d, chat_messages_30d
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                    """,
                    (
                        c.get("id"),
                        c.get("name"),
                        c.get("slug"),
                        c.get("description"),
                        c.get("format"),
                        c.get("access"),
                        c.get("join_policy"),
                        c.get("max_members"),
                        c.get("last_activity_at"),
                        c.get("feed_posts_30d", 0),
                        c.get("chat_messages_30d", 0),
                    ),
                )

                # Normalize topic vs tags. Only insert if recognized in our taxonomy.
                c_topics = set()
                primary_topic = c.get("topic")
                if primary_topic in valid_topics:
                    c_topics.add(primary_topic)

                for tag in c.get("tags", []):
                    if tag in valid_topics:
                        c_topics.add(tag)

                for slug in c_topics:
                    cursor.execute(
                        "INSERT OR IGNORE INTO circle_topics (circle_id, topic_slug) VALUES (?, ?)",
                        (c.get("id"), slug),
                    )

    # 5. Seed Memberships (Activates SQLite Triggers for synced member_count)
    memberships_file = data_dir / "memberships.json"
    if memberships_file.exists():
        with open(memberships_file, "r", encoding="utf-8") as f:
            memberships = json.load(f)
            for m in memberships:
                cursor.execute(
                    "INSERT INTO memberships (user_id, circle_id, role) VALUES (?, ?, ?)",
                    (m.get("user_id"), m.get("circle_id"), m.get("role")),
                )

    # 6. Correct member_count to reflect the true totals from circles.json
    # (Overwrites trigger behavior to ensure data exactly matches the provided snapshot)
    if circles_file.exists():
        with open(circles_file, "r", encoding="utf-8") as f:
            circles = json.load(f)
            for c in circles:
                if "member_count" in c:
                    cursor.execute(
                        "UPDATE circles SET member_count = ? WHERE id = ?",
                        (c["member_count"], c["id"]),
                    )

    conn.commit()
    conn.close()
    print(f"Database seeded successfully at {db_path}")


if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent.parent
    seed_db(
        db_path=root_dir / "src" / "db" / "connect.db",
        data_dir=root_dir / "data",
        schema_path=root_dir / "src" / "db" / "schema.sql",
    )
