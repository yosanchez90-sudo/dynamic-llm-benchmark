"""Freeze the fixed problem subsample for Gate C Stage 3c's epoch-onset curve.

Scope (per 2026-07-26 direction): epochs {1,3,5,10,20} only -- epoch 0 (PRE)
and epoch 30 (Stage 3a/3b, already landed) anchor the curve and are not
re-run. Per epoch point, the SAME fixed subsample (paired trajectories, no
problem-set noise across points):
  - 50 seen-in-training ULT core_400 problems (of 112)
  - 50 unseen ULT core_400 problems (of 288)
  - 75 Dynamic L1/L2 instantiation-1 problems (of the 150-problem L1+L2 pool)

Drawn with a recorded seed so the manifest is reproducible from this script
alone. Output is force-added under data/ (CLAUDE.md: manifest files under
data/ are force-added despite the blanket /data/ gitignore).

Usage: python scripts/build_onset_curve_manifest.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SEED = 20260726
OUT_PATH = ROOT / "data" / "raw" / "ult_plt" / "comparison_c_onset_curve_manifest.json"
SEEN_MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "comparison_c_seen_manifest.json"

N_SEEN = 50
N_UNSEEN = 50
N_DYNAMIC = 75
EPOCHS = [1, 3, 5, 10, 20]


def main() -> None:
    seen_manifest = json.loads(SEEN_MANIFEST_PATH.read_text())
    seen_ids = sorted(p["task_id"] for p in seen_manifest["problems"] if p["seen_in_training"])
    unseen_ids = sorted(p["task_id"] for p in seen_manifest["problems"] if not p["seen_in_training"])
    print(f"Seen pool: {len(seen_ids)}, unseen pool: {len(unseen_ids)}")

    rng = random.Random(SEED)
    sampled_seen = sorted(rng.sample(seen_ids, N_SEEN))
    sampled_unseen = sorted(rng.sample(unseen_ids, N_UNSEEN))

    # Dynamic L1/L2 inst1 pool: 15 templates/tier x 5 seeds x 2 tiers = 150.
    from src.data import test_gen
    dynamic_problems = test_gen.load(
        instantiation_id="1", instantiation_seed=1,
        instance_seeds=(101, 102, 103, 104, 105), tiers=("L1", "L2"),
        prompting_condition="zero_shot",
    )
    dynamic_pool = sorted((p.template_id, p.instance_seed) for p in dynamic_problems)
    print(f"Dynamic L1/L2 inst1 pool: {len(dynamic_pool)}")
    sampled_dynamic = sorted(rng.sample(dynamic_pool, N_DYNAMIC))

    manifest = {
        "generated_by": "scripts/build_onset_curve_manifest.py",
        "seed": SEED,
        "purpose": "Gate C Stage 3c epoch-onset curve -- fixed subsample, "
                   "same problem IDs at every epoch point (paired trajectories)",
        "epochs": EPOCHS,
        "epoch_anchors_already_landed": {"0": "PRE baseline", "30": "Stage 3a/3b full n"},
        "ult_seen": {"task_ids": sampled_seen, "n": len(sampled_seen), "pool_n": len(seen_ids)},
        "ult_unseen": {"task_ids": sampled_unseen, "n": len(sampled_unseen), "pool_n": len(unseen_ids)},
        "dynamic_l1l2_inst1": {
            "problems": [{"template_id": t, "instance_seed": s} for t, s in sampled_dynamic],
            "n": len(sampled_dynamic), "pool_n": len(dynamic_pool),
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {OUT_PATH}")
    print(f"Total problems/epoch: {len(sampled_seen) + len(sampled_unseen) + len(sampled_dynamic)}")
    print(f"Total generations across {len(EPOCHS)} epochs: "
          f"{(len(sampled_seen) + len(sampled_unseen) + len(sampled_dynamic)) * len(EPOCHS)}")


if __name__ == "__main__":
    main()
