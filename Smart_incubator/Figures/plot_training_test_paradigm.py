import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def _make_time_series(duration_min, dt_min=0.1):
    """Return time vector in minutes."""
    t = np.arange(0, duration_min + dt_min, dt_min)
    return t

def plot_paradigm():
    # --- Configuration ---
    duration_train_min = 300
    duration_test_min = 180
    
    basal_temp = 23.0
    heat_shock_temp = 32.0
    challenge_temp = 38.0
    
    # Colors (Modern Scientific Palette)
    col_temp_line = '#2c3e50'   # Dark Slate
    col_heat_fill = '#e74c3c'   # Alizarin Red
    col_lethal_fill = '#c0392b' # Darker Red
    col_cue_fill = '#f1c40f'    # Sunflower Yellow
    col_cue_text = '#d35400'    # Pumpkin
    col_bg = '#ffffff'          # White
    
    # Setup Figure
    # Try to use a clean style, fallback to default
    available_styles = plt.style.available
    if 'seaborn-v0_8-whitegrid' in available_styles:
        plt.style.use('seaborn-v0_8-whitegrid')
    elif 'seaborn-whitegrid' in available_styles:
        plt.style.use('seaborn-whitegrid')
    else:
        plt.style.use('default')
        plt.rcParams['grid.alpha'] = 0.3

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), constrained_layout=True)
    
    # Global Font Settings for "Poster/Talk" quality
    plt.rcParams.update({
        'font.size': 12,
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'font.family': 'sans-serif'
    })

    # ==========================================
    # Panel 1: Predictable Environment (Training)
    # ==========================================
    ax = axes[0]
    t = _make_time_series(duration_train_min)
    
    # Define Events
    # Cycle: Wait -> Cue (30m) -> Heat (30m) -> Recovery
    # Centered for visual balance
    cue_start = 120
    cue_dur = 30
    heat_start = 150
    heat_dur = 30
    ramp_dur = 10
    
    # Temperature Profile
    temp = np.full_like(t, basal_temp)
    
    # Heat Ramp Up
    ramp_mask = (t >= heat_start) & (t < heat_start + ramp_dur)
    temp[ramp_mask] = np.linspace(basal_temp, heat_shock_temp, np.sum(ramp_mask))
    
    # Heat Plateau
    plateau_mask = (t >= heat_start + ramp_dur) & (t < heat_start + heat_dur)
    temp[plateau_mask] = heat_shock_temp
    
    # Recovery (Ramp Down)
    rec_start = heat_start + heat_dur
    rec_dur = 10
    rec_mask = (t >= rec_start) & (t < rec_start + rec_dur)
    temp[rec_mask] = np.linspace(heat_shock_temp, basal_temp, np.sum(rec_mask))
    
    # Plotting
    # 1. Cue Region
    ax.axvspan(cue_start, cue_start + cue_dur, ymin=0, ymax=1, color=col_cue_fill, alpha=0.3, lw=0)
    ax.text(cue_start + cue_dur/2, 36, "Predictive Cue\n(LED + Vib)", 
            ha='center', va='center', color=col_cue_text, fontweight='bold')
    
    # 2. Temperature Line & Fill
    ax.plot(t, temp, color=col_temp_line, linewidth=3, label='Temperature')
    ax.fill_between(t, temp, basal_temp, where=(temp > basal_temp), 
                    color=col_heat_fill, alpha=0.2, interpolate=True)
    
    # 3. Annotations
    ax.set_title("A. Predictable Environment (Training Phase)", loc='left', fontweight='bold')
    ax.set_ylabel("Temperature (°C)")
    ax.set_ylim(20, 40)
    ax.set_xlim(0, 300)
    
    # Arrow indicating prediction
    ax.annotate("", 
                xy=(heat_start + 5, 34), xycoords='data',
                xytext=(cue_start + cue_dur - 5, 34), textcoords='data',
                arrowprops=dict(arrowstyle="->", color='black', lw=2, connectionstyle="arc3,rad=-0.2"))
    # Text removed as requested
    
    ax.text(heat_start + heat_dur/2, heat_shock_temp + 1, "Heat Stress\n(32°C)", 
            ha='center', color=col_heat_fill, fontweight='bold')

    # ==========================================
    # Panel 2: Random Environment (Control)
    # ==========================================
    ax = axes[1]
    
    # Events separated
    led_start_2 = 50
    led_dur_2 = 15
    vib_start_2 = 90
    vib_dur_2 = 15
    heat_start_2 = 200
    
    temp2 = np.full_like(t, basal_temp)
    
    # Heat Ramp Up
    ramp_mask2 = (t >= heat_start_2) & (t < heat_start_2 + ramp_dur)
    temp2[ramp_mask2] = np.linspace(basal_temp, heat_shock_temp, np.sum(ramp_mask2))
    
    # Heat Plateau
    plateau_mask2 = (t >= heat_start_2 + ramp_dur) & (t < heat_start_2 + heat_dur)
    temp2[plateau_mask2] = heat_shock_temp
    
    # Recovery
    rec_start2 = heat_start_2 + heat_dur
    rec_mask2 = (t >= rec_start2) & (t < rec_start2 + rec_dur)
    temp2[rec_mask2] = np.linspace(heat_shock_temp, basal_temp, np.sum(rec_mask2))
    
    # Plotting
    # LED Block
    ax.axvspan(led_start_2, led_start_2 + led_dur_2, ymin=0, ymax=1, color=col_cue_fill, alpha=0.3, lw=0)
    ax.text(led_start_2 + led_dur_2/2, 36, "Random\nLED", 
            ha='center', va='center', color=col_cue_text, fontweight='bold', fontsize=10)

    # Vib Block
    ax.axvspan(vib_start_2, vib_start_2 + vib_dur_2, ymin=0, ymax=1, color=col_cue_fill, alpha=0.3, lw=0)
    ax.text(vib_start_2 + vib_dur_2/2, 36, "Random\nVib", 
            ha='center', va='center', color=col_cue_text, fontweight='bold', fontsize=10)
            
    ax.plot(t, temp2, color=col_temp_line, linewidth=3)
    ax.fill_between(t, temp2, basal_temp, where=(temp2 > basal_temp), 
                    color=col_heat_fill, alpha=0.2, interpolate=True)
    
    ax.set_title("B. Random Environment (Control Group)", loc='left', fontweight='bold')
    ax.set_ylabel("Temperature (°C)")
    ax.set_ylim(20, 40)
    ax.set_xlim(0, 300)
    
    ax.text(heat_start_2 + heat_dur/2, heat_shock_temp + 1, "Heat Stress\n(32°C)", 
            ha='center', color=col_heat_fill, fontweight='bold')
            
    # Annotation for no correlation
    ax.text(150, 28, "No Correlation / Unpaired", ha='center', fontsize=14, color='gray', alpha=0.6, fontweight='bold')

    # ==========================================
    # Panel 3: Survival Test
    # ==========================================
    ax = axes[2]
    t3 = _make_time_series(duration_test_min)
    
    # Sequence: Cue (30m) -> Ramp to Lethal (38C)
    cue_dur_test = 30
    ramp_test_dur = 20
    ramp_start_3 = 30
    ramp_end_3 = ramp_start_3 + ramp_test_dur
    
    temp3 = np.full_like(t3, basal_temp)
    
    # Ramp
    ramp_mask3 = (t3 >= ramp_start_3) & (t3 < ramp_end_3)
    temp3[ramp_mask3] = np.linspace(basal_temp, challenge_temp, np.sum(ramp_mask3))
    
    # Plateau (Lethal)
    temp3[t3 >= ramp_end_3] = challenge_temp
    
    # Plotting
    # Increased alpha for intensity
    ax.axvspan(0, 30, ymin=0, ymax=1, color=col_cue_fill, alpha=0.7, lw=0)
    ax.text(15, 39, "Priming Cue\n(LED + Vib Full Strength)", ha='center', color=col_cue_text, fontweight='bold')
    
    ax.plot(t3, temp3, color=col_temp_line, linewidth=3)
    ax.fill_between(t3, temp3, basal_temp, where=(temp3 > basal_temp), 
                    color=col_lethal_fill, alpha=0.3, interpolate=True)
    
    ax.set_title("C. Survival Test (Lethal Challenge)", loc='left', fontweight='bold')
    ax.set_ylabel("Temperature (°C)")
    ax.set_xlabel("Time (minutes)")
    ax.set_ylim(20, 42)
    ax.set_xlim(0, 180)
    
    ax.text(100, challenge_temp + 1, "Lethal Challenge (38°C)", 
            ha='center', color=col_lethal_fill, fontweight='bold')
            
    # Add a "Survival Measured" annotation
    ax.annotate("Survival Measured", 
                xy=(150, 38), xycoords='data',
                xytext=(150, 30), textcoords='data',
                arrowprops=dict(arrowstyle="->", color='black', lw=1.5),
                ha='center')

    # Save
    output_path = os.path.join(os.path.dirname(__file__), 'experimental_paradigm_graphic_abstract.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Figure saved to: {output_path}")
    # plt.show() # Commented out for headless environments, but useful if running locally

if __name__ == "__main__":
    plot_paradigm()
