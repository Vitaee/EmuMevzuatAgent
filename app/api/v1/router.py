"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1 import chat, health, reg_docs

router = APIRouter(prefix="/api/v1")

router.include_router(health.router, tags=["Health"])
router.include_router(reg_docs.router, prefix="/reg-docs", tags=["Regulation Documents"])
router.include_router(chat.router, tags=["Chat Agent"])

