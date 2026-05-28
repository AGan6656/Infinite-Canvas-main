from __future__ import annotations

import os
import re
import uuid

from .runninghub.defaults import (
    RUNNINGHUB_DEFAULT_APPS,
    RUNNINGHUB_DEFAULT_BASE_URL,
    RUNNINGHUB_DEFAULT_IMAGE_MODELS,
    RUNNINGHUB_DEFAULT_WORKFLOWS,
    RUNNINGHUB_THUMBNAIL_EXTS,
)


__all__ = [
    "SERVICE_RUNTIME_GLOBALS",
    "APP_VERSION",
    "GITHUB_REPO_URL",
    "GITHUB_VERSION_URL",
    "GITHUB_TREE_URL",
    "GITHUB_RAW_ROOT",
    "CLIENT_ID",
    "BASE_DIR",
    "WORKFLOW_DIR",
    "WORKFLOW_PATH",
    "STATIC_DIR",
    "STATIC_RUNNINGHUB_DIR",
    "STATIC_RUNNINGHUB_THUMBNAIL_DIR",
    "STATIC_RUNNINGHUB_API_PROVIDERS_FILE",
    "OUTPUT_DIR",
    "ASSETS_DIR",
    "OUTPUT_INPUT_DIR",
    "OUTPUT_OUTPUT_DIR",
    "ASSET_LIBRARY_DIR",
    "HISTORY_FILE",
    "API_ENV_FILE",
    "DATA_DIR",
    "CONVERSATION_DIR",
    "CANVAS_DIR",
    "ASSET_LIBRARY_PATH",
    "API_PROVIDERS_FILE",
    "RUNNINGHUB_WORKFLOW_STORE_FILE",
    "GLOBAL_CONFIG_FILE",
    "CANVAS_TRASH_RETENTION_MS",
    "LOCAL_IMAGE_IMPORT_MAX_BYTES",
    "LOCAL_IMAGE_IMPORT_EXTS",
    "RUNNINGHUB_THUMBNAIL_EXTS",
    "PROVIDER_ID_RE",
    "SUPPORTED_PROVIDER_PROTOCOLS",
    "RUNNINGHUB_DEFAULT_BASE_URL",
    "RUNNINGHUB_DEFAULT_IMAGE_MODELS",
    "RUNNINGHUB_DEFAULT_APPS",
    "RUNNINGHUB_DEFAULT_WORKFLOWS",
    "COMFYUI_INSTANCES",
    "COMFYUI_ADDRESS",
    "AI_BASE_URL",
    "AI_API_KEY",
    "MODELSCOPE_API_KEY",
    "MODELSCOPE_CHAT_BASE_URL",
    "MODELSCOPE_DEFAULT_IMAGE_MODELS",
    "MODELSCOPE_DEFAULT_CHAT_MODELS",
    "MODELSCOPE_CHAT_MODELS",
    "MODELSCOPE_DEFAULT_IMAGE_MODEL",
    "MODELSCOPE_DEFAULT_CHAT_MODEL",
    "MODELSCOPE_DEFAULT_LORAS",
    "MODELSCOPE_DEFAULTS_VERSION",
    "CHAT_MODEL",
    "IMAGE_MODEL",
    "SYSTEM_PROMPT",
    "MAX_HISTORY_MESSAGES",
    "AI_REQUEST_TIMEOUT",
    "IMAGE_POLL_INTERVAL",
    "IMAGE_TASK_TIMEOUT",
    "COMFYUI_HISTORY_TIMEOUT",
    "APIMART_IMAGE_TASK_TIMEOUT",
    "APIMART_IMAGE_POLL_INTERVAL",
    "APIMART_IMAGE_INITIAL_POLL_DELAY",
    "VIDEO_POLL_TIMEOUT",
    "ONLINE_IMAGE_PROMPT_MAX_LENGTH",
    "VIDEO_PROMPT_MAX_LENGTH",
    "LLM_MESSAGE_MAX_LENGTH",
    "DEFAULT_CHAT_MODEL_EXTRAS",
    "DEFAULT_IMAGE_MODEL_EXTRAS",
    "DEFAULT_VIDEO_MODEL",
    "DEFAULT_VIDEO_MODEL_EXTRAS",
    "CHAT_MODELS",
    "IMAGE_MODELS",
    "VIDEO_MODELS",
    "ensure_runtime_config_files",
    "load_env_file",
    "model_list",
]


SERVICE_RUNTIME_GLOBALS = [
    "GLOBAL_LOOP",
    "AI_BASE_URL",
    "AI_API_KEY",
    "MODELSCOPE_API_KEY",
    "MODELSCOPE_CHAT_MODELS",
    "IMAGE_MODELS",
    "CHAT_MODELS",
    "VIDEO_MODELS",
    "COMFYUI_INSTANCES",
    "COMFYUI_ADDRESS",
    "BACKEND_LOCAL_LOAD",
]

APP_VERSION = "2026.05.19"
GITHUB_REPO_URL = "https://github.com/hero8152/Infinite-Canvas"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/hero8152/Infinite-Canvas/main/VERSION"
GITHUB_TREE_URL = "https://api.github.com/repos/hero8152/Infinite-Canvas/git/trees/main?recursive=1"
GITHUB_RAW_ROOT = "https://raw.githubusercontent.com/hero8152/Infinite-Canvas/main"

CLIENT_ID = str(uuid.uuid4())
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(BASE_DIR, "workflows")
WORKFLOW_PATH = os.path.join(WORKFLOW_DIR, "Z-Image.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")
STATIC_RUNNINGHUB_DIR = os.path.join(STATIC_DIR, "runninghub")
STATIC_RUNNINGHUB_THUMBNAIL_DIR = os.path.join(STATIC_RUNNINGHUB_DIR, "thumbnails")
STATIC_RUNNINGHUB_API_PROVIDERS_FILE = os.path.join(STATIC_RUNNINGHUB_DIR, "api_providers.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_INPUT_DIR = os.path.join(ASSETS_DIR, "input")
OUTPUT_OUTPUT_DIR = os.path.join(ASSETS_DIR, "output")
ASSET_LIBRARY_DIR = os.path.join(ASSETS_DIR, "library")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
API_ENV_FILE = os.path.join(BASE_DIR, "API", ".env")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONVERSATION_DIR = os.path.join(DATA_DIR, "conversations")
CANVAS_DIR = os.path.join(DATA_DIR, "canvases")
ASSET_LIBRARY_PATH = os.path.join(DATA_DIR, "asset_library.json")
API_PROVIDERS_FILE = os.path.join(DATA_DIR, "api_providers.json")
RUNNINGHUB_WORKFLOW_STORE_FILE = os.path.join(DATA_DIR, "runninghub_workflows.json")
GLOBAL_CONFIG_FILE = os.path.join(BASE_DIR, "global_config.json")
CANVAS_TRASH_RETENTION_MS = 30 * 24 * 60 * 60 * 1000
LOCAL_IMAGE_IMPORT_MAX_BYTES = int(os.getenv("LOCAL_IMAGE_IMPORT_MAX_BYTES", str(50 * 1024 * 1024)))
LOCAL_IMAGE_IMPORT_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
PROVIDER_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{2,40}$")
SUPPORTED_PROVIDER_PROTOCOLS = {"openai", "apimart", "gemini", "volcengine", "runninghub"}


def ensure_runtime_config_files():
    try:
        os.makedirs(os.path.dirname(API_ENV_FILE), exist_ok=True)
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(API_ENV_FILE):
            with open(API_ENV_FILE, "a", encoding="utf-8"):
                pass
    except Exception as e:
        print(f"Failed to initialize API config files: {e}")


def load_env_file():
    if not os.path.exists(API_ENV_FILE):
        return
    try:
        with open(API_ENV_FILE, "r", encoding="utf-8-sig") as f:
            for raw_line in f.read().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except Exception as e:
        print(f"Failed to load API/.env: {e}")


ensure_runtime_config_files()
load_env_file()

COMFYUI_INSTANCES = [s.strip() for s in os.getenv("COMFYUI_INSTANCES", "127.0.0.1:8188").split(",") if s.strip()]
COMFYUI_ADDRESS = COMFYUI_INSTANCES[0]

AI_BASE_URL = os.getenv("COMFLY_BASE_URL", "https://ai.comfly.chat").rstrip("/")
AI_API_KEY = os.getenv("COMFLY_API_KEY", "")
MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY", "")
MODELSCOPE_CHAT_BASE_URL = "https://api-inference.modelscope.cn/v1"
MODELSCOPE_DEFAULT_IMAGE_MODELS = [
    "Tongyi-MAI/Z-Image-Turbo",
    "Qwen/Qwen-Image-2512",
    "Qwen/Qwen-Image-Edit-2511",
    "black-forest-labs/FLUX.2-klein-9B",
]
MODELSCOPE_DEFAULT_CHAT_MODELS = [
    "Qwen/Qwen3-235B-A22B",
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "MiniMax/MiniMax-M2.7:MiniMax",
]
_MODELSCOPE_CONFIGURED_CHAT_MODELS = [m.strip() for m in os.getenv("MODELSCOPE_CHAT_MODELS", "").split(",") if m.strip()]
MODELSCOPE_CHAT_MODELS = list(dict.fromkeys([m for m in [*MODELSCOPE_DEFAULT_CHAT_MODELS, *_MODELSCOPE_CONFIGURED_CHAT_MODELS] if m]))
MODELSCOPE_DEFAULT_IMAGE_MODEL = MODELSCOPE_DEFAULT_IMAGE_MODELS[0]
MODELSCOPE_DEFAULT_CHAT_MODEL = "Qwen/Qwen3-235B-A22B"
MODELSCOPE_DEFAULT_LORAS = [
    {
        "id": "Daniel8152/film",
        "name": "Z-Image Film",
        "target_model": "Tongyi-MAI/Z-Image-Turbo",
        "strength": 0.8,
        "enabled": True,
        "note": "",
    },
    {
        "id": "Daniel8152/Qwen-Image-2512-Film",
        "name": "Qwen Image 2512 Film",
        "target_model": "Qwen/Qwen-Image-2512",
        "strength": 0.8,
        "enabled": True,
        "note": "",
    },
    {
        "id": "Daniel8152/Klein-enhance",
        "name": "Klein enhance",
        "target_model": "black-forest-labs/FLUX.2-klein-9B",
        "strength": 0.8,
        "enabled": True,
        "note": "",
    },
]
MODELSCOPE_DEFAULTS_VERSION = 3
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gpt-image-2")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "30"))
AI_REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "1800"))
IMAGE_POLL_INTERVAL = float(os.getenv("IMAGE_POLL_INTERVAL", "2"))
IMAGE_TASK_TIMEOUT = float(os.getenv("IMAGE_TASK_TIMEOUT", str(AI_REQUEST_TIMEOUT)))
COMFYUI_HISTORY_TIMEOUT = int(float(os.getenv("COMFYUI_HISTORY_TIMEOUT", "1800")))
APIMART_IMAGE_TASK_TIMEOUT = float(os.getenv("APIMART_IMAGE_TASK_TIMEOUT", "1800"))
APIMART_IMAGE_POLL_INTERVAL = float(os.getenv("APIMART_IMAGE_POLL_INTERVAL", "5"))
APIMART_IMAGE_INITIAL_POLL_DELAY = float(os.getenv("APIMART_IMAGE_INITIAL_POLL_DELAY", "10"))
VIDEO_POLL_TIMEOUT = float(os.getenv("VIDEO_POLL_TIMEOUT", "1800"))
ONLINE_IMAGE_PROMPT_MAX_LENGTH = int(os.getenv("ONLINE_IMAGE_PROMPT_MAX_LENGTH", "20000"))
VIDEO_PROMPT_MAX_LENGTH = int(os.getenv("VIDEO_PROMPT_MAX_LENGTH", "4000"))
LLM_MESSAGE_MAX_LENGTH = int(os.getenv("LLM_MESSAGE_MAX_LENGTH", "20000"))

DEFAULT_CHAT_MODEL_EXTRAS = ["gpt-4o-mini", "gemini-3.1-flash-image-preview-2k"]
DEFAULT_IMAGE_MODEL_EXTRAS = ["nano-banana-pro"]
DEFAULT_VIDEO_MODEL = "veo3-fast"
DEFAULT_VIDEO_MODEL_EXTRAS = [
    "veo2", "veo2-fast", "veo2-pro",
    "veo3", "veo3-fast", "veo3-pro",
    "veo3.1", "veo3.1-fast", "veo3.1-quality", "veo3.1-lite",
    "sora-2", "sora-2-pro",
    "wan2.6-t2v", "wan2.6-i2v",
    "wan2.5-t2v-preview", "wan2.5-i2v-preview",
    "wan2.2-t2v-plus", "wan2.2-i2v-plus", "wan2.2-i2v-flash",
]


def model_list(env_name, primary, defaults):
    configured = os.getenv(env_name, "")
    configured_values = [item.strip() for item in configured.split(",") if item.strip()]
    values = configured_values or [primary, *defaults]
    deduped = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


CHAT_MODELS = model_list("CHAT_MODELS", CHAT_MODEL, DEFAULT_CHAT_MODEL_EXTRAS)
IMAGE_MODELS = model_list("IMAGE_MODELS", IMAGE_MODEL, DEFAULT_IMAGE_MODEL_EXTRAS)
VIDEO_MODELS = model_list("VIDEO_MODELS", DEFAULT_VIDEO_MODEL, DEFAULT_VIDEO_MODEL_EXTRAS)
