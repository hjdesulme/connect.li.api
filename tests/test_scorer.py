import math
from src.models import CandidateCircle, AccessType, JoinPolicyType
from src.scorer import compute_base_score

def test_topic_score():
    circle = CandidateCircle(
        id=1,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=0,
        chat_messages_30d=0,
        topic_overlap_count=3,
        industry_match=False,
        location_match=False
    )
    
    breakdown = compute_base_score(circle)
    assert breakdown.topic_score == 3 / 5.0

    circle.topic_overlap_count = 6
    breakdown = compute_base_score(circle)
    assert breakdown.topic_score == 1.0

def test_demographic_score():
    circle = CandidateCircle(
        id=1,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=0,
        chat_messages_30d=0,
        topic_overlap_count=0,
        industry_match=True,
        location_match=False
    )
    
    breakdown = compute_base_score(circle)
    assert breakdown.demo_score == 1.0

    circle.industry_match = False
    circle.location_match = True
    breakdown = compute_base_score(circle)
    assert breakdown.demo_score == 1.0

    circle.industry_match = False
    circle.location_match = False
    breakdown = compute_base_score(circle)
    assert breakdown.demo_score == 0.0

def test_activity_score():
    circle = CandidateCircle(
        id=1,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=99,
        chat_messages_30d=900,
        topic_overlap_count=0,
        industry_match=False,
        location_match=False
    )
    # total activity = 999. log10(1 + 999) = 3. 3/3 = 1.0
    breakdown = compute_base_score(circle)
    assert math.isclose(breakdown.act_score, 1.0)
    
    circle.feed_posts_30d = 0
    circle.chat_messages_30d = 9
    # total = 9, log10(10) = 1. 1/3 = 0.333...
    breakdown = compute_base_score(circle)
    assert math.isclose(breakdown.act_score, 1 / 3.0)

def test_base_weighting():
    circle = CandidateCircle(
        id=1,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=9,
        chat_messages_30d=0,
        topic_overlap_count=5, # topic score 1.0
        industry_match=True,   # demo score 1.0
        location_match=False
    )
    # act score = 1/3 = 0.33333333
    breakdown = compute_base_score(circle)
    
    expected_base_score = (0.5 * 1.0) + (0.2 * 1.0) + (0.3 * (1/3.0))
    assert math.isclose(breakdown.base_score, expected_base_score)
