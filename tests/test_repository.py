import sqlite3
from pathlib import Path

from src.db.repository import Repository


def test_get_candidate_circles_cte_scenario_23():
    """
    Coverage Gate for Milestone 2:
    Tests User 23 (Full / Inactive Scenario) logic in isolation.
    Must only return Circle #22.
    """
    # 1. Spin up isolated in-memory DB and apply schema
    conn = sqlite3.connect(":memory:")
    schema_path = Path("src/db/schema.sql")

    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    cursor = conn.cursor()

    # 2. Plant User 23 and Topic Interest
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name, industry, location) VALUES (?, ?, ?, ?, ?)",
        (23, "Test", "User", "Tech", "New York"),
    )
    cursor.execute(
        "INSERT INTO topics (slug, label) VALUES (?, ?)",
        ("getting-promoted", "Getting Promoted"),
    )
    cursor.execute(
        "INSERT INTO user_topics (user_id, topic_slug) VALUES (?, ?)",
        (23, "getting-promoted"),
    )

    # 3. Plant Leader User (Used to trigger full capacities and test demo matches)
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name, industry, location) VALUES (?, ?, ?, ?, ?)",
        (99, "Leader", "Woman", "Tech", "New York"),
    )

    # --- PLANTING CIRCLES ---

    # Circle 20: "The Promotion Path" -> Is Full (max_members = 1, we will add 1 member via trigger)
    cursor.execute(
        """
        INSERT INTO circles (id, name, access, join_policy, max_members, feed_posts_30d) 
        VALUES (20, 'The Promotion Path', 'public', 'open', 1, 10)
        """
    )
    # Inserting membership triggers `member_count = 1`, filling capacity
    cursor.execute(
        "INSERT INTO memberships (user_id, circle_id, role) VALUES (99, 20, 'leader')"
    )

    # Circle 21: "Career Climbers" -> Is Inactive (posts & chats = 0)
    cursor.execute(
        """
        INSERT INTO circles (id, name, access, join_policy, max_members, feed_posts_30d, chat_messages_30d) 
        VALUES (21, 'Career Climbers', 'public', 'open', 10, 0, 0)
        """
    )

    # Circle 22: "Level Up Collective" -> Healthy alternative (Active, not full)
    cursor.execute(
        """
        INSERT INTO circles (id, name, access, join_policy, max_members, feed_posts_30d, chat_messages_30d) 
        VALUES (22, 'Level Up Collective', 'public', 'open', 10, 5, 5)
        """
    )
    cursor.execute(
        "INSERT INTO circle_topics (circle_id, topic_slug) VALUES (22, 'getting-promoted')"
    )
    cursor.execute(
        "INSERT INTO memberships (user_id, circle_id, role) VALUES (99, 22, 'leader')"
    )

    # 4. Execute Repository Logic
    repo = Repository(conn)
    results = repo.get_candidate_circles_cte(user_id=23)

    conn.close()

    # 5. Assertions
    # Should exclude Circle 20 (Full) and Circle 21 (Inactive)
    assert len(results) == 1

    # Circle 22 is the only valid result
    healthy_circle = results[0]
    assert healthy_circle.id == 22
    assert healthy_circle.name == "Level Up Collective"

    # Assert Computed Signals worked correctly based on CTE joins
    assert healthy_circle.topic_overlap_count == 1
    assert (
        healthy_circle.industry_match is True
    )  # User industry 'Tech' == Leader industry 'Tech'
    assert (
        healthy_circle.location_match is True
    )  # User location 'New York' == Leader location 'New York'
    assert healthy_circle.circle_topics == "getting-promoted"
