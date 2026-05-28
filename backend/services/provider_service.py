from __future__ import annotations

from typing import List

from ..core_imports import *
from ..runninghub.settings import (
    apply_runninghub_provider_payload,
    runninghub_endpoint_label,
    runninghub_upstream_model_headers,
    runninghub_upstream_models_url,
    saved_runninghub_api_key,
)
from ..schemas import ApiProviderPayload, TestConnectionPayload


@app.get("/api/config")
async def ai_config():
    preferred_chat = next((m for m in CHAT_MODELS if m == "gpt-5.5"), CHAT_MODELS[0] if CHAT_MODELS else CHAT_MODEL)
    providers = [public_provider(p) for p in load_api_providers()]
    return {
        "base_url": AI_BASE_URL,
        "chat_model": preferred_chat,
        "image_model": IMAGE_MODEL,
        "chat_models": CHAT_MODELS,
        "image_models": IMAGE_MODELS,
        "video_models": VIDEO_MODELS,
        "comfy_instances": COMFYUI_INSTANCES,
        "api_providers": providers,
        "has_api_key": bool(AI_API_KEY),
        "ms_chat_models": MODELSCOPE_CHAT_MODELS,
        "has_ms_key": bool(MODELSCOPE_API_KEY),
    }


@app.get("/api/models")
async def ai_models():
    return {"chat_models": CHAT_MODELS, "image_models": IMAGE_MODELS, "video_models": VIDEO_MODELS}


@app.get("/api/providers")
async def api_providers():
    return {"providers": [public_provider(p) for p in load_api_providers()]}


@app.put("/api/providers")
async def save_providers(payload: List[ApiProviderPayload]):
    providers = []
    env_updates = {}
    raw_primary_flags = [bool(getattr(item, "primary", False)) for item in payload]
    for item in payload:
        provider = normalize_provider(item.dict(exclude={"api_key"}))
        provider = apply_runninghub_provider_payload(provider, item, env_updates)
        if any(existing["id"] == provider["id"] for existing in providers):
            raise HTTPException(status_code=400, detail=f"Duplicate API provider ID: {provider['id']}")
        providers.append(provider)
        key_env = provider_key_env(provider["id"])
        if item.clear_key:
            env_updates[key_env] = ""
        elif item.api_key is not None and item.api_key.strip():
            env_updates[key_env] = item.api_key.strip()
        if provider["id"] == "comfly":
            env_updates["COMFLY_BASE_URL"] = provider["base_url"]
            env_updates["IMAGE_MODELS"] = ",".join(provider["image_models"])
            env_updates["CHAT_MODELS"] = ",".join(provider["chat_models"])
            env_updates["VIDEO_MODELS"] = ",".join(provider.get("video_models") or [])
        if provider["id"] == "modelscope":
            env_updates["MODELSCOPE_CHAT_MODELS"] = ",".join(provider["chat_models"])
    if not providers:
        raise HTTPException(status_code=400, detail="At least one API provider is required")
    primary_indices = [i for i, flag in enumerate(raw_primary_flags) if flag]
    if primary_indices:
        winner = primary_indices[-1]
        for i, provider in enumerate(providers):
            provider["primary"] = i == winner
    save_api_providers(providers)
    if env_updates:
        update_env_values(env_updates)
        reload_env_globals()
    return {"providers": [public_provider(p) for p in providers]}


@app.get("/api/config/token")
async def get_global_token():
    if MODELSCOPE_API_KEY:
        return {"token": MODELSCOPE_API_KEY}
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return {"token": config.get("modelscope_token", "")}
        except Exception:
            pass
    return {"token": ""}


def protocol_from_payload(payload):
    protocol = str(getattr(payload, "protocol", "") or "openai").strip().lower()
    return protocol if protocol in SUPPORTED_PROVIDER_PROTOCOLS else "openai"


def upstream_models_url(base_url: str, protocol: str):
    if protocol == "gemini":
        return f"{base_url}/models" if base_url.endswith("/v1beta") else f"{base_url}/v1beta/models"
    if protocol == "volcengine":
        return f"{base_url}/models" if base_url.endswith("/api/v3") else f"{base_url}/api/v3/models"
    if protocol == "runninghub":
        return runninghub_upstream_models_url(base_url)
    return f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"


def upstream_model_headers(api_key: str, protocol: str):
    if protocol == "gemini":
        return {"x-goog-api-key": api_key, "Accept": "application/json"}
    if protocol == "runninghub":
        return runninghub_upstream_model_headers(api_key)
    return {"Authorization": bearer_auth_value(api_key), "Accept": "application/json"}


def classify_upstream_model(mid):
    lc = str(mid or "").lower()
    video_keys = ["veo", "sora", "wan2", "wanx", "doubao-seedance", "doubao-1", "kling", "hailuo", "video", "t2v-", "i2v-", "s2v"]
    if any(key in lc for key in video_keys):
        return "video"
    image_keys = ["banana", "image", "dalle", "dall-e", "imagen", "flux", "stable", "sdxl", "midjourney", "nano-banana", "ideogram", "fal-ai", "z-image", "qwen-image", "klein", "seedream", "doubao-seedream", "text-to-image", "image-to-image"]
    if any(key in lc for key in image_keys):
        return "image"
    return "chat"


def parse_upstream_models(raw, protocol="openai"):
    items = raw.get("data") if isinstance(raw, dict) else None
    if not items and isinstance(raw, dict):
        items = raw.get("models") or raw.get("list") or []
    if not isinstance(items, list):
        items = []
    ids = []
    for item in items:
        if isinstance(item, str):
            mid = item
        elif isinstance(item, dict):
            mid = item.get("id") or item.get("name") or item.get("model")
        else:
            mid = ""
        if mid:
            mid = str(mid)
            if protocol == "gemini" and mid.startswith("models/"):
                mid = mid[len("models/"):]
            ids.append(mid)
    ids = sorted(set(ids))
    grouped = {"image": [], "chat": [], "video": []}
    for mid in ids:
        grouped[classify_upstream_model(mid)].append(mid)
    return grouped, ids


@app.post("/api/providers/test-connection")
async def test_provider_connection(payload: TestConnectionPayload):
    """Validate provider URL by requesting /v1/models."""
    base_url = (payload.base_url or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="Please enter the provider base URL")
    if not re.match(r"^https?://", base_url):
        raise HTTPException(status_code=400, detail="Provider base URL must start with http:// or https://")
    api_key = (payload.api_key or "").strip()
    if not api_key and payload.provider_id:
        api_key = saved_runninghub_api_key(payload.provider_id, provider_key_env)
        if not api_key:
            api_key = os.getenv(provider_key_env(payload.provider_id), "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Please enter or save an API Key")
    protocol = protocol_from_payload(payload)
    url = upstream_models_url(base_url, protocol)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=upstream_model_headers(api_key, protocol))
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "message": resp.text[:300]}
        data = resp.json() if resp.text else {}
        grouped, ids = parse_upstream_models(data, protocol)
        return {"ok": True, "status": resp.status_code, "model_count": len(ids), "image_models": grouped["image"], "chat_models": grouped["chat"], "video_models": grouped["video"], "all": ids}
    except httpx.HTTPError as e:
        return {"ok": False, "status": 0, "message": str(e)[:300]}


@app.post("/api/providers/probe-async")
async def probe_async_endpoint(payload: TestConnectionPayload):
    """Probe APIMart async tasks endpoint with a fake task id."""
    base_url = (payload.base_url or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="Please enter the provider base URL")
    api_key = (payload.api_key or "").strip()
    if not api_key and payload.provider_id:
        api_key = saved_runninghub_api_key(payload.provider_id, provider_key_env)
        if not api_key:
            api_key = os.getenv(provider_key_env(payload.provider_id), "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Please enter or save an API Key")
    tasks_base = base_url if base_url.endswith("/v1") else f"{base_url}/v1"
    probe_url = f"{tasks_base}/tasks/healthcheck_probe_do_not_submit"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(probe_url, headers={"Authorization": bearer_auth_value(api_key), "Accept": "application/json"})
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        sc = resp.status_code
        err_msg = ""
        if isinstance(body, dict):
            err = body.get("error") or {}
            if isinstance(err, dict):
                err_msg = str(err.get("message") or "").lower()
            else:
                err_msg = str(err).lower()
        if sc == 400 and "invalid task id" in err_msg:
            return {"ok": True, "status_code": sc, "message": "Async tasks endpoint is available and the API Key is authenticated", "raw": body}
        if sc in (401, 403):
            return {"ok": False, "status_code": sc, "message": "API Key is invalid or unauthorized", "raw": body}
        if sc == 404:
            return {"ok": False, "status_code": sc, "message": "Provider does not support the /v1/tasks/ endpoint; it may not use the APIMart async protocol", "raw": body}
        if 400 <= sc < 500:
            return {"ok": None, "status_code": sc, "message": f"Endpoint returned {sc}; inspect the raw response", "raw": body}
        if sc < 300:
            return {"ok": True, "status_code": sc, "message": f"Endpoint returned {sc} (unexpected success)", "raw": body}
        return {"ok": False, "status_code": sc, "message": f"Server error: {sc}", "raw": body}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)[:300])


async def fetch_models_from_upstream(base_url: str, api_key: str, protocol: str = "openai"):
    """Probe an OpenAI-compatible /v1/models endpoint."""
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="Please enter the provider base URL")
    if not re.match(r"^https?://", base_url):
        raise HTTPException(status_code=400, detail="Provider base URL must start with http:// or https://")
    api_key = (api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="Please enter or save an API Key")
    protocol = protocol if protocol in SUPPORTED_PROVIDER_PROTOCOLS else "openai"
    url = upstream_models_url(base_url, protocol)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=upstream_model_headers(api_key, protocol))
            if resp.status_code >= 400:
                endpoint_label = "/v1beta/models" if protocol == "gemini" else "/api/v3/models" if protocol == "volcengine" else runninghub_endpoint_label() if protocol == "runninghub" else "/v1/models"
                raise HTTPException(status_code=resp.status_code, detail=f"Upstream {endpoint_label} failed: {resp.text[:300]}")
            raw = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch upstream model list: {e}")
    grouped, ids = parse_upstream_models(raw, protocol)
    return {"total": len(ids), "image_models": grouped["image"], "chat_models": grouped["chat"], "video_models": grouped["video"], "all": ids}


@app.post("/api/providers/fetch-models")
async def fetch_upstream_models_from_payload(payload: TestConnectionPayload):
    """Model fetch routes."""
    api_key = (payload.api_key or "").strip()
    if not api_key and payload.provider_id:
        api_key = saved_runninghub_api_key(payload.provider_id, provider_key_env)
        if not api_key:
            api_key = os.getenv(provider_key_env(payload.provider_id), "")
    return await fetch_models_from_upstream(payload.base_url, api_key, protocol_from_payload(payload))


@app.get("/api/providers/{provider_id}/fetch-models")
async def fetch_upstream_models(provider_id: str):
    """Fetch /v1/models from a saved OpenAI-compatible provider."""
    provider = get_api_provider_exact(provider_id)
    api_key = saved_runninghub_api_key(provider["id"], provider_key_env)
    if not api_key:
        api_key = os.getenv(provider_key_env(provider["id"]), "")

    if not api_key:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider_id} API Key is not configured")
    return await fetch_models_from_upstream(provider.get("base_url") or "", api_key, provider_protocol(provider))
