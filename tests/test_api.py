import sqlite3
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from src.app import app, get_db


@pytest.fixture(name="test_db")
def fixture_test_db():
    """Provides a fresh in-memory database with schema and mock data applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    schema_path = Path("src/db/schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    cursor = conn.cursor()

    # --- SHARED DATA ---
    topics = [
        ("leadership-skills", "Leadership"),
        ("public-speaking", "Speaking"),
        ("negotiation", "Negotiation"),
        ("getting-promoted", "Promotion"),
    ]
    cursor.executemany("INSERT INTO topics (slug, label) VALUES (?, ?)", topics)

    # Insert a general leader user for triggering full capacities
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name, industry, location) VALUES (99, 'Leader', 'One', 'Tech', 'NYC')"
    )

    # --- BASE TEST DATA ---
    # Insert a dummy user
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name, industry, location) VALUES (1, 'Alice', 'Smith', 'Tech', 'London')"
    )

    # Insert a healthy dummy circle
    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, feed_posts_30d, chat_messages_30d) "
        "VALUES (100, 'Test Circle', 'public', 'open', 5, 5)"
    )

    # --- SCENARIO: User 42 (Cold-start) ---
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name) VALUES (42, 'Cold', 'Start')"
    )
    # No topics or memberships added. They will be recommended the active circles from other scenarios.

    # --- SCENARIO: User 7 (Obvious matches) ---
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name) VALUES (7, 'Obvious', 'Match')"
    )
    cursor.execute(
        "INSERT INTO user_topics (user_id, topic_slug) VALUES (7, 'leadership-skills')"
    )
    cursor.execute(
        "INSERT INTO user_topics (user_id, topic_slug) VALUES (7, 'public-speaking')"
    )

    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, feed_posts_30d, chat_messages_30d) VALUES (5, 'Women Who Lead', 'public', 'open', 10, 10)"
    )
    cursor.execute(
        "INSERT INTO circle_topics (circle_id, topic_slug) VALUES (5, 'leadership-skills')"
    )

    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, feed_posts_30d, chat_messages_30d) VALUES (6, 'Speak Up Circle', 'public', 'open', 10, 10)"
    )
    cursor.execute(
        "INSERT INTO circle_topics (circle_id, topic_slug) VALUES (6, 'public-speaking')"
    )

    # --- SCENARIO: User 15 (Duplicate Circles) ---
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name) VALUES (15, 'Dup', 'User')"
    )
    cursor.execute(
        "INSERT INTO user_topics (user_id, topic_slug) VALUES (15, 'negotiation')"
    )

    # 3 Identical Negotiation Circles
    for cid in [10, 11, 12]:
        cursor.execute(
            f"INSERT INTO circles (id, name, access, join_policy, feed_posts_30d, chat_messages_30d) VALUES ({cid}, 'Negotiation {cid}', 'public', 'open', 15, 15)"
        )
        cursor.execute(
            f"INSERT INTO circle_topics (circle_id, topic_slug) VALUES ({cid}, 'negotiation')"
        )

    # 1 Distinct Alternative
    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, feed_posts_30d, chat_messages_30d) VALUES (13, 'Alt Leadership', 'public', 'open', 10, 5)"
    )
    cursor.execute(
        "INSERT INTO circle_topics (circle_id, topic_slug) VALUES (13, 'leadership-skills')"
    )

    # --- SCENARIO: User 23 (Full/inactive) ---
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name) VALUES (23, 'Full', 'Inactive')"
    )
    cursor.execute(
        "INSERT INTO user_topics (user_id, topic_slug) VALUES (23, 'getting-promoted')"
    )

    # Circle 20 (Full)
    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, max_members, feed_posts_30d, chat_messages_30d) VALUES (20, 'The Promotion Path', 'public', 'request', 1, 10, 10)"
    )
    cursor.execute(
        "INSERT INTO circle_topics (circle_id, topic_slug) VALUES (20, 'getting-promoted')"
    )
    cursor.execute(
        "INSERT INTO memberships (user_id, circle_id, role) VALUES (99, 20, 'leader')"
    )

    # Circle 21 (Inactive)
    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, max_members, feed_posts_30d, chat_messages_30d) VALUES (21, 'Career Climbers', 'public', 'open', 10, 0, 0)"
    )
    cursor.execute(
        "INSERT INTO circle_topics (circle_id, topic_slug) VALUES (21, 'getting-promoted')"
    )

    # Circle 22 (Healthy)
    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, max_members, feed_posts_30d, chat_messages_30d) VALUES (22, 'Level Up Collective', 'public', 'open', 10, 5, 5)"
    )
    cursor.execute(
        "INSERT INTO circle_topics (circle_id, topic_slug) VALUES (22, 'getting-promoted')"
    )

    conn.commit()

    yield conn
    conn.close()


@pytest.fixture(name="client")
def fixture_client(test_db):
    """Overrides the get_db dependency to point to the isolated in-memory DB fixture."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # closing is handled by the db fixture lifecycle

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_recommendations_user_not_found(client):
    response = client.get("/v1/recommendations/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_recommendations_success(client):
    # Bump limit so Circle 100 isn't pushed out by the many other active plant circles
    response = client.get("/v1/recommendations/1?limit=50")
    assert response.status_code == 200

    data = response.json()
    assert data["user_id"] == 1
    assert "recommendations" in data

    recs = data["recommendations"]
    assert len(recs) >= 1
    assert any(r["id"] == 100 for r in recs)


def test_e2e_cold_start_user_42(client):
    """
    Scenario: Cold-start
    A user with no memberships or stated topic interests.
    """
    response = client.get("/v1/recommendations/42?limit=5")
    assert response.status_code == 200

    data = response.json()
    recs = data["recommendations"]

    # Ensure we got results derived purely from activity
    assert len(recs) > 0

    # Explanations should specifically mention the cold-start fallback
    assert (
        recs[0]["explanation"]["reason"]
        == "A highly active community to help you get started."
    )


def test_e2e_obvious_matches_user_7(client):
    """
    Scenario: Obvious matches
    Stated interests line up very well with a few Circles.
    """
    response = client.get("/v1/recommendations/7?limit=5")
    assert response.status_code == 200

    data = response.json()
    recs = data["recommendations"]

    # Circles 5 and 6 should be the top matches
    top_ids = [r["id"] for r in recs[:2]]
    assert set(top_ids) == {5, 6}

    # Explanations should reflect a strong topic match
    for r in recs[:2]:
        assert (
            r["explanation"]["reason"]
            == "A strong match based on your topic interests."
        )


def test_e2e_duplicate_circles_user_15(client):
    """
    Scenario: Duplicate Circles
    Several near-identical Circles on one topic; MMR diversity should penalize them.
    """
    response = client.get("/v1/recommendations/15?limit=10")
    assert response.status_code == 200

    data = response.json()
    recs = data["recommendations"]

    # The penalty should trigger for the subsequent identical circles in the ranking
    penalty_found = False
    for r in recs:
        if r["explanation"]["reason"] == "A popular circle outside your usual topics.":
            penalty_found = True
            break

    assert penalty_found is True


def test_e2e_full_inactive_user_23(client):
    """
    Scenario: Full / inactive
    Circles that look attractive on paper, but shouldn't rank based on activity or availability.
    """
    response = client.get("/v1/recommendations/23?limit=5")
    assert response.status_code == 200

    data = response.json()
    recs = data["recommendations"]
    rec_ids = [r["id"] for r in recs]

    # 20 (Full) and 21 (Inactive) should be entirely filtered out by the database CTE
    assert 20 not in rec_ids
    assert 21 not in rec_ids

    # 22 is healthy and matches topics, so it should be present
    assert 22 in rec_ids
