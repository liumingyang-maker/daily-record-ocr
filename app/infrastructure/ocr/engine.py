from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OCRResult:
    text: str
    confidence: float


class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image_path: str) -> OCRResult: ...
