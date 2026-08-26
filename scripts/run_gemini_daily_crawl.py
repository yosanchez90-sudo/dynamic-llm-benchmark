"""One day's worth of Gemini 3.1 Pro Preview Dynamic-benchmark backfill.

Gemini's free-tier quota for this model is 250 requests/day; this script
sends at most `--budget` (default 240, a buffer under that) across a
priority-ordered list of configs, then stops, cleanly on hitting the
daily budget, or cleanly on the first 429 (whichever comes first), never
crashing with a raw traceback for either expected-and-normal condition.
Meant to be invoked once per day by scripts/slurm/run_gemini_daily_crawl.slurm,
which resubmits itself 24h later until coverage is complete.

Scope: instantiations 1-4 only (inst5 was cut from this model's target
scope 2026-07-15, PROJECT_BRIEF.md Sec 11, see e.g. the "N=4 scope"
comment already on every gemini_3_1_pro_preview__dynamic_*.yaml config).

Priority: L3L4 configs (tier_priority=["L4"]) before L1L2 configs, since
Gemini Pro currently has zero L4 rows and that gap distorts every pooled
ranking it appears in (RQ5_INTERPRETATION.md). Within an L3L4 config, L4
problems are processed before L3 (test_gen_runner.py's tier_priority
support). Resume-safe: each config call only ever requests problems not
already present on disk (src/eval/test_gen_runner.py's existing tier-aware
resume matcher), so re-running this script (or a config within it) never
duplicates work, whether called again today or by tomorrow's chained job.

Usage:
    python scripts/run_gemini_daily_crawl.py [--budget 240] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Priority order: all four L3L4 configs (L4-first within each), then all
# four L1L2 configs. Instantiation order 1->4 within each group is
# arbitrary (no priority reason to prefer one over another) but fixed here
# for reproducibility across days.
_L3L4_CONFIGS = [
    f"configs/gemini_3_1_pro_preview__dynamic_L3L4__inst{i}.yaml" for i in (1, 2, 3, 4)
]
_L1L2_CONFIGS = [
    f"configs/gemini_3_1_pro_preview__dynamic_L1L2__inst{i}.yaml" for i in (1, 2, 3, 4)
]
PRIORITY_ORDER = _L3L4_CONFIGS + _L1L2_CONFIGS


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path) as f:
        return sum(1 for line in f if line.strip())


CONFIG_RETRY_ATTEMPTS = 3
CONFIG_RETRY_PAUSE_SECONDS = 60


def _run_config_with_retries(config: dict, cfg_path: str, run_fn, sleep_fn=time.sleep) -> tuple[Path | None, bool]:
    """Run one config, retrying the WHOLE call a few times on a persistent
    non-429 APIError before giving up on just this config.

    A persistent 5xx (e.g. "high demand") on one specific problem can
    exhaust GeminiModel's own 5-retry/62s backoff and raise, found
    2026-08-09/10 (job 9587710, 9590545) both crashing on
    L4-matrix-001/L4-mega-001 after burning only ~5% of the day's budget,
    wasting the rest since the old code treated ANY non-429 APIError as
    immediately fatal for the whole script. Confirmed empirically that
    this is genuinely transient, not a permanent block on that problem:
    resuming the SAME config a day later (append_jsonl + the resume
    matcher make this safe) got 3 more rows past the exact point day 2
    died before hitting the same class of error again. So: retry the
    whole config call a few times with a real pause (long enough to
    matter, GeminiModel's own backoff already proved insufficient)
    before giving up on just THIS config and moving to the next one,
    instead of crashing the whole script and abandoning every remaining
    config for the day.

    Returns (result_path, quota_exhausted_for_today). result_path is None
    if this config's retries were exhausted on a non-429 error (caller
    should move on to the next config, not treat it as a daily stop).
    """
    from google.genai import errors as genai_errors

    for attempt in range(1, CONFIG_RETRY_ATTEMPTS + 1):
        try:
            return run_fn(config), False
        except genai_errors.APIError as exc:
            if exc.code == 429:
                print(f"  429 (quota exhausted) on {cfg_path} -- stopping cleanly for today. "
                      f"Whatever completed before this point is already saved (append-only).\n")
                return None, True
            if attempt < CONFIG_RETRY_ATTEMPTS:
                print(f"  {exc.code} on {cfg_path} (attempt {attempt}/{CONFIG_RETRY_ATTEMPTS}) -- "
                      f"already-completed problems are saved; retrying this config in "
                      f"{CONFIG_RETRY_PAUSE_SECONDS}s in case it's transient.\n")
                sleep_fn(CONFIG_RETRY_PAUSE_SECONDS)
                continue
            print(f"  {exc.code} on {cfg_path} -- {CONFIG_RETRY_ATTEMPTS} attempts exhausted, "
                  f"deferring the rest of this config to a future run (not crashing the whole "
                  f"day's budget over one stubborn config).\n")
            return None, False
    raise AssertionError("unreachable")  # loop always returns explicitly


def _resume_file_row_count(config: dict) -> int:
    """Row count of whatever file test_gen_runner._find_resume_file would
    pick up for this exact config, right now, mirrors that function's own
    pattern construction so this stays a targeted glob (one model's one
    config), not a scan of every result file in the directory."""
    from src.eval.test_gen_problem import compute_model_label
    from src.eval.test_gen_runner import _tier_signature

    safe_model = compute_model_label(config["model"]["id"], config["model"].get("adapter_path"))
    tier_sig = _tier_signature(config)
    tier_part = f"__tiers{tier_sig}" if tier_sig else ""
    out_dir = Path(config["output_dir"])
    pattern = (
        f"{safe_model}__{config['benchmark']}__{config['prompting_condition']}"
        f"__inst{config['instantiation_id']}{tier_part}_*.jsonl"
    )
    candidates = sorted(out_dir.glob(pattern)) if out_dir.exists() else []
    if not candidates:
        return 0
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    return _count_rows(newest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=int, default=240,
                         help="Max requests to send today (buffer under the 250 quota).")
    parser.add_argument("--dry-run", action="store_true",
                         help="Print the plan without calling the API.")
    args = parser.parse_args()

    remaining_budget = args.budget
    print(f"=== Gemini Pro Preview daily crawl -- budget {remaining_budget} requests ===\n")

    for cfg_path in PRIORITY_ORDER:
        if remaining_budget <= 0:
            print("Daily budget exhausted -- stopping cleanly, remaining configs deferred to a future run.")
            break

        with open(cfg_path) as f:
            config = yaml.safe_load(f)

        is_l3l4 = cfg_path in _L3L4_CONFIGS
        if is_l3l4:
            config["tier_priority"] = ["L4"]
        config["max_requests"] = remaining_budget

        print(f"--- {cfg_path} (budget remaining: {remaining_budget}"
              f"{', tier_priority=L4' if is_l3l4 else ''}) ---")

        if args.dry_run:
            print("  [dry-run] skipped\n")
            continue

        from src.eval.test_gen_runner import run_test_gen_experiment

        # Snapshot row count of whatever resume file would match, so we can
        # tell exactly how many NEW rows this call added even if it fails
        # partway through. append_jsonl already guarantees partial
        # progress is on disk, this just measures it precisely. Taken
        # before the (possibly retried) run, matching what a single
        # successful attempt would have seen.
        before_count = _resume_file_row_count(config)
        result_path, quota_exhausted_for_today = _run_config_with_retries(
            config, cfg_path, run_test_gen_experiment,
        )

        if quota_exhausted_for_today:
            break
        if result_path is None:
            continue  # config retries exhausted on a non-429 error, move to the next config

        after_count = _count_rows(result_path)
        added = after_count - before_count
        remaining_budget -= added
        print(f"  +{added} new rows this call -> {result_path.name} "
              f"(budget remaining: {remaining_budget})\n")

    print(f"=== Done for today. Budget remaining: {max(remaining_budget, 0)} ===")


if __name__ == "__main__":
    main()
