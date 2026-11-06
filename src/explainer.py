from src.models import CandidateCircle, ScoreBreakdown


def generate_explanation(circle: CandidateCircle, breakdown: ScoreBreakdown) -> str:
    """
    Generates a human-readable explanation based on the score breakdown
    and the rules laid out in the architectural contract.
    """
    # Rule 1: Cold-Start
    if breakdown.is_cold_start:
        return "A highly active community to help you get started."

    # Rule 2: Diversity Penalty
    if breakdown.mmr_penalty_applied:
        return "A popular circle outside your usual topics."

    # Rule 3: Topic-Driven Recommendation
    if breakdown.topic_score >= breakdown.demo_score and breakdown.topic_score > 0:
        return "A strong match based on your topic interests."

    # Rule 4: Demographic-Driven Recommendation
    if breakdown.demo_score > breakdown.topic_score:
        return "Recommended based on your professional background or location."

    # Fallback
    return "A recommended community for you."
