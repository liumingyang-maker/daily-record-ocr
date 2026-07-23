"""FastAPI entry point for the lightweight application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from lite_app import __version__
from lite_app.config import load_settings
from lite_app.exporter import export_job
from lite_app.pipeline import analyze_job, save_edited_result
from lite_app.storage import create_job, job_dir, list_jobs, load_job, load_result

PACKAGE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="手写记录识别工具", version=__version__)
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


@app.get("/")
async def index(request: Request):
    settings = load_settings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "jobs": list_jobs(),
            "provider": settings.vision.get("provider", "mock"),
            "model": settings.vision.get("model", ""),
            "max_upload_mb": settings.app.get("max_upload_mb", 20),
        },
    )


@app.post("/jobs")
async def upload_and_recognize(
    files: Annotated[list[UploadFile], File(...)],
    rotation: Annotated[str, Form()] = "auto",
):
    settings = load_settings()
    if not files:
        raise HTTPException(status_code=400, detail="至少选择一张图片")

    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"空文件: {upload.filename}")
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"文件过大: {upload.filename}; 单文件上限 "
                    f"{settings.app.get('max_upload_mb', 20)} MB"
                ),
            )
        payloads.append((upload.filename or "image.jpg", content))

    job = create_job(payloads, rotation=rotation)
    try:
        await analyze_job(job["id"])
    except Exception:
        # Failure details are persisted in job.json and shown on the detail page.
        pass
    return RedirectResponse(f"/jobs/{job['id']}", status_code=303)


@app.get("/jobs/{job_id}")
async def job_detail(request: Request, job_id: str):
    try:
        job = load_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = load_result(job_id)
    result_text = json.dumps(result or {}, ensure_ascii=False, indent=2)
    return templates.TemplateResponse(
        request=request,
        name="job.html",
        context={"job": job, "result_text": result_text},
    )


@app.post("/jobs/{job_id}/recognize")
async def rerun_recognition(job_id: str):
    try:
        await analyze_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        pass
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/save")
async def save_reviewed_json(
    job_id: str,
    result_json: Annotated[str, Form()],
):
    try:
        payload = json.loads(result_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON 格式错误: {exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="顶层必须是 JSON 对象")
    try:
        save_edited_result(job_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.get("/jobs/{job_id}/export")
async def download_excel(job_id: str):
    try:
        output = export_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=output.name,
    )


@app.get("/jobs/{job_id}/result.json")
async def download_json(job_id: str):
    path = job_dir(job_id) / "result.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="识别结果不存在")
    return FileResponse(path, media_type="application/json", filename=f"{job_id}.json")


@app.get("/jobs/{job_id}/images/{filename}")
async def show_image(job_id: str, filename: str):
    job = load_job(job_id)
    allowed = {
        image.get(key)
        for image in job.get("images", [])
        for key in ("source", "prepared")
        if image.get(key)
    }
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="图片不存在")
    path = job_dir(job_id) / filename
    return FileResponse(path)


@app.get("/api/health")
async def health():
    settings = load_settings()
    return {
        "status": "ok",
        "version": __version__,
        "provider": settings.vision.get("provider", "mock"),
        "model": settings.vision.get("model", ""),
    }


if __name__ == "__main__":
    import uvicorn

    settings = load_settings()
    uvicorn.run("lite_app.main:app", host=settings.host, port=settings.port, reload=False)
