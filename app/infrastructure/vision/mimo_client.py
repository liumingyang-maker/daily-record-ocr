from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MimoResult:
    fields: dict[str, dict] = field(default_factory=dict)
    raw_response: str = ""
    success: bool = False
    error: str = ""


class MimoClient(ABC):
    @abstractmethod
    def recognize_record(self, image_path: str) -> MimoResult: ...
