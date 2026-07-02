"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import engine
from app.interfaces.web_routes import web_router
from app.interfaces.api_routes import api_router

INTERFACE_DIR = Path(__file__).resolve().parent / "interfaces"

app = FastAPI(title="每日生产记录智能识别系统")

app.mount("/static", StaticFiles(directory=INTERFACE_DIR / "static"), name="static")

app.include_router(web_router)
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    import uvicorn
    from app.settings import APP_HOST, APP_PORT

    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=True)
