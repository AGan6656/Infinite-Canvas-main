import json
import os
import re
import uuid
from threading import Lock

from fastapi import HTTPException

from .common import DATA_DIR, now_ms


CANVAS_ASSET_DIR = os.path.join(DATA_DIR, "canvas_assets")
CANVAS_ASSET_LOCK = Lock()
CANVAS_ASSET_TYPES = {"character", "scene", "prop"}


def _clean_canvas_id(canvas_id):
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", canvas_id or "")
    if not cleaned:
        raise HTTPException(status_code=400, detail="无效的画布 ID")
    return cleaned


def normalize_canvas_asset_type(asset_type):
    text = str(asset_type or "").strip().lower()
    return text if text in CANVAS_ASSET_TYPES else "character"


def canvas_assets_path(canvas_id):
    os.makedirs(CANVAS_ASSET_DIR, exist_ok=True)
    return os.path.join(CANVAS_ASSET_DIR, f"{_clean_canvas_id(canvas_id)}.json")


def default_canvas_assets(canvas_id):
    return {
        "canvas_id": _clean_canvas_id(canvas_id),
        "updated_at": now_ms(),
        "extractions": {},
        "assets": {"character": [], "scene": [], "prop": []},
    }


def load_canvas_assets(canvas_id):
    path = canvas_assets_path(canvas_id)
    if not os.path.exists(path):
        return default_canvas_assets(canvas_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = default_canvas_assets(canvas_id)
    data.setdefault("canvas_id", _clean_canvas_id(canvas_id))
    data.setdefault("updated_at", 0)
    data.setdefault("extractions", {})
    data.setdefault("assets", {})
    for asset_type in CANVAS_ASSET_TYPES:
        data["assets"].setdefault(asset_type, [])
    return data


def save_canvas_assets(data):
    canvas_id = data.get("canvas_id")
    data["updated_at"] = now_ms()
    with CANVAS_ASSET_LOCK:
        with open(canvas_assets_path(canvas_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _asset_name_from_item(item, fallback):
    if isinstance(item, dict):
        for key in ("name", "title", "角色名", "场景名", "道具名", "名称"):
            value = str(item.get(key) or "").strip()
            if value:
                return value[:120]
    text = str(item or "").strip()
    return (text[:120] if text else fallback)


def normalize_canvas_asset_item(item, asset_type, node_id, source_node_ids):
    raw = item if isinstance(item, dict) else {"description": str(item or "")}
    clean = dict(raw)
    name = _asset_name_from_item(raw, "未命名资产")
    clean["id"] = str(clean.get("id") or f"{asset_type}_{uuid.uuid4().hex[:12]}")
    clean["type"] = asset_type
    clean["name"] = name
    clean["extractor_node_id"] = node_id
    clean["source_node_ids"] = [str(x) for x in (source_node_ids or []) if str(x or "").strip()]
    clean["updated_at"] = now_ms()
    return clean


def rebuild_canvas_asset_index(data):
    assets = {"character": [], "scene": [], "prop": []}
    extractions = data.get("extractions") or {}
    for extraction in extractions.values():
        asset_type = normalize_canvas_asset_type(extraction.get("asset_type"))
        for item in extraction.get("items") or []:
            if isinstance(item, dict):
                assets.setdefault(asset_type, []).append(item)
    data["assets"] = assets
    return data


def save_canvas_asset_extraction(canvas_id, node_id, payload):
    data = load_canvas_assets(canvas_id)
    asset_type = normalize_canvas_asset_type(payload.get("asset_type"))
    clean_node_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(node_id or "")) or f"extractor_{uuid.uuid4().hex[:8]}"
    source_node_ids = [str(x) for x in (payload.get("source_node_ids") or []) if str(x or "").strip()]
    items = [
        normalize_canvas_asset_item(item, asset_type, clean_node_id, source_node_ids)
        for item in (payload.get("items") or [])[:500]
    ]
    extraction = {
        "node_id": clean_node_id,
        "asset_type": asset_type,
        "source_node_ids": source_node_ids,
        "instruction": str(payload.get("instruction") or ""),
        "provider": str(payload.get("provider") or ""),
        "model": str(payload.get("model") or ""),
        "raw_text": str(payload.get("raw_text") or ""),
        "items": items,
        "updated_at": now_ms(),
    }
    data.setdefault("extractions", {})[clean_node_id] = extraction
    rebuild_canvas_asset_index(data)
    return save_canvas_assets(data)


def delete_canvas_assets(canvas_id):
    path = canvas_assets_path(canvas_id)
    if os.path.exists(path):
        os.remove(path)
