"""
Clara AI Pipeline – Storage Manager
Handles saving/loading of account memos, agent specs, and changelogs.
"""
from __future__ import annotations
import json
from pathlib import Path
from scripts.config import ACCOUNTS_DIR, OUTPUT_DIR, logger


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def save_json(data: dict, path: Path):
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info(f"Saved: {path}")


def load_json(path: Path) -> dict | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_text(text: str, path: Path):
    _ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    logger.info(f"Saved: {path}")


def account_dir(account_id: str, version: str = "v1") -> Path:
    return ACCOUNTS_DIR / account_id / version


def save_account_v1(account_id: str, memo: dict, agent_spec: dict):
    """Save v1 (demo) artifacts for an account."""
    d = account_dir(account_id, "v1")
    save_json(memo, d / "account_memo.json")
    save_json(agent_spec, d / "agent_spec.json")
    # Also save agent prompt as standalone text for easy review
    if "system_prompt" in agent_spec:
        save_text(agent_spec["system_prompt"], d / "agent_prompt.txt")


def save_account_v2(account_id: str, memo: dict, agent_spec: dict,
                    changelog_md: str, changes_json: dict):
    """Save v2 (post-onboarding) artifacts for an account."""
    d = account_dir(account_id, "v2")
    save_json(memo, d / "account_memo.json")
    save_json(agent_spec, d / "agent_spec.json")
    save_text(changelog_md, d / "changelog.md")
    save_json(changes_json, d / "changes.json")
    if "system_prompt" in agent_spec:
        save_text(agent_spec["system_prompt"], d / "agent_prompt.txt")


def load_v1_memo(account_id: str) -> dict | None:
    return load_json(account_dir(account_id, "v1") / "account_memo.json")


def list_accounts() -> list[str]:
    """List all account IDs that have outputs."""
    if not ACCOUNTS_DIR.exists():
        return []
    return [d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()]


def get_run_summary() -> dict:
    """Get a summary of all processed accounts."""
    accounts = list_accounts()
    summary = {
        "total_accounts": len(accounts),
        "accounts": []
    }
    for aid in accounts:
        v1_exists = (account_dir(aid, "v1") / "account_memo.json").exists()
        v2_exists = (account_dir(aid, "v2") / "account_memo.json").exists()
        memo = load_json(account_dir(aid, "v1") / "account_memo.json") or {}
        summary["accounts"].append({
            "account_id": aid,
            "company_name": memo.get("company_name", "?"),
            "has_v1": v1_exists,
            "has_v2": v2_exists,
        })
    return summary
