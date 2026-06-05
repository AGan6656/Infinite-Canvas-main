from __future__ import annotations

import os
import re
import shutil
import time
import urllib.parse
import uuid
import zipfile
from io import BytesIO

from fastapi import Header, HTTPException, Request
from fastapi.responses import Response

from ..core import ASSET_LIBRARY_DIR, OUTPUT_DIR, app, manager
from ..repositories import (
    canvas_path,
    conversation_path,
    find_asset_category,
    list_canvases,
    list_conversations,
    list_deleted_canvases,
    load_canvas_assets,
    load_asset_library,
    load_canvas,
    load_canvas_any,
    load_conversation,
    load_instruction_templates,
    new_canvas,
    new_conversation,
    normalize_canvas_kind,
    now_ms,
    safe_user_id,
    sanitize_asset_name,
    save_canvas_asset_extraction,
    save_asset_library,
    save_canvas,
    save_instruction_templates,
    delete_canvas_assets,
)
from ..schemas import (
    AssetLibraryAddRequest,
    AssetLibraryCategoryRequest,
    AssetLibraryRenameRequest,
    CanvasAssetCheckRequest,
    CanvasAssetDownloadRequest,
    CanvasCreateRequest,
    CanvasExtractedAssetsSaveRequest,
    CanvasSaveRequest,
    ConversationCreateRequest,
    InstructionTemplateSaveRequest,
    SmartCanvasGroupExportRequest,
)
from .media_storage import content_type_for_path, output_file_from_url


@app.get("/api/conversations")
async def conversations(request: Request, x_user_id: str = Header(default="")):
    user_id = safe_user_id(x_user_id, request)
    return {"user_id": user_id, "conversations": list_conversations(user_id)}


@app.post("/api/conversations")
async def create_conversation(payload: ConversationCreateRequest, request: Request, x_user_id: str = Header(default="")):
    user_id = safe_user_id(x_user_id, request)
    return {"conversation": new_conversation(user_id, payload.title)}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, request: Request, x_user_id: str = Header(default="")):
    user_id = safe_user_id(x_user_id, request)
    return {"conversation": load_conversation(user_id, conversation_id)}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request, x_user_id: str = Header(default="")):
    user_id = safe_user_id(x_user_id, request)
    path = conversation_path(user_id, conversation_id)
    if os.path.exists(path):
        os.remove(path)
    return {"ok": True}


@app.get("/api/canvases")
async def canvases():
    return {"canvases": list_canvases()}


@app.get("/api/canvases/trash")
async def trashed_canvases():
    return {"canvases": list_deleted_canvases(), "retention_days": 30}


@app.post("/api/canvases")
async def create_canvas(payload: CanvasCreateRequest):
    return {"canvas": new_canvas(payload.title, payload.icon, payload.kind)}


@app.get("/api/canvases/{canvas_id}/meta")
async def get_canvas_meta(canvas_id: str):
    canvas = load_canvas(canvas_id)
    return {
        "id": canvas.get("id"),
        "updated_at": canvas.get("updated_at", 0),
        "title": canvas.get("title", "Untitled Canvas"),
        "icon": canvas.get("icon", "layers"),
        "kind": normalize_canvas_kind(canvas.get("kind")),
    }


@app.get("/api/canvases/{canvas_id}")
async def get_canvas(canvas_id: str):
    return {"canvas": load_canvas(canvas_id)}


@app.get("/api/canvases/{canvas_id}/assets")
async def get_canvas_extracted_assets(canvas_id: str):
    load_canvas(canvas_id)
    return {"assets": load_canvas_assets(canvas_id)}


@app.put("/api/canvases/{canvas_id}/assets/{node_id}")
async def save_canvas_extracted_assets(canvas_id: str, node_id: str, payload: CanvasExtractedAssetsSaveRequest):
    load_canvas(canvas_id)
    assets = save_canvas_asset_extraction(canvas_id, node_id, payload.dict())
    return {"assets": assets, "extraction": assets.get("extractions", {}).get(node_id)}


@app.post("/api/canvas-assets/check")
async def check_canvas_assets(payload: CanvasAssetCheckRequest):
    result = {}
    for url in payload.urls[:3000]:
        text = str(url or "").strip()
        if not text:
            continue
        if text.startswith("/output/") or text.startswith("/assets/"):
            result[text] = bool(output_file_from_url(text))
        else:
            result[text] = True
    return {"exists": result}


@app.post("/api/canvas-assets/download")
async def download_canvas_assets(payload: CanvasAssetDownloadRequest):
    buffer = BytesIO()
    used_names = set()
    count = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for url in payload.urls[:1000]:
            text = str(url or "").strip()
            if not text or not (text.startswith("/output/") or text.startswith("/assets/")):
                continue
            path = output_file_from_url(text)
            if not path or not os.path.isfile(path):
                continue
            base = os.path.basename(path) or f"image-{count + 1}.png"
            name, ext = os.path.splitext(base)
            archive_name = base
            suffix = 2
            while archive_name in used_names:
                archive_name = f"{name}-{suffix}{ext}"
                suffix += 1
            used_names.add(archive_name)
            zf.write(path, archive_name)
            count += 1
    if count <= 0:
        raise HTTPException(status_code=404, detail="No local images are available to download")
    buffer.seek(0)
    filename = re.sub(r'[\\/:*?"<>|]+', "_", payload.filename or "canvas-output-images.zip")
    if not filename.lower().endswith(".zip"):
        filename += ".zip"
    encoded = urllib.parse.quote(filename)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"}
    return Response(buffer.getvalue(), media_type="application/zip", headers=headers)


def sanitize_export_filename(name: str, fallback: str) -> str:
    base = os.path.basename(str(name or "").strip()) or fallback
    base = re.sub(r'[\\/:*?"<>|]+', "_", base)
    return base or fallback


def smart_group_export_folder(folder: str, group_name: str) -> str:
    text = str(folder or "").strip()
    if text:
        path = os.path.abspath(os.path.expanduser(text))
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_group = sanitize_export_filename(group_name or "group", "group")
        path = os.path.abspath(os.path.join(OUTPUT_DIR, "smart-groups", f"{safe_group}-{stamp}"))
    os.makedirs(path, exist_ok=True)
    return path


@app.post("/api/smart-canvas/group-export")
async def export_smart_canvas_group(payload: SmartCanvasGroupExportRequest):
    target_dir = smart_group_export_folder(payload.folder, payload.group_name)
    used_names = set()
    count = 0
    text_index = 1
    for item in payload.items[:2000]:
        kind = str(item.kind or "").lower()
        if kind == "text":
            text = str(item.text or "")
            if not text.strip():
                continue
            base = sanitize_export_filename(item.name or f"{text_index}.txt", f"{text_index}.txt")
            if not base.lower().endswith(".txt"):
                base += ".txt"
            text_index += 1
            name, ext = os.path.splitext(base)
            out_name = base
            suffix = 2
            while out_name in used_names:
                out_name = f"{name}-{suffix}{ext}"
                suffix += 1
            used_names.add(out_name)
            with open(os.path.join(target_dir, out_name), "w", encoding="utf-8") as f:
                f.write(text)
            count += 1
            continue
        src = output_file_from_url(item.url)
        if not src or not os.path.isfile(src):
            continue
        base = sanitize_export_filename(item.name or os.path.basename(src), os.path.basename(src) or f"asset-{count + 1}")
        name, ext = os.path.splitext(base)
        if not ext:
            _, src_ext = os.path.splitext(src)
            ext = src_ext or ".bin"
            base = name + ext
        out_name = base
        suffix = 2
        while out_name in used_names:
            out_name = f"{name}-{suffix}{ext}"
            suffix += 1
        used_names.add(out_name)
        shutil.copy2(src, os.path.join(target_dir, out_name))
        count += 1
    if count <= 0:
        raise HTTPException(status_code=404, detail="No exportable content found")
    return {"ok": True, "folder": target_dir, "count": count}


@app.get("/api/asset-library")
async def get_asset_library():
    return {"library": load_asset_library()}


@app.get("/api/instruction-templates")
async def get_instruction_templates():
    return load_instruction_templates()


@app.put("/api/instruction-templates")
async def put_instruction_templates(payload: InstructionTemplateSaveRequest):
    return save_instruction_templates(payload.templates)


@app.post("/api/asset-library/categories")
async def create_asset_library_category(payload: AssetLibraryCategoryRequest):
    lib = load_asset_library()
    cat_type = "workflow" if str(payload.type or "").lower() == "workflow" else "image"
    category = {"id": f"cat_{uuid.uuid4().hex[:12]}", "name": sanitize_asset_name(payload.name, "New Folder"), "type": cat_type, "items": []}
    lib.setdefault("categories", []).append(category)
    save_asset_library(lib)
    return {"library": lib, "category": category}


@app.patch("/api/asset-library/categories/{category_id}")
async def rename_asset_library_category(category_id: str, payload: AssetLibraryRenameRequest):
    lib = load_asset_library()
    cat = find_asset_category(lib, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat["name"] = sanitize_asset_name(payload.name, cat.get("name") or "New Folder")
    save_asset_library(lib)
    return {"library": lib, "category": cat}


@app.delete("/api/asset-library/categories/{category_id}")
async def delete_asset_library_category(category_id: str):
    lib = load_asset_library()
    cat = find_asset_category(lib, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.get("type") == "workflow" and category_id == "workflows":
        raise HTTPException(status_code=400, detail="The default workflow category cannot be deleted")
    lib["categories"] = [c for c in lib.get("categories", []) if c.get("id") != category_id]
    save_asset_library(lib)
    return {"library": lib}


@app.post("/api/asset-library/items")
async def add_asset_library_item(payload: AssetLibraryAddRequest):
    lib = load_asset_library()
    cat = find_asset_category(lib, payload.category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.get("type") != "image":
        raise HTTPException(status_code=400, detail="This category does not support image assets")
    src = output_file_from_url(payload.url)
    if not src:
        raise HTTPException(status_code=400, detail="Only local /assets or /output media can be saved")
    content_type = content_type_for_path(src)
    if content_type.startswith("video/"):
        kind = "video"
        fallback_ext = ".mp4"
    elif content_type.startswith("audio/"):
        kind = "audio"
        fallback_ext = ".mp3"
    elif content_type.startswith("image/"):
        kind = "image"
        fallback_ext = ".png"
    else:
        raise HTTPException(status_code=400, detail="Only local image, video, or audio assets can be saved")
    ext = os.path.splitext(src)[1].lower() or fallback_ext
    safe_name = sanitize_asset_name(payload.name or os.path.basename(src), "asset")
    if not os.path.splitext(safe_name)[1]:
        safe_name += ext
    dest_name = f"lib_{uuid.uuid4().hex[:12]}_{safe_name}"
    dest_path = os.path.join(ASSET_LIBRARY_DIR, dest_name)
    shutil.copy2(src, dest_path)
    item = {
        "id": f"asset_{uuid.uuid4().hex[:12]}",
        "name": os.path.splitext(safe_name)[0][:120],
        "url": f"/assets/library/{dest_name}",
        "kind": kind,
        "created_at": now_ms(),
    }
    cat.setdefault("items", []).append(item)
    save_asset_library(lib)
    return {"library": lib, "item": item}


@app.patch("/api/asset-library/items/{item_id}")
async def rename_asset_library_item(item_id: str, payload: AssetLibraryRenameRequest):
    lib = load_asset_library()
    for cat in lib.get("categories", []):
        for item in cat.get("items", []):
            if item.get("id") == item_id:
                item["name"] = sanitize_asset_name(payload.name, item.get("name") or "asset")
                save_asset_library(lib)
                return {"library": lib, "item": item}
    raise HTTPException(status_code=404, detail="Asset not found")


@app.delete("/api/asset-library/items/{item_id}")
async def delete_asset_library_item(item_id: str):
    lib = load_asset_library()
    removed = None
    for cat in lib.get("categories", []):
        keep = []
        for item in cat.get("items", []):
            if item.get("id") == item_id:
                removed = item
            else:
                keep.append(item)
        cat["items"] = keep
    if not removed:
        raise HTTPException(status_code=404, detail="Asset not found")
    save_asset_library(lib)
    return {"library": lib}


@app.put("/api/canvases/{canvas_id}")
async def update_canvas(canvas_id: str, payload: CanvasSaveRequest):
    canvas = load_canvas(canvas_id)
    current_updated_at = int(canvas.get("updated_at") or 0)
    if payload.base_updated_at and current_updated_at and int(payload.base_updated_at) < current_updated_at:
        raise HTTPException(status_code=409, detail={
            "message": "The canvas was updated elsewhere, so the older save was rejected.",
            "canvas": canvas,
            "updated_at": current_updated_at,
        })
    canvas["title"] = (payload.title or canvas.get("title") or "Untitled Canvas")[:80]
    canvas["icon"] = (payload.icon or canvas.get("icon") or "layers")[:32]
    canvas["kind"] = normalize_canvas_kind(canvas.get("kind"))
    canvas["nodes"] = payload.nodes
    canvas["connections"] = payload.connections
    canvas["viewport"] = payload.viewport
    canvas["logs"] = payload.logs[-500:]
    canvas["settings"] = payload.settings or {}
    save_canvas(canvas)
    await manager.broadcast_canvas_updated(canvas_id, int(canvas.get("updated_at") or now_ms()), payload.client_id)
    return {"canvas": canvas}


@app.delete("/api/canvases/{canvas_id}")
async def delete_canvas(canvas_id: str):
    canvas = load_canvas_any(canvas_id)
    if not canvas.get("deleted_at"):
        canvas["deleted_at"] = now_ms()
        save_canvas(canvas)
    return {"ok": True}


@app.post("/api/canvases/{canvas_id}/restore")
async def restore_canvas(canvas_id: str):
    canvas = load_canvas_any(canvas_id)
    if canvas.get("deleted_at"):
        canvas.pop("deleted_at", None)
        save_canvas(canvas)
    return {"canvas": canvas}


@app.delete("/api/canvases/{canvas_id}/purge")
async def purge_canvas(canvas_id: str):
    path = canvas_path(canvas_id)
    if os.path.exists(path):
        os.remove(path)
    delete_canvas_assets(canvas_id)
    return {"ok": True}
