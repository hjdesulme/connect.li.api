import sqlite3
from pathlib import Path
from fastapi import FastAPI, APIRouter, Depends, HTTPException

from src.db.repository import Repository
from src.models import (
    RecommendationParams,
    RecommendationResponse,
    RecommendedCircle,
    RecommendationExplanation,
)
from src.scorer import compute_base_score, sort_candidates, apply_mmr
from src.explainer import generate_explanation


app = FastAPI(
    title="Lean In Connect API", 
    description="API for recommending Circles to Lean In members",
    version="1.0.0"
)

def get_db():
    """Database connection dependency for FastAPI routes."""
    db_path = Path(__file__).parent / "db" / "connect.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# API v1 Router
v1_router = APIRouter(prefix="/v1")


@v1_router.get("/recommendations/{user_id}", response_model=RecommendationResponse, tags=["Recommendations"])
def get_recommendations(
    user_id: int, 
    params: RecommendationParams = Depends(),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Returns a mathematically ranked, MMR-diversified list of recommended Circles for a user.
    """
    repo = Repository(db)
    
    # 1. 404 Check
    if not repo.user_exists(user_id):
        raise HTTPException(status_code=404, detail="User not found")
        
    # 2. Hard Filters (Via SQL CTE)
    candidates = repo.get_candidate_circles_cte(user_id)
    
    # 3. Base Scoring Component
    is_cold = repo.is_cold_start_user(user_id)
    scored_candidates = [(c, compute_base_score(c, is_cold_start=is_cold)) for c in candidates]
    
    # 4. Sorting
    sorted_candidates = sort_candidates(scored_candidates)
    
    # 5. Greedy Diversity MMR over Top K pool
    diversified_candidates = apply_mmr(sorted_candidates, k=50)
    
    # 6. Apply hard limits
    final_selection = diversified_candidates[:params.limit]
    
    # 7. Generate Explanations and response structures
    recommended_circles = []
    for circle, breakdown in final_selection:
        explanation = generate_explanation(circle, breakdown)
        recommended_circles.append(
            RecommendedCircle(
                id=circle.id,
                name=circle.name,
                description=circle.description,
                explanation=RecommendationExplanation(reason=explanation)
            )
        )
        
    return RecommendationResponse(user_id=user_id, recommendations=recommended_circles)


app.include_router(v1_router)

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "ok"}
