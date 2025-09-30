"""Common utilities for experiment wrappers.

This module provides shared functionality for orchestrating MBA vs BA experiments,
including driver invocation, manifest management, CSV aggregation, and delta analysis.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib

def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists, creating if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def safe_write_json(path: Union[str, Path], obj: Dict[str, Any]) -> None:
    """Safely write JSON object to file, converting numpy types to native Python."""
    def _to_python(o):
        try:
            import numpy as _np
            if isinstance(o, (_np.bool_,)):
                return bool(o)
            if isinstance(o, (_np.integer,)):
                return int(o)
            if isinstance(o, (_np.floating,)):
                return float(o)
            if isinstance(o, (_np.ndarray,)):
                return o.tolist()
        except Exception:
            pass
        # Fallback: cast to string to avoid serialization errors
        return str(o)
    path = Path(path)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2, default=_to_python)

def run_driver(kind: str, args: Dict[str, Any], outdir: str, log: str) -> bool:
    """Run unified driver with specified arguments and capture output.
    
    Args:
        kind: "MBA" or "BA" for identification
        args: Dictionary of CLI arguments
        outdir: Output directory 
        log: Path to log file
        
    Returns:
        True if successful, False otherwise
    """
    # Build command
    cmd = [sys.executable, "unified_driver.py"]
    
    for key, value in args.items():
        if value is None:
            continue
        if isinstance(value, bool):
            if value:
                cmd.append(f"--{key}")
        else:
            cmd.extend([f"--{key}", str(value)])
    
    print(f"Running {kind}: {' '.join(cmd)}")
    
    try:
        # Run command and capture output
        # Handle path correctly when running from wrappers directory
        parent_dir = Path(__file__).parent.parent  # Go up from wrappers to MBA vs BA sim
        
        with open(log, 'w') as f:
            result = subprocess.run(
                cmd, 
                cwd=str(parent_dir),
                stdout=f, 
                stderr=subprocess.STDOUT,
                timeout=3600  # 1 hour timeout
            )
        
        success = result.returncode == 0
        print(f"  {kind}: {'SUCCESS' if success else 'FAILED'} (exit code: {result.returncode})")
        return success
        
    except subprocess.TimeoutExpired:
        print(f"  {kind}: TIMEOUT after 1 hour")
        return False
    except Exception as e:
        print(f"  {kind}: ERROR - {e}")
        return False

def list_csvs(outdir: str) -> List[str]:
    """Discover CSV files in output directory."""
    outdir = Path(outdir)
    # Handle both absolute and relative paths
    if not outdir.is_absolute():
        # If relative, resolve from parent directory (where unified_driver.py runs)
        parent_dir = Path(__file__).parent.parent
        outdir = parent_dir / outdir
    
    csv_files = [str(f) for f in outdir.glob("*.csv")]
    print(f"  Found {len(csv_files)} CSV files in {outdir}")
    return csv_files

def append_manifest(manifest_path: str, record: Dict[str, Any]) -> None:
    """Append record to manifest file."""
    manifest_path = Path(manifest_path)
    
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    else:
        manifest = {
            "wrapper_name": "unknown",
            "created_at": datetime.now().isoformat(),
            "driver_version": "unified_driver.py",
            "runs": []
        }
    
    manifest["runs"].append(record)
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

def compute_delta_csv(
    mba_dir: str, 
    ba_dir: str, 
    out_csv: str, 
    out_plots_dir: Optional[str] = None,
    window_last_days: int = 200
) -> Dict[str, float]:
    """Compute delta (MBA - BA) fitness analysis from CSV files.
    
    Args:
        mba_dir: Directory containing MBA CSV files
        ba_dir: Directory containing BA CSV files  
        out_csv: Output path for delta CSV
        out_plots_dir: Optional directory for plots
        window_last_days: Window for computing final metrics
        
    Returns:
        Dictionary with delta statistics
    """
    # Load MBA data
    mba_csvs = list_csvs(mba_dir)
    if not mba_csvs:
        raise ValueError(f"No CSV files found in MBA directory: {mba_dir}")
    
    mba_data = []
    for csv_file in mba_csvs:
        df = pd.read_csv(csv_file)
        mba_data.append(df)
    mba_df = pd.concat(mba_data, ignore_index=True)
    
    # Load BA data
    ba_csvs = list_csvs(ba_dir)
    if not ba_csvs:
        raise ValueError(f"No CSV files found in BA directory: {ba_dir}")
    
    ba_data = []
    for csv_file in ba_csvs:
        df = pd.read_csv(csv_file)
        ba_data.append(df)
    ba_df = pd.concat(ba_data, ignore_index=True)
    
    # Compute daily mean fitness by agent type
    mba_daily = mba_df.groupby(['rep_id', 'day'])['daily_fitness'].mean().reset_index()
    ba_daily = ba_df.groupby(['rep_id', 'day'])['daily_fitness'].mean().reset_index()
    
    # Compute delta fitness per replication and day
    delta_data = []
    
    # Get common reps and days
    mba_keys = set((r, d) for r, d in zip(mba_daily['rep_id'], mba_daily['day']))
    ba_keys = set((r, d) for r, d in zip(ba_daily['rep_id'], ba_daily['day']))
    common_keys = mba_keys.intersection(ba_keys)
    
    for rep_id, day in common_keys:
        mba_fitness = mba_daily[(mba_daily['rep_id'] == rep_id) & (mba_daily['day'] == day)]['daily_fitness'].iloc[0]
        ba_fitness = ba_daily[(ba_daily['rep_id'] == rep_id) & (ba_daily['day'] == day)]['daily_fitness'].iloc[0]
        
        delta_data.append({
            'rep_id': rep_id,
            'day': day,
            'mba_fitness': mba_fitness,
            'ba_fitness': ba_fitness,
            'delta_fitness': mba_fitness - ba_fitness
        })
    
    delta_df = pd.DataFrame(delta_data)
    
    # Save delta CSV
    delta_df.to_csv(out_csv, index=False)
    print(f"Delta analysis saved to: {out_csv}")
    
    # Compute statistics
    max_day = delta_df['day'].max()
    window_start = max(0, max_day - window_last_days + 1)
    final_window = delta_df[delta_df['day'] >= window_start]
    
    stats = {
        'delta_mean': delta_df['delta_fitness'].mean(),
        'delta_std': delta_df['delta_fitness'].std(),
        'delta_final_mean': final_window['delta_fitness'].mean(),
        'delta_final_std': final_window['delta_fitness'].std(),
        'proportion_positive': (delta_df['delta_fitness'] > 0).mean(),
        'proportion_final_positive': (final_window['delta_fitness'] > 0).mean(),
        'max_day': int(max_day),
        'total_comparisons': len(delta_df)
    }
    
    # Optional plotting
    if out_plots_dir:
        try:
            import matplotlib.pyplot as plt
            ensure_dir(out_plots_dir)
            
            # Time series plot
            plt.figure(figsize=(12, 6))
            
            # Plot delta over time (mean across reps)
            daily_delta = delta_df.groupby('day')['delta_fitness'].agg(['mean', 'std']).reset_index()
            plt.plot(daily_delta['day'], daily_delta['mean'], 'b-', label='Delta (MBA - BA)')
            plt.fill_between(daily_delta['day'], 
                           daily_delta['mean'] - daily_delta['std'],
                           daily_delta['mean'] + daily_delta['std'],
                           alpha=0.3)
            plt.axhline(y=0, color='k', linestyle='--', alpha=0.5)
            plt.xlabel('Day')
            plt.ylabel('Fitness Advantage (MBA - BA)')
            plt.title('MBA Fitness Advantage Over Time')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(Path(out_plots_dir) / 'delta_timeseries.png', dpi=150, bbox_inches='tight')
            plt.close()
            
            # Distribution plot
            plt.figure(figsize=(8, 6))
            plt.hist(final_window['delta_fitness'], bins=50, alpha=0.7, edgecolor='black')
            plt.axvline(stats['delta_final_mean'], color='red', linestyle='-', 
                       label=f"Mean = {stats['delta_final_mean']:.3f}")
            plt.axvline(0, color='black', linestyle='--', alpha=0.5)
            plt.xlabel('Delta Fitness (MBA - BA)')
            plt.ylabel('Frequency')
            plt.title(f'Final {window_last_days} Days Delta Distribution')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(Path(out_plots_dir) / 'delta_distribution.png', dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"Plots saved to: {out_plots_dir}")
            
        except ImportError:
            print("Warning: matplotlib not available, skipping plots")
        except Exception as e:
            print(f"Warning: Error creating plots - {e}")
    
    return stats

def create_base_manifest(wrapper_name: str, common_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create base manifest structure."""
    return {
        "wrapper_name": wrapper_name,
        "created_at": datetime.now().isoformat(),
        "driver_version": "unified_driver.py", 
        "common": common_config,
        "runs": []
    }

def get_permutation_hash(permutation_seq: str) -> str:
    """Get consistent hash for permutation sequence."""
    return hashlib.md5(permutation_seq.encode()).hexdigest()[:8]

def derive_seed(base_seed: int, rep_id: int) -> int:
    """Derive deterministic seed for replication."""
    return base_seed + rep_id * 10000

def load_json_params(params_file: str) -> Dict[str, Any]:
    """Load parameters from JSON file."""
    with open(params_file, 'r') as f:
        return json.load(f)

def validate_sanity_gates(stats: Dict[str, float], gates: Dict[str, float]) -> bool:
    """Validate results against sanity gates."""
    for metric, threshold in gates.items():
        if metric not in stats:
            print(f"Warning: Missing metric {metric} in results")
            continue
            
        value = stats[metric]
        if metric.startswith('min_'):
            passed = value >= threshold
            op = ">="
        elif metric.startswith('max_'):
            passed = value <= threshold  
            op = "<="
        else:
            passed = value >= threshold  # Default to minimum threshold
            op = ">="
        
        print(f"Sanity check: {metric} = {value:.4f} {op} {threshold:.4f} - {'PASS' if passed else 'FAIL'}")
        if not passed:
            return False
    
    return True
