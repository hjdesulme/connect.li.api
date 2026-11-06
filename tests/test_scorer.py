import math
from src.models import CandidateCircle, AccessType, JoinPolicyType, ScoreBreakdown
from src.scorer import compute_base_score, sort_candidates

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


def test_cold_start_fallback_score():
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
    
    breakdown = compute_base_score(circle)
    
    # Because both topic and demo scores are 0, it should fallback perfectly to act_score
    assert breakdown.base_score == breakdown.act_score
    assert math.isclose(breakdown.base_score, 1.0)


def test_candidate_sorting():
    c1 = CandidateCircle(
        id=10,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=0,
        chat_messages_30d=0,
        topic_overlap_count=0,
        industry_match=False,
        location_match=False,
        last_activity_at="2023-01-01"
    )
    b1 = ScoreBreakdown(base_score=0.5, topic_score=0.0, demo_score=0.0, act_score=0.0)
    
    c2 = CandidateCircle(
        id=2,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=0,
        chat_messages_30d=0,
        topic_overlap_count=0,
        industry_match=False,
        location_match=False,
        last_activity_at="2023-01-02"
    )
    b2 = ScoreBreakdown(base_score=0.5, topic_score=0.0, demo_score=0.0, act_score=0.0)

    c3 = CandidateCircle(
        id=3,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=0,
        chat_messages_30d=0,
        topic_overlap_count=0,
        industry_match=False,
        location_match=False,
        last_activity_at=None
    )
    b3 = ScoreBreakdown(base_score=0.8, topic_score=0.0, demo_score=0.0, act_score=0.0)
    
    c4 = CandidateCircle(
        id=1,
        access=AccessType.PUBLIC,
        join_policy=JoinPolicyType.OPEN,
        member_count=0,
        feed_posts_30d=0,
        chat_messages_30d=0,
        topic_overlap_count=0,
        industry_match=False,
        location_match=False,
        last_activity_at="2023-01-02"
    )
    b4 = ScoreBreakdown(base_score=0.5, topic_score=0.0, demo_score=0.0, act_score=0.0)
    
    candidates = [(c1, b1), (c2, b2), (c3, b3), (c4, b4)]
    sorted_candidates = sort_candidates(candidates)
    
    # Expected ranking:
    # 1. c3 (score 0.8 dominates)
    # 2. c4 (score 0.5, latest date 2023-01-02, lowest id 1)
    # 3. c2 (score 0.5, latest date 2023-01-02, higher id 2)
    # 4. c1 (score 0.5, oldest date 2023-01-01, highest id 10)
    assert sorted_candidates[0][0].id == 3
    assert sorted_candidates[1][0].id == 1
    assert sorted_candidates[2][0].id == 2
    assert sorted_candidates[3][0].id == 10
