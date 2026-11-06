import pytest
from pydantic import ValidationError

from src.models import (
    AccessType,
    JoinPolicyType,
    FormatType,
    CandidateCircle,
    RecommendationParams,
)


def test_enum_values():
    assert AccessType.PUBLIC == "public"
    assert AccessType.UNLISTED == "unlisted"
    
    assert JoinPolicyType.OPEN == "open"
    assert JoinPolicyType.REQUEST == "request"
    
    assert FormatType.IN_PERSON == "in_person"
    assert FormatType.VIRTUAL == "virtual"
    assert FormatType.HYBRID == "hybrid"


def test_recommendation_params_limit():
    # Valid bounds
    params = RecommendationParams(limit=1)
    assert params.limit == 1

    params = RecommendationParams(limit=50)
    assert params.limit == 50

    # Default logic
    params = RecommendationParams()
    assert params.limit == 10

    # Invalid limits should trigger validation errors
    with pytest.raises(ValidationError):
        RecommendationParams(limit=0)

    with pytest.raises(ValidationError):
        RecommendationParams(limit=51)


def test_candidate_circle_validation():
    valid_data = {
        "id": 1,
        "name": "Women in Tech",
        "access": "public",
        "join_policy": "open",
        "format": "virtual",
        "max_members": 100,
        "member_count": 5,
        "feed_posts_30d": 10,
        "chat_messages_30d": 2,
        "topic_overlap_count": 3,
        "industry_match": True,
        "location_match": False,
    }

    circle = CandidateCircle(**valid_data)
    assert circle.id == 1
    assert circle.access == AccessType.PUBLIC
    assert circle.format == FormatType.VIRTUAL

    # Simulate bad data from Database (e.g. unrecognizable enum value)
    invalid_data = valid_data.copy()
    invalid_data["access"] = "private"

    with pytest.raises(ValidationError):
        CandidateCircle(**invalid_data)
