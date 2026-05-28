from __future__ import annotations

from ..core_imports import *

VIDEO_URL_KEYS = (
    "url", "video_url", "videoUrl", "mp4_url", "mp4Url",
    "output", "output_url", "outputUrl", "download_url", "downloadUrl",
    "video", "src", "uri", "preview_url", "previewUrl", "path",
    "last_frame_url", "lastFrameUrl",
)

VIDEO_CONTAINER_KEYS = ("videos", "outputs", "data", "result", "content", "detail", "output")

VIDEO_TASK_SUCCESS_STATUSES = {
    "SUCCESS", "SUCCEED", "SUCCEEDED", "COMPLETED", "COMPLETE",
    "DONE", "FINISHED", "FINISH", "OK", "READY",
}
VIDEO_TASK_FAILURE_STATUSES = {
    "FAILURE", "FAILED", "FAIL", "ERROR", "ERRORED",
    "CANCELED", "CANCELLED", "TIMEOUT", "TIMEDOUT", "REJECTED", "EXPIRED",
}

def _collect_video_url(value, urls):
    if not value:
        return
    if isinstance(value, str):
        if value.startswith("http://") or value.startswith("https://") or value.startswith("/output/") or value.startswith("/assets/"):
            urls.append(value)
        return
    if isinstance(value, list):
        for item in value:
            _collect_video_url(item, urls)
        return
    if isinstance(value, dict):
        for key in VIDEO_CONTAINER_KEYS:
            if key in value:
                _collect_video_url(value.get(key), urls)
        for key in VIDEO_URL_KEYS:
            if key in value:
                _collect_video_url(value.get(key), urls)

def video_output_urls(raw):
    urls = []
    if not isinstance(raw, dict):
        return urls
    candidates = [raw]
    data = raw.get("data")
    content = raw.get("content")
    if isinstance(data, dict):
        candidates.append(data)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                candidates.append(item)
    if isinstance(content, dict):
        candidates.append(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                candidates.append(item)
    for node in list(candidates):
        result = node.get("result") if isinstance(node, dict) else None
        if isinstance(result, dict):
            candidates.append(result)
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    candidates.append(item)
    for node in candidates:
        if not isinstance(node, dict):
            continue
        for key in VIDEO_CONTAINER_KEYS:
            value = node.get(key)
            if value:
                _collect_video_url(value, urls)
        for key in VIDEO_URL_KEYS:
            if key in node:
                _collect_video_url(node.get(key), urls)
    deduped = []
    for url in urls:
        if isinstance(url, str) and url and url not in deduped:
            deduped.append(url)
    return deduped

def video_api_root(provider):
    base_url = (provider.get("base_url") or AI_BASE_URL).rstrip("/")
    if is_volcengine_provider(provider):
        if base_url.endswith("/api/v3"):
            base_url = base_url[: -len("/api/v3")]
        return base_url
    if base_url.endswith("/v1") or base_url.endswith("/v2"):
        base_url = base_url.rsplit("/", 1)[0]
    return base_url

def is_openai_unified_video_provider(provider):
    return provider_protocol(provider) == "openai" and not is_apimart_provider(provider) and not is_volcengine_provider(provider)

def openai_video_url(provider, task_id="", suffix=""):
    base_url = video_api_root(provider)
    path = "/v1/videos"
    if task_id:
        path += f"/{task_id}"
    if suffix:
        path += suffix
    return f"{base_url}{path}"

def legacy_openai_video_body(payload, image_payload=None):
    image_payload = image_payload if image_payload is not None else [
        reference_to_data_url(ref.dict(), max_size=1536)
        for ref in payload.images[:4]
        if ref.url
    ]
    body = {
        "prompt": payload.prompt,
        "model": selected_model(payload.model, "veo3-fast"),
        "duration": payload.duration,
        "watermark": payload.watermark,
    }
    if payload.aspect_ratio:
        body["aspect_ratio"] = payload.aspect_ratio
        body["ratio"] = payload.aspect_ratio
    if payload.size:
        body["size"] = payload.size
    if payload.resolution:
        body["resolution"] = payload.resolution
    if image_payload:
        body["images"] = image_payload
    if payload.videos:
        body["videos"] = [v for v in payload.videos if v]
    if payload.enhance_prompt:
        body["enhance_prompt"] = True
    if payload.enable_upsample:
        body["enable_upsample"] = True
    if payload.seed is not None:
        body["seed"] = payload.seed
    if payload.camerafixed:
        body["camerafixed"] = True
    if payload.return_last_frame:
        body["return_last_frame"] = True
    if payload.generate_audio:
        body["generate_audio"] = True
    return body

def openai_video_aspect_ratio(model, aspect_ratio):
    ratio = str(aspect_ratio or "").strip()
    if not ratio or ratio in {"keep_ratio", "adaptive"}:
        return ""
    if "grok" not in str(model or "").lower():
        return ratio
    if ratio == "1:1":
        return "1:1"
    if ratio in {"9:16", "9:21", "3:4", "2:3"}:
        return "2:3"
    if ratio in {"16:9", "21:9", "4:3", "3:2"}:
        return "3:2"
    return ratio if ratio in {"2:3", "3:2", "1:1"} else ""

def openai_video_size(payload):
    value = str(payload.size or payload.resolution or "").strip()
    if not value:
        return ""
    normalized = value.upper().replace(" ", "")
    if normalized == "780P":
        return "720P"
    if re.fullmatch(r"\d{3,4}P", normalized):
        return normalized
    return value

def openai_video_duration(payload):
    try:
        return max(1, min(60, int(payload.duration or 0)))
    except Exception:
        return 5

def data_url_to_file_part(value, fallback_name="image"):
    if not isinstance(value, str) or not value.startswith("data:") or ";base64," not in value:
        return None
    header, encoded = value.split(";base64,", 1)
    mime = header.replace("data:", "", 1) or "application/octet-stream"
    try:
        raw = base64.b64decode(encoded)
    except Exception:
        return None
    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(mime.lower(), ".bin")
    return (f"{fallback_name}{ext}", raw, mime)

def reference_to_openai_video_file(ref, index):
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(ref.name or f"reference_{index}").strip()) or f"reference_{index}"
    path = output_file_from_url(ref.url)
    if path:
        content_type = content_type_for_path(path)
        with open(path, "rb") as f:
            return (os.path.basename(path) or f"{name}.png", f.read(), content_type)
    value = reference_to_data_url(ref.dict(), max_size=1536)
    return data_url_to_file_part(value, name)

def append_openai_video_field(files, name, value):
    if value is None:
        return
    if isinstance(value, bool):
        value = "true" if value else "false"
    text = str(value).strip()
    if text:
        files.append((name, (None, text)))

def openai_video_common_fields(payload):
    model = selected_model(payload.model, "veo3-fast")
    fields = {
        "model": model,
        "prompt": payload.prompt,
    }
    duration = openai_video_duration(payload)
    if "grok" in model.lower():
        fields["seconds"] = duration
    else:
        fields["duration"] = duration
        fields["seconds"] = duration
    aspect_ratio = openai_video_aspect_ratio(model, payload.aspect_ratio)
    if aspect_ratio:
        fields["aspect_ratio"] = aspect_ratio
    size = openai_video_size(payload)
    if size:
        fields["size"] = size
    if payload.seed is not None:
        fields["seed"] = payload.seed
    if payload.watermark:
        fields["watermark"] = payload.watermark
    if payload.enhance_prompt:
        fields["enhance_prompt"] = payload.enhance_prompt
    if payload.enable_upsample:
        fields["enable_upsample"] = payload.enable_upsample
    if payload.camerafixed:
        fields["camerafixed"] = payload.camerafixed
    if payload.return_last_frame:
        fields["return_last_frame"] = payload.return_last_frame
    if payload.generate_audio:
        fields["generate_audio"] = payload.generate_audio
    return fields

def build_openai_unified_video_request(payload):
    fields = openai_video_common_fields(payload)

    files = []
    for key, value in fields.items():
        append_openai_video_field(files, key, value)

    reference_image_urls = []
    for idx, ref in enumerate(payload.images[:9], start=1):
        if not ref.url:
            continue
        file_part = reference_to_openai_video_file(ref, idx)
        if file_part:
            files.append(("input_reference", file_part))
            continue
        role = str(ref.role or "").strip()
        url = str(ref.url or "").strip()
        if not url:
            continue
        if role == "last_frame":
            append_openai_video_field(files, "last_frame_image_url", url)
        elif role == "first_frame" or idx == 1:
            append_openai_video_field(files, "image_url", url)
            append_openai_video_field(files, "first_frame_image_url", url)
        else:
            reference_image_urls.append(url)
    for url in reference_image_urls:
        append_openai_video_field(files, "reference_image_urls", url)
    if reference_image_urls:
        append_openai_video_field(files, "reference_image_url", reference_image_urls[0])

    video_urls = [str(v or "").strip() for v in payload.videos if str(v or "").strip()]
    for url in video_urls:
        append_openai_video_field(files, "reference_video_urls", url)
    if video_urls:
        append_openai_video_field(files, "reference_video_url", video_urls[0])

    return files

def build_openai_unified_video_json_body(payload, image_payload=None):
    body = openai_video_common_fields(payload)
    image_payload = image_payload if image_payload is not None else [
        reference_to_data_url(ref.dict(), max_size=1536)
        for ref in payload.images[:9]
        if ref.url
    ]
    reference_image_urls = []
    for idx, ref in enumerate(payload.images[:9]):
        if idx >= len(image_payload):
            break
        url = image_payload[idx]
        if not url:
            continue
        role = str(ref.role or "").strip()
        if role == "last_frame":
            body["last_frame_image_url"] = url
        elif role == "first_frame" or idx == 0:
            body["image_url"] = url
            body["first_frame_image_url"] = url
        else:
            reference_image_urls.append(url)
    if reference_image_urls:
        body["reference_image_url"] = reference_image_urls[0]
        body["reference_image_urls"] = reference_image_urls
    video_urls = [str(v or "").strip() for v in payload.videos if str(v or "").strip()]
    if video_urls:
        body["reference_video_url"] = video_urls[0]
        body["reference_video_urls"] = video_urls
        body["video_urls"] = video_urls
    return body

def should_retry_openai_video_json(exc):
    status = getattr(exc.response, "status_code", 0)
    if status in {415, 422}:
        return True
    text = (getattr(exc.response, "text", "") or "").lower()
    return status == 400 and any(token in text for token in ("content-type", "multipart", "form-data", "json"))

def should_fallback_to_legacy_video(exc):
    status = getattr(exc.response, "status_code", 0)
    if status in {404, 405}:
        return True
    text = (getattr(exc.response, "text", "") or "").lower()
    return "not found" in text and "/v1/videos" in text

def video_bytes_extension(content_type="", source_url=""):
    content_type = str(content_type or "").lower()
    clean_path = urllib.parse.urlparse(str(source_url or "")).path
    ext = os.path.splitext(clean_path)[1].lower()
    if ext in {".mp4", ".webm", ".mov", ".m4v"}:
        return ext
    if "webm" in content_type:
        return ".webm"
    if "quicktime" in content_type or "mov" in content_type:
        return ".mov"
    return ".mp4"

def save_video_bytes_to_output(content, content_type="", source_url="", prefix="video_", category="output"):
    if not content:
        return ""
    ext = video_bytes_extension(content_type, source_url)
    filename = f"{prefix}{uuid.uuid4().hex[:10]}{ext}"
    path = output_path_for(filename, category)
    with open(path, "wb") as f:
        f.write(content)
    return output_url_for(filename, category)

async def fetch_openai_video_content(client, provider, task_id):
    if not task_id:
        return []
    content_url = openai_video_url(provider, task_id, "/content")
    headers = api_headers(json_body=False, provider=provider)
    headers["Accept"] = "*/*"
    response = await client.get(content_url, headers=headers)
    if response.status_code in {404, 405}:
        return []
    response.raise_for_status()
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "json" in content_type:
        try:
            raw = response.json()
        except Exception:
            raw = {}
        urls = video_output_urls(raw)
        return [await save_remote_video_to_output(url) for url in urls]
    return [save_video_bytes_to_output(response.content, content_type, str(response.url))]

async def wait_for_video_task(client, provider, task_id, api_style=""):
    base_url = video_api_root(provider)
    if not base_url:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider['id']} 未配置 Base URL")
    if is_apimart_provider(provider):
        task_path = f"{base_url}/tasks/{task_id}" if base_url.endswith("/v1") else f"{base_url}/v1/tasks/{task_id}"
        task_url = f"{task_path}?language=zh"
    elif is_volcengine_provider(provider):
        task_url = f"{base_url}/api/v3/contents/generations/tasks/{task_id}"
    elif api_style == "openai_v1" or (api_style != "legacy_v2" and is_openai_unified_video_provider(provider)):
        task_url = openai_video_url(provider, task_id)
    else:
        task_url = f"{base_url}/v2/videos/generations/{task_id}"
    deadline = time.monotonic() + VIDEO_POLL_TIMEOUT
    delay = max(2.0, IMAGE_POLL_INTERVAL)
    last_payload = {}
    while time.monotonic() < deadline:
        await asyncio.sleep(delay)
        response = await client.get(task_url, headers=api_headers(provider=provider))
        response.raise_for_status()
        raw = response.json()
        last_payload = raw
        task_data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        status = str(task_data.get("status") or task_data.get("task_status") or raw.get("status") or raw.get("task_status") or "").upper()
        if status in VIDEO_TASK_SUCCESS_STATUSES:
            return raw
        # Some providers omit status but already include a video URL; treat that as success.
        if not status and video_output_urls(raw):
            return raw
        if status in VIDEO_TASK_FAILURE_STATUSES:
            error = task_data.get("error") if isinstance(task_data.get("error"), dict) else {}
            reason = task_data.get("fail_reason") or task_data.get("message") or error.get("message") or raw.get("error") or raw.get("message") or str(raw)
            raise HTTPException(status_code=502, detail=f"视频生成任务失败：{reason}")
        delay = min(delay * 1.6, 12)
    raise HTTPException(status_code=504, detail=f"视频生成任务超时：{last_payload or task_id}")

def apimart_video_size(size):
    value = str(size or "16:9").strip()
    if value == "keep_ratio":
        return "adaptive"
    allowed = {"16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "adaptive"}
    return value if value in allowed else "16:9"

def volcengine_video_prompt_text(prompt, aspect_ratio="", duration=None):
    text = str(prompt or "").strip()
    suffixes = []
    ratio = str(aspect_ratio or "").strip()
    if ratio:
        suffixes.append(f"--ratio {ratio}")
    if not suffixes:
        return text
    suffix_text = " ".join(suffixes)
    return f"{text} {suffix_text}".strip() if text else suffix_text

@app.post("/api/canvas-video")
async def canvas_video(payload: CanvasVideoRequest):
    provider = get_api_provider(payload.provider_id)
    base_url = video_api_root(provider)
    if not base_url:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider['id']} 未配置 Base URL")
    api_key = os.getenv(provider_key_env(provider["id"]), "")
    if not api_key:
        raise HTTPException(status_code=400, detail=f"未配置 {provider.get('name') or provider['id']} 的 API Key，请在 API 设置中填写。")
    is_apimart = is_apimart_provider(provider)
    is_volcengine = is_volcengine_provider(provider)
    is_openai_unified = is_openai_unified_video_provider(provider)
    submit_url = (
        f"{base_url}/videos/generations" if is_apimart and base_url.endswith("/v1")
        else f"{base_url}/v1/videos/generations" if is_apimart
        else f"{base_url}/api/v3/contents/generations/tasks" if is_volcengine
        else openai_video_url(provider) if is_openai_unified
        else f"{base_url}/v2/videos/generations"
    )
    requested_model = selected_model(payload.model, "veo3-fast")
    is_veo31 = is_apimart and is_apimart_veo31_model(requested_model)
    try:
        async with httpx.AsyncClient(timeout=VIDEO_POLL_TIMEOUT, follow_redirects=True) as client:
            # --- Build image payload ---
            if is_apimart:
                # APIMart only accepts http/https or asset:// URLs, so upload local images first.
                image_with_roles = []
                invalid_images = []  # Each item is (original URL, failure reason).
                apimart_model = apimart_veo31_model(requested_model) if is_veo31 else ""
                if apimart_model == "veo3.1-lite" and payload.images:
                    raise HTTPException(status_code=400, detail="veo3.1-lite 不支持图片输入，请改用 veo3.1-fast 或 veo3.1-quality。")
                image_limit = 0 if apimart_model == "veo3.1-lite" else (3 if is_veo31 else 9)
                for ref in payload.images[:image_limit]:
                    if not ref.url:
                        continue
                    role = str(ref.role or "").strip()
                    if not is_veo31 and role in {"first_frame", "last_frame", "reference_image"}:
                        up_url = await upload_image_for_apimart(client, provider, ref.url)
                        if valid_apimart_video_image_input(up_url):
                            image_with_roles.append({"url": up_url, "role": role})
                        else:
                            reason = up_url[4:] if isinstance(up_url, str) and up_url.startswith("ERR:") else "未知错误"
                            invalid_images.append((ref.url, reason))
                image_payload = []
                if not image_with_roles:
                    for ref in payload.images[:image_limit]:
                        if not ref.url:
                            continue
                        up_url = await upload_image_for_apimart(client, provider, ref.url)
                        if valid_apimart_video_image_input(up_url):
                            image_payload.append(up_url)
                        else:
                            reason = up_url[4:] if isinstance(up_url, str) and up_url.startswith("ERR:") else "未知错误"
                            invalid_images.append((ref.url, reason))
                if payload.images and not image_with_roles and not image_payload:
                    first_url, first_reason = invalid_images[0] if invalid_images else ("", "未知错误")
                    sample = invalid_video_image_preview(first_url)
                    raise HTTPException(status_code=400, detail=f"输入图片无法转换为视频接口支持的格式：{sample}\n原因：{first_reason}\n请确认本地文件存在且不超过 10MB；VEO3.1 需要图片是 APIMart 可访问的 http/https / asset:// / data URL。")
                # --- APIMart request body ---
                if is_veo31:
                    model = apimart_model
                    body = {
                        "prompt": payload.prompt,
                        "model": model,
                        "duration": 8,
                        "aspect_ratio": apimart_veo31_aspect(payload.aspect_ratio),
                        "resolution": apimart_veo31_resolution(payload.resolution),
                    }
                    if image_payload and model != "veo3.1-lite":
                        video_images = image_payload[:3]
                        if model == "veo3.1-quality" and len(video_images) > 2:
                            video_images = video_images[:2]
                        body["image_urls"] = video_images
                        if len(video_images) == 2:
                            body["generation_type"] = "frame"
                        elif len(video_images) >= 3 and model != "veo3.1-quality":
                            body["generation_type"] = "reference"
                    if model != "veo3.1-lite":
                        body["official_fallback"] = False
                else:
                    body = {
                        "prompt": payload.prompt,
                        "model": selected_model(payload.model, "doubao-seedance-2.0"),
                        "duration": payload.duration,
                        "size": apimart_video_size(payload.aspect_ratio or payload.size),
                        "resolution": payload.resolution or "480p",
                    }
                    if image_with_roles:
                        body["image_with_roles"] = image_with_roles
                    elif image_payload:
                        body["image_urls"] = image_payload[:9]
                    if payload.videos:
                        body["video_urls"] = [v for v in payload.videos if v][:3]
                    if payload.seed is not None:
                        body["seed"] = payload.seed
                    if payload.return_last_frame:
                        body["return_last_frame"] = True
                    if payload.generate_audio:
                        body["generate_audio"] = True
            else:
                # Non-APIMart providers use data URLs for OpenAI / ComflyAI-compatible APIs.
                image_payload = []
                image_ref_limit = 9 if is_openai_unified else 4
                for ref in payload.images[:image_ref_limit]:
                    if ref.url:
                        image_payload.append(reference_to_data_url(ref.dict(), max_size=1536))
                if is_volcengine:
                    text = volcengine_video_prompt_text(payload.prompt, payload.aspect_ratio, payload.duration)
                    body = {
                        "model": selected_model(payload.model, "doubao-seedance-2-0-fast-260128"),
                        "content": [
                            {
                                "type": "text",
                                "text": text,
                            }
                        ],
                    }
                    if image_payload:
                        body["content"].append({
                            "type": "image_url",
                            "image_url": {"url": image_payload[0]},
                        })
                    if payload.seed is not None:
                        body["seed"] = payload.seed
                elif is_openai_unified:
                    multipart_body = build_openai_unified_video_request(payload)
                    unified_json_body = build_openai_unified_video_json_body(payload, image_payload)
                    legacy_body = legacy_openai_video_body(payload, image_payload[:4])
                    body = {"model": requested_model, "multipart": True, "fields": [item[0] for item in multipart_body]}
                else:
                    body = legacy_openai_video_body(payload, image_payload)
            # --- Submit video generation request ---
            used_api_style = "openai_v1" if is_openai_unified else ""
            try:
                if is_openai_unified:
                    response = await client.post(
                        submit_url,
                        headers=api_headers(json_body=False, provider=provider),
                        files=multipart_body,
                    )
                else:
                    response = await client.post(submit_url, headers=api_headers(provider=provider), json=body)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if is_openai_unified and should_retry_openai_video_json(exc):
                    try:
                        body = unified_json_body
                        response = await client.post(submit_url, headers=api_headers(provider=provider), json=body)
                        response.raise_for_status()
                    except httpx.HTTPStatusError as json_exc:
                        if should_fallback_to_legacy_video(json_exc) or should_fallback_to_legacy_video(exc):
                            used_api_style = "legacy_v2"
                            submit_url = f"{base_url}/v2/videos/generations"
                            body = legacy_body
                            response = await client.post(submit_url, headers=api_headers(provider=provider), json=body)
                            response.raise_for_status()
                        else:
                            raise
                elif is_openai_unified and should_fallback_to_legacy_video(exc):
                    used_api_style = "legacy_v2"
                    submit_url = f"{base_url}/v2/videos/generations"
                    body = legacy_body
                    response = await client.post(submit_url, headers=api_headers(provider=provider), json=body)
                    response.raise_for_status()
                else:
                    raise
            try:
                raw = response.json()
            except Exception:
                # The upstream returned an HTML error page or another non-JSON response.
                resp_text = response.text[:500]
                raise HTTPException(status_code=502, detail=f"上游视频接口返回非 JSON 响应（状态 {response.status_code}）：{resp_text}")
            task_id = extract_task_id(raw) or raw.get("task_id") or raw.get("id")
            result = raw
            if task_id and not video_output_urls(raw):
                result = await wait_for_video_task(client, provider, task_id, used_api_style)
            urls = video_output_urls(result)
            if not urls and used_api_style == "openai_v1" and task_id:
                local_urls = [url for url in await fetch_openai_video_content(client, provider, task_id) if url]
                if local_urls:
                    return {"videos": local_urls, "task_id": task_id, "raw": result}
            if not urls:
                raise HTTPException(status_code=502, detail=f"视频生成成功但没有返回视频：{result}")
            local_urls = []
            failed_download_urls = []
            for url in urls:
                saved = await save_remote_video_to_output(url)
                if saved == url and isinstance(url, str) and url.startswith(("http://", "https://")):
                    failed_download_urls.append(url)
                else:
                    local_urls.append(saved)
            if failed_download_urls and used_api_style == "openai_v1" and task_id:
                content_urls = [url for url in await fetch_openai_video_content(client, provider, task_id) if url]
                if content_urls:
                    local_urls.extend(content_urls)
            if not local_urls:
                local_urls = failed_download_urls
            return {"videos": local_urls, "task_id": task_id, "raw": result}
    except httpx.HTTPStatusError as exc:
        text = exc.response.text
        try:
            requested_model = body.get("model", "") or payload.model or ""
        except NameError:
            requested_model = payload.model or ""
        provider_name = provider.get('name') or provider['id']
        # 1. The model name is not supported upstream; extract the valid list from the error.
        valid_models_match = re.search(r"not in\s*\[([^\]]+)\]", text)
        if valid_models_match:
            valid_models = [m.strip() for m in valid_models_match.group(1).split(",") if m.strip()]
            sample = valid_models[:30]
            more = f"（共 {len(valid_models)} 个，仅显示前 {len(sample)} 个）" if len(valid_models) > len(sample) else ""
            hint = (
                f"上游「{provider_name}」不识别模型「{requested_model}」。\n\n"
                f"上游支持的视频模型清单{more}：\n  {', '.join(sample)}\n\n"
                f"请到「API 设置」里把视频模型改成上面列表中的一个。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        # 2. The model name is valid, but this account has no enabled channel.
        if "channel not found" in text or "model_not_found" in text:
            hint = (
                f"上游「{provider_name}」识别了模型「{requested_model}」，但你的 API Key 账号下**没有该模型的可用通道**。\n\n"
                f"原因：你的账号没开通这个模型的访问权限（付费/订阅相关）。\n\n"
                f"解决方法：\n"
                f"  1. 登录 {provider.get('base_url') or '上游平台'} 控制台，开通该模型 / 充值；\n"
                f"  2. 或在「API 设置」里把视频模型改成你账号已开通的型号（如 veo3-fast / veo2-fast / sora-2 等）。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        if "text.duration" in text or "specified duration is not supported" in text:
            hint = (
                f"上游「{provider_name}」模型「{requested_model}」不支持当前时长参数。\n\n"
                f"我方已改为不主动给火山 Seedance fast 传 duration；如果仍报这个错误，请把视频时长先切回默认值再试，"
                f"或改用该账号已开通的其他视频模型。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        if "inputimagesensitivecontentdetected" in text.lower() or "privacyinformation" in text.lower() or "may contain real person" in text.lower():
            hint = (
                f"上游「{provider_name}」拦截了输入参考图，原因是图片里可能包含真人身份/隐私信息。\n\n"
                f"这不是代码协议错误，而是火山视频模型的内容安全策略。\n\n"
                f"建议你这样处理：\n"
                f"  1. 改用非真人参考图，例如插画、AI 头像、商品图、场景图；\n"
                f"  2. 先把真人脸做模糊、遮挡、裁掉，或转成明显的二次元/插画风；\n"
                f"  3. 如果只是想做文生视频，先去掉参考图只保留文字提示词测试。"
            )
            raise HTTPException(status_code=exc.response.status_code, detail=hint) from exc
        raise HTTPException(status_code=exc.response.status_code, detail=f"上游视频接口错误：{text}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"请求上游视频接口失败：{exc}") from exc
