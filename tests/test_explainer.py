from src.models import CandidateCircle, ScoreBreakdown, AccessType, JoinPolicyType
from src.explainer import generate_explanation


def create_dummy_circle():
    return CandidateCircle(
        id=1,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=10,
        chat_messages_30d=10,
        engagement_count=0,
        topic_overlap_count=0,
        industry_match=False,
        location_match=False,
    )


def test_cold_start_explanation():
    circle = create_dummy_circle()
    breakdown = ScoreBreakdown(
        base_score=1.0,
        topic_score=0.0,
        demo_score=0.0,
        act_score=1.0,
        is_cold_start=True,
    )
    assert (
        generate_explanation(circle, breakdown)
        == "A highly active community to help you get started."
    )


def test_mmr_penalty_explanation():
    circle = create_dummy_circle()
    # MMR Penalty should trigger the specific diversity explanation
    breakdown = ScoreBreakdown(
        base_score=0.8,
        topic_score=0.5,
        demo_score=0.0,
        act_score=0.5,
        mmr_penalty_applied=True,
    )
    assert (
        generate_explanation(circle, breakdown)
        == "A popular circle outside your usual topics."
    )


def test_topic_match_explanation():
    circle = create_dummy_circle()
    breakdown = ScoreBreakdown(
        base_score=0.8, topic_score=0.8, demo_score=0.2, act_score=0.5
    )
    assert (
        generate_explanation(circle, breakdown)
        == "A strong match based on your topic interests."
    )


def test_demo_match_explanation():
    circle = create_dummy_circle()
    breakdown = ScoreBreakdown(
        base_score=0.8, topic_score=0.2, demo_score=1.0, act_score=0.5
    )
    assert (
        generate_explanation(circle, breakdown)
        == "Recommended based on your professional background or location."
    )
