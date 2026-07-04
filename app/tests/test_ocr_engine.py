import app.infrastructure.ocr as ocr_mod
from app.infrastructure.ocr import get_ocr_engine, set_ocr_engine
from app.infrastructure.ocr.engine import OCREngine, OCRResult
from app.infrastructure.ocr.mock_engine import MockEngine


def test_mock_engine_recognizes_time():
    engine = MockEngine()
    result = engine.recognize("/path/to/time_field.png")
    assert result.text == "08:30"
    assert result.confidence == 0.95


def test_mock_engine_recognizes_material():
    engine = MockEngine()
    result = engine.recognize("material_sample.jpg")
    assert result.text == "铝合金"
    assert result.confidence == 0.95


def test_mock_engine_unknown_field():
    engine = MockEngine()
    result = engine.recognize("unknown_image.png")
    assert result.text == "[未识别]"
    assert result.confidence == 0.0


def test_get_engine_returns_mock():
    ocr_mod._engine = None
    engine = get_ocr_engine()
    assert isinstance(engine, MockEngine)


def test_set_engine():
    class DummyEngine(OCREngine):
        def recognize(self, image_path: str) -> OCRResult:
            return OCRResult(text="dummy", confidence=1.0)

    dummy = DummyEngine()
    set_ocr_engine(dummy)
    assert get_ocr_engine() is dummy
    ocr_mod._engine = None
