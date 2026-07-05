"""Convert all JSONL result files in data/results/dynamic/ to a single Excel workbook.

Each JSONL file becomes one sheet named by model (truncated to fit Excel's 31-char
sheet name limit). A final "Summary" sheet appends the tail of each .out log file.

The function source code is reconstructed from the template engine so you can read
exactly what function the model was asked to test, even though it is not stored in
the JSONL (only prompt_hash is stored).

Usage (from the dissertation root):
    python scripts/results_to_excel.py
    python scripts/results_to_excel.py --out analysis/results.xlsx
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Reconstruct function source from template engine
# ---------------------------------------------------------------------------

def _build_source_map(records: list[dict]) -> dict[tuple, str]:
    """Return {(template_id, instance_seed): source_code} for every unique pair."""
    try:
        from src.data.test_gen import _load_template, _extract_fn_name
        from engine import instantiate  # noqa: F401 – on sys.path via test_gen import
    except Exception:
        return {}

    template_root = ROOT / "template_corpus" / "templates"
    cache: dict[tuple, str] = {}
    needed: set[tuple] = {(r["template_id"], r["instance_seed"]) for r in records}

    for template_id, seed in needed:
        tier = template_id.split("-")[0]  # e.g. "L1"
        tmpl_path = template_root / tier / f"{template_id}.py"
        if not tmpl_path.exists():
            continue
        try:
            tmpl = _load_template(tmpl_path)
            inst = instantiate(tmpl, seed)
            cache[(template_id, seed)] = inst.get("source", "")
        except Exception:
            pass

    return cache


# ---------------------------------------------------------------------------
# Flatten one JSONL record into a dict of plain values
# ---------------------------------------------------------------------------

def _flatten(r: dict, source_map: dict[tuple, str]) -> dict:
    gen = r.get("generation_config") or {}
    rt  = r.get("runtime_info") or {}

    source = source_map.get((r.get("template_id", ""), r.get("instance_seed", 0)), "")

    return {
        # ── identity ────────────────────────────────────────────────────────
        "model":             r.get("model", ""),
        "tier":              r.get("tier", ""),
        "template_id":       r.get("template_id", ""),
        "instance_seed":     r.get("instance_seed", ""),
        # ── primary metrics ──────────────────────────────────────────────────
        "exec_ok":           r.get("exec_rate", 0) == 1.0,
        "baseline_passed":   r.get("baseline_passed", False),
        "mutation_score":    r.get("mutation_score"),
        "mutants_killed":    r.get("mutants_killed", 0),
        "mutants_total":     r.get("mutants_total", 0),
        "mutants_dropped":   r.get("mutants_dropped_for_import_failure", 0),
        "statement_cov":     r.get("statement_coverage"),
        "branch_cov":        r.get("branch_coverage"),
        # ── repair flags (non-empty = row was patched) ───────────────────────
        "notes":             r.get("notes", ""),
        # ── content for debugging ─────────────────────────────────────────────
        "fn_source":         source,
        "extracted_test":    r.get("extracted_test_file", ""),
        "raw_response":      r.get("response", ""),
        # ── generation meta ──────────────────────────────────────────────────
        "latency_s":         r.get("generation_latency_seconds"),
        "cost_usd":          r.get("cost_usd"),
        "temperature":       gen.get("temperature"),
        "max_new_tokens":    gen.get("max_new_tokens"),
        "gpu":               rt.get("gpu"),
        "hostname":          rt.get("hostname"),
        "timestamp":         r.get("timestamp", ""),
        "model_revision":    r.get("model_revision", ""),
        "prompting":         r.get("prompting_condition", ""),
        "provider":          r.get("provider", ""),
        "prompt_hash":       r.get("prompt_hash", ""),
    }


# ---------------------------------------------------------------------------
# Excel sheet name helpers
# ---------------------------------------------------------------------------

def _sheet_name(jsonl_path: Path, used: set[str]) -> str:
    """Derive a unique ≤31-char Excel sheet name from the JSONL filename."""
    # Strip timestamp suffix and __dynamic__zero_shot__inst1 boilerplate
    stem = jsonl_path.stem
    for noise in ("__dynamic__zero_shot__inst1", "__dynamic__zero_shot", "__dynamic"):
        stem = stem.replace(noise, "")
    # Strip timestamp _20260617T124709
    import re
    stem = re.sub(r"_\d{8}T\d{6}$", "", stem)
    # Shorten Qwen org prefix
    stem = stem.replace("Qwen__Qwen2.5-Coder-", "Qwen-")
    name = stem.rstrip("_")[:31]
    # Deduplicate
    original, idx = name, 1
    while name in used:
        suffix = f"_{idx}"
        name = original[:31 - len(suffix)] + suffix
        idx += 1
    used.add(name)
    return name


# ---------------------------------------------------------------------------
# Summary sheet: tail of each .out log
# ---------------------------------------------------------------------------

def _build_summary(jsonl_files: list[Path], logs_dir: Path) -> pd.DataFrame:
    rows = []
    for jf in jsonl_files:
        # Match e.g. l1l2-7b-9141294.out or eval-api-9141612.out by looking for
        # a .out file whose stem contains the job id embedded in the jsonl timestamp.
        # Simpler: just read all .out files and pick the one closest in mtime.
        records = [json.loads(l) for l in jf.read_text().splitlines() if l.strip()]
        if not records:
            continue
        total   = len(records)
        exec_ok = sum(1 for r in records if r.get("exec_rate", 0) == 1.0)
        bp      = sum(1 for r in records if r.get("baseline_passed"))
        ms      = [r["mutation_score"] for r in records if r.get("mutation_score") is not None]
        rows.append({
            "file":              jf.name,
            "model":             records[0].get("model", ""),
            "n_problems":        total,
            "exec_rate":         f"{exec_ok}/{total} ({exec_ok/total:.1%})",
            "baseline_pass":     f"{bp}/{total} ({bp/total:.1%})",
            "mut_score_mean":    round(sum(ms)/len(ms), 3) if ms else None,
            "mut_score_min":     round(min(ms), 3) if ms else None,
            "mut_score_max":     round(max(ms), 3) if ms else None,
            "n_mut_scored":      len(ms),
            "total_cost_usd":    round(sum(r["cost_usd"] for r in records
                                          if r.get("cost_usd")), 4) or None,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="data/results/dynamic",
                        type=Path, help="Directory with JSONL files")
    parser.add_argument("--logs-dir", default="logs", type=Path)
    parser.add_argument("--out", default="analysis/results.xlsx",
                        type=Path, help="Output Excel path")
    args = parser.parse_args()

    jsonl_files = sorted(args.results_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"No JSONL files found in {args.results_dir}")
        sys.exit(1)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()

    with pd.ExcelWriter(args.out, engine="openpyxl") as writer:
        # One sheet per model
        for jf in jsonl_files:
            records = [json.loads(l) for l in jf.read_text().splitlines() if l.strip()]
            if not records:
                continue

            print(f"  Building source map for {jf.name} ({len(records)} rows)…", flush=True)
            source_map = _build_source_map(records)

            rows = [_flatten(r, source_map) for r in records]
            df = pd.DataFrame(rows)

            sheet = _sheet_name(jf, used_names)
            df.to_excel(writer, sheet_name=sheet, index=False)

            # Auto-width for non-text columns; cap text columns so Excel opens fast
            ws = writer.sheets[sheet]
            for col_cells in ws.iter_cols(min_row=1, max_row=1):
                col_letter = col_cells[0].column_letter
                header = col_cells[0].value or ""
                if header in ("fn_source", "extracted_test", "raw_response", "notes"):
                    ws.column_dimensions[col_letter].width = 60
                else:
                    ws.column_dimensions[col_letter].width = max(12, len(str(header)) + 2)

            # Wrap text + top-align all cells; freeze header row
            from openpyxl.styles import Alignment
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
            ws.freeze_panes = "A2"

            print(f"    → sheet '{sheet}' written ({len(rows)} rows)")

        # Summary sheet
        print("  Building Summary sheet…", flush=True)
        summary_df = _build_summary(jsonl_files, args.logs_dir)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        ws_s = writer.sheets["Summary"]
        for col_cells in ws_s.iter_cols(min_row=1, max_row=1):
            col_letter = col_cells[0].column_letter
            ws_s.column_dimensions[col_letter].width = max(14, len(str(col_cells[0].value or "")) + 4)
        ws_s.freeze_panes = "A2"

    print(f"\nSaved: {args.out.resolve()}")


if __name__ == "__main__":
    main()
