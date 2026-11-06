import json
import sqlite3
from pathlib import Path


def seed_db(db_path: Path, data_dir: Path, schema_path: Path):
    """
    Parses JSON seeds, normalizes relationships, and populates the SQLite database.
    Idempotent: removes the existing database file before running.
    """
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory not found at {data_dir}. "
            "Please ensure the 'data' folder (containing users.json, circles.json, etc.) "
            "is placed in the root of the project."
        )

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Execute Schema
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
    print(f"[*] Executed schema from {schema_path.name}")

    # 2. Seed Topics
    topics_file = data_dir / "topics.json"
    with open(topics_file, "r", encoding="utf-8") as f:
        topics = json.load(f)
        for t in topics:
            cursor.execute(
                "INSERT INTO topics (slug, label, domain) VALUES (?, ?, ?)",
                (t.get("slug"), t.get("label"), t.get("domain")),
            )
    print(f"[*] Inserted {len(topics)} topics.")

    # Load valid topics for normalization checks early
    cursor.execute("SELECT slug FROM topics")
    valid_topics = {row["slug"] for row in cursor.fetchall()}

    # 3. Seed Users and User Topics
    users_file = data_dir / "users.json"
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
                if slug in valid_topics:
                    cursor.execute(
                        "INSERT OR IGNORE INTO user_topics (user_id, topic_slug) VALUES (?, ?)",
                        (u.get("id"), slug),
                    )
    print(f"[*] Inserted {len(users)} users.")

    # 4. Seed Circles and Normalize Circle Topics
    circles_file = data_dir / "circles.json"
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
    print(f"[*] Inserted {len(circles)} circles.")

    # 5. Seed Memberships (Activates SQLite Triggers for synced member_count)
    memberships_file = data_dir / "memberships.json"
    with open(memberships_file, "r", encoding="utf-8") as f:
        memberships = json.load(f)
        for m in memberships:
            cursor.execute(
                "INSERT INTO memberships (user_id, circle_id, role) VALUES (?, ?, ?)",
                (m.get("user_id"), m.get("circle_id"), m.get("role")),
            )
    print(f"[*] Inserted {len(memberships)} memberships.")

    # 6. Seed Activity Data (Engagement)
    activity_file = data_dir / "activity.json"
    with open(activity_file, "r", encoding="utf-8") as f:
        activities = json.load(f)
        engagement_by_circle = {}
        for act in activities:
            cid = act.get("circle_id")
            eng = (
                act.get("reaction_count", 0)
                + act.get("comment_count", 0)
                + act.get("save_count", 0)
            )
            engagement_by_circle[cid] = engagement_by_circle.get(cid, 0) + eng

        for cid, total_eng in engagement_by_circle.items():
            cursor.execute(
                "UPDATE circles SET engagement_count = ? WHERE id = ?", (total_eng, cid)
            )
    print(f"[*] Processed {len(activities)} activity records.")

    # 7. Correct member_count to reflect the true totals from circles.json
    # (Overwrites trigger behavior to ensure data exactly matches the provided snapshot)
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
    print(f"[+] Database seeded successfully at {db_path}")


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent.parent
    seed_db(
        db_path=root_dir / "src" / "db" / "connect.db",
        data_dir=root_dir / "data",
        schema_path=root_dir / "src" / "db" / "schema.sql",
    )
