import sqlite3
from typing import List

from src.models import CandidateCircle


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        """
        Initializes the repository with a SQLite connection.
        Ensures the row_factory is set for dictionary-like access.
        """
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    def user_exists(self, user_id: int) -> bool:
        """
        Checks if a user exists in the database.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE id = :user_id", {"user_id": user_id})
        return cursor.fetchone() is not None

    def is_cold_start_user(self, user_id: int) -> bool:
        """
        Checks if a user is a true cold-start (no stated topics, no demographic signals).
        """
        cursor = self.conn.cursor()
        query = """
            SELECT 
                (SELECT COUNT(*) FROM user_topics WHERE user_id = :user_id) AS topic_count,
                industry,
                location
            FROM users 
            WHERE id = :user_id
        """
        cursor.execute(query, {"user_id": user_id})
        row = cursor.fetchone()
        if not row:
            return True
        return row["topic_count"] == 0 and not row["industry"] and not row["location"]

    def get_candidate_circles_cte(self, user_id: int) -> List[CandidateCircle]:
        """
        Executes a single parameterized SQL query using Common Table Expressions (CTEs)
        to aggressively filter invalid candidates at the DB layer, and compute match signals.
        """
        query = """
        WITH user_info AS (
            SELECT id, industry, location 
            FROM users 
            WHERE id = :user_id
        ),
        user_topics_cte AS (
            SELECT topic_slug 
            FROM user_topics 
            WHERE user_id = :user_id
        ),
        circle_leaders AS (
            SELECT 
                m.circle_id, 
                u.industry, 
                u.location
            FROM memberships m
            JOIN users u ON m.user_id = u.id
            WHERE m.role = 'leader'
        )
        SELECT 
            c.id,
            c.name,
            c.description,
            c.access,
            c.join_policy,
            c.format,
            c.max_members,
            c.member_count,
            c.last_activity_at,
            c.feed_posts_30d,
            c.chat_messages_30d,
            (
                SELECT COUNT(*)
                FROM circle_topics ct
                JOIN user_topics_cte ut ON ct.topic_slug = ut.topic_slug
                WHERE ct.circle_id = c.id
            ) AS topic_overlap_count,
            (
                SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END
                FROM circle_leaders cl
                JOIN user_info ui ON (cl.industry = ui.industry AND ui.industry IS NOT NULL AND ui.industry != '')
                WHERE cl.circle_id = c.id
            ) AS industry_match,
            (
                SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END
                FROM circle_leaders cl
                JOIN user_info ui ON (cl.location = ui.location AND ui.location IS NOT NULL AND ui.location != '')
                WHERE cl.circle_id = c.id
            ) AS location_match,
            (
                SELECT GROUP_CONCAT(ct.topic_slug)
                FROM circle_topics ct
                WHERE ct.circle_id = c.id
            ) AS circle_topics
        FROM circles c
        WHERE c.access IN ('public', 'unlisted')
          AND c.join_policy IN ('open', 'request')
          
          -- Hard Filter: Capacity Constraints
          AND (
              c.max_members IS NULL 
              OR c.member_count < c.max_members 
              OR c.join_policy = 'request'
          )
          
          -- Hard Filter: Inactive Circles
          AND (c.feed_posts_30d + c.chat_messages_30d) > 0
          
          -- Hard Filter: Already a Member
          AND NOT EXISTS (
              SELECT 1 
              FROM memberships m 
              WHERE m.user_id = :user_id AND m.circle_id = c.id
          );
        """

        cursor = self.conn.cursor()
        cursor.execute(query, {"user_id": user_id})

        # Pydantic models automatically cast SQLite's 1/0 integers to booleans
        # for industry_match and location_match.
        return [CandidateCircle(**dict(row)) for row in cursor.fetchall()]
