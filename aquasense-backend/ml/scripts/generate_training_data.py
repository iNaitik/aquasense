"""
AQUA-SENSE ML Historical Training Dataset Generator (`generate_training_data.py`)

This script generates 15,000 synthetic historical pipeline observations (`pipeline_training_data.csv`)
for developing and evaluating the ML pipeline failure-risk prediction prototype (`failure_next_12_months`).

IMPORTANT DOCUMENTATION:
"The historical pipeline failure dataset is synthetically generated for prototype ML development and evaluation."
Never present synthetic values as real city infrastructure information.
"""

import os
import sys
import numpy as np
import pandas as pd

def generate_historical_training_data(num_rows: int = 15000, seed: int = 42) -> pd.DataFrame:
    """Generate the synthetic historical pipeline training dataset."""
    print(f"Initializing historical training data generation (N={num_rows}, seed={seed})...")
    np.random.seed(seed)

    # 1. pipeline_id: identifier only, e.g. HIST-PIPE-00001
    pipeline_id = [f"HIST-PIPE-{i:05d}" for i in range(1, num_rows + 1)]

    # 2. pipe_age_years: integer range [1, 80], skewed toward middle ranges
    age_raw = np.random.beta(a=2.5, b=2.5, size=num_rows)
    pipe_age_years = np.clip(np.round(1 + age_raw * 79).astype(int), 1, 80)

    # 3. material: non-uniform probabilities, correlated with age, influencing risk
    # Categories: PVC, Cast Iron, Ductile Iron, Steel, Concrete
    materials = []
    for age in pipe_age_years:
        if age <= 20:
            probs = [0.55, 0.02, 0.38, 0.03, 0.02]  # PVC, Cast Iron, Ductile Iron, Steel, Concrete
        elif age <= 45:
            probs = [0.30, 0.10, 0.42, 0.12, 0.06]
        else:
            probs = [0.05, 0.45, 0.15, 0.20, 0.15]
        mat = np.random.choice(['PVC', 'Cast Iron', 'Ductile Iron', 'Steel', 'Concrete'], p=probs)
        materials.append(mat)
    material = np.array(materials)

    # 4. diameter_mm: discrete realistic values [100, 150, 200, 250, 300, 400, 500, 600, 800]
    diameters_choices = [100, 150, 200, 250, 300, 400, 500, 600, 800]
    diameters_probs = [0.22, 0.20, 0.18, 0.13, 0.10, 0.08, 0.05, 0.03, 0.01]
    diameter_mm = np.random.choice(diameters_choices, size=num_rows, p=diameters_probs)

    # 5. length_m: positive segment lengths [50, 2000], right-skewed
    length_raw = 50 + np.random.exponential(scale=350, size=num_rows)
    length_m = np.clip(np.round(length_raw, 1), 50.0, 2000.0)

    # 6. previous_failures: most 0 to 2, smaller number 3+
    # Correlated with higher pipe age and riskier materials
    mat_failure_multiplier = {
        'PVC': 0.5,
        'Ductile Iron': 0.6,
        'Steel': 0.9,
        'Concrete': 1.1,
        'Cast Iron': 1.5
    }
    mat_mult = np.array([mat_failure_multiplier[m] for m in material])
    lambda_fail = (pipe_age_years / 35.0) * mat_mult * np.random.uniform(0.6, 1.4, size=num_rows)
    previous_failures = np.random.poisson(lambda_fail)

    # 7. days_since_last_maintenance: approximately 0 to 3000 days
    # Most maintained within a few years; varied distribution
    maint_scale = 550.0 * (1.0 + 0.25 * (pipe_age_years / 40.0))
    days_since_last_maintenance = np.clip(
        np.round(np.random.exponential(scale=maint_scale, size=num_rows)).astype(int),
        0,
        3000
    )

    # 8. complaints_last_30_days: skewed count (most 0 to 3, some higher)
    lambda_comp = 0.5 + 0.015 * pipe_age_years + 0.35 * previous_failures + 0.0004 * days_since_last_maintenance
    gamma_noise = np.random.gamma(shape=1.5, scale=1.0/1.5, size=num_rows)
    complaints_last_30_days = np.random.poisson(lambda_comp * gamma_noise)

    # 9. leakage_complaints_30d: 0 <= leakage_complaints_30d <= complaints_last_30_days
    p_leak = np.clip(0.30 + 0.006 * pipe_age_years + 0.04 * previous_failures + np.random.normal(0, 0.08, size=num_rows), 0.1, 0.85)
    leakage_complaints_30d = np.random.binomial(n=complaints_last_30_days, p=p_leak)

    # 10. Target: failure_next_12_months (0 or 1)
    # Hidden probabilistic mechanism with non-linear interaction effects
    mat_risk_score = {
        'PVC': -0.4,
        'Ductile Iron': -0.3,
        'Steel': 0.2,
        'Concrete': 0.3,
        'Cast Iron': 0.7
    }
    mat_risk = np.array([mat_risk_score[m] for m in material])

    age_effect = (pipe_age_years - 35.0) / 20.0
    fail_effect = previous_failures * 0.45
    maint_effect = (days_since_last_maintenance - 700.0) / 800.0
    comp_effect = complaints_last_30_days * 0.18
    leak_effect = leakage_complaints_30d * 0.35

    # Interaction terms
    interaction_age_fail = np.where((pipe_age_years > 45) & (previous_failures >= 2), 0.40, 0.0)
    interaction_leak_maint = np.where((leakage_complaints_30d >= 2) & (days_since_last_maintenance > 1000), 0.45, 0.0)
    interaction_mat_age = np.where(np.isin(material, ['Cast Iron', 'Concrete']) & (pipe_age_years > 40), 0.30, 0.0)

    latent_risk_score = (
        -3.10
        + 0.45 * age_effect
        + mat_risk
        + 0.30 * fail_effect
        + 0.25 * maint_effect
        + 0.12 * comp_effect
        + 0.20 * leak_effect
        + interaction_age_fail
        + interaction_leak_maint
        + interaction_mat_age
        + np.random.normal(0, 0.5, size=num_rows)  # random noise
    )

    failure_probs = 1.0 / (1.0 + np.exp(-latent_risk_score))
    failure_next_12_months = np.random.binomial(n=1, p=failure_probs)

    df = pd.DataFrame({
        'pipeline_id': pipeline_id,
        'pipe_age_years': pipe_age_years,
        'material': material,
        'diameter_mm': diameter_mm,
        'length_m': length_m,
        'previous_failures': previous_failures,
        'days_since_last_maintenance': days_since_last_maintenance,
        'complaints_last_30_days': complaints_last_30_days,
        'leakage_complaints_30d': leakage_complaints_30d,
        'failure_next_12_months': failure_next_12_months
    })

    return df

def validate_and_summarize(df: pd.DataFrame) -> None:
    """Validate dataset rules and print required summary statistics."""
    print("\n" + "="*70)
    print("HISTORICAL TRAINING DATASET — VALIDATION & SUMMARY REPORT")
    print("="*70)

    # Assertions
    assert df.shape[0] == 15000, f"Expected 15000 rows, got {df.shape[0]}"
    assert len(df['pipeline_id'].unique()) == 15000, "Duplicate pipeline_id values!"
    assert not df.isnull().any().any(), "Missing values detected!"
    assert (df['pipe_age_years'] >= 1).all() and (df['pipe_age_years'] <= 80).all(), "pipe_age_years out of bounds!"
    assert set(df['material'].unique()).issubset({'PVC', 'Cast Iron', 'Ductile Iron', 'Steel', 'Concrete'}), "Invalid materials!"
    assert set(df['diameter_mm'].unique()).issubset({100, 150, 200, 250, 300, 400, 500, 600, 800}), "Invalid diameters!"
    assert (df['previous_failures'] >= 0).all(), "Negative previous_failures!"
    assert (df['days_since_last_maintenance'] >= 0).all(), "Negative days_since_last_maintenance!"
    assert (df['complaints_last_30_days'] >= 0).all(), "Negative complaints_last_30_days!"
    assert (df['leakage_complaints_30d'] >= 0).all(), "Negative leakage_complaints_30d!"
    assert (df['leakage_complaints_30d'] <= df['complaints_last_30_days']).all(), "leakage_complaints_30d > complaints_last_30_days!"
    assert set(df['failure_next_12_months'].unique()).issubset({0, 1}), "Invalid target values!"

    print("[PASS] All data quality & integrity assertions passed successfully.")

    # 1. Dataset shape
    print(f"\n1. Dataset Shape: {df.shape[0]:,d} rows × {df.shape[1]} columns")

    # 2. First 5 rows
    print("\n2. First 5 Rows:")
    print(df.head().to_string(index=False))

    # 3. Data types
    print("\n3. Data Types:")
    print(df.dtypes)

    # 4. Missing values
    print("\n4. Missing Values Count:")
    print(df.isnull().sum())

    # 5. Material distribution
    print("\n5. Material Distribution:")
    mat_counts = df['material'].value_counts()
    mat_pct = df['material'].value_counts(normalize=True) * 100
    for m in mat_counts.index:
        print(f"   - {m}: {mat_counts[m]:,d} ({mat_pct[m]:.2f}%)")

    # 6. Numeric summary statistics
    print("\n6. Numeric Summary Statistics:")
    numeric_cols = [
        'pipe_age_years', 'diameter_mm', 'length_m', 'previous_failures',
        'days_since_last_maintenance', 'complaints_last_30_days', 'leakage_complaints_30d'
    ]
    print(df[numeric_cols].describe().round(2).to_string())

    # 7 & 8. Failure class counts and percentages
    counts = df['failure_next_12_months'].value_counts().sort_index()
    percentages = (df['failure_next_12_months'].value_counts(normalize=True) * 100).sort_index()
    print("\n7 & 8. Failure Class Distribution (`failure_next_12_months`):")
    for cls in counts.index:
        label = "No Failure (0)" if cls == 0 else "Failure (1)"
        print(f"   - {label}: {counts[cls]:,d} rows ({percentages[cls]:.2f}%)")

    assert 10.0 <= percentages[1] <= 20.0, f"Target failure percentage {percentages[1]:.2f}% is not within 10% to 20%!"
    print("="*70 + "\n")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ml_dir = os.path.dirname(script_dir)
    raw_dir = os.path.join(ml_dir, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)

    df = generate_historical_training_data(num_rows=15000, seed=42)
    validate_and_summarize(df)

    output_path = os.path.join(raw_dir, "pipeline_training_data.csv")
    df.to_csv(output_path, index=False)
    print(f"[PASS] Historical training dataset generated and saved to: {output_path}")

if __name__ == "__main__":
    main()
