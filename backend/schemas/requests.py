import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..runninghub.schemas import (
    RunningHubSubmitRequest,
    RunningHubUploadAssetRequest,
    RunningHubWorkflowConfig,
    RunningHubWorkflowConfigField,
    RunningHubWorkflowSubmitRequest,
)


ONLINE_IMAGE_PROMPT_MAX_LENGTH = int(os.getenv("ONLINE_IMAGE_PROMPT_MAX_LENGTH", "20000"))
VIDEO_PROMPT_MAX_LENGTH = int(os.getenv("VIDEO_PROMPT_MAX_LENGTH", "4000"))
LLM_MESSAGE_MAX_LENGTH = int(os.getenv("LLM_MESSAGE_MAX_LENGTH", "20000"))


class UpdateRequest(BaseModel):
    auto_restart: bool = False
    restart_delay: int = 3


class RollbackRequest(BaseModel):
    name: str = ""
    auto_restart: bool = False
    restart_delay: int = 3


class GenerateRequest(BaseModel):
    prompt: str = ""
    width: int = 1024
    height: int = 1024
    workflow_json: str = "Z-Image.json"
    params: Dict[str, Any] = {}
    type: str = "zimage"
    client_id: str = ""
    convert_to_jpg: bool = False


class DeleteHistoryRequest(BaseModel):
    timestamp: float


class TokenRequest(BaseModel):
    token: str


class CloudGenRequest(BaseModel):
    prompt: str
    api_key: str = ""
    model: str = ""
    resolution: str = "1024x1024"
    type: str = "zimage"
    image_urls: List[str] = []
    loras: Optional[Any] = None
    client_id: Optional[str] = None


class CloudPollRequest(BaseModel):
    task_id: str
    api_key: str = ""
    client_id: Optional[str] = None


class AIReference(BaseModel):
    url: str = ""
    name: str = ""
    role: str = ""


class OnlineImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=ONLINE_IMAGE_PROMPT_MAX_LENGTH)
    provider_id: str = "comfly"
    model: str = ""
    size: str = "1024x1024"
    quality: str = "auto"
    n: int = 1
    reference_images: List[AIReference] = []


class CanvasVideoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=VIDEO_PROMPT_MAX_LENGTH)
    provider_id: str = "comfly"
    model: str = "veo3-fast"
    duration: int = 5
    aspect_ratio: str = "16:9"
    resolution: str = ""
    size: str = ""
    images: List[AIReference] = []
    videos: List[str] = []
    enhance_prompt: bool = False
    enable_upsample: bool = False
    watermark: bool = False
    seed: Optional[int] = None
    camerafixed: bool = False
    return_last_frame: bool = False
    generate_audio: bool = False


class ApiProviderPayload(BaseModel):
    id: str = ""
    name: str = ""
    base_url: str = ""
    protocol: str = "openai"
    image_generation_endpoint: str = ""
    image_edit_endpoint: str = ""
    enabled: bool = True
    primary: bool = False
    image_models: List[str] = []
    chat_models: List[str] = []
    video_models: List[str] = []
    ms_loras: List[Dict[str, Any]] = []
    ms_defaults_version: int = 0
    rh_apps: List[Dict[str, Any]] = []
    rh_workflows: List[Dict[str, Any]] = []
    api_key: Optional[str] = None
    wallet_api_key: Optional[str] = None
    clear_key: bool = False
    clear_wallet_key: bool = False


class ChatRequest(BaseModel):
    conversation_id: str = ""
    message: str = Field(min_length=1, max_length=LLM_MESSAGE_MAX_LENGTH)
    model: str = ""
    image_model: str = ""
    mode: str = "chat"
    size: str = "1024x1024"
    quality: str = "auto"
    reference_images: List[AIReference] = []
    provider: str = "comfly"
    ms_model: str = ""


class MsGenerateRequest(BaseModel):
    prompt: str
    api_key: str = ""
    model: str = "black-forest-labs/FLUX.2-klein-9B"
    image_urls: List[str] = []
    width: int = 0
    height: int = 0
    size: str = ""
    loras: Optional[Any] = None
    client_id: Optional[str] = None


class CanvasLLMRequest(BaseModel):
    message: str = Field(min_length=1, max_length=LLM_MESSAGE_MAX_LENGTH)
    system_prompt: str = ""
    model: str = ""
    messages: List[Dict[str, Any]] = []
    provider: str = "comfly"
    ms_model: str = ""
    images: List[str] = []


class ConversationCreateRequest(BaseModel):
    title: str = "新对话"


class CanvasCreateRequest(BaseModel):
    title: str = "未命名画布"
    icon: str = "🧩"
    kind: str = "classic"


class CanvasSaveRequest(BaseModel):
    title: str = "未命名画布"
    icon: str = "🧩"
    nodes: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []
    viewport: Dict[str, Any] = {}
    logs: List[Dict[str, Any]] = []
    settings: Dict[str, Any] = {}
    client_id: str = ""
    base_updated_at: int = 0


class CanvasExtractedAssetsSaveRequest(BaseModel):
    asset_type: str = "character"
    source_node_ids: List[str] = []
    instruction: str = ""
    provider: str = ""
    model: str = ""
    raw_text: str = ""
    items: List[Dict[str, Any]] = []


class CanvasAssetCheckRequest(BaseModel):
    urls: List[str] = []


class CanvasAssetDownloadRequest(BaseModel):
    urls: List[str] = []
    filename: str = "canvas-output-images.zip"


class SmartCanvasGroupExportItem(BaseModel):
    kind: str = ""
    url: str = ""
    text: str = ""
    name: str = ""


class SmartCanvasGroupExportRequest(BaseModel):
    folder: str = ""
    group_name: str = "group"
    items: List[SmartCanvasGroupExportItem] = []


class LocalImageImportRequest(BaseModel):
    path: str = ""
    paths: List[str] = Field(default_factory=list)


class AssetLibraryCategoryRequest(BaseModel):
    name: str = "新文件夹"
    type: str = "image"


class AssetLibraryAddRequest(BaseModel):
    category_id: str = ""
    url: str = ""
    name: str = ""


class AssetLibraryRenameRequest(BaseModel):
    name: str = ""


class TestConnectionPayload(BaseModel):
    base_url: str = ""
    api_key: str = ""
    provider_id: str = ""
    protocol: str = "openai"
