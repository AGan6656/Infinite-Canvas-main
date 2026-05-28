from __future__ import annotations

import base64
import mimetypes
import os
import re
from io import BytesIO
from typing import Callable

from PIL import Image

from ..services.media_storage import content_type_for_path, output_file_from_url
from ..services.media_storage import reference_to_data_url


def unwrap_response(raw):
    if isinstance(raw, dict) and "data" in raw and isinstance(raw.get("data"), dict) and "choices" not in raw:
        return raw["data"]
    return raw


def provider_protocol(provider):
    return str((provider or {}).get("protocol") or "openai").strip().lower()


def is_provider(provider):
    base_url = str((provider or {}).get("base_url") or "").lower()
    return provider_protocol(provider) == "apimart" or "apimart.ai" in base_url


def valid_video_image_input(value: str) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    return value.startswith("http://") or value.startswith("https://") or value.startswith("asset://")


def is_veo31_model(model: str) -> bool:
    return str(model or "").strip().lower().startswith("veo3.1")


def veo31_model(model: str) -> str:
    value = str(model or "").strip().lower()
    aliases = {
        "veo3.1": "veo3.1-fast",
        "veo3.1-pro": "veo3.1-quality",
        "veo3.1-preview": "veo3.1-fast",
    }
    value = aliases.get(value, value or "veo3.1-fast")
    allowed = {"veo3.1-fast", "veo3.1-quality", "veo3.1-lite"}
    return value if value in allowed else "veo3.1-fast"


def veo31_aspect(aspect: str) -> str:
    value = str(aspect or "16:9").strip()
    return value if value in {"16:9", "9:16"} else "16:9"


def veo31_resolution(resolution: str) -> str:
    value = str(resolution or "").strip().lower()
    aliases = {"": "720p", "auto": "720p", "480p": "720p", "780p": "720p", "1080": "1080p", "4k": "4k"}
    value = aliases.get(value, value)
    return value if value in {"720p", "1080p", "4k"} else "720p"


def upload_file_payload(path: str):
    max_bytes = 9_500_000
    size = os.path.getsize(path)
    if size <= max_bytes:
        with open(path, "rb") as fh:
            return os.path.basename(path), fh.read(), content_type_for_path(path)
    with Image.open(path) as img:
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        quality = 92
        while quality >= 62:
            buf = BytesIO()
            bg.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes:
                name = os.path.splitext(os.path.basename(path))[0] + ".jpg"
                return name, data, "image/jpeg"
            quality -= 8
    raise ValueError("Image exceeds the APIMart 10MB upload limit after compression")


def extract_asset_url(payload):
    if isinstance(payload, list):
        for item in payload:
            found = extract_asset_url(item)
            if found:
                return found
        return ""
    if not isinstance(payload, dict):
        return ""
    for key in ("url", "asset_url", "assetUrl", "uri", "file_url", "fileUrl"):
        value = str(payload.get(key) or "").strip()
        if valid_video_image_input(value):
            return value
    for key in ("asset_id", "assetId", "file_id", "fileId", "id"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value if value.startswith("asset://") else f"asset://{value}"
    for key in ("data", "file", "asset", "result"):
        found = extract_asset_url(payload.get(key))
        if found:
            return found
    return ""


def upload_payload_from_bytes(data: bytes, mime: str, name_hint: str = "image"):
    max_bytes = 9_500_000
    ext = mimetypes.guess_extension(mime or "image/png") or ".png"
    if len(data) <= max_bytes and (mime or "").lower() in ("image/png", "image/jpeg", "image/webp"):
        return f"{name_hint}{ext}", data, (mime or "image/png")
    with Image.open(BytesIO(data)) as img:
        has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
        if has_alpha:
            base = img.convert("RGBA")
            bg = Image.new("RGB", base.size, (255, 255, 255))
            bg.paste(base, mask=base.split()[-1])
            target = bg
        else:
            target = img.convert("RGB")
        quality = 92
        while quality >= 62:
            buf = BytesIO()
            target.save(buf, format="JPEG", quality=quality, optimize=True)
            payload = buf.getvalue()
            if len(payload) <= max_bytes:
                return f"{name_hint}.jpg", payload, "image/jpeg"
            quality -= 8
    raise ValueError("Data URL image exceeds the APIMart 10MB upload limit after compression")


def size_resolution(size, parse_size_pair: Callable):
    width, height = parse_size_pair(size)
    if not width or not height:
        raw = str(size or "").strip().lower()
        if raw in {"1k", "2k", "4k"}:
            return "1:1", raw
        if re.fullmatch(r"(auto|\d+\s*:\s*\d+)", raw):
            return raw.replace(" ", ""), "1k"
        return "1:1", "1k"
    long_edge = max(width, height)
    pixels = width * height
    if long_edge >= 3000 or pixels > 4_500_000:
        resolution = "4k"
    elif long_edge >= 1800 or pixels > 1_800_000:
        resolution = "2k"
    else:
        resolution = "1k"
    common = [
        (1, 1, "1:1"), (3, 2, "3:2"), (2, 3, "2:3"), (4, 3, "4:3"), (3, 4, "3:4"),
        (5, 4, "5:4"), (4, 5, "4:5"), (16, 9, "16:9"), (9, 16, "9:16"),
        (2, 1, "2:1"), (1, 2, "1:2"), (3, 1, "3:1"), (1, 3, "1:3"),
        (21, 9, "21:9"), (9, 21, "9:21"),
    ]
    ratio = width / height
    best = min(common, key=lambda item: abs(ratio - item[0] / item[1]))
    return best[2], resolution


async def upload_image(client, provider, ref_url: str, *, api_root: str, headers_factory: Callable) -> str:
    ref_url = str(ref_url or "").strip()
    if not ref_url:
        return "ERR:empty URL"
    if ref_url.startswith("http://") or ref_url.startswith("https://") or ref_url.startswith("asset://"):
        return ref_url
    upload_url = f"{api_root.rstrip('/')}/v1/uploads/images"
    if ref_url.startswith("data:"):
        try:
            if ";base64," not in ref_url:
                return "ERR:unsupported data URL"
            header, encoded = ref_url.split(";base64,", 1)
            mime = header.split(":", 1)[1].split(";", 1)[0] if ":" in header else "image/png"
            raw = base64.b64decode(encoded)
            filename, content, ct = upload_payload_from_bytes(raw, mime, name_hint="canvas_image")
            files = {"file": (filename, content, ct)}
            resp = await client.post(upload_url, headers=headers_factory(json_body=False, provider=provider), files=files, timeout=60)
            if resp.status_code in (200, 201):
                url = extract_asset_url(resp.json())
                if valid_video_image_input(url):
                    return url
                return "ERR:APIMart upload response did not include a usable URL"
            return f"ERR:APIMart upload failed({resp.status_code})"
        except ValueError as e:
            return f"ERR:{e}"
        except Exception as e:
            return f"ERR:upload failed {e}"
    if ref_url.startswith("/output/") or ref_url.startswith("/assets/"):
        path = output_file_from_url(ref_url)
        if not path:
            return "ERR:local file does not exist"
        try:
            filename, content, ct = upload_file_payload(path)
            files = {"file": (filename, content, ct)}
            resp = await client.post(upload_url, headers=headers_factory(json_body=False, provider=provider), files=files, timeout=60)
            if resp.status_code in (200, 201):
                url = extract_asset_url(resp.json())
                if valid_video_image_input(url):
                    return url
                return "ERR:APIMart upload response did not include a usable URL"
            return f"ERR:APIMart upload failed({resp.status_code})"
        except ValueError as e:
            return f"ERR:{e}"
        except Exception as e:
            return f"ERR:upload failed {e}"
    return "ERR:unsupported image source"


async def generate_image(
    *,
    provider,
    prompt,
    size,
    model,
    reference_images=None,
    gen_url,
    headers_factory: Callable,
    parse_size_pair: Callable,
    extract_image: Callable,
    extract_task_id: Callable,
    wait_for_image_task: Callable,
):
    import httpx
    from fastapi import HTTPException

    apimart_size, resolution = size_resolution(size, parse_size_pair)
    refs = [ref for ref in (reference_images or []) if ref.get("url")]
    mask_refs = [
        ref for ref in refs
        if str(ref.get("role") or "").strip().lower() == "mask"
        or str(ref.get("name") or "").lower().endswith("_mask.png")
    ]
    image_refs = [ref for ref in refs if ref not in mask_refs]
    body = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": apimart_size,
        "resolution": resolution,
        "official_fallback": False,
    }
    if image_refs:
        body["image_urls"] = [reference_to_data_url(ref, max_size=1536) for ref in image_refs[:16]]
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=20.0, read=1800.0, write=120.0, pool=20.0)) as client:
        response = await client.post(gen_url, headers=headers_factory(provider=provider), json=body)
        response.raise_for_status()
        raw = response.json()
        try:
            return extract_image(raw), raw
        except HTTPException:
            task_id = extract_task_id(raw)
            if not task_id:
                raise
        task_result = await wait_for_image_task(client, task_id, provider)
        return extract_image(task_result), task_result
