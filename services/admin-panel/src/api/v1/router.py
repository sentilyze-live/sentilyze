"""API v1 router."""

from fastapi import APIRouter

from .auth import router as auth_router
from .budget import router as budget_router
from .costs import router as costs_router
from .feature_flags import router as feature_flags_router
from .users import router as users_router

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(budget_router)
api_router.include_router(costs_router)
api_router.include_router(feature_flags_router)
