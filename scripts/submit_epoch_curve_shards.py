"""Submit the Part G / G2 epoch-curve rebuild as SLURM shards.

Why sharded: a single job per condition (8 epochs x 3 instantiations x 150
problems, greedy + R=3 sampling at epoch 30) costs up to ~40h for the
slowest condition (bp_gpt5/7B), forcing a 1.5-2.5 day wall-clock ceiling if
run one-job-per-condition. That ceiling is a packing artifact, not an
experiment-size constraint, so this script shards each condition by
(epoch [+ epoch0 baseline folded into the epoch=1 shard]) for the 7
non-final epochs, and by (epoch=30, draw) for the endpoint (greedy +
3 sampling seeds) -- 11 shards/condition x 6 conditions = 66 shards.

Each shard writes to its OWN CSV file under
data/results/finetune_rebuild/shards/ to avoid concurrent-write races on
NFS; merge_epoch_curve_shards.py combines them afterward, after verifying
shard-count / row-count completeness. See CLAUDE.md: results are
append-only, so shard files are never combined by overwriting -- the merge
script only ever creates the new epoch_perf_<name>.csv once, or appends
rows a resumed eval_checkpoints.py run hadn't already written.

Usage:
    python scripts/submit_epoch_curve_shards.py            # submit everything
    python scripts/submit_epoch_curve_shards.py --dry-run  # print the plan only
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARD_DIR = ROOT / "data/results/finetune_rebuild/shards"
SLURM_SCRIPT = ROOT / "scripts/slurm/run_eval_checkpoints_shard.slurm"
MANIFEST_DIR = SHARD_DIR / "manifests"

NON_FINAL_EPOCHS = [3, 5, 10, 15, 20, 25]  # epoch 1 handled separately (folded w/ baseline)
SAMPLING_SEEDS = [42, 43, 44]

# (config stem, is_slow) -- bp_gpt5 conditions are the long-output, slow ones
# (measured ~5h/epoch-shard for the 7B variant); everything else is fast.
CONDITIONS = [
    ("finetune_qwen1_5b_inst1_30ep",   False),
    ("finetune_qwen1_5b_bp_own_30ep",  False),
    ("finetune_qwen1_5b_bp_gpt5_30ep", True),
    ("finetune_qwen7b_inst1_30ep",     False),
    ("finetune_qwen7b_bp_own_30ep",    False),
    ("finetune_qwen7b_bp_gpt5_30ep",   True),
]


@dataclass
class Shard:
    config_name: str
    label: str            # e.g. "epoch01+baseline", "epoch30_greedy", "epoch30_sampling_seed42"
    epoch_arg: int         # the --epochs value passed (single epoch per shard)
    greedy_flag: str
    sampling_flag: str
    baseline_flag: str
    time_limit: str
    out_path: Path


def build_plan() -> list[Shard]:
    shards: list[Shard] = []
    for config_name, is_slow in CONDITIONS:
        single_time = "10:00:00" if is_slow else "05:00:00"
        double_time = "16:00:00" if is_slow else "08:00:00"  # epoch1+baseline = 2x generations

        # epoch 1, folded with the epoch=0 baseline (same instrument requirement:
        # each condition's own CSV carries its own pre-finetune measurement).
        shards.append(Shard(
            config_name=config_name,
            label="epoch01+baseline",
            epoch_arg=1,
            greedy_flag="--greedy",
            sampling_flag="",
            baseline_flag="--baseline",
            time_limit=double_time,
            out_path=SHARD_DIR / f"{config_name}__epoch01_baseline.csv",
        ))

        for ep in NON_FINAL_EPOCHS:
            shards.append(Shard(
                config_name=config_name,
                label=f"epoch{ep:02d}",
                epoch_arg=ep,
                greedy_flag="--greedy",
                sampling_flag="",
                baseline_flag="",
                time_limit=single_time,
                out_path=SHARD_DIR / f"{config_name}__epoch{ep:02d}.csv",
            ))

        # epoch 30: greedy (primary) + R=3 sampling (secondary), each its own shard.
        shards.append(Shard(
            config_name=config_name,
            label="epoch30_greedy",
            epoch_arg=30,
            greedy_flag="--greedy",
            sampling_flag="",
            baseline_flag="",
            time_limit=single_time,
            out_path=SHARD_DIR / f"{config_name}__epoch30_greedy.csv",
        ))
        for seed in SAMPLING_SEEDS:
            shards.append(Shard(
                config_name=config_name,
                label=f"epoch30_sampling_seed{seed}",
                epoch_arg=30,
                greedy_flag="--no-greedy",
                sampling_flag=f"--sampling-seeds {seed}",
                baseline_flag="",
                time_limit=single_time,
                out_path=SHARD_DIR / f"{config_name}__epoch30_sampling_seed{seed}.csv",
            ))

    return shards


def submit(shard: Shard) -> str:
    env_exports = ",".join([
        "ALL",
        f"CONFIG=configs/{shard.config_name}.yaml",
        f"EPOCH={shard.epoch_arg}",
        f"OUT={shard.out_path.relative_to(ROOT)}",
        f"GREEDY_FLAG={shard.greedy_flag}",
        f"SAMPLING_FLAG={shard.sampling_flag}",
        f"BASELINE_FLAG={shard.baseline_flag}",
    ])
    job_name = f"epc_{shard.config_name.replace('finetune_', '')}_{shard.label}"
    # env -u BASH_ENV per CLAUDE.md — avoids BASH_ENV hook conflicts on sbatch.
    cmd = [
        "env", "-u", "BASH_ENV",
        "sbatch",
        f"--job-name={job_name}",
        f"--time={shard.time_limit}",
        f"--export={env_exports}",
        "--parsable",
        str(SLURM_SCRIPT),
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"sbatch failed for {job_name}: {result.stderr}")
    return result.stdout.strip().split(";")[0]  # --parsable prints "<jobid>;<cluster>" or just "<jobid>"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without submitting")
    args = parser.parse_args()

    plan = build_plan()
    print(f"Shard plan: {len(plan)} shards across {len(CONDITIONS)} conditions "
          f"({len(NON_FINAL_EPOCHS) + 1} epoch shards + 4 epoch-30 draw shards each)")
    for s in plan:
        print(f"  {s.config_name:35s} {s.label:26s} time={s.time_limit} out={s.out_path.name}")

    if args.dry_run:
        print("\n--dry-run: no jobs submitted.")
        return

    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for s in plan:
        job_id = submit(s)
        print(f"submitted {job_id}: {s.config_name} {s.label}")
        manifest_rows.append({
            "job_id": job_id,
            "config_name": s.config_name,
            "label": s.label,
            "epoch_arg": s.epoch_arg,
            "out_path": str(s.out_path.relative_to(ROOT)),
            "time_limit": s.time_limit,
        })

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = MANIFEST_DIR / f"manifest_{ts}.csv"
    with manifest_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"\nManifest written: {manifest_path}")
    print(f"Monitor with: squeue -u $USER")
    print(f"After all jobs complete: python scripts/merge_epoch_curve_shards.py --manifest {manifest_path}")


if __name__ == "__main__":
    main()
