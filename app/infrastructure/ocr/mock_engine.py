from app.infrastructure.ocr.engine import OCREngine, OCRResult

PRESET: dict[str, str] = {
    "time": "08:30",
    "customer_queue": "A-001",
    "color": "红色",
    "date_batch_no": "20260703-01",
    "material": "铝合金",
    "usage": "结构件",
    "main_speed": "1200",
    "temperature": "25.5",
}


class MockEngine(OCREngine):
    def recognize(self, image_path: str) -> OCRResult:
        for key, value in PRESET.items():
            if key in image_path:
                return OCRResult(text=value, confidence=0.95)
        return OCRResult(text="[未识别]", confidence=0.0)
