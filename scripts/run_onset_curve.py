"""Gate C Stage 3c: epoch-onset curve for the canonical Qwen-1.5B-on-ULT
adapter. Mirrors the six supplementary runs' epoch-curve design
(scripts/eval_checkpoints.py) but adds a verbatim-match metric and covers
ULT seen/unseen + Dynamic L1/L2, not just Dynamic.

Fixed subsample (data/raw/ult_plt/comparison_c_onset_curve_manifest.json,
seed=20260726): same 50 seen-ULT + 50 unseen-ULT + 75 Dynamic-L1/L2-inst1
problems at every epoch point, paired trajectories, no per-epoch
problem-set noise. Epochs {1,3,5,10,20} only; epoch 0 (PRE) and 30 (Stage
3a/3b) already exist at full n and anchor the curve.

Scoring: fast baseline-pass only (src/eval/test_gen_scorer's _write_case/
_collect_ok/_run_pytest, the real harness's isolated-subprocess path, no
full mutation sweep), matching the supplementary study's own onset-curve
metric. For the seen-ULT split only, also computes verbatim-match against
the training target (data/finetune/train_ult_final.jsonl): exact (after
.strip()) and >=0.95 difflib.SequenceMatcher ratio. Not meaningful for
unseen-ULT/Dynamic (no training target exists for those).

Output: analysis/comparison_c_onset_curve.csv (one row per epoch x split x
problem), with model_label/adapter_path/adapter_hash/resolved generation
config on every row per CONVENTIONS.md's identity-logging rule.

Usage: python scripts/run_onset_curve.py (submit via SLURM, GPU required)
"""
from __future__ import annotations

import csv
import difflib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("HF_HOME", f"/mnt/scratch2/users/{os.environ['USER']}/.huggingface")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from src.data import test_gen, ult_plt  # noqa: E402
from src.eval.test_gen_problem import compute_model_label  # noqa: E402
from src.eval.test_gen_scorer import (  # noqa: E402
    _collect_ok, _run_pytest, _write_case, extract_test_file, sanitize_test_file,
)
from src.models.base import GenerationConfig  # noqa: E402
from src.models.local import LocalModel  # noqa: E402

MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
REVISION = "2e1fd397ee46e1388853d2af2c993145b0f1098a"
ADAPTER_BASE = ROOT / "data" / "finetune" / "qwen1_5b_lora_ult_30ep"
STEPS_PER_EPOCH = 127  # 1014 examples / (batch=1 x grad_accum=8), see training log

MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "comparison_c_onset_curve_manifest.json"
TRAIN_FILE = ROOT / "data" / "finetune" / "train_ult_final.jsonl"
OUT_PATH = ROOT / "analysis" / "comparison_c_onset_curve.csv"
SCORE_TIMEOUT = 30

FIELDNAMES = [
    "epoch", "split", "template_id", "instance_seed", "model_label",
    "adapter_path", "adapter_hash", "exec_rate", "baseline_passed",
    "verbatim_exact", "verbatim_similarity", "generation_latency_seconds",
    "generation_config", "timestamp",
]


def fast_score(fn_source: str, test_source: str) -> tuple[bool, bool]:
    """(exec_ok, baseline_passed) via the real isolated-subprocess harness."""
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        _write_case(wd, fn_source, test_source)
        if not _collect_ok(wd, SCORE_TIMEOUT):
            return False, False
        rc, _ = _run_pytest(wd, SCORE_TIMEOUT)
        return True, rc == 0


def load_problems(manifest: dict):
    seen_ids = set(manifest["ult_seen"]["task_ids"])
    unseen_ids = set(manifest["ult_unseen"]["task_ids"])
    ult_seen = ult_plt.load(benchmark="ult", prompting_condition="zero_shot",
                             task_ids=seen_ids)
    ult_unseen = ult_plt.load(benchmark="ult", prompting_condition="zero_shot",
                               task_ids=unseen_ids)

    dyn_pairs = frozenset(
        (p["template_id"], p["instance_seed"])
        for p in manifest["dynamic_l1l2_inst1"]["problems"]
    )
    dynamic = test_gen.load(
        instantiation_id="1", instantiation_seed=1,
        instance_seeds=(101, 102, 103, 104, 105), tiers=("L1", "L2"),
        prompting_condition="zero_shot", only_instances=dyn_pairs,
    )
    return [("seen", p) for p in ult_seen] + [("unseen", p) for p in ult_unseen] + \
           [("dynamic_l1l2", p) for p in dynamic]


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    problems = load_problems(manifest)
    print(f"Loaded {len(problems)} problems/epoch "
          f"(seen={sum(1 for s,_ in problems if s=='seen')}, "
          f"unseen={sum(1 for s,_ in problems if s=='unseen')}, "
          f"dynamic={sum(1 for s,_ in problems if s=='dynamic_l1l2')})")

    train_targets = {}
    for line in TRAIN_FILE.read_text().splitlines():
        r = json.loads(line)
        tid = r["template_id"].split("-", 1)[1]
        train_targets[tid] = r["messages"][-1]["content"].strip()

    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2,
                           top_p=1.0, seed=42)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    done: set[tuple[int, str, str, int]] = set()
    if OUT_PATH.exists():
        with OUT_PATH.open() as f:
            for row in csv.DictReader(f):
                done.add((int(row["epoch"]), row["split"], row["template_id"], int(row["instance_seed"])))
        print(f"Resuming: {len(done)} (epoch, split, template_id, seed) rows already done")
    else:
        with OUT_PATH.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()

    epochs = [1, 3, 5, 10, 20]
    for epoch in epochs:
        step = epoch * STEPS_PER_EPOCH
        ckpt_dir = ADAPTER_BASE / f"checkpoint-{step}"
        if not ckpt_dir.exists():
            raise FileNotFoundError(f"No checkpoint for epoch {epoch}: {ckpt_dir}")

        print(f"\n=== Epoch {epoch} ({ckpt_dir.name}) ===", flush=True)
        model = LocalModel(MODEL_ID, revision=REVISION, adapter_path=str(ckpt_dir))
        model_label = compute_model_label(MODEL_ID, str(ckpt_dir))

        n_done_this_epoch = 0
        for split, prob in problems:
            tid = prob.template_id
            seed = prob.instance_seed
            if (epoch, split, tid, seed) in done:
                continue

            t0 = time.monotonic()
            out = model.generate(prob.messages, cfg)
            latency = time.monotonic() - t0
            test_file = extract_test_file(out.response)
            test_file, _ = sanitize_test_file(test_file, prob.fn_name)
            exec_ok, baseline_passed = fast_score(prob.source, test_file)

            verbatim_exact = ""
            verbatim_sim = ""
            if split == "seen":
                task_id = tid.split("-", 1)[1]
                target = train_targets.get(task_id)
                if target is not None:
                    actual = test_file.strip()
                    if actual == target:
                        verbatim_exact, verbatim_sim = True, 1.0
                    else:
                        ratio = difflib.SequenceMatcher(None, target, actual).ratio()
                        verbatim_exact, verbatim_sim = False, round(ratio, 4)

            row = {
                "epoch": epoch, "split": split, "template_id": tid, "instance_seed": seed,
                "model_label": model_label, "adapter_path": out.adapter_path,
                "adapter_hash": out.adapter_hash, "exec_rate": 1.0 if exec_ok else 0.0,
                "baseline_passed": baseline_passed,
                "verbatim_exact": verbatim_exact, "verbatim_similarity": verbatim_sim,
                "generation_latency_seconds": latency,
                "generation_config": json.dumps(out.generation_config),
                "timestamp": out.timestamp,
            }
            with OUT_PATH.open("a", newline="") as f:
                csv.DictWriter(f, fieldnames=FIELDNAMES).writerow(row)
            n_done_this_epoch += 1
            if n_done_this_epoch % 25 == 0:
                print(f"  {n_done_this_epoch}/{len(problems)} done this epoch", flush=True)

        print(f"Epoch {epoch}: {n_done_this_epoch} new rows written")

    print(f"\nDone. Results at: {OUT_PATH}")


if __name__ == "__main__":
    main()
