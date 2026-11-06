import sqlite3
from pathlib import Path


def test_schema_and_triggers():
    # Connect to a fresh in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Load and execute the schema
    schema_path = Path("src/db/schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # Insert a dummy user
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name, industry, location) VALUES (?, ?, ?, ?, ?)",
        (1, "Ada", "Lovelace", "Tech", "London"),
    )

    # Insert a dummy circle (member_count should default to 0)
    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy) VALUES (?, ?, ?, ?)",
        (1, "Women in Tech", "public", "open"),
    )

    # Verify default member_count is 0
    cursor.execute("SELECT member_count FROM circles WHERE id = 1")
    circle_before = cursor.fetchone()
    assert circle_before["member_count"] == 0

    # Test the trg_increment_member_count trigger
    cursor.execute(
        "INSERT INTO memberships (user_id, circle_id, role) VALUES (?, ?, ?)",
        (1, 1, "member"),
    )

    cursor.execute("SELECT member_count FROM circles WHERE id = 1")
    circle_after_insert = cursor.fetchone()
    assert circle_after_insert["member_count"] == 1

    # Test the trg_decrement_member_count trigger
    cursor.execute("DELETE FROM memberships WHERE user_id = 1 AND circle_id = 1")

    cursor.execute("SELECT member_count FROM circles WHERE id = 1")
    circle_after_delete = cursor.fetchone()
    assert circle_after_delete["member_count"] == 0

    conn.close()
