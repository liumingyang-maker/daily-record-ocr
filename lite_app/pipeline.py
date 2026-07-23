"""Whole-image structured recognition pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lite_app.config import load_settings
from lite_app.image_utils import prepare_image
from lite_app.providers import build_provider
from lite_app.storage import job_dir, load_job, save_job, save_result


def build_prompts(schema_config: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    schema = schema_config.get("schema", {})
    if not isinstance(schema, dict) or not schema:
        raise ValueError("record_schema.yaml must contain a non-empty 'schema' mapping")

    system_prompt = str(
        schema_config.get(
            "system_prompt",
            "You transcribe handwritten production notes into structured JSON.",
        )
    ).strip()
    instructions = str(schema_config.get("instructions", "")).strip()
    schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
    user_prompt = (
        f"{instructions}\n\n"
        "只返回一个 JSON 对象，不要使用 Markdown 代码块，不要补写图片中看不清的内容。\n"
        "输出必须符合下面的 JSON Schema：\n"
        f"{schema_json}"
    ).strip()
    return system_prompt, user_prompt, schema


def extract_json(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        starts = [index for index in (text.find("{"), text.find("[")) if index >= 0]
        if not starts:
            raise ValueError("Vision model did not return JSON")
        start = min(starts)
        try:
            payload, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Vision model returned invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Top-level recognition result must be a JSON object")
    return payload


def validate_result(result: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(result), key=lambda error: list(error.path))
    formatted: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        formatted.append(f"{location}: {error.message}")
    return formatted


async def analyze_job(job_id: str) -> dict[str, Any]:
    settings = load_settings()
    job = load_job(job_id)
    directory = job_dir(job_id)

    try:
        job.update(status="PREPARING", error="", validation_errors=[])
        save_job(job)

        prepared_paths: list[Path] = []
        for index, image in enumerate(job.get("images", []), start=1):
            source = directory / image["source"]
            prepared_name = f"prepared_{index:02d}.jpg"
            prepared = prepare_image(
                source,
                directory / prepared_name,
                settings.preprocess,
                rotation=str(job.get("rotation", "auto")),
            )
            image["prepared"] = prepared.name
            prepared_paths.append(prepared)

        provider_name = str(settings.vision.get("provider", "mock"))
        model_name = str(settings.vision.get("model", ""))
        job.update(
            status="RECOGNIZING",
            provider=provider_name,
            model=model_name,
        )
        save_job(job)

        system_prompt, user_prompt, schema = build_prompts(settings.schema)
        provider = build_provider(settings)
        raw_response = await provider.analyze(
            prepared_paths, system_prompt, user_prompt, schema
        )
        (directory / "raw_response.txt").write_text(raw_response, encoding="utf-8")

        result = extract_json(raw_response)
        validation_errors = validate_result(result, schema)
        save_result(job_id, result)

        job.update(
            status="NEED_REVIEW" if validation_errors else "READY",
            validation_errors=validation_errors,
            error="",
        )
        save_job(job)
        return job
    except Exception as exc:
        job.update(status="FAILED", error=str(exc))
        save_job(job)
        raise


def save_edited_result(job_id: str, result: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings()
    schema = settings.schema.get("schema", {})
    if not isinstance(schema, dict):
        raise ValueError("Invalid schema configuration")
    errors = validate_result(result, schema)
    save_result(job_id, result)
    job = load_job(job_id)
    job.update(
        status="NEED_REVIEW" if errors else "READY",
        validation_errors=errors,
        error="",
    )
    save_job(job)
    return job
