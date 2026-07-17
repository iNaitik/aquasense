"""
AQUA-SENSE Indore Pipeline Network Prediction & Risk Mapping (`predict_indore_network.py`)

Step 3: Load trained preprocessing + ML pipeline (`pipeline_failure_model.joblib`), predict
failure probabilities for the simulated current Indore network (`indore_pipeline_network.csv`),
calculate risk scores and levels (`LOW`, `MEDIUM`, `HIGH`), export predictions
(`indore_pipeline_predictions.csv`), and generate interactive geographic risk map (`indore_pipeline_risk_map.html`).

IMPORTANT INTEGRITY DOCUMENTATION:
"The Indore pipeline network used by this prototype is simulated and does not represent official pipeline
infrastructure data from Indore Municipal Corporation or any other government authority.
The model is a prototype trained on synthetic data. Predicted risk scores are demonstration outputs and
must not be interpreted as actual risk assessments of Indore's real water infrastructure."
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
import folium

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ml_dir = os.path.dirname(script_dir)
    raw_dir = os.path.join(ml_dir, "data", "raw")
    processed_dir = os.path.join(ml_dir, "data", "processed")
    models_dir = os.path.join(ml_dir, "models")
    reports_dir = os.path.join(ml_dir, "reports")
    figures_dir = os.path.join(reports_dir, "figures")
    
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    print("="*70)
    print("STEP 1: LOADING SIMULATED INDORE NETWORK & TRAINED MODEL PIPELINE")
    print("="*70)
    
    # 1. Load Indore Network
    network_path = os.path.join(raw_dir, "indore_pipeline_network.csv")
    if not os.path.exists(network_path):
        raise FileNotFoundError(f"Indore network file not found at {network_path}")
    df_indore = pd.read_csv(network_path)
    print(f"[PASS] Loaded {len(df_indore):,d} simulated Indore pipeline segments from: {network_path}")

    # 2. Load Model Pipeline
    model_path = os.path.join(models_dir, "pipeline_failure_model.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model artifact not found at {model_path}. Please run train_model.py first.")
    model_pipeline = joblib.load(model_path)
    print(f"[PASS] Loaded complete fitted preprocessing + classifier pipeline from: {model_path}")

    # 3. Predict Failure Probabilities using exact 8 ML input feature names
    feature_names = [
        'pipe_age_years', 'material', 'diameter_mm', 'length_m',
        'previous_failures', 'days_since_last_maintenance',
        'complaints_last_30_days', 'leakage_complaints_30d'
    ]
    X_indore = df_indore[feature_names]

    print("\nGenerating failure probabilities and risk scores across all network segments...")
    failure_probabilities = model_pipeline.predict_proba(X_indore)[:, 1]
    
    # Calculate risk_score = round(failure_probability * 100, 1)
    risk_scores = np.round(failure_probabilities * 100.0, 1)

    # Assign risk_level (Prototype visualization thresholds: LOW < 40, MEDIUM 40-<70, HIGH >= 70)
    # Note: These prototype visualization thresholds are separate from the binary classification threshold.
    risk_levels = []
    for score in risk_scores:
        if score < 40.0:
            risk_levels.append("LOW")
        elif score < 70.0:
            risk_levels.append("MEDIUM")
        else:
            risk_levels.append("HIGH")

    # Preserve all original columns and append predictions
    df_predictions = df_indore.copy()
    df_predictions['failure_probability'] = np.round(failure_probabilities, 4)
    df_predictions['risk_score'] = risk_scores
    df_predictions['risk_level'] = risk_levels

    output_csv_path = os.path.join(processed_dir, "indore_pipeline_predictions.csv")
    df_predictions.to_csv(output_csv_path, index=False)
    print(f"[PASS] Saved Indore prediction dataset ({len(df_predictions)} rows x {df_predictions.shape[1]} cols) to: {output_csv_path}")
    print("="*70 + "\n")

    # 4. Validate & Print Risk Distribution
    print("="*70)
    print("STEP 2: INDORE NETWORK RISK DISTRIBUTION & STATISTICAL SUMMARY")
    print("="*70)
    level_counts = df_predictions['risk_level'].value_counts()
    level_pcts = df_predictions['risk_level'].value_counts(normalize=True) * 100.0

    print("Risk Level Counts & Percentages (Thresholds: LOW <40, MEDIUM 40-70, HIGH >=70):")
    for lvl in ["LOW", "MEDIUM", "HIGH"]:
        cnt = level_counts.get(lvl, 0)
        pct = level_pcts.get(lvl, 0.0)
        print(f"   - {lvl:6s} Risk: {cnt:3d} segments ({pct:5.2f}%)")

    print("\nRisk Score Statistics (`risk_score = failure_probability * 100`):")
    print(f"   - Minimum Risk Score: {df_predictions['risk_score'].min():.1f}")
    print(f"   - Maximum Risk Score: {df_predictions['risk_score'].max():.1f}")
    print(f"   - Mean Risk Score:    {df_predictions['risk_score'].mean():.2f}")
    print(f"   - Median Risk Score:  {df_predictions['risk_score'].median():.1f}")

    # Verify distribution sanity
    assert len(df_predictions) == len(df_indore), "Row count mismatch in prediction output!"
    assert not df_predictions['risk_level'].isnull().any(), "Missing risk levels detected!"
    assert level_counts.get("LOW", 0) > 0 and level_counts.get("MEDIUM", 0) > 0 and level_counts.get("HIGH", 0) > 0, \
        "Warning: One or more risk categories are completely empty!"
    print("\n[PASS] Risk score distribution verified: meaningful multi-zone variation observed across LOW, MEDIUM, and HIGH segments.")
    print("="*70 + "\n")

    # 5. Generate Development Geographic Risk Map using Folium
    print("="*70)
    print("STEP 3: GENERATING DEVELOPMENT GEOGRAPHIC RISK MAP (FOLIUM)")
    print("="*70)
    # Center map on Indore City Anchor
    center_lat = df_predictions['center_latitude'].mean()
    center_lon = df_predictions['center_longitude'].mean()
    risk_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='CartoDB positron'
    )

    color_map = {
        "LOW": "#2ca02c",      # Green
        "MEDIUM": "#ff9900",   # Yellow/Orange
        "HIGH": "#d62728"      # Red
    }

    # Add city center marker
    folium.Marker(
        location=[22.7196, 75.8577],
        popup=folium.Popup("<b>Indore City Center Anchor</b><br>(22.7196° N, 75.8577° E)<br><i>Simulated Prototype Reference</i>", max_width=250),
        icon=folium.Icon(color='darkblue', icon='star')
    ).add_to(risk_map)

    # Plot each segment
    for idx, row in df_predictions.iterrows():
        coords = [
            [row['start_latitude'], row['start_longitude']],
            [row['end_latitude'], row['end_longitude']]
        ]
        lvl = row['risk_level']
        seg_color = color_map.get(lvl, "#333333")
        
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 13px; width: 230px;">
            <b style="font-size: 14px; color: #111;">Segment: {row['pipeline_id']}</b><br>
            <hr style="margin: 5px 0;">
            <b>Risk Level:</b> <span style="color: {seg_color}; font-weight: bold;">{lvl}</span><br>
            <b>Risk Score:</b> {row['risk_score']:.1f} / 100<br>
            <b>Failure Probability:</b> {row['failure_probability']*100:.1f}%<br>
            <hr style="margin: 5px 0;">
            <b>Material:</b> {row['material']}<br>
            <b>Diameter:</b> {row['diameter_mm']} mm<br>
            <b>Length:</b> {row['length_m']} m<br>
            <b>Age:</b> {row['pipe_age_years']} yrs<br>
            <b>Past Failures:</b> {row['previous_failures']}<br>
            <b>Days Since Maint.:</b> {row['days_since_last_maintenance']} d<br>
            <b>Recent Complaints (30d):</b> {row['complaints_last_30_days']} (Leaks: {row['leakage_complaints_30d']})
        </div>
        """
        
        folium.PolyLine(
            locations=coords,
            color=seg_color,
            weight=4 if lvl == "HIGH" else (3 if lvl == "MEDIUM" else 2.5),
            opacity=0.85 if lvl == "HIGH" else 0.7,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{row['pipeline_id']} | Risk: {lvl} ({row['risk_score']})"
        ).add_to(risk_map)

    # Add Prototype Legend & Disclaimer Banner
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; width: 330px; background-color: rgba(255, 255, 255, 0.95);
                border: 2px solid #ccc; z-index: 9999; font-size: 12px; padding: 12px; border-radius: 6px; box-shadow: 2px 2px 6px rgba(0,0,0,0.2);">
        <b style="font-size: 14px; color: #222;">AQUA-SENSE Development Risk Map</b><br>
        <span style="font-size: 11px; color: #666;">Prototype Simulated Indore Network</span><hr style="margin: 6px 0;">
        <i style="background: #2ca02c; width: 14px; height: 14px; float: left; margin-right: 8px; border-radius: 3px;"></i> LOW Risk (Score &lt; 40)<br>
        <i style="background: #ff9900; width: 14px; height: 14px; float: left; margin-right: 8px; border-radius: 3px; margin-top: 4px;"></i> MEDIUM Risk (Score 40 - 69)<br>
        <i style="background: #d62728; width: 14px; height: 14px; float: left; margin-right: 8px; border-radius: 3px; margin-top: 4px;"></i> HIGH Risk (Score &ge; 70)<br>
        <hr style="margin: 6px 0;">
        <div style="font-size: 10px; color: #777; line-height: 1.3;">
            <b>DISCLAIMER:</b> Simulated network for prototype demonstration only. Not official IMC municipal data.
            Risk levels are demonstration outputs and not actual engineering safety assessments.
        </div>
    </div>
    """
    risk_map.get_root().html.add_child(folium.Element(legend_html))

    map_output_path = os.path.join(figures_dir, "indore_pipeline_risk_map.html")
    risk_map.save(map_output_path)
    print(f"[PASS] Development geographic risk map generated and saved to: {map_output_path}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
