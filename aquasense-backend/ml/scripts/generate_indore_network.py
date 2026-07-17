"""
AQUA-SENSE Simulated Current Indore Pipeline Network Generator (`generate_indore_network.py`)

This script generates approximately 750 simulated pipeline segments (`indore_pipeline_network.csv`)
for prototype demonstration and testing with the ML failure-risk model.

IMPORTANT DOCUMENTATION:
"The Indore pipeline network used by this prototype is simulated and does not represent official pipeline infrastructure data from Indore Municipal Corporation or any other government authority."
Never present synthetic values as real city infrastructure information.
"""

import os
import sys
import numpy as np
import pandas as pd

def haversine_distance_m(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Calculate geographic distance in meters between coordinate arrays using Haversine formula."""
    R = 6371000.0  # Earth radius in meters
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return R * c

def generate_indore_network(num_segments: int = 750, seed: int = 42) -> pd.DataFrame:
    """Generate the simulated Indore water pipeline network graph with spatial variation."""
    print(f"Initializing simulated Indore network generation (target segments={num_segments}, seed={seed})...")
    np.random.seed(seed)

    # 1. Define 5 simulated urban zones across Indore (anchored around city center 22.7196, 75.8577)
    zones = [
        # Zone 0: Old City / Rajwada Core (Older, Cast Iron/Concrete, higher historical failures)
        {"name": "Old City Core", "center": (22.7196, 75.8577), "radius": 0.022, "n_nodes": 100,
         "age_mean": 58, "age_std": 10, "mat_probs": [0.05, 0.55, 0.15, 0.10, 0.15],
         "maint_scale": 900, "fail_mult": 1.4, "comp_base": 2.5},
        # Zone 1: Vijay Nagar / North-East Hub (Newer, PVC/Ductile Iron, well-maintained)
        {"name": "North-East Expansion", "center": (22.7550, 75.8950), "radius": 0.025, "n_nodes": 100,
         "age_mean": 14, "age_std": 6, "mat_probs": [0.55, 0.02, 0.38, 0.03, 0.02],
         "maint_scale": 300, "fail_mult": 0.5, "comp_base": 0.6},
        # Zone 2: Silicon City / South-West Perimeter (Developing, mixed PVC/Ductile)
        {"name": "South-West Perimeter", "center": (22.6700, 75.8150), "radius": 0.025, "n_nodes": 90,
         "age_mean": 24, "age_std": 8, "mat_probs": [0.45, 0.05, 0.35, 0.10, 0.05],
         "maint_scale": 500, "fail_mult": 0.7, "comp_base": 1.1},
        # Zone 3: Palasia / AB Road Corridor (Established middle/high density, mixed materials)
        {"name": "Central-East Corridor", "center": (22.7280, 75.8820), "radius": 0.020, "n_nodes": 90,
         "age_mean": 38, "age_std": 9, "mat_probs": [0.20, 0.25, 0.35, 0.15, 0.05],
         "maint_scale": 600, "fail_mult": 1.0, "comp_base": 1.8},
        # Zone 4: Western Industrial / Airport Road (Industrial corridor, Cast Iron/Steel, stressed)
        {"name": "Western Corridor", "center": (22.7250, 75.8200), "radius": 0.022, "n_nodes": 80,
         "age_mean": 48, "age_std": 11, "mat_probs": [0.10, 0.38, 0.20, 0.22, 0.10],
         "maint_scale": 800, "fail_mult": 1.2, "comp_base": 2.1},
    ]

    # Generate geographic nodes per zone
    nodes_lat = []
    nodes_lon = []
    nodes_zone_idx = []

    for idx, z in enumerate(zones):
        # Sample coordinates with Gaussian scatter around zone center
        lats = np.random.normal(loc=z["center"][0], scale=z["radius"] * 0.45, size=z["n_nodes"])
        lons = np.random.normal(loc=z["center"][1], scale=z["radius"] * 0.45, size=z["n_nodes"])
        nodes_lat.extend(lats)
        nodes_lon.extend(lons)
        nodes_zone_idx.extend([idx] * z["n_nodes"])

    nodes_lat = np.array(nodes_lat)
    nodes_lon = np.array(nodes_lon)
    nodes_zone_idx = np.array(nodes_zone_idx)
    total_nodes = len(nodes_lat)
    print(f"Generated {total_nodes} geographic network nodes across 5 simulated infrastructure zones.")

    # 2. Connect nodes to form coherent pipeline segments (k-NN / radius edges)
    edges = []
    for i in range(total_nodes):
        # Calculate Haversine distance from node i to all other nodes j > i
        dists = haversine_distance_m(nodes_lat[i], nodes_lon[i], nodes_lat, nodes_lon)
        # We look at candidate neighbors j > i
        for j in range(i + 1, total_nodes):
            d = dists[j]
            # Connect if distance is between 60m and 1100m, with higher probability for closer nodes
            if 60.0 <= d <= 1100.0:
                # Probability of edge inversely proportional to distance to create tree/grid structure
                prob = np.exp(-d / 450.0)
                if np.random.random() < prob * 1.35:
                    edges.append((i, j, d))

    # Sort candidates by distance / structure and pick exactly `num_segments` (or keep all if close)
    # To maintain coherent distribution across zones, we shuffle slightly or take the top num_segments
    if len(edges) > num_segments:
        # Pick a balanced/connected subset of exactly num_segments
        indices = np.random.choice(len(edges), size=num_segments, replace=False)
        selected_edges = [edges[idx] for idx in sorted(indices)]
    else:
        selected_edges = edges

    num_actual_segments = len(selected_edges)
    print(f"Constructed {num_actual_segments} connected pipeline segments from node graph.")

    # 3. Build segment features based on spatial zone assignment
    pipeline_id = [f"IND-PIPE-{k:05d}" for k in range(1, num_actual_segments + 1)]
    start_lat = []
    start_lon = []
    end_lat = []
    end_lon = []
    center_lat = []
    center_lon = []
    length_m = []
    pipe_age_years = []
    material = []
    diameter_mm = []
    previous_failures = []
    days_since_last_maintenance = []
    complaints_last_30_days = []
    leakage_complaints_30d = []

    diameters_choices = [100, 150, 200, 250, 300, 400, 500, 600, 800]
    diameters_probs = [0.22, 0.20, 0.18, 0.13, 0.10, 0.08, 0.05, 0.03, 0.01]

    for i, j, geo_dist in selected_edges:
        s_lat, s_lon = nodes_lat[i], nodes_lon[i]
        e_lat, e_lon = nodes_lat[j], nodes_lon[j]
        c_lat = (s_lat + e_lat) / 2.0
        c_lon = (s_lon + e_lon) / 2.0

        start_lat.append(round(s_lat, 6))
        start_lon.append(round(s_lon, 6))
        end_lat.append(round(e_lat, 6))
        end_lon.append(round(e_lon, 6))
        center_lat.append(round(c_lat, 6))
        center_lon.append(round(c_lon, 6))

        # Stored length has minor variation (1% to 6% longer due to buried trench routing)
        l_m = round(geo_dist * np.random.uniform(1.01, 1.06), 1)
        length_m.append(l_m)

        # Determine governing zone (node i's zone or node j's zone)
        z_idx = nodes_zone_idx[i] if np.random.random() < 0.5 else nodes_zone_idx[j]
        z = zones[z_idx]

        # Sample age
        age = int(np.clip(np.round(np.random.normal(z["age_mean"], z["age_std"])), 1, 80))
        pipe_age_years.append(age)

        # Sample material
        mat = np.random.choice(['PVC', 'Cast Iron', 'Ductile Iron', 'Steel', 'Concrete'], p=z["mat_probs"])
        material.append(mat)

        # Sample diameter
        diam = np.random.choice(diameters_choices, p=diameters_probs)
        diameter_mm.append(int(diam))

        # Sample previous failures
        mat_mult = {'PVC': 0.5, 'Ductile Iron': 0.6, 'Steel': 0.9, 'Concrete': 1.1, 'Cast Iron': 1.5}[mat]
        l_fail = (age / 35.0) * mat_mult * z["fail_mult"] * np.random.uniform(0.6, 1.3)
        pf = int(np.random.poisson(l_fail))
        previous_failures.append(pf)

        # Sample maintenance
        maint = int(np.clip(np.round(np.random.exponential(scale=z["maint_scale"])), 0, 3000))
        days_since_last_maintenance.append(maint)

        # Sample complaints
        l_comp = z["comp_base"] + 0.02 * age + 0.3 * pf + 0.0003 * maint
        comp = int(np.random.poisson(l_comp * np.random.gamma(1.3, 1.0/1.3)))
        complaints_last_30_days.append(comp)

        # Sample leakage complaints (must be <= total complaints)
        p_l = np.clip(0.30 + 0.007 * age + 0.04 * pf, 0.1, 0.85)
        leak_comp = int(np.random.binomial(n=comp, p=p_l))
        leakage_complaints_30d.append(leak_comp)

    df = pd.DataFrame({
        'pipeline_id': pipeline_id,
        'start_latitude': start_lat,
        'start_longitude': start_lon,
        'end_latitude': end_lat,
        'end_longitude': end_lon,
        'center_latitude': center_lat,
        'center_longitude': center_lon,
        'pipe_age_years': pipe_age_years,
        'material': material,
        'diameter_mm': diameter_mm,
        'length_m': length_m,
        'previous_failures': previous_failures,
        'days_since_last_maintenance': days_since_last_maintenance,
        'complaints_last_30_days': complaints_last_30_days,
        'leakage_complaints_30d': leakage_complaints_30d
    })

    return df, total_nodes

def validate_and_summarize_indore(df: pd.DataFrame, total_nodes: int) -> None:
    """Validate Indore network rules and print comprehensive summary statistics."""
    print("\n" + "="*70)
    print("SIMULATED INDORE PIPELINE NETWORK — VALIDATION & SUMMARY REPORT")
    print("="*70)

    # Assertions
    assert len(df['pipeline_id'].unique()) == df.shape[0], "Duplicate pipeline_id values detected!"
    assert not df.isnull().any().any(), "Missing values detected!"
    assert (df['pipe_age_years'] >= 1).all() and (df['pipe_age_years'] <= 80).all(), "pipe_age_years out of bounds!"
    assert set(df['material'].unique()).issubset({'PVC', 'Cast Iron', 'Ductile Iron', 'Steel', 'Concrete'}), "Invalid materials!"
    assert set(df['diameter_mm'].unique()).issubset({100, 150, 200, 250, 300, 400, 500, 600, 800}), "Invalid diameters!"
    assert (df['previous_failures'] >= 0).all(), "Negative previous_failures!"
    assert (df['days_since_last_maintenance'] >= 0).all(), "Negative days_since_last_maintenance!"
    assert (df['complaints_last_30_days'] >= 0).all(), "Negative complaints_last_30_days!"
    assert (df['leakage_complaints_30d'] >= 0).all(), "Negative leakage_complaints_30d!"
    assert (df['leakage_complaints_30d'] <= df['complaints_last_30_days']).all(), "leakage_complaints_30d > complaints_last_30_days!"

    # Geographic assertions (within general Indore urban area ~ 22.60 to 22.85 N, 75.72 to 75.98 E)
    assert (df['start_latitude'] >= 22.60).all() and (df['start_latitude'] <= 22.85).all(), "start_latitude out of Indore area!"
    assert (df['start_longitude'] >= 75.72).all() and (df['start_longitude'] <= 75.98).all(), "start_longitude out of Indore area!"
    assert (df['end_latitude'] >= 22.60).all() and (df['end_latitude'] <= 22.85).all(), "end_latitude out of Indore area!"
    assert (df['end_longitude'] >= 75.72).all() and (df['end_longitude'] <= 75.98).all(), "end_longitude out of Indore area!"

    # Verify no target columns leak into Indore dataset
    forbidden_cols = {'failure_next_12_months', 'risk_score', 'failure_probability', 'risk_level'}
    assert not forbidden_cols.intersection(df.columns), "Forbidden target/risk columns found in Indore dataset!"

    print("[PASS] All Indore network geographic & data quality assertions passed successfully.")

    # 1. Dataset shape
    print(f"\n1. Dataset Shape: {df.shape[0]:,d} segments × {df.shape[1]} columns")
    print(f"   - Total Unique Geographic Nodes: {total_nodes}")

    # 2. First 5 rows
    print("\n2. First 5 Rows:")
    print(df.head().to_string(index=False))

    # 3. Coordinate ranges
    print("\n3. Coordinate Ranges (Indore Urban Anchor):")
    print(f"   - Latitude Range:  {df['start_latitude'].min():.4f}° to {df['start_latitude'].max():.4f}° N")
    print(f"   - Longitude Range: {df['start_longitude'].min():.4f}° to {df['start_longitude'].max():.4f}° E")

    # 4. Material distribution
    print("\n4. Material Distribution across Zones:")
    mat_counts = df['material'].value_counts()
    mat_pct = df['material'].value_counts(normalize=True) * 100
    for m in mat_counts.index:
        print(f"   - {m}: {mat_counts[m]:,d} ({mat_pct[m]:.2f}%)")

    # 5. Pipeline age & previous failure statistics
    print("\n5. Numeric Summary Statistics (Age, Failures, Complaints, Length):")
    stats_cols = [
        'pipe_age_years', 'length_m', 'previous_failures',
        'days_since_last_maintenance', 'complaints_last_30_days', 'leakage_complaints_30d'
    ]
    print(df[stats_cols].describe().round(2).to_string())
    print("="*70 + "\n")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ml_dir = os.path.dirname(script_dir)
    raw_dir = os.path.join(ml_dir, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)

    df, total_nodes = generate_indore_network(num_segments=750, seed=42)
    validate_and_summarize_indore(df, total_nodes)

    output_path = os.path.join(raw_dir, "indore_pipeline_network.csv")
    df.to_csv(output_path, index=False)
    print(f"[PASS] Indore pipeline network generated and saved to: {output_path}")

if __name__ == "__main__":
    main()
