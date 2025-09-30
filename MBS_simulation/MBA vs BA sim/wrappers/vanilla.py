"""Vanilla MBA vs BA comparison wrapper.

Runs canonical MBA-only and BA-only experiments with standard parameters,
computes delta fitness analysis, and generates plots. This serves as the
baseline comparison and validation of the simulation system.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    ensure_dir, safe_write_json, run_driver, compute_delta_csv, 
    create_base_manifest, derive_seed, validate_sanity_gates
)

def main():
    """Run vanilla MBA vs BA comparison experiment."""
    print("=" * 60)
    print("VANILLA MBA vs BA COMPARISON")
    print("=" * 60)
    print()
    
    # Configuration (per experiment_wrappers.md spec)
    base_config = {
        "days": 1000,
        "reps": 10,
        "n_agents": 100,  # n_mba=100/n_ba=0 for MBA run, n_mba=0/n_ba=100 for BA run
        "learning_rate": 0.3,
        "cost_multiplier": 1.0,
        "epsilon": 0.0,
        "penalty": 0.7,
        "permutation_seq": "0,1,2,3,4",
        "base_seed": 42
    }
    
    # Create output structure
    base_dir = Path("wrappers_output/vanilla")
    ensure_dir(base_dir)
    
    mba_dir = base_dir / "mba"
    ba_dir = base_dir / "ba"
    plots_dir = base_dir / "plots"
    logs_dir = base_dir / "logs"
    
    for d in [mba_dir, ba_dir, plots_dir, logs_dir]:
        ensure_dir(d)
    
    # Initialize manifest
    manifest = create_base_manifest("vanilla", base_config)
    manifest_path = base_dir / "manifest.json"
    
    print("Running vanilla comparison:")
    print(f"  Days: {base_config['days']}")
    print(f"  Replications: {base_config['reps']}")
    print(f"  Agents per type: {base_config['n_agents']}")
    print(f"  Output: {base_dir}")
    print()
    
    # Run MBA simulation
    print("1. Running MBA-only simulation...")
    mba_args = {
        "n_mba": base_config["n_agents"],
        "n_ba": 0,
        "learning_rate": base_config["learning_rate"],
        "cost_multiplier": base_config["cost_multiplier"],
        "epsilon": base_config["epsilon"],
        "penalty": base_config["penalty"],
        "permutation_seq": base_config["permutation_seq"],
        "days": base_config["days"],
        "reps": base_config["reps"],
        "seed": base_config["base_seed"],
        "output_dir": str(mba_dir)
    }
    
    mba_success = run_driver("MBA", mba_args, str(mba_dir), str(logs_dir / "mba.log"))
    
    if mba_success:
        manifest["runs"].append({
            "kind": "MBA",
            "args": mba_args,
            "output_dir": str(mba_dir),
            "seed_policy": "fixed",
            "log": str(logs_dir / "mba.log"),
            "success": True
        })
        print("  MBA simulation completed successfully")
    else:
        print("  ERROR: MBA simulation failed")
        return False
    
    # Run BA simulation
    print("\n2. Running BA-only simulation...")
    ba_args = {
        "n_mba": 0,
        "n_ba": base_config["n_agents"],
        "learning_rate": base_config["learning_rate"],
        "cost_multiplier": base_config["cost_multiplier"],
        "epsilon": base_config["epsilon"],
        "penalty": base_config["penalty"],
        "permutation_seq": base_config["permutation_seq"],
        "days": base_config["days"],
        "reps": base_config["reps"],
        "seed": base_config["base_seed"] + 50000,  # Different seed for BA
        "output_dir": str(ba_dir)
    }
    
    ba_success = run_driver("BA", ba_args, str(ba_dir), str(logs_dir / "ba.log"))
    
    if ba_success:
        manifest["runs"].append({
            "kind": "BA", 
            "args": ba_args,
            "output_dir": str(ba_dir),
            "seed_policy": "fixed",
            "log": str(logs_dir / "ba.log"),
            "success": True
        })
        print("  BA simulation completed successfully")
    else:
        print("  ERROR: BA simulation failed")
        return False
    
    # Compute delta analysis
    print("\n3. Computing delta analysis...")
    try:
        delta_stats = compute_delta_csv(
            str(mba_dir), 
            str(ba_dir),
            str(base_dir / "delta.csv"),
            str(plots_dir),
            window_last_days=200  # Last 200 days per spec
        )
        
        # Add delta stats to manifest
        manifest["delta_analysis"] = delta_stats
        
        print("Delta analysis results:")
        print(f"  Overall delta mean: {delta_stats['delta_mean']:.4f}")
        print(f"  Final {200} days delta mean: {delta_stats['delta_final_mean']:.4f}")
        print(f"  Proportion positive (overall): {delta_stats['proportion_positive']:.3f}")
        print(f"  Proportion positive (final): {delta_stats['proportion_final_positive']:.3f}")
        
    except Exception as e:
        print(f"  ERROR: Delta analysis failed - {e}")
        return False
    
    # Validate sanity gates (per experiment_wrappers.md spec)
    print("\n4. Validating sanity gates...")
    sanity_gates = {
        "delta_final_mean": 0.10,  # Conservative acceptance: Δ_mean_last200 ≥ +0.10
        "proportion_final_positive": 0.7,  # At least 70% of final comparisons should favor MBA
    }
    
    gates_passed = validate_sanity_gates(delta_stats, sanity_gates)
    manifest["sanity_gates"] = {
        "gates": sanity_gates,
        "passed": gates_passed
    }
    
    # Save manifest
    safe_write_json(manifest_path, manifest)
    
    print(f"\nVANILLA COMPARISON COMPLETE!")
    print(f"Results saved to: {base_dir}")
    print(f"Sanity gates: {'PASSED' if gates_passed else 'FAILED'}")
    
    if not gates_passed:
        print("WARNING: Sanity gates failed - results may not be as expected")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
