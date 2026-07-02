"""API routes."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
