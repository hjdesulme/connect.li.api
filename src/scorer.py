import math

from src.models import CandidateCircle, ScoreBreakdown


def compute_base_score(
    circle: CandidateCircle, is_cold_start: bool = False
) -> ScoreBreakdown:
    # Score_topic: min(overlap_count, 5) / 5.0
    topic_score = min(circle.topic_overlap_count, 5) / 5.0

    # Score_demo: 1.0 if user industry/location matches, else 0.0
    demo_score = 1.0 if (circle.industry_match or circle.location_match) else 0.0

    # Score_act: min(log10(1 + posts + chats + engagements) / 3.0, 1.0)
    total_activity = (
        circle.feed_posts_30d + circle.chat_messages_30d + circle.engagement_count
    )
    act_score = min(math.log10(1 + total_activity) / 3.0, 1.0)

    # Total_Score = (0.5 * Score_topic) + (0.2 * Score_demo) + (0.3 * Score_act)
    base_score = (0.5 * topic_score) + (0.2 * demo_score) + (0.3 * act_score)

    # Cold-Start Fallback:
    if is_cold_start:
        base_score = act_score

    return ScoreBreakdown(
        base_score=base_score,
        topic_score=topic_score,
        demo_score=demo_score,
        act_score=act_score,
        is_cold_start=is_cold_start,
        mmr_penalty_applied=False,
    )


def sort_candidates(
    candidates: list[tuple[CandidateCircle, ScoreBreakdown]],
) -> list[tuple[CandidateCircle, ScoreBreakdown]]:
    """
    Sorts candidates by Total Score DESC, last_activity_at DESC, id ASC
    """
    return sorted(
        candidates,
        key=lambda x: (x[1].base_score, x[0].last_activity_at or "", -x[0].id),
        reverse=True,
    )


def jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0


def apply_mmr(
    candidates: list[tuple[CandidateCircle, ScoreBreakdown]], k: int = 50
) -> list[tuple[CandidateCircle, ScoreBreakdown]]:
    """
    Applies Greedy MMR Diversity over the Top K candidates.
    Assumes candidates is already sorted by base score & tie-breakers.
    """
    pool = candidates[:k]
    tail = candidates[k:]

    selected_candidates = []
    selected_topics = set()

    while pool:
        best_idx = -1
        best_score = -float("inf")
        best_penalty = 0.0

        for i, (circle, breakdown) in enumerate(pool):
            c_topics = (
                set(circle.circle_topics.split(",")) if circle.circle_topics else set()
            )

            penalty = 0.0
            if selected_topics:
                penalty = jaccard_similarity(c_topics, selected_topics)

            adjusted_score = (0.75 * breakdown.base_score) - (0.25 * penalty)

            if adjusted_score > best_score:
                best_score = adjusted_score
                best_idx = i
                best_penalty = penalty

        winner_circle, winner_breakdown = pool.pop(best_idx)

        if best_penalty > 0:
            winner_breakdown.mmr_penalty_applied = True

        selected_candidates.append((winner_circle, winner_breakdown))

        c_topics = (
            set(winner_circle.circle_topics.split(","))
            if winner_circle.circle_topics
            else set()
        )
        selected_topics.update(c_topics)

    return selected_candidates + tail
