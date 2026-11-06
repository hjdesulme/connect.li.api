from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class AccessType(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"


class JoinPolicyType(str, Enum):
    OPEN = "open"
    REQUEST = "request"


class FormatType(str, Enum):
    IN_PERSON = "in_person"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class RecommendationParams(BaseModel):
    """Query parameters to validate the recommendation requests."""

    limit: int = Field(
        default=10, ge=1, le=50, description="Max number of circles to recommend"
    )

    @field_validator("limit", mode="before")
    @classmethod
    def handle_empty_limit(cls, v: Any) -> Any:
        if v == "" or v is None or str(v).lower() == "null":
            return 10
        return v


class CandidateCircle(BaseModel):
    """Internal model representing a circle extracted from the DB CTE."""

    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    access: AccessType
    join_policy: JoinPolicyType
    format: Optional[FormatType] = None
    max_members: Optional[int] = None
    member_count: int
    last_activity_at: Optional[str] = None
    feed_posts_30d: int
    chat_messages_30d: int
    circle_topics: Optional[str] = None

    # Computed strictly via SQL CTE
    topic_overlap_count: int
    industry_match: bool
    location_match: bool


class ScoreBreakdown(BaseModel):
    base_score: float
    topic_score: float
    demo_score: float
    act_score: float
    is_cold_start: bool = False
    mmr_penalty_applied: bool = False


class RecommendationExplanation(BaseModel):
    reason: str


class RecommendedCircle(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    explanation: RecommendationExplanation


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[RecommendedCircle]
