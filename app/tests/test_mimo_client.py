"""Tests for MiMo API client abstraction."""

from app.infrastructure.vision import get_mimo_client, set_mimo_client
from app.infrastructure.vision.mimo_client import MimoClient, MimoResult
from app.infrastructure.vision.mock_mimo_client import MockMimoClient


def test_mock_mimo_client_returns_preset_fields():
    client = MockMimoClient()
    result = client.recognize_record("/tmp/fake_record.jpg")

    assert result.success is True
    assert "time" in result.fields
    assert result.fields["time"]["value"] == "08:30"
    assert result.fields["time"]["confidence"] == 0.98
    assert "customer_queue" in result.fields
    assert "material_name" in result.fields


def test_get_set_mimo_client():
    original = get_mimo_client()
    assert isinstance(original, MockMimoClient)

    class StubClient(MimoClient):
        def recognize_record(self, image_path: str) -> MimoResult:
            return MimoResult(success=True, raw_response="stub")

    stub = StubClient()
    set_mimo_client(stub)
    assert get_mimo_client() is stub

    set_mimo_client(None)
    refreshed = get_mimo_client()
    assert isinstance(refreshed, MockMimoClient)

    set_mimo_client(original)
