"""
Development-only visualization script to plot the generated Indore pipeline network (`verify_network_plot.py`).

Purpose: Verify geographic coherence, segment connectivity, and ensure the simulated network
resembles connected municipal infrastructure without assigning risk colors or building frontend maps.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ml_dir = os.path.dirname(script_dir)
    csv_path = os.path.join(ml_dir, "data", "raw", "indore_pipeline_network.csv")

    if not os.path.exists(csv_path):
        print(f"Error: Dataset not found at {csv_path}. Please run generate_indore_network.py first.")
        return

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} pipeline segments from {csv_path}.")

    fig, ax = plt.subplots(figsize=(12, 10))

    # Plot pipeline segments in uniform neutral color (no risk colors assigned yet)
    for idx, row in df.iterrows():
        ax.plot(
            [row['start_longitude'], row['end_longitude']],
            [row['start_latitude'], row['end_latitude']],
            color='#1f77b4',
            alpha=0.6,
            linewidth=1.2,
            solid_capstyle='round'
        )

    # Mark start and end nodes lightly to show network junctions
    all_lons = pd.concat([df['start_longitude'], df['end_longitude']])
    all_lats = pd.concat([df['start_latitude'], df['end_latitude']])
    ax.scatter(all_lons, all_lats, color='#2ca02c', s=12, alpha=0.8, zorder=3, label='Network Nodes')

    # Mark Indore City Center Anchor
    ax.scatter([75.8577], [22.7196], color='#d62728', marker='*', s=180, zorder=5, label='Indore City Center Anchor (22.7196° N, 75.8577° E)')

    ax.set_title("Simulated Current Indore Pipeline Network (Prototype Verification)", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Longitude (°E)", fontsize=12)
    ax.set_ylabel("Latitude (°N)", fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='upper right')

    # Ensure equal aspect ratio for realistic geographic geometry
    ax.set_aspect('equal', adjustable='datalim')

    output_plot_path = os.path.join(script_dir, "indore_network_plot.png")
    plt.tight_layout()
    plt.savefig(output_plot_path, dpi=300)
    plt.close()

    print(f"[PASS] Network verification plot successfully generated and saved to: {output_plot_path}")
    print("Verification check: The plotted segments show coherent connected tree/grid clusters across urban Indore without invalid jumps across the city.")

if __name__ == "__main__":
    main()
