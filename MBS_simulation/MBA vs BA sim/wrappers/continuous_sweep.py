"""Continuous parameter sweep wrapper for MBA vs BA experiments.

Performs randomized sampling across epsilon, learning_rate, cost_multiplier, penalty
within specified ranges and randomly selects from available permutations.
Runs MBA-only and BA-only experiments, computes delta (MBA - BA) per experiment,
and maintains a continuous_summary.csv compatible with CatBoost analysis.

Each experiment generates a JSON specification for independent execution and
allows incremental data collection for ongoing regression analysis.
"""

import sys
import json
import argparse
import concurrent.futures as futures
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    ensure_dir, safe_write_json, run_driver, compute_delta_csv,
    create_base_manifest, get_permutation_hash, load_json_params
)


def load_perms(perms_file: str) -> List[str]:
    """Load permutation list from JSON file."""
    perms_path = Path(perms_file)
    if not perms_path.exists():
        raise FileNotFoundError(f"Permutations file not found: {perms_file}")
    
    with open(perms_path, 'r') as f:
        perms = json.load(f)
    
    if not isinstance(perms, list) or not all(isinstance(p, str) for p in perms):
        raise ValueError(f"Expected list of strings in {perms_file}")
    
    print(f"Loaded {len(perms)} permutations from {perms_file}")
    return perms


def sample_params(rng: np.random.Generator, 
                 epsilon_range: Tuple[float, float] = (0.0, 0.2),
                 learning_rate_range: Tuple[float, float] = (0.0, 0.9),
                 cost_multiplier_range: Tuple[float, float] = (0.0, 2.0),
                 penalty_range: Tuple[float, float] = (0.0, 0.8)) -> Tuple[float, float, float, float]:
    """Sample parameters uniformly from specified ranges."""
    epsilon = rng.uniform(*epsilon_range)
    learning_rate = rng.uniform(*learning_rate_range)
    cost_multiplier = rng.uniform(*cost_multiplier_range)
    penalty = rng.uniform(*penalty_range)
    
    return epsilon, learning_rate, cost_multiplier, penalty


def choose_permutation(rng: np.random.Generator, perms: List[str]) -> Tuple[str, str]:
    """Choose a random permutation and return (perm_str, perm_hash)."""
    perm_str = rng.choice(perms)
    perm_hash = get_permutation_hash(perm_str)
    return perm_str, perm_hash


def format_cell_dir(epsilon: float, learning_rate: float, cost_multiplier: float, 
                   penalty: float, perm_hash: str, base_dir: Path) -> Dict[str, Path]:
    """Build consistent cell directory structure with 4-decimal precision."""
    cell_name = f"eps_{epsilon:.4f}_lr_{learning_rate:.4f}_cm_{cost_multiplier:.4f}_pen_{penalty:.4f}"
    cell_dir = base_dir / f"perm_{perm_hash}" / cell_name
    
    return {
        "cell_dir": cell_dir,
        "mba_dir": cell_dir / "mba",
        "ba_dir": cell_dir / "ba",
    }


def build_experiment_json(exp_id: int, params: Dict[str, float], run_cfg: Dict[str, Any], 
                         paths: Dict[str, Path], perm: str, perm_hash: str) -> Dict[str, Any]:
    """Construct complete per-experiment JSON record."""
    return {
        "exp_id": exp_id,
        "timestamp": datetime.now().isoformat(),
        "permutation": perm,
        "perm_hash": perm_hash,
        "params": params,
        "run_config": run_cfg,
        "paths": {k: str(v) for k, v in paths.items()},
        "execution": {
            "status": "PENDING",
            "error": None
        }
    }


def write_experiment_json(base_dir: Path, exp_obj: Dict[str, Any]) -> Path:
    """Write experiments/exp_<id>.json."""
    experiments_dir = ensure_dir(base_dir / "experiments")
    exp_path = experiments_dir / f"exp_{exp_obj['exp_id']:05d}.json"
    safe_write_json(exp_path, exp_obj)
    return exp_path


def get_next_exp_id(base_dir: Path) -> int:
    """Determine next experiment ID by checking existing experiments."""
    experiments_dir = base_dir / "experiments"
    if not experiments_dir.exists():
        return 1
    
    existing_ids = []
    for json_file in experiments_dir.glob("exp_*.json"):
        try:
            # Extract ID from filename like exp_00001.json
            id_str = json_file.stem.split("_")[1]
            existing_ids.append(int(id_str))
        except (IndexError, ValueError):
            continue
    
    return max(existing_ids, default=0) + 1


def run_cell(task: Tuple[int, float, float, float, float, str, str, Dict[str, Any], Path]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Execute MBA-only and BA-only runs for a single experiment.
    
    Args:
        task: (exp_id, epsilon, learning_rate, cost_multiplier, penalty, perm_str, perm_hash, run_config, base_dir)
        
    Returns:
        Tuple of (manifest_record, summary_row_or_None)
    """
    exp_id, epsilon, learning_rate, cost_multiplier, penalty, perm_str, perm_hash, run_config, base_dir = task
    
    try:
        print(f"[{exp_id}] eps={epsilon:.4f} lr={learning_rate:.4f} cost={cost_multiplier:.4f} pen={penalty:.4f} perm={perm_str} ({perm_hash})")
        
        # Build directories
        paths = format_cell_dir(epsilon, learning_rate, cost_multiplier, penalty, perm_hash, base_dir)
        for d in paths.values():
            ensure_dir(d)
        
        # Add log paths
        logs_dir = ensure_dir(base_dir / "logs")
        mba_log = logs_dir / f"mba_{perm_hash}_{exp_id:05d}.log"
        ba_log = logs_dir / f"ba_{perm_hash}_{exp_id:05d}.log"
        delta_csv = paths["cell_dir"] / "delta.csv"
        
        paths.update({
            "mba_log": mba_log,
            "ba_log": ba_log,
            "delta_csv": delta_csv
        })
        
        # Create experiment JSON
        params = {
            "epsilon": epsilon,
            "learning_rate": learning_rate,
            "cost_multiplier": cost_multiplier,
            "penalty": penalty
        }
        
        exp_obj = build_experiment_json(exp_id, params, run_config, paths, perm_str, perm_hash)
        exp_obj["execution"]["status"] = "RUNNING"
        write_experiment_json(base_dir, exp_obj)
        
        # Run MBA-only
        mba_args = {
            "n_mba": run_config["n_agents"],
            "n_ba": 0,
            "learning_rate": learning_rate,
            "cost_multiplier": cost_multiplier,
            "epsilon": epsilon,
            "penalty": penalty,
            "permutation_seq": perm_str,
            "days": run_config["days"],
            "reps": run_config["reps"],
            "seed": run_config["seed_mba"],
            "output_dir": str(paths["mba_dir"])
        }
        mba_success = run_driver("MBA", mba_args, str(paths["mba_dir"]), str(mba_log))
        
        # Run BA-only
        ba_args = {
            "n_mba": 0,
            "n_ba": run_config["n_agents"],
            "learning_rate": learning_rate,
            "cost_multiplier": cost_multiplier,
            "epsilon": epsilon,
            "penalty": penalty,
            "permutation_seq": perm_str,
            "days": run_config["days"],
            "reps": run_config["reps"],
            "seed": run_config["seed_ba"],
            "output_dir": str(paths["ba_dir"])
        }
        ba_success = run_driver("BA", ba_args, str(paths["ba_dir"]), str(ba_log))
        
        success = bool(mba_success and ba_success)
        
        # Create manifest record
        args_dict = params.copy()
        args_dict["permutation_seq"] = perm_str
        
        record = {
            "kind": "EXPERIMENT",
            "exp_id": exp_id,
            "args": args_dict,
            "dirs": {"mba": str(paths["mba_dir"]), "ba": str(paths["ba_dir"])},
            "logs": {"mba": str(mba_log), "ba": str(ba_log)},
            "success": success
        }
        
        if not success:
            print(f"  [{exp_id}] ERROR: experiment failed, skipping delta computation")
            exp_obj["execution"]["status"] = "FAILED"
            exp_obj["execution"]["error"] = "MBA or BA run failed"
            write_experiment_json(base_dir, exp_obj)
            return record, None
        
        # Compute delta analysis
        delta_stats = compute_delta_csv(
            str(paths["mba_dir"]), str(paths["ba_dir"]), str(delta_csv),
            None,  # no per-cell plots
            window_last_days=200
        )
        
        # Create summary row
        summary_row = {
            "epsilon": epsilon,
            "learning_rate": learning_rate,
            "cost_multiplier": cost_multiplier,
            "penalty": penalty,
            "permutation": perm_str,
            "perm_hash": perm_hash,
            "delta_mean": delta_stats["delta_mean"],
            "delta_final_mean": delta_stats["delta_final_mean"],
            "delta_std": delta_stats["delta_std"],
            "proportion_positive": delta_stats["proportion_positive"],
            "proportion_final_positive": delta_stats["proportion_final_positive"],
            "success": True,
            "exp_id": exp_id
        }
        
        print(f"  [{exp_id}] Δ_final_mean={delta_stats['delta_final_mean']:.4f}")
        
        # Update experiment JSON
        exp_obj["execution"]["status"] = "DONE"
        write_experiment_json(base_dir, exp_obj)
        
        return record, summary_row
        
    except Exception as e:
        print(f"  [{exp_id}] ERROR: experiment failed - {e}")
        
        # Update experiment JSON if it exists
        try:
            exp_obj["execution"]["status"] = "FAILED" 
            exp_obj["execution"]["error"] = str(e)
            write_experiment_json(base_dir, exp_obj)
        except:
            pass
        
        record = {
            "kind": "EXPERIMENT",
            "exp_id": exp_id,
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


def append_summary_csv(summary_rows: List[Dict[str, Any]], csv_path: Path) -> None:
    """Append summary rows to CSV file."""
    if not summary_rows:
        return
    
    df_new = pd.DataFrame(summary_rows)
    
    if csv_path.exists():
        # Append mode
        df_new.to_csv(csv_path, mode='a', header=False, index=False)
        print(f"Appended {len(summary_rows)} rows to {csv_path}")
    else:
        # Create new
        df_new.to_csv(csv_path, index=False)
        print(f"Created {csv_path} with {len(summary_rows)} rows")


def main():
    """Run continuous parameter sweep across randomized samples."""
    print("=" * 60)
    print("CONTINUOUS SWEEP - RANDOMIZED PARAMETER EXPLORATION")
    print("=" * 60)
    print()
    
    # CLI parsing
    parser = argparse.ArgumentParser(description="CONTINUOUS SWEEP - RANDOMIZED PARAMETER EXPLORATION")
    parser.add_argument("--n_experiments", type=int, default=5000, help="Number of experiments to run (default 5000)")
    parser.add_argument("--days", type=int, default=600, help="Days per run (default 600)")
    parser.add_argument("--reps", type=int, default=5, help="Replicates per experiment (default 5)")
    parser.add_argument("--n_agents", type=int, default=100, help="Population size per run (default 100)")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default 1)")
    parser.add_argument("--output_dir", type=str, default="wrappers_output/continuous_sweep", help="Output directory")
    parser.add_argument("--perms_file", type=str, default="wrappers/params/perms5.json", help="Permutations JSON file")
    parser.add_argument("--seed", type=int, default=1312, help="Base random seed (default 1312)")
    
    # Parameter range overrides
    parser.add_argument("--epsilon_min", type=float, default=0.0, help="Epsilon minimum (default 0.0)")
    parser.add_argument("--epsilon_max", type=float, default=0.2, help="Epsilon maximum (default 0.2)")
    parser.add_argument("--learning_rate_min", type=float, default=0.0, help="Learning rate minimum (default 0.0)")
    parser.add_argument("--learning_rate_max", type=float, default=0.9, help="Learning rate maximum (default 0.9)")
    parser.add_argument("--cost_multiplier_min", type=float, default=0.0, help="Cost multiplier minimum (default 0.0)")
    parser.add_argument("--cost_multiplier_max", type=float, default=2.0, help="Cost multiplier maximum (default 2.0)")
    parser.add_argument("--penalty_min", type=float, default=0.0, help="Penalty minimum (default 0.0)")
    parser.add_argument("--penalty_max", type=float, default=0.8, help="Penalty maximum (default 0.8)")
    
    args = parser.parse_args()
    
    # Setup
    base_dir = ensure_dir(Path(args.output_dir))
    rng = np.random.default_rng(args.seed)
    
    # Load permutations
    if args.perms_file.startswith("wrappers/"):
        # Remove leading "wrappers/" since we're already in the wrappers directory
        relative_perms_path = args.perms_file[9:]  # Remove "wrappers/"
        perms_path = Path(__file__).parent / relative_perms_path
    else:
        perms_path = Path(__file__).parent / args.perms_file
    perms = load_perms(str(perms_path))
    
    # Parameter ranges
    epsilon_range = (args.epsilon_min, args.epsilon_max)
    learning_rate_range = (args.learning_rate_min, args.learning_rate_max)
    cost_multiplier_range = (args.cost_multiplier_min, args.cost_multiplier_max)
    penalty_range = (args.penalty_min, args.penalty_max)
    
    # Base configuration
    base_config = {
        "n_experiments": args.n_experiments,
        "days": args.days,
        "reps": args.reps,
        "n_agents": args.n_agents,
        "base_seed": args.seed,
        "perms_file": str(perms_path),
        "parameter_ranges": {
            "epsilon": epsilon_range,
            "learning_rate": learning_rate_range,
            "cost_multiplier": cost_multiplier_range,
            "penalty": penalty_range
        }
    }
    
    # Initialize manifest
    manifest = create_base_manifest("continuous_sweep", base_config)
    manifest_path = base_dir / "manifest.json"
    
    print(f"Configuration:")
    print(f"  Experiments: {args.n_experiments}")
    print(f"  Days: {args.days}, Reps: {args.reps}, Agents: {args.n_agents}")
    print(f"  Parameter ranges:")
    print(f"    epsilon: {epsilon_range}")
    print(f"    learning_rate: {learning_rate_range}")
    print(f"    cost_multiplier: {cost_multiplier_range}")
    print(f"    penalty: {penalty_range}")
    print(f"  Permutations: {len(perms)} available")
    print(f"  Output: {base_dir}")
    print(f"  Workers: {args.workers}")
    print()
    
    # Determine starting experiment ID
    start_exp_id = get_next_exp_id(base_dir)
    print(f"Starting from experiment ID: {start_exp_id}")
    
    # Generate tasks
    tasks = []
    for i in range(args.n_experiments):
        exp_id = start_exp_id + i
        
        # Sample parameters
        epsilon, learning_rate, cost_multiplier, penalty = sample_params(
            rng, epsilon_range, learning_rate_range, cost_multiplier_range, penalty_range
        )
        
        # Choose permutation
        perm_str, perm_hash = choose_permutation(rng, perms)
        
        # Build run config for this experiment
        run_config = {
            "days": args.days,
            "reps": args.reps,
            "n_agents": args.n_agents,
            "base_seed": args.seed,
            "seed_mba": args.seed + exp_id * 1000,
            "seed_ba": args.seed + exp_id * 1000 + 50000
        }
        
        task = (exp_id, epsilon, learning_rate, cost_multiplier, penalty, perm_str, perm_hash, run_config, base_dir)
        tasks.append(task)
    
    print(f"Generated {len(tasks)} experiment tasks")
    print()
    
    # Execute tasks
    summary_rows = []
    runs_records = []
    
    if args.workers > 1:
        print(f"Running in parallel with {args.workers} workers...")
        with futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            for record, summary_row in executor.map(run_cell, tasks):
                runs_records.append(record)
                if summary_row is not None:
                    summary_rows.append(summary_row)
    else:
        print("Running sequentially...")
        for task in tasks:
            record, summary_row = run_cell(task)
            runs_records.append(record)
            if summary_row is not None:
                summary_rows.append(summary_row)
    
    # Update manifest
    manifest["runs"].extend(runs_records)
    safe_write_json(manifest_path, manifest)
    
    # Save summary CSV
    if summary_rows:
        summary_csv = base_dir / "continuous_summary.csv"
        append_summary_csv(summary_rows, summary_csv)
        
        print("\nSample of results:")
        try:
            df = pd.DataFrame(summary_rows)
            print(df.head(10))
        except Exception as e:
            print(f"Could not display sample: {e}")
        
        # Update manifest with summary info
        manifest["summary"] = {
            "continuous_summary_file": str(summary_csv),
            "n_experiments_requested": args.n_experiments,
            "n_successful": len(summary_rows)
        }
        safe_write_json(manifest_path, manifest)
        
        print("\nCONTINUOUS SWEEP COMPLETE!")
        print(f"Results saved to: {base_dir}")
        print(f"Summary CSV: {summary_csv}")
        print(f"Successful experiments: {len(summary_rows)}/{args.n_experiments}")
        return True
        
    else:
        print("ERROR: no successful experiments to summarize")
        safe_write_json(manifest_path, manifest)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
