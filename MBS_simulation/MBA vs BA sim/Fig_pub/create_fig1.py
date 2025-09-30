import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path

# --- Configuration ---
OUT_DIR = Path(__file__).resolve().parent
OUT_FILE = OUT_DIR / 'Figure1_EnvironmentAndFitness.png'
HES_PLOT_PATH = Path('plots') / 'final_environment_cycle_annotated.png'
FITNESS_PLOT_PATH = Path('plots') / 'fitness_heatmap_conditional.png'

# --- Check for source images ---
if not HES_PLOT_PATH.exists() or not FITNESS_PLOT_PATH.exists():
    print(f"Error: Could not find source images.")
    print(f"  - Searched for HES plot at: {HES_PLOT_PATH.resolve()}")
    print(f"  - Searched for Fitness plot at: {FITNESS_PLOT_PATH.resolve()}")
    exit()

# --- Create Figure ---
fig, axs = plt.subplots(2, 1, figsize=(8, 10))

# Panel A: HES Cycle
axs[0].imshow(mpimg.imread(HES_PLOT_PATH))
axs[0].set_title('A. Daily Environmental Cycle', loc='left', fontsize=12, fontweight='bold')
axs[0].axis('off')

# Panel B: Fitness Landscape
axs[1].imshow(mpimg.imread(FITNESS_PLOT_PATH))
axs[1].set_title('B. Phenotype Fitness Landscape', loc='left', fontsize=12, fontweight='bold')
axs[1].axis('off')

# Final adjustments and save
plt.tight_layout(pad=1.5)
plt.savefig(OUT_FILE, dpi=300, bbox_inches='tight')

print(f"Combined Figure 1 saved to: {OUT_FILE.resolve()}") 