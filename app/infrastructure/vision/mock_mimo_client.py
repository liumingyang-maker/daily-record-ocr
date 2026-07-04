from app.infrastructure.vision.mimo_client import MimoClient, MimoResult

PRESET: dict[str, dict] = {
    "time": {"value": "08:30", "confidence": 0.98, "raw_text": "08:30"},
    "customer_queue": {"value": "A-001", "confidence": 0.95, "raw_text": "A-001"},
    "material_name": {
        "value": "铝合金",
        "confidence": 0.92,
        "raw_text": "铝合金",
    },
}


class MockMimoClient(MimoClient):
    def recognize_record(self, image_path: str) -> MimoResult:
        fields = {
            key: {
                "value": info["value"],
                "confidence": info["confidence"],
                "raw_text": info["raw_text"],
            }
            for key, info in PRESET.items()
        }
        return MimoResult(
            fields=fields,
            raw_response='{"mock": true}',
            success=True,
        )
