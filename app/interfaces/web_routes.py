"""Web page routes."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.application.upload_service import list_jobs

templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

web_router = APIRouter()


@web_router.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"title": "首页"})


@web_router.get("/jobs")
async def jobs_page(request: Request):
    jobs = list_jobs(limit=50)
    return templates.TemplateResponse(request=request, name="jobs.html", context={"title": "识别任务", "jobs": jobs})
