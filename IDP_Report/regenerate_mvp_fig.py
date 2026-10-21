import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Set clean aesthetic styling
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'

OUTPUT_DIR = r"c:\LIL\IDP_Report\figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_improved_mvp_validation():
    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')

    questions = [
        "Prefers Automated AI\nSurveillance over Manual",
        "Exit Warning & Turnstile\nLock Deterrence Impact",
        "Photo Evidence Makes\nViolations Undisputed",
        "GIS Heatmaps Helpful for\nSanitation Planning",
        "Clear Compliance with\nDPDP Act Privacy Norms"
    ]
    scores = [94.2, 91.8, 96.5, 89.4, 92.0]
    colors = ['#2563EB', '#059669', '#D97706', '#7C3AED', '#0284C7']
    edge_colors = ['#1D4ED8', '#047857', '#B45309', '#6D28D9', '#0369A1']

    # Draw subtle background grid
    ax.grid(axis='y', linestyle='--', linewidth=0.8, color='#CBD5E1', alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    # Plot bars with generous width and spacing
    x_indices = range(len(questions))
    bars = ax.bar(x_indices, scores, color=colors, width=0.52, edgecolor=edge_colors, linewidth=1.5, zorder=3)

    # Y-axis bounds and styling
    ax.set_ylim(0, 120)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'], fontsize=10, fontweight='bold', color='#334155')
    ax.set_ylabel("Stakeholder Approval Rate (%)", fontsize=11.5, fontweight='bold', color='#0F172A', labelpad=14)

    # X-axis ticks and labels with generous padding so text never overlaps
    ax.set_xticks(x_indices)
    ax.set_xticklabels(questions, fontsize=9.5, fontweight='bold', color='#1E293B', linespacing=1.2)
    ax.tick_params(axis='x', pad=10, bottom=False)
    ax.tick_params(axis='y', left=True, color='#94A3B8')

    # Spines styling
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('#94A3B8')
        ax.spines[spine].set_linewidth(1.2)

    # Target threshold reference line (e.g., 85% Target Acceptance)
    bench_line = ax.axhline(85, color='#DC2626', linestyle='--', linewidth=1.5, alpha=0.85, zorder=2, label='Target Acceptance Benchmark (85%)')

    # Value tags above bars
    for bar, score, color in zip(bars, scores, colors):
        h = bar.get_height()
        # Draw small pill badge background for the score
        ax.annotate(f"{score:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=10.5, fontweight='bold', color='#0F172A',
                    bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#CBD5E1', lw=1.2, alpha=0.98),
                    zorder=4)

    # Main Title and Subtitle
    ax.set_title("Figure A.I.4: Stakeholder MVP Validation Survey Results (N=120)\n"
                 "Evaluated across Campus Administration, Security Officers, Facility Management, and Student Body",
                 fontsize=12, fontweight='bold', pad=18, color='#0F172A', linespacing=1.35)

    # Clean legend for the benchmark line
    ax.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', 
              fontsize=9.2, fancybox=True, framealpha=0.95, borderpad=0.6)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig_ai4_mvp_validation.png")
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Regenerated figure successfully:", out_path)

if __name__ == "__main__":
    generate_improved_mvp_validation()
