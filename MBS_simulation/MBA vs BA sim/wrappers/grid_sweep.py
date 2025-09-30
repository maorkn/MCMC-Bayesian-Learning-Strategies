"""Grid sweep wrapper for MBA vs BA experiments.

Sweeps across epsilon, learning_rate, cost_multiplier, penalty for a set of
permutations, runs MBA-only and BA-only, computes delta (MBA - BA) per cell,
and aggregates to grid_summary.csv. Optionally produces simple heatmaps.

Default parameter grid is defined in wrappers/params/grid4x4x4x4.json.
"""

import sys
import itertools
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import json
import argparse
import concurrent.futures as futures

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    ensure_dir, safe_write_json, run_driver, compute_delta_csv,
    create_base_manifest, load_json_params, get_permutation_hash
)


def _combos(params: Dict[str, List[Any]]) -> List[Tuple[Any, Any, Any, Any, str]]:
    """Yield product of epsilon, learning_rate, cost_multiplier, penalty, permutation_seq."""
    eps = params.get("epsilon", [])
    lr = params.get("learning_rate", [])
    cm = params.get("cost_multiplier", [])
    pen = params.get("penalty", [])
    perms = params.get("permutations", [])
    return list(itertools.product(eps, lr, cm, pen, perms))


def _try_heatmaps(summary_df: pd.DataFrame, plots_dir: Path) -> None:
    """Produce simple heatmaps by aggregating across two of the four axes."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        ensure_dir(plots_dir)

        # For each permutation, create heatmaps:
        # 1) epsilon (x) vs learning_rate (y), mean over cost_multiplier and penalty
        # 2) epsilon (x) vs penalty (y), mean over learning_rate and cost_multiplier
        for perm_hash in summary_df["perm_hash"].unique():
            dfp = summary_df[summary_df["perm_hash"] == perm_hash]

            # 1) eps vs lr
            h1 = dfp.pivot_table(
                index="learning_rate",
                columns="epsilon",
                values="delta_final_mean",
                aggfunc="mean",
            )
            if not h1.empty:
                plt.figure(figsize=(8, 5))
                im = plt.imshow(h1.values, aspect="auto", origin="lower", cmap="coolwarm")
                plt.colorbar(im, label="Δ_final_mean")
                plt.xticks(range(len(h1.columns)), [f"{c:.2f}" for c in h1.columns], rotation=45)
                plt.yticks(range(len(h1.index)), [f"{i:.2f}" for i in h1.index])
                plt.xlabel("epsilon")
                plt.ylabel("learning_rate")
                plt.title(f"Heatmap (eps vs lr) - perm {perm_hash}")
                plt.tight_layout()
                plt.savefig(plots_dir / f"heatmap_eps_vs_lr_{perm_hash}.png", dpi=150, bbox_inches="tight")
                plt.close()

            # 2) eps vs penalty
            h2 = dfp.pivot_table(
                index="penalty",
                columns="epsilon",
                values="delta_final_mean",
                aggfunc="mean",
            )
            if not h2.empty:
                plt.figure(figsize=(8, 5))
                im = plt.imshow(h2.values, aspect="auto", origin="lower", cmap="coolwarm")
                plt.colorbar(im, label="Δ_final_mean")
                plt.xticks(range(len(h2.columns)), [f"{c:.2f}" for c in h2.columns], rotation=45)
                plt.yticks(range(len(h2.index)), [f"{i:.2f}" for i in h2.index])
                plt.xlabel("epsilon")
                plt.ylabel("penalty")
                plt.title(f"Heatmap (eps vs penalty) - perm {perm_hash}")
                plt.tight_layout()
                plt.savefig(plots_dir / f"heatmap_eps_vs_penalty_{perm_hash}.png", dpi=150, bbox_inches="tight")
                plt.close()

    except ImportError:
        print("Warning: matplotlib not available, skipping heatmaps")
    except Exception as e:
        print(f"Warning: error creating heatmaps - {e}")


def main():
    """Run grid sweep across parameter grid and permutations."""
    print("=" * 60)
    print("GRID SWEEP - PARAMETER SCAN")
    print("=" * 60)
    print()

    # CLI
    parser = argparse.ArgumentParser(description="GRID SWEEP - PARAMETER SCAN")
    parser.add_argument("--grid_params_file", default="wrappers/params/grid4x4x4x4.json", help="Path to grid params JSON")
    parser.add_argument("--days", type=int, default=600, help="Days per run (default 600)")
    parser.add_argument("--reps", type=int, default=5, help="Replicates per cell (default 5)")
    parser.add_argument("--n_agents", type=int, default=100, help="Population size per run (default 100)")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default 1)")
    parser.add_argument("--output_dir", type=str, default=None, help="Directory to save all output")
    args = parser.parse_args()

    # Base configuration for runs
    base_config = {
        "days": args.days,                 # override via CLI
        "reps": args.reps,
        "n_agents": args.n_agents,
        "base_seed": 1312,
        "learning_rate": 0.3,        # default; each cell overrides
        "cost_multiplier": 1.0,      # default; each cell overrides
        "epsilon": 0.0,              # default; each cell overrides
        "penalty": 0.7,              # default; each cell overrides
        "grid_params_file": args.grid_params_file
    }

    # Output structure
    output_dir = args.output_dir or "wrappers_output/grid_sweep"
    base_dir = Path(output_dir)
    plots_dir = base_dir / "plots"
    logs_dir = base_dir / "logs"
    for d in (base_dir, plots_dir, logs_dir):
        ensure_dir(d)

    # Load parameter grid
    params_file = Path(base_config["grid_params_file"])
    if not params_file.exists():
        print(f"ERROR: grid params file not found: {params_file}")
        return False

    grid_params = load_json_params(str(params_file))
    required_keys = ["epsilon", "learning_rate", "cost_multiplier", "penalty", "permutations"]
    for k in required_keys:
        if k not in grid_params:
            print(f"ERROR: grid params missing key '{k}'")
            return False

    # Manifest
    manifest = create_base_manifest("grid_sweep", {**base_config, "grid_params_file": str(params_file)})
    manifest_path = base_dir / "manifest.json"

    print("Parameter grid:")
    for k in required_keys:
        print(f"  {k}: {grid_params[k]}")
    print(f"  Days: {base_config['days']}, Reps: {base_config['reps']}, Agents: {base_config['n_agents']}")
    print(f"  Output: {base_dir}")
    print()

    # Iterate over all cells
    combos = _combos(grid_params)
    n_total = len(combos)
    if n_total == 0:
        print("ERROR: empty parameter grid")
        return False

    summary_rows: List[Dict[str, Any]] = []
    runs_records: List[Dict[str, Any]] = []

    tasks = list(enumerate(combos, start=1))

    def run_cell(task):
        run_index, (epsilon, learning_rate, cost_multiplier, penalty, perm_str) = task
        perm_hash = get_permutation_hash(perm_str)
        try:
            print(f"[{run_index}/{n_total}] eps={epsilon} lr={learning_rate} cost={cost_multiplier} pen={penalty} perm={perm_str} ({perm_hash})")

            # Per-cell directories
            cell_dir = base_dir / f"perm_{perm_hash}" / f"eps_{epsilon}_lr_{learning_rate}_cm_{cost_multiplier}_pen_{penalty}"
            mba_dir = cell_dir / "mba"
            ba_dir = cell_dir / "ba"
            for d in (cell_dir, mba_dir, ba_dir):
                ensure_dir(d)

            # 1) MBA
            mba_args = {
                "n_mba": base_config["n_agents"],
                "n_ba": 0,
                "learning_rate": float(learning_rate),
                "cost_multiplier": float(cost_multiplier),
                "epsilon": float(epsilon),
                "penalty": float(penalty),
                "permutation_seq": str(perm_str),
                "days": base_config["days"],
                "reps": base_config["reps"],
                "seed": base_config["base_seed"] + run_index * 1000,
                "output_dir": str(mba_dir)
            }
            mba_log = logs_dir / f"mba_{perm_hash}_{run_index}.log"
            mba_success = run_driver("MBA", mba_args, str(mba_dir), str(mba_log))

            # 2) BA
            ba_args = {
                "n_mba": 0,
                "n_ba": base_config["n_agents"],
                "learning_rate": float(learning_rate),
                "cost_multiplier": float(cost_multiplier),
                "epsilon": float(epsilon),
                "penalty": float(penalty),
                "permutation_seq": str(perm_str),
                "days": base_config["days"],
                "reps": base_config["reps"],
                "seed": base_config["base_seed"] + run_index * 1000 + 50000,
                "output_dir": str(ba_dir)
            }
            ba_log = logs_dir / f"ba_{perm_hash}_{run_index}.log"
            ba_success = run_driver("BA", ba_args, str(ba_dir), str(ba_log))

            success = bool(mba_success and ba_success)

            record = {
                "kind": "CELL",
                "args": {
                    "epsilon": epsilon,
                    "learning_rate": learning_rate,
                    "cost_multiplier": cost_multiplier,
                    "penalty": penalty,
                    "permutation_seq": perm_str
                },
                "dirs": {"mba": str(mba_dir), "ba": str(ba_dir)},
                "logs": {"mba": str(mba_log), "ba": str(ba_log)},
                "success": success
            }

            if not success:
                print("  ERROR: cell run failed, skipping delta computation")
                return record, None

            # 3) Delta analysis
            delta_csv = cell_dir / "delta.csv"
            delta_stats = compute_delta_csv(
                str(mba_dir), str(ba_dir), str(delta_csv),
                None,  # no per-cell plots
                window_last_days=200
            )
            srow = {
                "epsilon": float(epsilon),
                "learning_rate": float(learning_rate),
                "cost_multiplier": float(cost_multiplier),
                "penalty": float(penalty),
                "permutation": perm_str,
                "perm_hash": perm_hash,
                "delta_mean": delta_stats["delta_mean"],
                "delta_final_mean": delta_stats["delta_final_mean"],
                "delta_std": delta_stats["delta_std"],
                "proportion_positive": delta_stats["proportion_positive"],
                "proportion_final_positive": delta_stats["proportion_final_positive"],
                "success": True
            }
            print(f"  Δ_final_mean={delta_stats['delta_final_mean']:.4f}")
            return record, srow
        except Exception as e:
            print(f"  ERROR: delta analysis failed - {e}")
            record = {
                "kind": "CELL",
                "args": {
                    "epsilon": epsilon,
                    "learning_rate": learning_rate,
                    "cost_multiplier": cost_multiplier,
                    "penalty": penalty,
                    "permutation_seq": perm_str
                },
                "success": False,
                "error": str(e)
            }
            return record, None

    if args.workers and args.workers > 1:
        print(f"Running in parallel with {args.workers} workers...")
        with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            for rec, srow in ex.map(run_cell, tasks):
                runs_records.append(rec)
                if srow is not None:
                    summary_rows.append(srow)
    else:
        print("Running sequentially...")
        for task in tasks:
            rec, srow = run_cell(task)
            runs_records.append(rec)
            if srow is not None:
                summary_rows.append(srow)

    manifest["runs"].extend(runs_records)

    # Aggregate and save summary
    if not summary_rows:
        print("ERROR: no successful grid runs to summarize")
        safe_write_json(manifest_path, manifest)
        return False

    summary_df = pd.DataFrame(summary_rows)
    summary_csv = base_dir / "grid_summary.csv"
    summary_df.to_csv(summary_csv, index=False)

    print("\nTop rows of grid summary:")
    try:
        print(summary_df.head(10))
    except Exception:
        pass

    # Try simple heatmaps
    success_col = "success" in summary_df.columns
    successful_df = summary_df[summary_df["success"] == True] if success_col else summary_df
    _try_heatmaps(successful_df, plots_dir)

    # Save manifest and finalize
    manifest["summary"] = {
        "grid_summary_file": str(summary_csv),
        "n_cells": int(n_total),
        "n_successful": int(successful_df.shape[0])
    }
    safe_write_json(manifest_path, manifest)

    print("\nGRID SWEEP COMPLETE!")
    print(f"Results saved to: {base_dir}")
    print(f"Summary CSV: {summary_csv}")
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
