# KG Config file management
# List and read configuration files from knowledge_config/ directory

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import yaml
import json


# Base directory for configs (relative to project root)
CONFIG_BASE_DIR = Path("knowledge_config")

# File type whitelist
ALLOWED_EXTENSIONS = {".yml", ".yaml", ".json"}

# Security: max file size 2MB
MAX_FILE_SIZE = 2 * 1024 * 1024


def _is_safe_path(base_dir: Path, requested_path: str) -> bool:
    """Check if requested path is safe (no ../, no absolute paths)"""
    if ".." in requested_path or os.path.isabs(requested_path):
        return False
    
    try:
        full_path = (base_dir / requested_path).resolve()
        return full_path.is_relative_to(base_dir.resolve())
    except (ValueError, OSError):
        return False


def _get_file_info(file_path: Path, base_dir: Path) -> Dict[str, Any]:
    """Get file metadata"""
    stat = file_path.stat()
    rel_path = file_path.relative_to(base_dir)
    
    file_type = "unknown"
    if file_path.suffix in [".yml", ".yaml"]:
        file_type = "yaml"
    elif file_path.suffix == ".json":
        file_type = "json"
    
    return {
        "name": file_path.name,
        "type": file_type,
        "rel_path": str(rel_path).replace("\\", "/"),
        "size_bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


async def list_kg_configs(subdir: Optional[str] = None) -> Dict[str, Any]:
    """List configuration files in knowledge_config/ directory
    
    Args:
        subdir: Optional subdirectory to list (e.g., "config")
    
    Returns:
        Dict with items list and metadata
    """
    base_dir = CONFIG_BASE_DIR
    
    if subdir:
        if not _is_safe_path(base_dir, subdir):
            raise ValueError("Invalid subdirectory path")
        base_dir = base_dir / subdir
    
    if not base_dir.exists():
        return {"items": [], "total": 0, "base_dir": str(base_dir)}
    
    items = []
    
    # Recursively find all config files
    for ext in ALLOWED_EXTENSIONS:
        for file_path in base_dir.rglob(f"*{ext}"):
            if file_path.is_file() and file_path.stat().st_size <= MAX_FILE_SIZE:
                try:
                    info = _get_file_info(file_path, CONFIG_BASE_DIR)
                    items.append(info)
                except (OSError, ValueError):
                    continue
    
    # Sort by path
    items.sort(key=lambda x: x["rel_path"])
    
    return {
        "items": items,
        "total": len(items),
        "base_dir": str(CONFIG_BASE_DIR)
    }


async def read_kg_config(rel_path: str) -> Dict[str, Any]:
    """Read a specific configuration file
    
    Args:
        rel_path: Relative path from knowledge_config/
    
    Returns:
        Dict with name, type, and content
    """
    if not _is_safe_path(CONFIG_BASE_DIR, rel_path):
        raise ValueError("Invalid file path")
    
    file_path = CONFIG_BASE_DIR / rel_path
    
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"Config file not found: {rel_path}")
    
    if file_path.suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type not allowed: {file_path.suffix}")
    
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large (max {MAX_FILE_SIZE} bytes)")
    
    # Read and parse content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content_str = f.read()
        
        file_type = "unknown"
        parsed_content = None
        
        if file_path.suffix in [".yml", ".yaml"]:
            file_type = "yaml"
            parsed_content = yaml.safe_load(content_str)
        elif file_path.suffix == ".json":
            file_type = "json"
            parsed_content = json.loads(content_str)
        
        return {
            "name": file_path.name,
            "type": file_type,
            "rel_path": rel_path,
            "content": parsed_content,
            "raw_content": content_str,
        }
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse config file: {str(e)}")
    except UnicodeDecodeError:
        raise ValueError("File must be UTF-8 encoded")
