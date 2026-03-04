"""
Clara AI Pipeline – Versioning & Diff Engine
Handles v1 → v2 transitions, changelog generation, and merge logic.
"""
from __future__ import annotations
import json, copy
from datetime import datetime, timezone
from pathlib import Path
from deepdiff import DeepDiff
from scripts.config import logger


def deep_merge(base: dict, updates: dict) -> dict:
    """
    Deep-merge `updates` into `base`. 
    - None/null values in updates are skipped (don't overwrite).
    - Empty lists in updates are skipped.
    - Non-empty values in updates overwrite base.
    """
    merged = copy.deepcopy(base)
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, list) and len(value) == 0:
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def compute_diff(v1: dict, v2: dict) -> dict:
    """Compute a human-readable diff between v1 and v2 memos."""
    diff = DeepDiff(v1, v2, ignore_order=True, verbose_level=2)
    
    changes = {
        "added": {},
        "removed": {},
        "changed": {},
    }

    if "dictionary_item_added" in diff:
        for path in diff["dictionary_item_added"]:
            changes["added"][path] = diff["dictionary_item_added"][path]

    if "dictionary_item_removed" in diff:
        for path in diff["dictionary_item_removed"]:
            changes["removed"][path] = diff["dictionary_item_removed"][path]

    if "values_changed" in diff:
        for path, change in diff["values_changed"].items():
            changes["changed"][path] = {
                "old": change.get("old_value"),
                "new": change.get("new_value")
            }

    if "iterable_item_added" in diff:
        for path in diff["iterable_item_added"]:
            changes["added"][path] = diff["iterable_item_added"][path]

    if "iterable_item_removed" in diff:
        for path in diff["iterable_item_removed"]:
            changes["removed"][path] = diff["iterable_item_removed"][path]

    return changes


def generate_changelog(account_id: str, company_name: str, changes: dict) -> str:
    """Generate a markdown changelog from a diff."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    lines = [
        f"# Changelog – {company_name}",
        f"**Account ID:** {account_id}",
        f"**Updated:** {timestamp}",
        f"**Transition:** v1 (Demo) → v2 (Post-Onboarding)",
        "",
        "---",
        "",
    ]

    if changes["changed"]:
        lines.append("## Changed Fields")
        lines.append("")
        for path, vals in changes["changed"].items():
            clean_path = path.replace("root['", "").replace("']['", " → ").replace("']", "")
            lines.append(f"### `{clean_path}`")
            lines.append(f"- **Before:** {vals['old']}")
            lines.append(f"- **After:** {vals['new']}")
            lines.append("")

    if changes["added"]:
        lines.append("## Added Fields / Items")
        lines.append("")
        for path, val in changes["added"].items():
            clean_path = path.replace("root['", "").replace("']['", " → ").replace("']", "")
            lines.append(f"- **{clean_path}:** {val}")
        lines.append("")

    if changes["removed"]:
        lines.append("## Removed Fields / Items")
        lines.append("")
        for path, val in changes["removed"].items():
            clean_path = path.replace("root['", "").replace("']['", " → ").replace("']", "")
            lines.append(f"- ~~{clean_path}~~: {val}")
        lines.append("")

    if not any(changes.values()):
        lines.append("_No changes detected between v1 and v2._")

    return "\n".join(lines)


def generate_changes_json(account_id: str, company_name: str, changes: dict) -> dict:
    """Generate a structured JSON changelog."""
    return {
        "account_id": account_id,
        "company_name": company_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transition": "v1 → v2",
        "summary": {
            "fields_changed": len(changes.get("changed", {})),
            "fields_added": len(changes.get("added", {})),
            "fields_removed": len(changes.get("removed", {})),
        },
        "details": changes,
    }


def apply_onboarding_update(v1_memo: dict, onboarding_memo: dict) -> tuple[dict, dict, str, dict]:
    """
    Apply onboarding updates to a v1 memo.
    
    Returns:
        (v2_memo, diff_dict, changelog_md, changes_json)
    """
    account_id = v1_memo.get("account_id", "unknown")
    company = v1_memo.get("company_name", "Unknown")
    
    logger.info(f"Applying onboarding update to {account_id}")
    
    # Merge onboarding data into v1
    v2_memo = deep_merge(v1_memo, onboarding_memo)
    v2_memo["account_id"] = account_id  # preserve original account_id
    
    # Compute diff
    diff = compute_diff(v1_memo, v2_memo)
    
    # Generate changelogs
    changelog_md = generate_changelog(account_id, company, diff)
    changes_json = generate_changes_json(account_id, company, diff)
    
    logger.info(f"Update applied: {changes_json['summary']['fields_changed']} changed, "
                f"{changes_json['summary']['fields_added']} added, "
                f"{changes_json['summary']['fields_removed']} removed")
    
    return v2_memo, diff, changelog_md, changes_json
