"""Lock-in experiment wrapper for MBA vs BA.

Runs MBA-only and BA-only simulations using a phase schedule that changes
the environment permutation mid-run while reusing the same population. Computes:
- Delta (MBA - BA) over time
- Pre-switch vs post-switch delta window means
- Time-to-recovery after the switch

Outputs CSVs, plots, and a manifest.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    ensure_dir, safe_write_json, run_driver, compute_delta_csv,
    create_base_manifest, load_json_params
)

def _sum_schedule_days(schedule: List[Dict[str, Any]]) -> int:
    return int(sum(int(phase["days"]) for phase in schedule))

def _compute_lockin_metrics(delta_csv_path: Path, schedule: List[Dict[str, Any]], plots_dir: Path) -> Dict[str, Any]:
    """
    Compute lock-in specific metrics:
      - pre_switch_mean_delta (last N days of phase 1)
      - post_switch_mean_delta (first N days of phase 2)
      - time_to_recovery_days (first post-switch day where 10-day rolling mean >= pre_switch_mean)
    """
    df = pd.read_csv(delta_csv_path)
    if df.empty:
        raise ValueError("Delta CSV is empty, cannot compute lock-in metrics")

    # Determine first switch day (between phase 1 and phase 2)
    if len(schedule) < 2:
        raise ValueError("Lock-in metrics expect at least two phases in the schedule")

    phase1_days = int(schedule[0]["days"])
    switch_day = phase1_days - 1  # 0-indexed 'day' in driver output

    # Windows
    pre_window = min(200, phase1_days)
    # Post window length limited by phase 2 length if available
    phase2_days = int(schedule[1]["days"])
    post_window = min(200, phase2_days)

    # Pre-switch window: [switch_day - pre_window + 1, switch_day]
    pre_mask = (df["day"] >= (switch_day - pre_window + 1)) & (df["day"] <= switch_day)
    pre_window_df = df.loc[pre_mask].copy()
    pre_switch_mean = float(pre_window_df["delta_fitness"].mean()) if not pre_window_df.empty else float("nan")

    # Post-switch window: [switch_day + 1, switch_day + post_window]
    post_mask = (df["day"] >= (switch_day + 1)) & (df["day"] <= (switch_day + post_window))
    post_window_df = df.loc[post_mask].copy()
    post_switch_mean = float(post_window_df["delta_fitness"].mean()) if not post_window_df.empty else float("nan")

    # Time-to-recovery: earliest day t > switch_day such that rolling mean(10) of delta_fitness from (t-9..t) >= pre_switch_mean
    post_df = df[df["day"] > switch_day].copy()
    post_df = post_df.sort_values("day")
    post_df["rolling_mean_10"] = post_df["delta_fitness"].rolling(window=10, min_periods=10).mean()
    recovery_row = post_df[post_df["rolling_mean_10"] >= pre_switch_mean].head(1)

    if not recovery_row.empty:
        time_to_recovery_day = int(recovery_row["day"].iloc[0] - switch_day)
    else:
        time_to_recovery_day = None

    # Plot enhancements (switch marker + windows) atop delta_timeseries.png if available
    try:
        import matplotlib.pyplot as plt
        # Aggregate mean and std across reps by day
        daily = df.groupby("day")["delta_fitness"].agg(["mean", "std"]).reset_index()

        plt.figure(figsize=(12, 6))
        plt.plot(daily["day"], daily["mean"], "b-", label="Delta (MBA - BA)")
        if (daily["std"].notna()).any():
            plt.fill_between(daily["day"], daily["mean"] - daily["std"], daily["mean"] + daily["std"], color="b", alpha=0.2)

        # Switch marker
        plt.axvline(switch_day, color="red", linestyle="--", label="Switch")

        # Shade pre and post windows
        plt.axvspan(switch_day - pre_window + 1, switch_day, color="green", alpha=0.1, label=f"Pre-window (N={pre_window})")
        plt.axvspan(switch_day + 1, switch_day + post_window, color="orange", alpha=0.1, label=f"Post-window (N={post_window})")

        # Pre mean line
        plt.axhline(pre_switch_mean, color="green", linestyle=":", alpha=0.8, label=f"Pre mean Δ={pre_switch_mean:.3f}")

        # Recovery marker
        if time_to_recovery_day is not None:
            rec_day_abs = switch_day + time_to_recovery_day
            plt.axvline(rec_day_abs, color="purple", linestyle="--", label=f"Recovery t={time_to_recovery_day} days")

        plt.xlabel("Day")
        plt.ylabel("Fitness Advantage (MBA - BA)")
        plt.title("Lock-in Delta Over Time")
        plt.grid(True, alpha=0.3)
        plt.legend()
        ensure_dir(plots_dir)
        plt.tight_layout()
        plt.savefig(plots_dir / "lock_in_delta_timeseries.png", dpi=150, bbox_inches="tight")
        plt.close()
    except Exception as e:
        print(f"Warning: Could not render lock-in plot: {e}")

    return {
        "switch_day": int(switch_day),
        "pre_window": int(pre_window),
        "post_window": int(post_window),
        "pre_switch_mean_delta": pre_switch_mean,
        "post_switch_mean_delta": post_switch_mean,
        "time_to_recovery_days": time_to_recovery_day,
    }

def main():
    """Run lock-in experiment using a phase schedule."""
    print("=" * 60)
    print("LOCK-IN EXPERIMENT")
    print("=" * 60)
    print()

    # Base configuration
    base_config = {
        "reps": 10,
        "n_agents": 100,
        "learning_rate": 0.3,
        "cost_multiplier": 1.0,
        "penalty": 0.7,
        "epsilon": 0.0,  # baseline; per-phase overrides can change this
        "phase_schedule": "wrappers/params/lockin_schedule.json",
        "base_seed": 4242,
    }

    # Resolve directories
    base_dir = Path("wrappers_output/lock_in")
    ensure_dir(base_dir)

    mba_dir = base_dir / "mba"
    ba_dir = base_dir / "ba"
    plots_dir = base_dir / "plots"
    logs_dir = base_dir / "logs"
    for d in (mba_dir, ba_dir, plots_dir, logs_dir):
        ensure_dir(d)

    # Load and sum phase schedule (resolve robustly relative to CWD and script dir)
    schedule_candidates = [
        Path(base_config["phase_schedule"]),
        Path(__file__).parent / "params" / "lockin_schedule.json",
        Path(__file__).parent.parent / Path(base_config["phase_schedule"]),
    ]
    schedule_path = None
    for cand in schedule_candidates:
        if cand.exists():
            schedule_path = cand
            break
    if schedule_path is None:
        print("ERROR: Phase schedule file not found: tried " + ", ".join(str(c) for c in schedule_candidates))
        return False

    schedule = load_json_params(str(schedule_path))
    if not isinstance(schedule, list) or len(schedule) < 2:
        print("ERROR: Phase schedule must be a JSON array with at least two phases for lock-in")
        return False

    total_days = _sum_schedule_days(schedule)

    # Manifest
    manifest = create_base_manifest("lock_in", {**base_config, "total_days": total_days})
    manifest_path = base_dir / "manifest.json"

    print("Running lock-in experiment:")
    print(f"  Phases: {len(schedule)}")
    for i, ph in enumerate(schedule):
        print(f"    Phase {i+1}: days={ph.get('days')}, perm={ph.get('permutation_seq')}, overrides={{epsilon:{ph.get('epsilon')}, penalty:{ph.get('penalty')}, lr:{ph.get('learning_rate')}, cost:{ph.get('cost_multiplier')}}}")
    print(f"  Total days: {total_days}")
    print(f"  Reps: {base_config['reps']}")
    print()

    # 1) MBA run
    print("1. Running MBA-only with phase schedule...")
    mba_args = {
        "n_mba": base_config["n_agents"],
        "n_ba": 0,
        "learning_rate": base_config["learning_rate"],
        "cost_multiplier": base_config["cost_multiplier"],
        "epsilon": base_config["epsilon"],
        "penalty": base_config["penalty"],
        "permutation_seq": "0,1,2,3,4",  # ignored when --phase_schedule is used
        "days": total_days,
        "reps": base_config["reps"],
        "seed": base_config["base_seed"],
        "output_dir": str(mba_dir),
        "phase_schedule": str(schedule_path),
    }
    mba_log = logs_dir / "mba.log"
    mba_success = run_driver("MBA", mba_args, str(mba_dir), str(mba_log))
    manifest["runs"].append({
        "kind": "MBA",
        "args": mba_args,
        "output_dir": str(mba_dir),
        "log": str(mba_log),
        "success": bool(mba_success),
    })
    if not mba_success:
        print("ERROR: MBA run failed")
        safe_write_json(manifest_path, manifest)
        return False

    # 2) BA run
    print("2. Running BA-only with phase schedule...")
    ba_args = {
        "n_mba": 0,
        "n_ba": base_config["n_agents"],
        "learning_rate": base_config["learning_rate"],
        "cost_multiplier": base_config["cost_multiplier"],
        "epsilon": base_config["epsilon"],
        "penalty": base_config["penalty"],
        "permutation_seq": "0,1,2,3,4",
        "days": total_days,
        "reps": base_config["reps"],
        "seed": base_config["base_seed"] + 50000,
        "output_dir": str(ba_dir),
        "phase_schedule": str(schedule_path),
    }
    ba_log = logs_dir / "ba.log"
    ba_success = run_driver("BA", ba_args, str(ba_dir), str(ba_log))
    manifest["runs"].append({
        "kind": "BA",
        "args": ba_args,
        "output_dir": str(ba_dir),
        "log": str(ba_log),
        "success": bool(ba_success),
    })
    if not ba_success:
        print("ERROR: BA run failed")
        safe_write_json(manifest_path, manifest)
        return False

    # 3) Delta analysis
    print("3. Computing delta analysis and lock-in metrics...")
    try:
        delta_csv_path = base_dir / "delta.csv"
        delta_stats = compute_delta_csv(
            str(mba_dir),
            str(ba_dir),
            str(delta_csv_path),
            str(plots_dir),
            window_last_days=200
        )
        manifest["delta_analysis"] = delta_stats

        # Lock-in specific metrics
        lockin_metrics = _compute_lockin_metrics(delta_csv_path, schedule, plots_dir)
        manifest["lock_in_metrics"] = lockin_metrics

        print("Delta analysis:")
        print(f"  Δ_mean (overall): {delta_stats['delta_mean']:.4f}")
        print(f"  Δ_mean (final 200): {delta_stats['delta_final_mean']:.4f}")
        print("Lock-in metrics:")
        print(f"  Switch day: {lockin_metrics['switch_day']}")
        print(f"  Pre-switch mean Δ: {lockin_metrics['pre_switch_mean_delta']:.4f}")
        print(f"  Post-switch mean Δ: {lockin_metrics['post_switch_mean_delta']:.4f}")
        print(f"  Time-to-recovery (days): {lockin_metrics['time_to_recovery_days']}")
    except Exception as e:
        print(f"ERROR: Delta or lock-in analysis failed: {e}")
        safe_write_json(manifest_path, manifest)
        return False

    # Save manifest
    safe_write_json(manifest_path, manifest)

    print("\nLOCK-IN EXPERIMENT COMPLETE!")
    print(f"Results saved to: {base_dir}")
    return True

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
