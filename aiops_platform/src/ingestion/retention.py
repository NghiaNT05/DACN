"""Retention policy for ingestion state and history files.

Implements cleanup of:
- Stale entries in ingestion_state_v1.json
- Old history files in data/incidents/history/
- Old bundle files in data/retrieval/
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_STATE_RETENTION_DAYS = 7
DEFAULT_HISTORY_RETENTION_DAYS = 14
DEFAULT_BUNDLE_RETENTION_DAYS = 14


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def prune_state_entries(
    state_path: Path,
    retention_days: int = DEFAULT_STATE_RETENTION_DAYS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Remove stale entries from ingestion state file.
    
    Returns summary of pruned entries.
    """
    if not state_path.exists():
        return {
            "status": "skipped",
            "reason": "state file not found",
            "path": str(state_path),
        }
    
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {
            "status": "error",
            "reason": str(e),
            "path": str(state_path),
        }
    
    entries = state.get("entries", {})
    if not isinstance(entries, dict):
        return {
            "status": "skipped",
            "reason": "no entries dict",
            "path": str(state_path),
        }
    
    cutoff = _now_utc() - timedelta(days=retention_days)
    original_count = len(entries)
    pruned_keys: List[str] = []
    
    for key, entry in list(entries.items()):
        if not isinstance(entry, dict):
            pruned_keys.append(key)
            continue
        
        last_seen = _parse_iso(entry.get("last_seen_at", ""))
        if last_seen is None or last_seen < cutoff:
            pruned_keys.append(key)
    
    if not dry_run:
        for key in pruned_keys:
            entries.pop(key, None)
        
        state["entries"] = entries
        state["updated_at"] = _now_utc().isoformat()
        state["last_prune_at"] = _now_utc().isoformat()
        state_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    
    return {
        "status": "ok",
        "path": str(state_path),
        "retention_days": retention_days,
        "original_count": original_count,
        "pruned_count": len(pruned_keys),
        "remaining_count": original_count - len(pruned_keys),
        "dry_run": dry_run,
        "pruned_keys_sample": pruned_keys[:10],
    }


def prune_history_files(
    history_dir: Path,
    retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Remove old history files from data/incidents/history/.
    
    Files are identified by modification time.
    """
    if not history_dir.exists():
        return {
            "status": "skipped",
            "reason": "history dir not found",
            "path": str(history_dir),
        }
    
    cutoff = _now_utc() - timedelta(days=retention_days)
    cutoff_timestamp = cutoff.timestamp()
    
    files = list(history_dir.glob("*.json"))
    original_count = len(files)
    pruned_files: List[str] = []
    freed_bytes = 0
    
    for file_path in files:
        try:
            mtime = file_path.stat().st_mtime
            if mtime < cutoff_timestamp:
                freed_bytes += file_path.stat().st_size
                pruned_files.append(file_path.name)
                if not dry_run:
                    file_path.unlink()
        except OSError:
            continue
    
    return {
        "status": "ok",
        "path": str(history_dir),
        "retention_days": retention_days,
        "original_count": original_count,
        "pruned_count": len(pruned_files),
        "remaining_count": original_count - len(pruned_files),
        "freed_bytes": freed_bytes,
        "dry_run": dry_run,
        "pruned_files_sample": pruned_files[:10],
    }


def prune_bundle_files(
    bundle_dir: Path,
    retention_days: int = DEFAULT_BUNDLE_RETENTION_DAYS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Remove old retrieval bundle files.
    
    Handles both .txt and .json bundle formats.
    """
    if not bundle_dir.exists():
        return {
            "status": "skipped",
            "reason": "bundle dir not found",
            "path": str(bundle_dir),
        }
    
    cutoff = _now_utc() - timedelta(days=retention_days)
    cutoff_timestamp = cutoff.timestamp()
    
    files = list(bundle_dir.glob("bundle*.txt")) + list(bundle_dir.glob("bundle*.json"))
    original_count = len(files)
    pruned_files: List[str] = []
    freed_bytes = 0
    
    for file_path in files:
        try:
            mtime = file_path.stat().st_mtime
            if mtime < cutoff_timestamp:
                freed_bytes += file_path.stat().st_size
                pruned_files.append(file_path.name)
                if not dry_run:
                    file_path.unlink()
        except OSError:
            continue
    
    return {
        "status": "ok",
        "path": str(bundle_dir),
        "retention_days": retention_days,
        "original_count": original_count,
        "pruned_count": len(pruned_files),
        "remaining_count": original_count - len(pruned_files),
        "freed_bytes": freed_bytes,
        "dry_run": dry_run,
        "pruned_files_sample": pruned_files[:10],
    }


def run_full_retention(
    state_path: Optional[Path] = None,
    history_dir: Optional[Path] = None,
    bundle_dir: Optional[Path] = None,
    state_retention_days: int = DEFAULT_STATE_RETENTION_DAYS,
    history_retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS,
    bundle_retention_days: int = DEFAULT_BUNDLE_RETENTION_DAYS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run all retention policies.
    
    Uses default paths if not specified.
    """
    root = Path(__file__).resolve().parents[2]
    
    state_path = state_path or (root / "data" / "incidents" / "ingestion_state_v1.json")
    history_dir = history_dir or (root / "data" / "incidents" / "history")
    bundle_dir = bundle_dir or (root / "data" / "retrieval")
    
    results = {
        "timestamp": _now_utc().isoformat(),
        "dry_run": dry_run,
        "state_prune": prune_state_entries(
            state_path=state_path,
            retention_days=state_retention_days,
            dry_run=dry_run,
        ),
        "history_prune": prune_history_files(
            history_dir=history_dir,
            retention_days=history_retention_days,
            dry_run=dry_run,
        ),
        "bundle_prune": prune_bundle_files(
            bundle_dir=bundle_dir,
            retention_days=bundle_retention_days,
            dry_run=dry_run,
        ),
    }
    
    total_pruned = (
        results["state_prune"].get("pruned_count", 0) +
        results["history_prune"].get("pruned_count", 0) +
        results["bundle_prune"].get("pruned_count", 0)
    )
    total_freed = (
        results["history_prune"].get("freed_bytes", 0) +
        results["bundle_prune"].get("freed_bytes", 0)
    )
    
    results["summary"] = {
        "total_items_pruned": total_pruned,
        "total_bytes_freed": total_freed,
    }
    
    return results
