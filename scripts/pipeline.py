"""
Clara AI Pipeline – Main Orchestrator
Runs Pipeline A (Demo → v1) and Pipeline B (Onboarding → v2) end-to-end.
"""
from __future__ import annotations
import json, sys, argparse
from pathlib import Path
from scripts.config import DATASET_DIR, OUTPUT_DIR, logger
from scripts.extractor import extract_account_memo, generate_account_id
from scripts.prompt_generator import generate_agent_spec
from scripts.versioning import apply_onboarding_update
from scripts.storage import (
    save_account_v1, save_account_v2, load_v1_memo,
    list_accounts, get_run_summary, save_json
)
from scripts.task_tracker import create_task


# ── Pipeline A: Demo Call → Preliminary Agent (v1) ────────────────────

def run_pipeline_a(transcript_path: Path) -> dict:
    """
    Pipeline A: Process a demo call transcript → v1 account memo + agent spec.
    
    Args:
        transcript_path: Path to the demo call transcript file
    
    Returns:
        dict with account_id and paths to outputs
    """
    logger.info(f"═══ Pipeline A: {transcript_path.name} ═══")
    
    # 1. Read transcript
    transcript = transcript_path.read_text(encoding="utf-8")
    logger.info(f"Read transcript: {len(transcript)} chars")
    
    # 2. Extract account memo
    memo = extract_account_memo(transcript, call_type="demo")
    
    # 3. Generate agent spec
    agent_spec = generate_agent_spec(memo, version="v1")
    
    # 4. Save outputs
    account_id = memo["account_id"]
    save_account_v1(account_id, memo, agent_spec)
    
    # 5. Create tracking task
    create_task(
        account_id=account_id,
        company_name=memo.get("company_name", "Unknown"),
        action="demo_processed",
        version="v1",
        details=f"Generated from {transcript_path.name}"
    )
    
    logger.info(f"✓ Pipeline A complete: {account_id}")
    return {
        "account_id": account_id,
        "company_name": memo.get("company_name"),
        "version": "v1",
        "source": str(transcript_path)
    }


# ── Pipeline B: Onboarding → Agent Update (v2) ───────────────────────

def run_pipeline_b(transcript_path: Path, account_id: str | None = None) -> dict:
    """
    Pipeline B: Process an onboarding call transcript → update to v2.
    
    Args:
        transcript_path: Path to the onboarding call transcript
        account_id: Optional explicit account_id (auto-detected if omitted)
    
    Returns:
        dict with account_id and update summary
    """
    logger.info(f"═══ Pipeline B: {transcript_path.name} ═══")
    
    # 1. Read transcript
    transcript = transcript_path.read_text(encoding="utf-8")
    logger.info(f"Read transcript: {len(transcript)} chars")
    
    # 2. Extract onboarding updates
    onboarding_memo = extract_account_memo(transcript, call_type="onboarding")
    
    # 3. Find matching v1 account
    if account_id is None:
        account_id = onboarding_memo.get("account_id")
    
    v1_memo = load_v1_memo(account_id)
    if v1_memo is None:
        # Try to match by company name
        logger.warning(f"No v1 found for {account_id}, searching by company name...")
        target_name = onboarding_memo.get("company_name", "").lower()
        for aid in list_accounts():
            existing = load_v1_memo(aid)
            if existing and existing.get("company_name", "").lower() == target_name:
                account_id = aid
                v1_memo = existing
                logger.info(f"Matched to existing account: {account_id}")
                break
    
    if v1_memo is None:
        logger.error(f"No v1 memo found for account {account_id}. Run Pipeline A first.")
        return {"error": "No v1 memo found", "account_id": account_id}
    
    # 4. Apply updates (merge + diff)
    v2_memo, diff, changelog_md, changes_json = apply_onboarding_update(v1_memo, onboarding_memo)
    
    # 5. Generate updated agent spec
    agent_spec_v2 = generate_agent_spec(v2_memo, version="v2")
    
    # 6. Save v2 outputs
    save_account_v2(account_id, v2_memo, agent_spec_v2, changelog_md, changes_json)
    
    # 7. Create tracking task
    create_task(
        account_id=account_id,
        company_name=v2_memo.get("company_name", "Unknown"),
        action="onboarding_processed",
        version="v2",
        details=f"Updated from {transcript_path.name}. Changes: {changes_json['summary']}"
    )
    
    logger.info(f"✓ Pipeline B complete: {account_id} (v1 → v2)")
    return {
        "account_id": account_id,
        "company_name": v2_memo.get("company_name"),
        "version": "v2",
        "source": str(transcript_path),
        "changes_summary": changes_json["summary"]
    }


# ── Batch Processing ──────────────────────────────────────────────────

def run_batch():
    """
    Run all demo calls (Pipeline A) then all onboarding calls (Pipeline B).
    Expects files in dataset/demo/ and dataset/onboarding/ directories.
    File naming convention: 01_company_name.txt, 02_company_name.txt, etc.
    Demo and onboarding files with the same number are paired.
    """
    demo_dir = DATASET_DIR / "demo"
    onboarding_dir = DATASET_DIR / "onboarding"
    
    if not demo_dir.exists():
        logger.error(f"Demo directory not found: {demo_dir}")
        logger.info("Please create dataset/demo/ with transcript files.")
        return
    
    # Collect demo files
    demo_files = sorted(demo_dir.glob("*.txt"))
    onboarding_files = sorted(onboarding_dir.glob("*.txt")) if onboarding_dir.exists() else []
    
    logger.info(f"Found {len(demo_files)} demo files, {len(onboarding_files)} onboarding files")
    
    # Phase 1: Process all demo calls
    results_a = []
    logger.info("═══════════════════════════════════════════")
    logger.info("  PHASE 1: Demo Calls → v1 Agents")
    logger.info("═══════════════════════════════════════════")
    for f in demo_files:
        try:
            result = run_pipeline_a(f)
            results_a.append(result)
        except Exception as e:
            logger.error(f"Pipeline A failed for {f.name}: {e}")
            results_a.append({"error": str(e), "source": str(f)})
    
    # Phase 2: Process all onboarding calls
    results_b = []
    if onboarding_files:
        logger.info("═══════════════════════════════════════════")
        logger.info("  PHASE 2: Onboarding Calls → v2 Updates")
        logger.info("═══════════════════════════════════════════")
        
        # Build mapping: file number → account_id from Phase 1
        # Convention: files numbered 01_, 02_, etc. are paired
        account_map = {}
        for r in results_a:
            if "error" not in r:
                # Extract number prefix from source filename
                src = Path(r["source"]).stem
                num = src.split("_")[0] if "_" in src else src
                account_map[num] = r["account_id"]
        
        for f in onboarding_files:
            try:
                # Try to match by file number prefix
                num = f.stem.split("_")[0] if "_" in f.stem else f.stem
                aid = account_map.get(num)
                result = run_pipeline_b(f, account_id=aid)
                results_b.append(result)
            except Exception as e:
                logger.error(f"Pipeline B failed for {f.name}: {e}")
                results_b.append({"error": str(e), "source": str(f)})
    
    # Save batch summary
    summary = {
        "pipeline_a_results": results_a,
        "pipeline_b_results": results_b,
        "run_summary": get_run_summary()
    }
    save_json(summary, OUTPUT_DIR / "batch_summary.json")
    
    logger.info("═══════════════════════════════════════════")
    logger.info(f"  BATCH COMPLETE")
    logger.info(f"  Demo calls processed: {len(results_a)}")
    logger.info(f"  Onboarding updates processed: {len(results_b)}")
    logger.info(f"  Accounts: {summary['run_summary']['total_accounts']}")
    logger.info("═══════════════════════════════════════════")
    
    return summary


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Clara AI Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.pipeline --batch                    Run all dataset files
  python -m scripts.pipeline --demo dataset/demo/01_acme.txt    Process one demo call
  python -m scripts.pipeline --onboarding dataset/onboarding/01_acme.txt --account acc-acme-abc123
  python -m scripts.pipeline --summary                  Show processing summary
        """
    )
    parser.add_argument("--batch", action="store_true", help="Run batch processing on all dataset files")
    parser.add_argument("--demo", type=str, help="Path to a single demo call transcript")
    parser.add_argument("--onboarding", type=str, help="Path to a single onboarding call transcript")
    parser.add_argument("--account", type=str, help="Account ID for onboarding (optional)")
    parser.add_argument("--summary", action="store_true", help="Show processing summary")
    
    args = parser.parse_args()
    
    if args.batch:
        run_batch()
    elif args.demo:
        run_pipeline_a(Path(args.demo))
    elif args.onboarding:
        run_pipeline_b(Path(args.onboarding), account_id=args.account)
    elif args.summary:
        summary = get_run_summary()
        print(json.dumps(summary, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
