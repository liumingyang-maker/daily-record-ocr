"""Compatibility entry point for the lightweight application."""

from lite_app.main import app


if __name__ == "__main__":
    import uvicorn

    from lite_app.config import load_settings

    settings = load_settings()
    uvicorn.run("lite_app.main:app", host=settings.host, port=settings.port, reload=False)
