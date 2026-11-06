from fastapi import FastAPI, APIRouter

app = FastAPI(
    title="Lean In Connect API", 
    description="API for recommending Circles to Lean In members",
    version="1.0.0"
)

# API v1 Router
v1_router = APIRouter(prefix="/v1")

# We will attach our recommendation endpoints to v1_router later.
# For now, it's just registered to the main app.
app.include_router(v1_router)

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "ok"}
