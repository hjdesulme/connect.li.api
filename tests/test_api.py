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
    
    # Insert a dummy user
    cursor.execute(
        "INSERT INTO users (id, first_name, last_name, industry, location) VALUES (1, 'Alice', 'Smith', 'Tech', 'London')"
    )
    
    # Insert a healthy dummy circle
    cursor.execute(
        "INSERT INTO circles (id, name, access, join_policy, feed_posts_30d, chat_messages_30d) "
        "VALUES (100, 'Test Circle', 'public', 'open', 5, 5)"
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
            pass # closing is handled by the db fixture lifecycle
            
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_recommendations_user_not_found(client):
    response = client.get("/v1/recommendations/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_recommendations_success(client):
    response = client.get("/v1/recommendations/1?limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == 1
    assert "recommendations" in data
    
    recs = data["recommendations"]
    assert len(recs) == 1
    assert recs[0]["id"] == 100
    assert "reason" in recs[0]["explanation"]