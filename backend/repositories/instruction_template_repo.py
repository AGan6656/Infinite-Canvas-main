import json
import os
import re
import uuid

from .common import DATA_DIR, INSTRUCTION_TEMPLATES_PATH, now_ms


VALID_TEMPLATE_SCOPES = {"storyboard", "asset:character", "asset:scene", "asset:prop"}
CUSTOM_TEMPLATE_SCOPE_RE = re.compile(r"^custom:[a-z0-9_-]{1,72}$")


def sanitize_instruction_template_name(name, fallback="未命名指令"):
    text = re.sub(r'[\r\n\t]+', " ", str(name or fallback)).strip()
    return text[:120] or fallback


def sanitize_instruction_group_name(name, fallback="未命名分组"):
    text = re.sub(r'[\r\n\t]+', " ", str(name or fallback)).strip()
    return text[:80] or fallback


def sanitize_instruction_template_tags(*values):
    tags = []
    seen = set()
    for value in values:
        if isinstance(value, (list, tuple)):
            parts = value
        else:
            parts = re.split(r"[,，;；|#\r\n\t]+", str(value or ""))
        for part in parts:
            tag = re.sub(r"[\r\n\t]+", " ", str(part or "")).strip()
            key = tag.lower()
            if not tag or key in seen:
                continue
            seen.add(key)
            tags.append(tag[:32])
    return tags[:24]


def is_valid_template_scope(scope):
    return scope in VALID_TEMPLATE_SCOPES or bool(CUSTOM_TEMPLATE_SCOPE_RE.match(scope or ""))


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
    if not is_valid_template_scope(scope) or not text:
        return None
    template_id = str(item.get("id") or "").strip()
    if not template_id:
        template_id = f"instruction_template_{uuid.uuid4().hex[:12]}"
    created_at = _int_ms(item.get("createdAt") or item.get("created_at"))
    updated_at = _int_ms(item.get("updatedAt") or item.get("updated_at"), created_at)
    normalized = {
        "id": template_id[:80],
        "scope": scope,
        "name": sanitize_instruction_template_name(item.get("name")),
        "text": text,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }
    tags = sanitize_instruction_template_tags(item.get("tags"), item.get("tag"), item.get("labels"))
    if tags:
        normalized["tags"] = tags
    return normalized


def normalize_instruction_group(item):
    if not isinstance(item, dict):
        return None
    group_id = str(item.get("id") or item.get("scope") or "").strip().lower()
    if group_id in VALID_TEMPLATE_SCOPES:
        return None
    if not CUSTOM_TEMPLATE_SCOPE_RE.match(group_id):
        group_id = f"custom:{uuid.uuid4().hex[:12]}"
    created_at = _int_ms(item.get("createdAt") or item.get("created_at"))
    updated_at = _int_ms(item.get("updatedAt") or item.get("updated_at"), created_at)
    return {
        "id": group_id[:80],
        "name": sanitize_instruction_group_name(item.get("name")),
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


def sort_instruction_groups(groups):
    def key(item):
        try:
            return int(item.get("createdAt") or item.get("updatedAt") or 0)
        except (TypeError, ValueError):
            return 0

    return sorted(groups, key=key)


def default_instruction_templates():
    return {"templates": [], "groups": [], "updated_at": now_ms()}


def _read_instruction_template_data():
    if not os.path.exists(INSTRUCTION_TEMPLATES_PATH):
        return default_instruction_templates()
    try:
        with open(INSTRUCTION_TEMPLATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_instruction_templates()


def _normalize_groups(raw_groups, templates=None):
    groups = [
        normalized
        for normalized in (normalize_instruction_group(item) for item in (raw_groups or []))
        if normalized
    ]
    seen = set()
    unique = []
    for group in groups:
        group_id = group.get("id")
        if group_id in seen:
            continue
        seen.add(group_id)
        unique.append(group)
    for template in templates or []:
        scope = template.get("scope")
        if scope and scope not in VALID_TEMPLATE_SCOPES and scope not in seen:
            seen.add(scope)
            unique.append({
                "id": scope,
                "name": sanitize_instruction_group_name(scope.replace("custom:", "") or "未命名分组"),
                "createdAt": template.get("createdAt") or now_ms(),
                "updatedAt": template.get("updatedAt") or template.get("createdAt") or now_ms(),
            })
    return sort_instruction_groups(unique)


def load_instruction_templates():
    data = _read_instruction_template_data()
    raw_templates = data.get("templates") if isinstance(data, dict) else data
    templates = [
        normalized
        for normalized in (normalize_instruction_template(item) for item in (raw_templates or []))
        if normalized
    ]
    raw_groups = data.get("groups") if isinstance(data, dict) else []
    groups = _normalize_groups(raw_groups, templates)
    updated_at = _int_ms(data.get("updated_at") if isinstance(data, dict) else None)
    result = {"templates": sort_instruction_templates(templates), "groups": groups, "updated_at": updated_at}
    if not os.path.exists(INSTRUCTION_TEMPLATES_PATH):
        save_instruction_templates(result.get("templates", []), result.get("groups", []))
    return result


def save_instruction_templates(templates, groups=None):
    clean = [
        normalized
        for normalized in (normalize_instruction_template(item) for item in (templates or []))
        if normalized
    ]
    if groups is None:
        existing = _read_instruction_template_data()
        groups = existing.get("groups") if isinstance(existing, dict) else []
        existing_templates = existing.get("templates") if isinstance(existing, dict) else []
        existing_custom = [
            normalized
            for normalized in (normalize_instruction_template(item) for item in (existing_templates or []))
            if normalized and normalized.get("scope") not in VALID_TEMPLATE_SCOPES
        ]
        clean = [item for item in clean if item.get("scope") in VALID_TEMPLATE_SCOPES]
        known_ids = {item.get("id") for item in clean}
        clean.extend(item for item in existing_custom if item.get("id") not in known_ids)
    clean_groups = _normalize_groups(groups, clean)
    data = {"templates": sort_instruction_templates(clean), "groups": clean_groups, "updated_at": now_ms()}
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INSTRUCTION_TEMPLATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def create_instruction_template_group(name):
    data = load_instruction_templates()
    group = {
        "id": f"custom:{uuid.uuid4().hex[:12]}",
        "name": sanitize_instruction_group_name(name),
        "createdAt": now_ms(),
        "updatedAt": now_ms(),
    }
    groups = data.get("groups", []) + [group]
    saved = save_instruction_templates(data.get("templates", []), groups)
    return {"library": saved, "group": group}


def rename_instruction_template_group(group_id, name):
    group_id = str(group_id or "").strip().lower()
    if group_id in VALID_TEMPLATE_SCOPES:
        raise ValueError("Default instruction template groups cannot be renamed")
    if not CUSTOM_TEMPLATE_SCOPE_RE.match(group_id):
        raise KeyError("Group not found")
    data = load_instruction_templates()
    groups = data.get("groups", [])
    target = None
    for group in groups:
        if group.get("id") == group_id:
            target = group
            break
    if not target:
        raise KeyError("Group not found")
    target["name"] = sanitize_instruction_group_name(name, target.get("name") or "未命名分组")
    target["updatedAt"] = now_ms()
    saved = save_instruction_templates(data.get("templates", []), groups)
    return {"library": saved, "group": target}


def delete_instruction_template_group(group_id):
    group_id = str(group_id or "").strip().lower()
    if group_id in VALID_TEMPLATE_SCOPES:
        raise ValueError("Default instruction template groups cannot be deleted")
    if not CUSTOM_TEMPLATE_SCOPE_RE.match(group_id):
        raise KeyError("Group not found")
    data = load_instruction_templates()
    groups = data.get("groups", [])
    if not any(group.get("id") == group_id for group in groups):
        raise KeyError("Group not found")
    templates = [item for item in data.get("templates", []) if item.get("scope") != group_id]
    groups = [group for group in groups if group.get("id") != group_id]
    return save_instruction_templates(templates, groups)
