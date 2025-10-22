# Knowledge Graph config listing and reading routes
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import os
import json
import yaml
from datetime import datetime

router = APIRouter()

# Root directory for knowledge configs
BASE_DIR = Path(__file__).resolve().parents[2]
KC_ROOT = (BASE_DIR / "knowledge_config").resolve()

ALLOWED_EXTS = {".yml", ".yaml", ".json"}
MAX_BYTES = 2 * 1024 * 1024  # 2 MiB


class ConfigItem(BaseModel):
    name: str
    type: str  # 'yaml' | 'json'
    rel_path: str
    size_bytes: int
    mtime: str
    meta: Optional[Dict[str, Any]] = None


class ConfigListResponse(BaseModel):
    items: List[ConfigItem]


class ConfigContentResponse(BaseModel):
    name: str
    type: str
    content: str


def _detect_type(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in {".yml", ".yaml"}:
        return "yaml"
    if ext == ".json":
        return "json"
    return "unknown"


def _safe_rel_path(p: Path) -> str:
    return str(p.relative_to(KC_ROOT)).replace("\\", "/")


@router.get("/configs", response_model=ConfigListResponse)
async def list_knowledge_configs() -> ConfigListResponse:
    if not KC_ROOT.exists() or not KC_ROOT.is_dir():
        raise HTTPException(status_code=404, detail="knowledge_config directory not found")

    items: List[ConfigItem] = []
    for p in KC_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in ALLOWED_EXTS:
            continue
        try:
            stat = p.stat()
            meta: Optional[Dict[str, Any]] = None
            file_type = _detect_type(p)
            # Light meta for YAML files (version/description)
            if file_type == "yaml":
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    doc = yaml.safe_load(text) or {}
                    if isinstance(doc, dict):
                        md: Dict[str, Any] = {}
                        if "version" in doc:
                            md["version"] = doc.get("version")
                        if "description" in doc:
                            md["description"] = doc.get("description")
                        meta = md or None
                except Exception:
                    meta = None
            items.append(
                ConfigItem(
                    name=p.name,
                    type=file_type,
                    rel_path=_safe_rel_path(p),
                    size_bytes=stat.st_size,
                    mtime=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    meta=meta,
                )
            )
        except Exception:
            # Skip unreadable entries
            continue

    items.sort(key=lambda x: x.rel_path)
    return ConfigListResponse(items=items)


@router.get("/configs/{name:path}", response_model=ConfigContentResponse)
async def read_knowledge_config(name: str) -> ConfigContentResponse:
    # Deny absolute or parent traversal by resolving and verifying root containment
    target = (KC_ROOT / name).resolve()
    try:
        target.relative_to(KC_ROOT)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid path")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="config not found")

    if target.suffix.lower() not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="unsupported file type")

    size = target.stat().st_size
    if size > MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large")

    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=500, detail="failed to read file")

    return ConfigContentResponse(name=target.name, type=_detect_type(target), content=content)