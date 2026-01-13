import os
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import argparse

def load_experiment_data(data_folder):
    """
    Loads experiment data from a folder of JSON files.
    Reconstructs time series for each cycle.
    Returns cycles and metadata.
    """
    print(f"Loading data from: {data_folder}")
    
    # Try to read metadata
    meta_path = os.path.join(data_folder, 'meta.json')
    metadata = {'experiment_id': os.path.basename(os.path.normpath(data_folder)), 'correlation': 'unknown'}
    
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
                metadata['experiment_id'] = meta.get('experiment_id', metadata['experiment_id'])
                params = meta.get('parameters', {})
                metadata['correlation'] = params.get('correlation', 'unknown')
        except Exception as e:
            print(f"Error reading meta.json: {e}")
    
    # Find all cycle snapshot files (exclude summaries and meta/manifest)
    # Pattern: cycle_{num}_{timestamp}.json
    # We need to be careful not to pick up cycle_{num}_summary.json
    files = glob.glob(os.path.join(data_folder, "cycle_*.json"))
    snapshot_files = [f for f in files if "_summary.json" not in f]
    
    if not snapshot_files:
        print("No cycle data files found.")
        return [], metadata

    data_records = []
    
    print(f"Found {len(snapshot_files)} snapshot files. Parsing...")
    
    for file_path in snapshot_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                data_records.append(data)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
            
    if not data_records:
        print("No valid data records found.")
        return [], metadata

    # Convert to DataFrame
    df = pd.DataFrame(data_records)
    
    # Ensure numeric types
    numeric_cols = ['cycle_num', 'elapsed_seconds', 'temp', 'set_temp', 'us_active', 'cycle_length_seconds']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Sort by cycle and time
    df = df.sort_values(by=['cycle_num', 'elapsed_seconds'])
    
    # Group by cycle
    cycles = []
    for cycle_num, group in df.groupby('cycle_num'):
        cycles.append(group.copy())
        
    # If correlation is still unknown, try to get it from the first cycle data
    if metadata['correlation'] == 'unknown' and cycles:
        if 'correlation' in cycles[0].columns:
             metadata['correlation'] = cycles[0]['correlation'].iloc[0]
        
    print(f"Reconstructed {len(cycles)} cycles.")
    return cycles, metadata

def process_cycles(cycles):
    """
    Aligns cycles such that t=0 is the START of the Heat Shock.
    Removes the first 10 minutes (cool down).
    Calculates the gap between Heat Shock Start and US End.
    """
    aligned_cycles = []
    cycle_lengths = []
    us_hs_gaps = []
    
    for cycle in cycles:
        # 1. Cut the first 10 minutes (600 seconds) - Cool down phase
        # We do this before processing to ensure we don't plot it
        # However, we must ensure we don't lose the HS start if it's early (unlikely)
        cycle_cut = cycle[cycle['elapsed_seconds'] >= 600].copy()
        
        if cycle_cut.empty:
            continue
            
        # Find Heat Shock Start Time (using the cut data)
        # We look for the transition where set_temp rises significantly (> 28)
        hs_start_data = cycle_cut[cycle_cut['set_temp'] > 28]
        
        if hs_start_data.empty:
            print(f"Cycle {cycle['cycle_num'].iloc[0]} has no Heat Shock (temp rise) after 10 mins. Skipping.")
            continue
            
        # The start of HS is the first timestamp where set_temp is high
        hs_start_time = hs_start_data['elapsed_seconds'].min()
        
        # Calculate US-HS Gap
        # We look for US activity in the whole cycle (or cut cycle? Let's use cut to be consistent)
        us_active_data = cycle_cut[cycle_cut['us_active'] == 1]
        if not us_active_data.empty:
            # End of US
            us_end_time = us_active_data['elapsed_seconds'].max()
            # Gap = Start of HS - End of US
            # Positive means US ended BEFORE HS started (Gap)
            # Negative means US ended AFTER HS started (Overlap)
            gap_seconds = hs_start_time - us_end_time
            us_hs_gaps.append(gap_seconds / 60.0) # Minutes
        
        # Calculate aligned time
        # t=0 will be the start of the heat shock
        cycle_cut['aligned_time'] = cycle_cut['elapsed_seconds'] - hs_start_time
        
        # Clip data: 
        # Keep data before HS (Basal phase) AND during HS (30 mins)
        hs_duration = 1800 # 30 minutes in seconds
        clipped_cycle = cycle_cut[cycle_cut['aligned_time'] <= hs_duration].copy()
        
        if not clipped_cycle.empty:
            aligned_cycles.append(clipped_cycle)
            
            # Calculate total length of the original cycle for the boxplot
            if 'cycle_length_seconds' in cycle.columns and not pd.isna(cycle['cycle_length_seconds'].iloc[0]):
                length = cycle['cycle_length_seconds'].iloc[0]
            else:
                length = cycle['elapsed_seconds'].max()
            cycle_lengths.append(length / 60.0) # Convert to minutes
            
    return aligned_cycles, cycle_lengths, us_hs_gaps

def plot_analysis(aligned_cycles, cycle_lengths, us_hs_gaps, metadata=None):
    """
    Plots the aligned temperature traces, US status, and statistics.
    """
    if not aligned_cycles:
        print("No cycles to plot.")
        return

    # Setup plot with GridSpec
    # Main plot on left (spans 2 rows), Boxplot top right, Histogram bottom right
    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(2, 2, width_ratios=[3, 1], height_ratios=[1, 1])
    
    # Left column: Split into Temp (Top) and US (Bottom)
    gs_left = gs[:, 0].subgridspec(2, 1, height_ratios=[4, 1], hspace=0.05)
    ax1 = fig.add_subplot(gs_left[0]) # Temp Plot
    ax_us = fig.add_subplot(gs_left[1], sharex=ax1) # US Plot
    
    ax_box = fig.add_subplot(gs[0, 1]) # Top Right
    ax_hist = fig.add_subplot(gs[1, 1]) # Bottom Right
    
    # Color palette
    temp_color = 'tab:blue'
    us_color = 'tab:orange'
    
    # --- Main Plot ---
    print("Plotting cycles...")
    
    # Find global min/max aligned time
    min_time = min([c['aligned_time'].min() for c in aligned_cycles])
    max_time = max([c['aligned_time'].max() for c in aligned_cycles])
    
    # Plot individual cycles
    for i, cycle in enumerate(aligned_cycles):
        # Plot Temperature on Top Left (ax1)
        label = 'Individual Cycles' if i == 0 else None
        ax1.plot(cycle['aligned_time'], cycle['temp'], color=temp_color, alpha=0.2, linewidth=1, label=label)
        
        # Plot US Active on Bottom Left (ax_us)
        # Use steps-post for digital signal
        label_us = 'US Active' if i == 0 else None
        ax_us.plot(cycle['aligned_time'], cycle['us_active'], color=us_color, alpha=0.5, linewidth=2.5, drawstyle='steps-post', label=label_us)

    # Plot Mean Temperature Trace
    all_times = np.linspace(min_time, max_time, 1000)
    interp_temps = []
    for cycle in aligned_cycles:
        cycle_dedup = cycle.drop_duplicates(subset='aligned_time')
        if len(cycle_dedup) > 1:
            y_interp = np.interp(all_times, cycle_dedup['aligned_time'], cycle_dedup['temp'])
            interp_temps.append(y_interp)
    
    if interp_temps:
        mean_temp = np.mean(interp_temps, axis=0)
        ax1.plot(all_times, mean_temp, color='navy', linewidth=2, label='Mean Temp')
        
    # Formatting Main Axes (Temp)
    ax1.set_ylabel('Temperature (°C)', color=temp_color, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=temp_color)
    ax1.set_ylim(19, 33)
    ax1.grid(True, alpha=0.3)
    plt.setp(ax1.get_xticklabels(), visible=False) # Hide x labels for top plot
    
    # Formatting US Axes
    ax_us.set_xlabel('Time relative to Heat Shock Start (seconds)')
    ax_us.set_ylabel('US Active', color=us_color, fontsize=10)
    ax_us.tick_params(axis='y', labelcolor=us_color)
    ax_us.set_ylim(-0.1, 1.1)
    ax_us.set_yticks([0, 1])
    ax_us.set_yticklabels(['Off', 'On'])
    ax_us.grid(True, alpha=0.3)
    
    ax1.set_xlim(-15000, max_time)
    
    # Title with metadata
    title = 'Post-Run Analysis: Approach and Heat Shock (First 10m cut)'
    if metadata:
        exp_id = metadata.get('experiment_id', 'Unknown')
        corr = metadata.get('correlation', 'Unknown')
        title += f"\nExp: {exp_id} | Corr: {corr}"
    ax1.set_title(title, fontsize=14)
    
    # Add vertical line at t=0
    ax1.axvline(x=0, color='red', linestyle='--', alpha=0.5, label='Heat Shock Start')
    ax_us.axvline(x=0, color='red', linestyle='--', alpha=0.5)
    
    # Legends
    ax1.legend(loc='upper left')
    # ax_us.legend(loc='upper left') # Optional for US
    
    # --- Box Plot (Top Right) ---
    ax_box.boxplot(cycle_lengths, patch_artist=True, 
                     boxprops=dict(facecolor='lightgray', color='black'),
                     medianprops=dict(color='red'))
    ax_box.set_title('Cycle Length Distribution')
    ax_box.set_ylabel('Minutes')
    ax_box.set_xticklabels([''])
    ax_box.grid(True, axis='y', alpha=0.5)
    
    # --- Histogram (Bottom Right) ---
    if us_hs_gaps:
        ax_hist.hist(us_hs_gaps, bins=15, color='purple', alpha=0.7, edgecolor='black')
        ax_hist.set_title('Gap: HS Start - US End')
        ax_hist.set_xlabel('Minutes (Positive = Gap, Negative = Overlap)')
        ax_hist.set_ylabel('Count')
        ax_hist.grid(True, alpha=0.3)
        # Add vertical line at 0
        ax_hist.axvline(x=0, color='black', linestyle='--', alpha=0.5)
        
        # Set support (x-axis) centered at 0, range +/- max_cycle_length / 2
        if cycle_lengths:
            max_cycle = max(cycle_lengths)
            limit = max_cycle / 2.0
            
            # Ensure we cover the actual data if it falls outside (robustness)
            if us_hs_gaps:
                max_data_abs = max([abs(g) for g in us_hs_gaps])
                limit = max(limit, max_data_abs * 1.1)
            
            ax_hist.set_xlim(-limit, limit)
    else:
        ax_hist.text(0.5, 0.5, "No US Data", ha='center', va='center')
    
    plt.tight_layout()
    
    # Save and Show
    exp_id = metadata.get('experiment_id', 'experiment') if metadata else 'experiment'
    corr = metadata.get('correlation', 'NA') if metadata else 'NA'
    # Sanitize filename
    exp_id = "".join([c for c in str(exp_id) if c.isalnum() or c in (' ', '.', '_')]).strip()
    corr = "".join([c for c in str(corr) if c.isalnum() or c in (' ', '.', '_')]).strip()
    
    output_file = f'post_run_analysis_{exp_id}_corr{corr}.png'
    plt.savefig(output_file, dpi=300)
    print(f"Plot saved to {output_file}")
    plt.show()

def main():
    # Default path or argument
    default_path = r"I:\data\20000101_000006_0"
    
    parser = argparse.ArgumentParser(description='Smart Incubator Post-Run Analysis')
    parser.add_argument('data_folder', nargs='?', default=default_path, help='Path to the experiment data folder')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_folder):
        print(f"Error: Data folder not found: {args.data_folder}")
        print("Please provide a valid path or ensure the default path exists.")
        return

    cycles, metadata = load_experiment_data(args.data_folder)
    if cycles:
        aligned_cycles, lengths, gaps = process_cycles(cycles)
        plot_analysis(aligned_cycles, lengths, gaps, metadata)

if __name__ == "__main__":
    main()
