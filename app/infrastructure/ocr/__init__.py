from app.infrastructure.ocr.engine import OCREngine, OCRResult
from app.infrastructure.ocr.mock_engine import MockEngine

_engine: OCREngine | None = None


def get_ocr_engine() -> OCREngine:
    global _engine
    if _engine is None:
        _engine = MockEngine()
    return _engine


def set_ocr_engine(engine: OCREngine) -> None:
    global _engine
    _engine = engine
