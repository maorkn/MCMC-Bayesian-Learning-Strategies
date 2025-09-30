"""Stress test wrapper for MBA vs BA experiments.

Tests MBA performance across increasing environmental noise (epsilon) levels.
Expects MBA advantage to decrease as epsilon increases, validating that
MBA learning is most beneficial in stable environments.
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    ensure_dir, safe_write_json, run_driver, compute_delta_csv,
    create_base_manifest, validate_sanity_gates
)

def main():
    """Run stress test across epsilon values."""
    print("=" * 60)
    print("STRESS TEST - EPSILON SWEEP")
    print("=" * 60)
    print()
    
    # Configuration (per experiment_wrappers.md spec)
    base_config = {
        "days": 1000,  # Full-scale runs per spec
        "reps": 10,    # Full reps per spec
        "n_agents": 100,
        "learning_rate": 0.3,
        "cost_multiplier": 1.0,
        "penalty": 0.7,
        "permutation_seq": "0,1,2,3,4",
        "base_seed": 42,
        "epsilon_values": [0.01, 0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # Per spec
    }
    
    # Create output structure
    base_dir = Path("wrappers_output/stress")
    ensure_dir(base_dir)
    
    plots_dir = base_dir / "plots"
    logs_dir = base_dir / "logs"
    ensure_dir(plots_dir)
    ensure_dir(logs_dir)
    
    # Initialize manifest
    manifest = create_base_manifest("stress", base_config)
    manifest_path = base_dir / "manifest.json"
    
    print("Running stress test:")
    print(f"  Epsilon values: {base_config['epsilon_values']}")
    print(f"  Days per run: {base_config['days']}")
    print(f"  Replications per epsilon: {base_config['reps']}")
    print(f"  Output: {base_dir}")
    print()
    
    # Store results for summary
    epsilon_results = []
    
    # Run experiments for each epsilon value
    for i, epsilon in enumerate(base_config["epsilon_values"]):
        print(f"Running epsilon = {epsilon} ({i+1}/{len(base_config['epsilon_values'])})...")
        
        # Create directories for this epsilon
        eps_dir = base_dir / f"eps_{epsilon}"
        mba_dir = eps_dir / "mba" 
        ba_dir = eps_dir / "ba"
        
        for d in [eps_dir, mba_dir, ba_dir]:
            ensure_dir(d)
        
        # Run MBA simulation
        mba_args = {
            "n_mba": base_config["n_agents"],
            "n_ba": 0,
            "learning_rate": base_config["learning_rate"],
            "cost_multiplier": base_config["cost_multiplier"],
            "epsilon": epsilon,
            "penalty": base_config["penalty"],
            "permutation_seq": base_config["permutation_seq"],
            "days": base_config["days"],
            "reps": base_config["reps"],
            "seed": base_config["base_seed"] + i * 1000,
            "output_dir": str(mba_dir)
        }
        
        mba_log = logs_dir / f"mba_eps_{epsilon}.log"
        mba_success = run_driver("MBA", mba_args, str(mba_dir), str(mba_log))
        
        if not mba_success:
            print(f"  ERROR: MBA simulation failed for epsilon={epsilon}")
            continue
        
        # Run BA simulation
        ba_args = {
            "n_mba": 0,
            "n_ba": base_config["n_agents"],
            "learning_rate": base_config["learning_rate"],
            "cost_multiplier": base_config["cost_multiplier"],
            "epsilon": epsilon,
            "penalty": base_config["penalty"],
            "permutation_seq": base_config["permutation_seq"],
            "days": base_config["days"],
            "reps": base_config["reps"],
            "seed": base_config["base_seed"] + i * 1000 + 50000,
            "output_dir": str(ba_dir)
        }
        
        ba_log = logs_dir / f"ba_eps_{epsilon}.log"
        ba_success = run_driver("BA", ba_args, str(ba_dir), str(ba_log))
        
        if not ba_success:
            print(f"  ERROR: BA simulation failed for epsilon={epsilon}")
            continue
        
        # Compute delta analysis for this epsilon
        try:
            delta_stats = compute_delta_csv(
                str(mba_dir),
                str(ba_dir), 
                str(eps_dir / "delta.csv"),
                None,  # No individual plots
                window_last_days=100  # Shorter window for shorter runs
            )
            
            # Store results
            epsilon_result = {
                "epsilon": epsilon,
                "mba_args": mba_args,
                "ba_args": ba_args,
                "delta_stats": delta_stats,
                "mba_log": str(mba_log),
                "ba_log": str(ba_log),
                "success": True
            }
            epsilon_results.append(epsilon_result)
            manifest["runs"].append(epsilon_result)
            
            print(f"  Epsilon {epsilon}: Delta = {delta_stats['delta_final_mean']:.4f}")
            
        except Exception as e:
            print(f"  ERROR: Delta analysis failed for epsilon={epsilon} - {e}")
            epsilon_results.append({
                "epsilon": epsilon,
                "success": False,
                "error": str(e)
            })
    
    # Create summary analysis
    print("\nCreating summary analysis...")
    
    successful_results = [r for r in epsilon_results if r.get("success", False)]
    if not successful_results:
        print("ERROR: No successful epsilon runs to analyze")
        return False
    
    # Create grid summary
    summary_data = []
    for result in successful_results:
        eps = result["epsilon"]
        stats = result["delta_stats"]
        summary_data.append({
            "epsilon": eps,
            "delta_mean": stats["delta_mean"],
            "delta_final_mean": stats["delta_final_mean"],
            "delta_std": stats["delta_std"],
            "proportion_positive": stats["proportion_positive"],
            "proportion_final_positive": stats["proportion_final_positive"]
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(base_dir / "grid_summary.csv", index=False)
    
    print("Summary results:")
    for _, row in summary_df.iterrows():
        print(f"  ε={row['epsilon']:3.1f}: Δ={row['delta_final_mean']:6.3f}, P(Δ>0)={row['proportion_final_positive']:.2f}")
    
    # Create summary plots
    try:
        import matplotlib.pyplot as plt
        
        # Delta vs epsilon plot
        plt.figure(figsize=(10, 6))
        plt.plot(summary_df['epsilon'], summary_df['delta_final_mean'], 'bo-', linewidth=2, markersize=8)
        plt.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        plt.xlabel('Environmental Noise (ε)')
        plt.ylabel('Final Delta Fitness (MBA - BA)')
        plt.title('MBA Advantage vs Environmental Noise')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "epsilon_sweep.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        # Proportion positive plot
        plt.figure(figsize=(10, 6))
        plt.plot(summary_df['epsilon'], summary_df['proportion_final_positive'], 'ro-', linewidth=2, markersize=8)
        plt.axhline(y=0.5, color='k', linestyle='--', alpha=0.5, label='50% threshold')
        plt.xlabel('Environmental Noise (ε)')
        plt.ylabel('Proportion Delta > 0')
        plt.title('MBA Success Rate vs Environmental Noise')
        plt.ylim(0, 1)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "success_rate_sweep.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Summary plots saved to: {plots_dir}")
        
    except ImportError:
        print("Warning: matplotlib not available, skipping summary plots")
    except Exception as e:
        print(f"Warning: Error creating summary plots - {e}")
    
    # Validate sanity gates
    print("\nValidating sanity gates...")
    
    # Check that delta decreases with epsilon (at least monotonic trend)
    delta_values = summary_df['delta_final_mean'].values
    epsilon_values = summary_df['epsilon'].values
    
    # Check if MBA advantage decreases with noise
    low_noise_delta = summary_df[summary_df['epsilon'] == summary_df['epsilon'].min()]['delta_final_mean'].iloc[0]  # Use min (0.01)
    high_noise_delta = summary_df[summary_df['epsilon'] == summary_df['epsilon'].max()]['delta_final_mean'].iloc[0]
    
    monotonic_decrease = low_noise_delta > high_noise_delta
    zero_epsilon_positive = low_noise_delta > 0.05  # Should have clear advantage at low noise
    
    sanity_gates = {
        "monotonic_decrease": monotonic_decrease,
        "zero_epsilon_positive": zero_epsilon_positive,
        "all_runs_successful": len(successful_results) == len(base_config["epsilon_values"])
    }
    
    gates_passed = all(sanity_gates.values())
    
    print(f"Monotonic decrease: {'PASS' if monotonic_decrease else 'FAIL'}")
    print(f"Zero epsilon positive: {'PASS' if zero_epsilon_positive else 'FAIL'} (Δ={low_noise_delta:.3f})")
    print(f"All runs successful: {'PASS' if sanity_gates['all_runs_successful'] else 'FAIL'}")
    
    # Add results to manifest
    manifest["summary"] = {
        "grid_summary_file": str(base_dir / "grid_summary.csv"),
        "successful_runs": len(successful_results),
        "total_runs": len(base_config["epsilon_values"]),
        "sanity_gates": sanity_gates,
        "gates_passed": gates_passed
    }
    
    # Save manifest
    safe_write_json(manifest_path, manifest)
    
    print(f"\nSTRESS TEST COMPLETE!")
    print(f"Results saved to: {base_dir}")
    print(f"Successful runs: {len(successful_results)}/{len(base_config['epsilon_values'])}")
    print(f"Sanity gates: {'PASSED' if gates_passed else 'FAILED'}")
    
    return gates_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
