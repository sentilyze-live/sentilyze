"""User Dashboard API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.analytics import router as analytics_router

app = FastAPI(title="Sentilyze User Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "healthy"}
