from __future__ import annotations

import re
import urllib.parse
from typing import Callable

import httpx
from fastapi import HTTPException

from ..services.media_storage import reference_to_data_url
from . import apimart


DEFAULT_IMAGE_MODEL = "gemini-3-pro-image-preview"


def provider_protocol(provider):
    return str((provider or {}).get("protocol") or "openai").strip().lower()


def is_provider(provider):
    return provider_protocol(provider) == "gemini"


def uses_google_api_key_header(provider):
    base_url = str((provider or {}).get("base_url") or "").strip()
    if not base_url:
        return is_provider(provider)
    parsed = urllib.parse.urlsplit(base_url if "://" in base_url else f"https://{base_url}")
    host = parsed.netloc.lower()
    return host.endswith("googleapis.com")


def is_image_model(model):
    value = str(model or "").strip().lower()
    if value.startswith("models/"):
        value = value[len("models/"):]
    return value.startswith("gemini-") and "image" in value


def model_name(model):
    value = str(model or DEFAULT_IMAGE_MODEL).strip()
    if not value:
        raise HTTPException(status_code=400, detail="模型名称不能为空")
    if len(value) > 240 or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise HTTPException(status_code=400, detail=f"模型名称不合法：{value}")
    return value[len("models/"):] if value.startswith("models/") else value


def endpoint_url(provider, model, provider_endpoint_url: Callable | None = None):
    encoded_model = urllib.parse.quote(model_name(model), safe="")
    default_path = f"/v1beta/models/{encoded_model}:generateContent"
    override = str((provider or {}).get("image_generation_endpoint") or "").strip()
    if override and provider_endpoint_url:
        url = provider_endpoint_url(provider, "image_generation_endpoint", default_path)
        return url.replace("{model}", encoded_model).replace("%7Bmodel%7D", encoded_model)

    base_url = str((provider or {}).get("base_url") or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail=f"{(provider or {}).get('name') or 'Gemini'} 未配置 Base URL")
    if base_url.endswith("/v1beta"):
        return f"{base_url}/models/{encoded_model}:generateContent"
    if base_url.endswith("/v1"):
        return f"{base_url[:-3]}/v1beta/models/{encoded_model}:generateContent"
    return f"{base_url}{default_path}"


def image_config(size, parse_size_pair: Callable):
    width, height = parse_size_pair(size)
    if not width or not height:
        raw = str(size or "").strip().upper()
        if raw in {"1K", "2K", "4K"}:
            return {"aspectRatio": "1:1", "imageSize": raw}
        if re.fullmatch(r"\d+\s*:\s*\d+", raw):
            return {"aspectRatio": raw.replace(" ", ""), "imageSize": "1K"}
        return {"aspectRatio": "1:1", "imageSize": "2K"}
    aspect_ratio, resolution = apimart.size_resolution(size, parse_size_pair)
    return {"aspectRatio": aspect_ratio, "imageSize": resolution.upper()}


def reference_part(ref):
    value = reference_to_data_url(ref, max_size=1536)
    if not value:
        return None
    if isinstance(value, str) and value.startswith("data:image/") and ";base64," in value:
        header, encoded = value.split(";base64,", 1)
        mime_type = header.replace("data:", "", 1) or "image/png"
        return {"inlineData": {"mimeType": mime_type, "data": encoded}}
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return {"inlineData": {"mimeType": "image/png", "data": value}}
    return None


def request_body(prompt, size, reference_images, parse_size_pair: Callable):
    parts = [{"text": str(prompt or "").strip()}]
    for ref in (reference_images or [])[:16]:
        part = reference_part(ref)
        if part:
            parts.append(part)
    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": image_config(size, parse_size_pair),
        },
    }


async def generate_image(
    *,
    provider,
    prompt,
    size,
    model,
    reference_images=None,
    headers_factory: Callable,
    provider_endpoint_url: Callable,
    parse_size_pair: Callable,
    extract_image: Callable,
):
    endpoint = endpoint_url(provider, model, provider_endpoint_url)
    body = request_body(prompt, size, reference_images, parse_size_pair)
    headers = headers_factory(provider=provider, force_bearer=not uses_google_api_key_header(provider))
    timeout = httpx.Timeout(connect=20.0, read=1800.0, write=120.0, pool=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(endpoint, headers=headers, json=body)
        response.raise_for_status()
        raw = response.json()
        return extract_image(raw), raw
