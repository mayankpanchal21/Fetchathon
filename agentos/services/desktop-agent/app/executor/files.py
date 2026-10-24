import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..policy import validate_workspace_path, PolicyViolation

MAX_FILE_READ_BYTES = 500 * 1024  # 500 KB limit for safe read


def list_files(directory: str = ".") -> Dict[str, Any]:
    target_dir = validate_workspace_path(directory, allow_read_only_cwd=True)
    if not target_dir.exists():
        raise FileNotFoundError(f"Directory '{directory}' does not exist.")
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Path '{directory}' is a file, not a directory.")

    entries: List[Dict[str, Any]] = []
    for item in sorted(target_dir.iterdir()):
        try:
            stat = item.stat()
            entries.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": stat.st_size if not item.is_dir() else 0,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except (PermissionError, FileNotFoundError):
            continue

    return {
        "directory": str(target_dir),
        "total_items": len(entries),
        "items": entries[:200]
    }


def search_files(directory: str = ".", query: str = "") -> Dict[str, Any]:
    target_dir = validate_workspace_path(directory, allow_read_only_cwd=True)
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Search directory '{directory}' does not exist.")

    clean_query = query.strip().lower()
    matches: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(target_dir):
        # Don't recurse into hidden or heavy directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", ".venv", "__pycache__"}]
        for f in files:
            if clean_query in f.lower():
                full_path = Path(root) / f
                try:
                    stat = full_path.stat()
                    matches.append({
                        "filename": f,
                        "path": str(full_path),
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception:
                    continue
            if len(matches) >= 100:
                break
        if len(matches) >= 100:
            break

    return {
        "query": query,
        "search_root": str(target_dir),
        "total_matches": len(matches),
        "matches": matches
    }


def create_directory(path: str) -> Dict[str, Any]:
    target_dir = validate_workspace_path(path)
    target_dir.mkdir(parents=True, exist_ok=True)
    return {
        "action": "create_directory",
        "created_path": str(target_dir),
        "status": "success",
        "verified": target_dir.exists() and target_dir.is_dir()
    }


def read_text_file(path: str) -> Dict[str, Any]:
    target_file = validate_workspace_path(path, allow_read_only_cwd=True)
    if not target_file.exists():
        raise FileNotFoundError(f"File '{path}' does not exist.")
    if not target_file.is_file():
        raise IsADirectoryError(f"Path '{path}' is a directory, not a file.")

    stat = target_file.stat()
    if stat.st_size > MAX_FILE_READ_BYTES:
        raise PolicyViolation(
            f"File '{path}' size ({stat.st_size} bytes) exceeds maximum safe read limit ({MAX_FILE_READ_BYTES} bytes)."
        )

    with open(target_file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return {
        "path": str(target_file),
        "size_bytes": stat.st_size,
        "content": content
    }


def write_text_file(path: str, content: str) -> Dict[str, Any]:
    target_file = validate_workspace_path(path)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "action": "write_text_file",
        "path": str(target_file),
        "bytes_written": len(content.encode("utf-8")),
        "status": "success",
        "verified": target_file.exists() and target_file.stat().st_size >= len(content.encode("utf-8"))
    }
