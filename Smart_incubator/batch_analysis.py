import os
import sys
import glob
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# Add the current directory to path so we can import post_run_analysis
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import post_run_analysis

def get_experiment_duration(folder_path):
    files = glob.glob(os.path.join(folder_path, "cycle_*.json"))
    snapshot_files = [f for f in files if "_summary.json" not in f]
    
    timestamps = []
    for f in snapshot_files:
        # filename: cycle_{num}_{timestamp}.json
        basename = os.path.basename(f)
        try:
            parts = basename.replace('.json', '').split('_')
            # parts should be ['cycle', 'num', 'timestamp']
            if len(parts) >= 3:
                ts = int(parts[-1])
                timestamps.append(ts)
        except ValueError:
            continue
            
    if not timestamps:
        return 0
        
    min_ts = min(timestamps)
    max_ts = max(timestamps)
    
    duration_seconds = max_ts - min_ts
    return duration_seconds / 3600.0 # Return in hours

def analyze_folder(folder_path):
    print(f"Analyzing {folder_path}...")
    cycles, metadata = post_run_analysis.load_experiment_data(folder_path)
    
    if not cycles:
        print(f"No cycles found in {folder_path}")
        return None

    aligned_cycles, lengths, gaps = post_run_analysis.process_cycles(cycles)
    
    # Calculate duration
    total_duration_h = get_experiment_duration(folder_path)
    
    # Generate Plot (and save it, suppress show)
    # We need to handle the fact that plot_analysis calls plt.show()
    original_show = plt.show
    plt.show = lambda: None # Suppress show
    try:
        # We also want to control the output filename to be in the current directory or specific place
        # The script saves to current working directory.
        post_run_analysis.plot_analysis(aligned_cycles, lengths, gaps, metadata)
    finally:
        plt.show = original_show
        plt.close('all') # Close figures to free memory

    # Calculate Statistics
    num_cycles = len(aligned_cycles)
    
    avg_length = np.mean(lengths) if lengths else 0
    std_length = np.std(lengths) if lengths else 0
    
    avg_gap = np.mean(gaps) if gaps else 0
    std_gap = np.std(gaps) if gaps else 0
    
    return {
        'folder': os.path.basename(folder_path),
        'correlation': metadata.get('correlation', 'Unknown'),
        'experiment_id': metadata.get('experiment_id', 'Unknown'),
        'num_cycles': num_cycles,
        'avg_length_min': avg_length,
        'std_length_min': std_length,
        'avg_gap_min': avg_gap, # HS Start - US End
        'std_gap_min': std_gap,
        'gaps': gaps,
        'total_duration_h': total_duration_h
    }

def generate_markdown_summary(results, output_file="experiment_summary.md"):
    with open(output_file, 'w') as f:
        f.write("# Experiment Summary\n\n")
        f.write(f"Date: {pd.Timestamp.now()}\n\n")
        
        f.write("## Overview\n")
        f.write("| Experiment ID | Correlation | Cycles | Avg Length (min) | Avg HS-US Gap (min) | Total Duration (h) |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for res in results:
            if res:
                f.write(f"| {res['experiment_id']} | {res['correlation']} | {res['num_cycles']} | {res['avg_length_min']:.2f} +/- {res['std_length_min']:.2f} | {res['avg_gap_min']:.2f} +/- {res['std_gap_min']:.2f} | {res['total_duration_h']:.2f} |\n")
        
        f.write("\n## Detailed Analysis\n")
        
        for res in results:
            if not res:
                continue
                
            f.write(f"### Experiment: {res['experiment_id']} (Corr: {res['correlation']})\n")
            f.write(f"- **Folder**: `{res['folder']}`\n")
            f.write(f"- **Total Cycles**: {res['num_cycles']}\n")
            f.write(f"- **Total Duration**: {res['total_duration_h']:.2f} hours\n")
            f.write(f"- **Cycle Length**: {res['avg_length_min']:.2f} +/- {res['std_length_min']:.2f} minutes\n")
            f.write(f"- **HS-US Gap**: {res['avg_gap_min']:.2f} +/- {res['std_gap_min']:.2f} minutes\n")
            f.write("  - *Note: Positive Gap means US ended BEFORE HS started. Negative means Overlap.*\n")
            
            if res['gaps']:
                f.write(f"  - Min Gap: {min(res['gaps']):.2f} min\n")
                f.write(f"  - Max Gap: {max(res['gaps']):.2f} min\n")
            
            f.write("\n")

    print(f"Summary written to {output_file}")

def main():
    base_path = r"C:\Users\maork\Documents\Papers\Cond smart incubators\Pilot 10_11_25\SD_card_data"
    folders = [
        os.path.join(base_path, "20000101_000006_0"),
        os.path.join(base_path, "20000101_000007_1")
    ]
    
    results = []
    for folder in folders:
        if os.path.exists(folder):
            res = analyze_folder(folder)
            results.append(res)
        else:
            print(f"Folder not found: {folder}")
            
    generate_markdown_summary(results)

if __name__ == "__main__":
    main()
