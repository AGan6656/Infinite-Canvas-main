import json
import os
import re
import uuid

from .common import DATA_DIR, INSTRUCTION_TEMPLATES_PATH, now_ms


VALID_TEMPLATE_SCOPES = {"storyboard", "asset:character", "asset:scene", "asset:prop"}


def sanitize_instruction_template_name(name, fallback="未命名指令"):
    text = re.sub(r'[\r\n\t]+', " ", str(name or fallback)).strip()
    return text[:120] or fallback


def _int_ms(value, fallback=None):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return now_ms() if fallback is None else fallback


def normalize_instruction_template(item):
    if not isinstance(item, dict):
        return None
    scope = str(item.get("scope") or "").strip().lower()
    text = str(item.get("text") or "").strip()
    if scope not in VALID_TEMPLATE_SCOPES or not text:
        return None
    template_id = str(item.get("id") or "").strip()
    if not template_id:
        template_id = f"instruction_template_{uuid.uuid4().hex[:12]}"
    created_at = _int_ms(item.get("createdAt") or item.get("created_at"))
    updated_at = _int_ms(item.get("updatedAt") or item.get("updated_at"), created_at)
    return {
        "id": template_id[:80],
        "scope": scope,
        "name": sanitize_instruction_template_name(item.get("name")),
        "text": text,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }


def sort_instruction_templates(templates):
    def key(item):
        try:
            return int(item.get("updatedAt") or item.get("createdAt") or 0)
        except (TypeError, ValueError):
            return 0

    return sorted(templates, key=key, reverse=True)


def default_instruction_templates():
    return {"templates": [], "updated_at": now_ms()}


def load_instruction_templates():
    if not os.path.exists(INSTRUCTION_TEMPLATES_PATH):
        data = default_instruction_templates()
        save_instruction_templates(data.get("templates", []))
        return data
    try:
        with open(INSTRUCTION_TEMPLATES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = default_instruction_templates()
    raw_templates = data.get("templates") if isinstance(data, dict) else data
    templates = [
        normalized
        for normalized in (normalize_instruction_template(item) for item in (raw_templates or []))
        if normalized
    ]
    updated_at = _int_ms(data.get("updated_at") if isinstance(data, dict) else None)
    return {"templates": sort_instruction_templates(templates), "updated_at": updated_at}


def save_instruction_templates(templates):
    clean = [
        normalized
        for normalized in (normalize_instruction_template(item) for item in (templates or []))
        if normalized
    ]
    data = {"templates": sort_instruction_templates(clean), "updated_at": now_ms()}
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INSTRUCTION_TEMPLATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
