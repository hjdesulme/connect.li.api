# Technical Design Doc: Lean In Connect Recommendations

## What Was Built
I built a stateless, RESTful Python API using **FastAPI** backed by a local **SQLite** database. The system ingests member and community (Circle) data, normalizes it into a highly indexed relational schema, and returns a mathematically ranked, diversified list of recommended Circles for a given user. 

The API generates human-readable explanations dynamically by tracing the mathematical "score breakdown" (e.g., falling back to a pure-activity score for cold-start users, or penalizing a score to enforce topic diversity).

## Database Schema & Rationale
The database is fully normalized into 5 tables: `users`, `circles`, `topics`, `user_topics`, and `circle_topics`, alongside a `memberships` junction table. 

**Decisions & Rationale:**
* **Composite Primary Keys (Indexing):** The junction tables (`user_topics`, `circle_topics`, and `memberships`) utilize composite primary keys (e.g., `PRIMARY KEY (user_id, circle_id)`). This naturally indexes the exact queries we use for lookups and acts as a strict constraint preventing duplicate records from being inserted.
* **Foreign Key Cascades:** All relationships enforce `ON DELETE CASCADE`. If a user or circle is deleted, their associated topics and memberships are automatically purged, preventing orphaned data without requiring extra Python application logic.
* **SQLite Triggers for Aggregation:** I added DB-level triggers (`trg_increment_member_count`, `trg_decrement_member_count`) to automatically sync the `member_count` column on the `circles` table whenever a membership is added or removed. This trades a minor write-penalty for absolute O(1) performance on the highly-frequented read path (evaluating if a circle has reached `max_members`).

## Technical Decisions
1. **The Single Parameterized CTE (Common Table Expression)**: 
   Instead of pulling all data into Python and filtering it in memory, we pushed the elimination logic (capacities, join policies, inactive circles, and already-joined circles) down into the database via a single parameterized SQL query. This acts as a highly optimized "Hard Filter" and efficiently computes base feature counts (like `topic_overlap_count` and demographic booleans) before Python ever touches the data.
2. **Log-Normalized Activity Scoring**: 
   Circle engagement often follows a power-law distribution. A circle with 1,000 messages shouldn't entirely mathematically eclipse a circle with 50 messages if the topic overlap is strong. I used `min(log10(1 + posts + chats + engagement) / 3.0, 1.0)` to normalize activity on a 0-to-1 curve.
3. **Greedy MMR (Maximal Marginal Relevance) for Diversity**: 
   To solve the "Duplicate Circles" problem, we implemented a greedy MMR algorithm. It evaluates a top-K candidate pool iteratively. Once a circle is selected, the remaining unselected candidates are penalized based on their Jaccard Similarity to the *already selected* topics: `Adjusted = 0.75 * BaseScore - 0.25 * Penalty`. This seamlessly pushes duplicate niche circles down the ranking.

## Tradeoffs
* **Database Triggers vs. Count Aggregations**: I utilized SQLite triggers to maintain a real-time `member_count` on the `CIRCLES` table. This trades a slight performance hit on write operations (inserting a membership) for absolute O(1) performance on the highly-frequented read path (filtering full circles).
* **Synchronous Computation vs. Pre-computation**: The current pipeline fetches and scores the candidate pool synchronously on the API request thread. For a community of 170,000 circles, this is an acceptable tradeoff for real-time accuracy, but it would become a bottleneck at millions of records.
* **Exact Matching vs. Semantic Matching**: I relied on strictly normalized taxonomy intersections for topics and demographics. While fast and deterministic, it misses semantic nuances (e.g., "Leadership" vs "Management").

## Production Scale Additions
If taking this to production to support millions of women, we would implement:
1. **PostgreSQL & Read Replicas**: Migrate off SQLite to Postgres. All recommendation queries would be routed to a read-replica to prevent analytical loads from locking transaction tables.
2. **Redis & Background Workers**: Extract the 30-day activity aggregation (feed posts/chats) out of the relational database and into Redis counters. I would use Celery/Kafka (I have more familiarity with Kafka) to calculate candidates offline/asynchronously.
3. **Vector Embeddings**: Introduce semantic similarity (via `pgvector` or a dedicated vector DB like Pinecone). By embedding member bios and circle descriptions, we could recommend circles with no explicit topic tags but high semantic overlap.

## AI Fluency & Collaboration
AI was heavily leveraged throughout this project as a pair-programmer:
* **TDD & Scaffolding**: LLMs were used to instantly generate boilerplate, `pytest` fixtures, and the foundational environment pipeline (Makefiles, project structure).
* **Algorithm Tuning**: AI helped rapidly conceptualize and debug the edge cases in the Greedy MMR mathematics.
* **Raw SQL Generation**: The complex Common Table Expression (CTE) query was scaffolded by an LLM, allowing us to rapidly iterate on database-level filtering without manually debugging `GROUP BY` and `JOIN` syntax.
