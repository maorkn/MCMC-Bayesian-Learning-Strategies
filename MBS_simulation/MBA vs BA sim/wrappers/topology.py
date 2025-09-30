"""Topology scan wrapper for MBA vs BA experiments.

Iterates over permutations of the 5 HES stages (0..4), runs MBA-only and BA-only
simulations per permutation, computes delta (MBA - BA) metrics, and aggregates
a topology_summary.csv with permutation-level metrics (e.g., Hamming distance
to canonical cycle). Generates optional plots.

Defaults are moderate-scale; edit base_config for full-scale scans.
"""

import sys
import itertools
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    ensure_dir, safe_write_json, run_driver, compute_delta_csv,
    create_base_manifest, get_permutation_hash
)

CANON = [0, 1, 2, 3, 4]

def hamming_to_canon(perm: List[int]) -> int:
    return int(sum(int(v != i) for i, v in enumerate(perm)))

def p_slots(perm: List[int]) -> Dict[str, Any]:
    """P3 slot and P1 slots indices under a permutation."""
    p3_slot = int(perm.index(3))
    p1_slots = [int(i) for i, v in enumerate(perm) if v in {0, 4}]
    return {"p3_slot": p3_slot, "p1_slots": p1_slots}       

def main():
    """Run topology scan across permutations."""
    print("=" * 60)
    print("TOPOLOGY SCAN - PERMUTATION SWEEP")
    print("=" * 60)
    print()

    # Configuration (tune as needed; full-scale = reps=10, days=1000, n_permutations=120)
    base_config = {
        "days": 600,
        "reps": 5,
        "n_agents": 100,
        "learning_rate": 0.3,
        "cost_multiplier": 1.0,
        "epsilon": 0.0,
        "penalty": 0.7,
        "n_permutations": 120,  # 5! = 120
        "base_seed": 777
    }

    # Output structure
    base_dir = Path("wrappers_output/topology")
    ensure_dir(base_dir)
    plots_dir = base_dir / "plots"
    logs_dir = base_dir / "logs"
    for d in [plots_dir, logs_dir]:
        ensure_dir(d)

    # Manifest
    manifest = create_base_manifest("topology", base_config)
    manifest_path = base_dir / "manifest.json"

    print("Running topology scan:")
    print(f"  Days: {base_config['days']}")
    print(f"  Replications: {base_config['reps']}")
    print(f"  Agents per type: {base_config['n_agents']}")
    print(f"  Epsilon: {base_config['epsilon']}")
    print(f"  Permutations: {base_config['n_permutations']}")
    print(f"  Output: {base_dir}")
    print()

    # Generate permutations (lexicographic)
    all_perms = list(itertools.permutations([0, 1, 2, 3, 4], 5))
    if base_config["n_permutations"] < len(all_perms):
        all_perms = all_perms[: base_config["n_permutations"]]

    summary_rows: List[Dict[str, Any]] = []
    n_total = len(all_perms)

    for idx, perm_tuple in enumerate(all_perms, start=1):
        perm = list(map(int, perm_tuple))
        perm_str = ",".join(map(str, perm))
        perm_hash = get_permutation_hash(perm_str)
        print(f"[{idx}/{n_total}] Perm={perm_str} (hash={perm_hash})")

        # Per-permutation output dirs
        perm_dir = base_dir / f"perm_{perm_hash}"
        mba_dir = perm_dir / "mba"
        ba_dir = perm_dir / "ba"
        for d in [perm_dir, mba_dir, ba_dir]:
            ensure_dir(d)

        # 1) MBA run
        mba_args = {
            "n_mba": base_config["n_agents"],
            "n_ba": 0,
            "learning_rate": base_config["learning_rate"],
            "cost_multiplier": base_config["cost_multiplier"],
            "epsilon": base_config["epsilon"],
            "penalty": base_config["penalty"],
            "permutation_seq": perm_str,
            "days": base_config["days"],
            "reps": base_config["reps"],
            "seed": base_config["base_seed"] + idx * 1000,
            "output_dir": str(mba_dir)
        }
        mba_log = logs_dir / f"mba_{perm_hash}.log"
        mba_success = run_driver("MBA", mba_args, str(mba_dir), str(mba_log))
        if not mba_success:
            print(f"  ERROR: MBA run failed for perm={perm_str}")
            manifest["runs"].append({
                "kind": "MBA", "args": mba_args, "output_dir": str(mba_dir),
                "log": str(mba_log), "success": False
            })
            continue
        manifest["runs"].append({
            "kind": "MBA", "args": mba_args, "output_dir": str(mba_dir),
            "log": str(mba_log), "success": True
        })

        # 2) BA run
        ba_args = {
            "n_mba": 0,
            "n_ba": base_config["n_agents"],
            "learning_rate": base_config["learning_rate"],
            "cost_multiplier": base_config["cost_multiplier"],
            "epsilon": base_config["epsilon"],
            "penalty": base_config["penalty"],
            "permutation_seq": perm_str,
            "days": base_config["days"],
            "reps": base_config["reps"],
            "seed": base_config["base_seed"] + idx * 1000 + 50000,
            "output_dir": str(ba_dir)
        }
        ba_log = logs_dir / f"ba_{perm_hash}.log"
        ba_success = run_driver("BA", ba_args, str(ba_dir), str(ba_log))
        if not ba_success:
            print(f"  ERROR: BA run failed for perm={perm_str}")
            manifest["runs"].append({
                "kind": "BA", "args": ba_args, "output_dir": str(ba_dir),
                "log": str(ba_log), "success": False
            })
            continue
        manifest["runs"].append({
            "kind": "BA", "args": ba_args, "output_dir": str(ba_dir),
            "log": str(ba_log), "success": True
        })

        # 3) Delta analysis per permutation
        try:
            delta_csv = perm_dir / "delta.csv"
            delta_stats = compute_delta_csv(
                str(mba_dir), str(ba_dir), str(delta_csv),
                None,  # no per-permutation plots
                window_last_days=200
            )
            slots = p_slots(perm)
            row = {
                "perm": perm_str,
                "perm_hash": perm_hash,
                "hamming_to_canon": hamming_to_canon(perm),
                "p3_slot": slots["p3_slot"],
                "p1_slot_a": slots["p1_slots"][0] if len(slots["p1_slots"]) > 0 else None,
                "p1_slot_b": slots["p1_slots"][1] if len(slots["p1_slots"]) > 1 else None,
                "delta_mean": delta_stats["delta_mean"],
                "delta_final_mean": delta_stats["delta_final_mean"],
                "delta_std": delta_stats["delta_std"],
                "proportion_positive": delta_stats["proportion_positive"],
                "proportion_final_positive": delta_stats["proportion_final_positive"]
            }
            summary_rows.append(row)
            print(f"  Δ_final_mean={row['delta_final_mean']:.4f}, Hamming={row['hamming_to_canon']}")
        except Exception as e:
            print(f"  ERROR: Delta analysis failed for perm={perm_str} - {e}")

        # Save interim manifest occasionally
        if idx % 10 == 0:
            safe_write_json(manifest_path, manifest)

    # Build and save summary
    if not summary_rows:
        print("ERROR: No successful permutation runs to summarize")
        safe_write_json(manifest_path, manifest)
        return False

    summary_df = pd.DataFrame(summary_rows)
    summary_csv = base_dir / "topology_summary.csv"
    summary_df.to_csv(summary_csv, index=False)

    print("\nSummary by hamming distance (first rows):")
    try:
        print(summary_df.sort_values(["hamming_to_canon", "delta_final_mean"]).head(10))
    except Exception:
        pass

    # Simple plot: Δ_final_mean vs Hamming
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(9, 6))
        plt.scatter(summary_df["hamming_to_canon"], summary_df["delta_final_mean"], c="tab:blue", alpha=0.7)
        plt.axhline(0.0, color="k", linestyle="--", alpha=0.5)
        plt.xlabel("Hamming distance to canonical (0,1,2,3,4)")
        plt.ylabel("Final Delta Fitness (MBA - BA)")
        plt.title("MBA Advantage vs Topology (Hamming distance)")
        plt.grid(True, alpha=0.3)
        ensure_dir(plots_dir)
        plt.tight_layout()
        plt.savefig(plots_dir / "delta_vs_hamming.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Summary plot saved to: {plots_dir / 'delta_vs_hamming.png'}")
    except ImportError:
        print("Warning: matplotlib not available, skipping topology plots")
    except Exception as e:
        print(f"Warning: Error creating topology plots - {e}")

    # Save manifest and finalize
    manifest["summary"] = {
        "topology_summary_file": str(summary_csv),
        "n_permutations": n_total,
        "n_successful": int(len(summary_rows)),
    }
    safe_write_json(manifest_path, manifest)

    print("\nTOPOLOGY SCAN COMPLETE!")
    print(f"Results saved to: {base_dir}")
    print(f"Summary CSV: {summary_csv}")
    return True

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
