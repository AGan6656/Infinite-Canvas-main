import json
import os
import re

from .common import ASSET_LIBRARY_PATH, DATA_DIR, now_ms


DEFAULT_IMAGE_CATEGORIES = (
    {"id": "characters", "name": "角色", "type": "image", "items": []},
    {"id": "scenes", "name": "场景", "type": "image", "items": []},
)
DEFAULT_WORKFLOW_CATEGORY = {"id": "workflows", "name": "工作流", "type": "workflow", "items": []}


def _default_category(cat):
    return {**cat, "items": []}


def default_asset_library():
    return {
        "categories": [_default_category(cat) for cat in (*DEFAULT_IMAGE_CATEGORIES, DEFAULT_WORKFLOW_CATEGORY)],
        "updated_at": now_ms(),
    }


def _int_ms(value, fallback=None):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return now_ms() if fallback is None else fallback


def _clean_category(cat):
    if not isinstance(cat, dict):
        return None
    cat_type = "workflow" if str(cat.get("type") or "").lower() == "workflow" else "image"
    clean = dict(cat)
    clean["id"] = str(clean.get("id") or "").strip()[:80]
    if not clean["id"]:
        return None
    clean["name"] = sanitize_asset_name(clean.get("name"), "工作流" if cat_type == "workflow" else "素材")
    clean["type"] = cat_type
    clean["items"] = clean.get("items") if isinstance(clean.get("items"), list) else []
    return clean


def normalize_asset_library(lib):
    if not isinstance(lib, dict):
        lib = default_asset_library()
    cats = [
        clean
        for clean in (_clean_category(cat) for cat in (lib.get("categories") or []))
        if clean
    ]
    if not any(cat.get("type") == "image" for cat in cats):
        cats.extend(_default_category(cat) for cat in DEFAULT_IMAGE_CATEGORIES)
    if not any(cat.get("type") == "workflow" for cat in cats):
        cats.append(_default_category(DEFAULT_WORKFLOW_CATEGORY))
    lib["categories"] = cats
    lib["updated_at"] = _int_ms(lib.get("updated_at"))
    return lib


def load_asset_library():
    if not os.path.exists(ASSET_LIBRARY_PATH):
        lib = default_asset_library()
        save_asset_library(lib)
        return lib
    try:
        with open(ASSET_LIBRARY_PATH, "r", encoding="utf-8") as f:
            lib = json.load(f)
    except Exception:
        lib = default_asset_library()
    lib = normalize_asset_library(lib)
    sort_asset_library_items(lib)
    return lib


def sort_asset_library_items(lib):
    for cat in lib.get("categories", []):
        items = cat.get("items")
        if isinstance(items, list):
            def created_at_key(item):
                if not isinstance(item, dict):
                    return 0
                try:
                    return int(float(item.get("created_at") or 0))
                except (TypeError, ValueError):
                    return 0

            items.sort(key=created_at_key, reverse=True)
    return lib


def save_asset_library(lib):
    lib = normalize_asset_library(lib)
    sort_asset_library_items(lib)
    lib["updated_at"] = now_ms()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ASSET_LIBRARY_PATH, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)


def find_asset_category(lib, category_id):
    for cat in lib.get("categories", []):
        if cat.get("id") == category_id:
            return cat
    return None


def sanitize_asset_name(name, fallback="asset"):
    name = re.sub(r'[\\/:*?"<>|]+', "_", str(name or fallback)).strip()
    return name[:120] or fallback
