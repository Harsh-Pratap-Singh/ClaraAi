"""
Clara AI Pipeline – Task Tracker
Creates tracking items for each processed account.
Supports: local JSON tracker (always), GitHub Issues (optional).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.config import OUTPUT_DIR, GITHUB_TOKEN, GITHUB_REPO, logger


TRACKER_FILE = OUTPUT_DIR / "task_tracker.json"


def _load_tracker() -> list[dict]:
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
    return []


def _save_tracker(tasks: list[dict]):
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(tasks, indent=2, default=str), encoding="utf-8")


def create_task(account_id: str, company_name: str, action: str, version: str, details: str = "") -> dict:
    """
    Create a tracking task for an account processing step.
    Saves locally and optionally creates a GitHub Issue.
    """
    task = {
        "id": f"{account_id}-{version}-{action}",
        "account_id": account_id,
        "company_name": company_name,
        "action": action,
        "version": version,
        "status": "completed",
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save to local tracker
    tasks = _load_tracker()
    # Remove duplicate if re-running (idempotent)
    tasks = [t for t in tasks if t["id"] != task["id"]]
    tasks.append(task)
    _save_tracker(tasks)
    logger.info(f"Task tracked: {task['id']}")

    # Optional: create GitHub issue
    if GITHUB_TOKEN and GITHUB_REPO:
        _create_github_issue(task)

    return task


def _create_github_issue(task: dict):
    """Create a GitHub Issue as task tracker (optional)."""
    try:
        import requests
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        body = (
            f"**Account:** {task['company_name']} (`{task['account_id']}`)\n"
            f"**Action:** {task['action']}\n"
            f"**Version:** {task['version']}\n"
            f"**Details:** {task['details']}\n"
        )
        data = {
            "title": f"[{task['version'].upper()}] {task['company_name']} – {task['action']}",
            "body": body,
            "labels": ["automation", task["version"]],
        }
        resp = requests.post(url, json=data, headers=headers, timeout=10)
        if resp.status_code == 201:
            logger.info(f"GitHub Issue created: {resp.json().get('html_url')}")
        else:
            logger.warning(f"GitHub Issue creation failed: {resp.status_code}")
    except Exception as e:
        logger.warning(f"GitHub Issue creation skipped: {e}")
