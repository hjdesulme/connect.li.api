import math
from src.models import CandidateCircle, ScoreBreakdown

def compute_base_score(circle: CandidateCircle) -> ScoreBreakdown:
    # Score_topic: min(overlap_count, 5) / 5.0
    topic_score = min(circle.topic_overlap_count, 5) / 5.0
    
    # Score_demo: 1.0 if user industry/location matches, else 0.0
    demo_score = 1.0 if (circle.industry_match or circle.location_match) else 0.0
    
    # Score_act: min(log10(1 + posts + chats) / 3.0, 1.0)
    total_activity = circle.feed_posts_30d + circle.chat_messages_30d
    act_score = min(math.log10(1 + total_activity) / 3.0, 1.0)
    
    # Total_Score = (0.5 * Score_topic) + (0.2 * Score_demo) + (0.3 * Score_act)
    base_score = (0.5 * topic_score) + (0.2 * demo_score) + (0.3 * act_score)
    
    return ScoreBreakdown(
        base_score=base_score,
        topic_score=topic_score,
        demo_score=demo_score,
        act_score=act_score,
        mmr_penalty_applied=False
    )
