"""Pluggable vision-model providers.

The built-in adapter targets OpenAI-compatible chat-completions APIs, which also
covers many local model servers. A custom provider only needs to implement the
``VisionProvider.analyze`` method and be added to ``build_provider``.
"""

from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from lite_app.config import Settings


class VisionProvider(ABC):
    @abstractmethod
    async def analyze(
        self,
        image_paths: list[Path],
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> str:
        """Return the model's raw text response."""


class MockProvider(VisionProvider):
    def __init__(self, result_path: Path):
        self.result_path = result_path

    async def analyze(
        self,
        image_paths: list[Path],
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> str:
        del image_paths, system_prompt, user_prompt, json_schema
        with self.result_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return json.dumps(payload, ensure_ascii=False)


class OpenAICompatibleProvider(VisionProvider):
    def __init__(self, config: dict[str, Any]):
        self.config = config

    @staticmethod
    def _data_url(path: Path) -> str:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    async def analyze(
        self,
        image_paths: list[Path],
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> str:
        base_url = str(self.config.get("base_url", "")).rstrip("/")
        endpoint = str(self.config.get("endpoint", "/chat/completions"))
        if not base_url:
            raise ValueError("vision.base_url is required for openai_compatible provider")

        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        detail = str(self.config.get("image_detail", "high"))
        for path in image_paths:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._data_url(path), "detail": detail},
                }
            )

        payload: dict[str, Any] = {
            "model": str(self.config.get("model", "")),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "temperature": float(self.config.get("temperature", 0)),
        }

        if bool(self.config.get("use_json_schema", False)):
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": str(self.config.get("schema_name", "handwritten_record")),
                    "strict": True,
                    "schema": json_schema,
                },
            }

        extra_body = self.config.get("extra_body", {})
        if isinstance(extra_body, dict):
            payload.update(extra_body)

        headers = {"Content-Type": "application/json"}
        api_key = str(self.config.get("api_key", ""))
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        extra_headers = self.config.get("extra_headers", {})
        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items()})

        timeout = float(self.config.get("timeout_seconds", 120))
        url = f"{base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.is_error:
            detail_text = response.text[:2000]
            raise RuntimeError(
                f"Vision API returned HTTP {response.status_code}: {detail_text}"
            )

        data = response.json()
        try:
            content_value = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected vision API response: {data}") from exc

        if isinstance(content_value, str):
            return content_value
        if isinstance(content_value, list):
            pieces: list[str] = []
            for part in content_value:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    pieces.append(part["text"])
            if pieces:
                return "\n".join(pieces)
        raise RuntimeError("Vision API response did not contain text content")


def build_provider(settings: Settings) -> VisionProvider:
    config = settings.vision
    provider_name = str(config.get("provider", "mock")).strip().lower()
    if provider_name == "mock":
        result_path = settings.resolve_path(
            str(config.get("mock_result", "config/mock_result.json"))
        )
        return MockProvider(result_path)
    if provider_name in {"openai", "openai_compatible"}:
        return OpenAICompatibleProvider(config)
    raise ValueError(
        f"Unknown vision provider '{provider_name}'. "
        "Add an adapter in lite_app/providers.py or use openai_compatible."
    )
