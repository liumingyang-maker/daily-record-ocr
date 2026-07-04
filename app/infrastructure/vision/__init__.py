from app.infrastructure.vision.mimo_client import MimoClient, MimoResult
from app.infrastructure.vision.mock_mimo_client import MockMimoClient

_client: MimoClient | None = None


def get_mimo_client() -> MimoClient | None:
    global _client
    if _client is None:
        _client = MockMimoClient()
    return _client


def set_mimo_client(client: MimoClient | None) -> None:
    global _client
    _client = client
