"""Idempotent script to import simulated Indore pipeline network predictions into PostgreSQL (`pipelines` table).

DISCLAIMER:
The pipeline network used in this prototype is simulated and does not represent official
Indore Municipal Corporation infrastructure. The ML model was trained on synthetic historical data.
Risk predictions are prototype demonstration outputs and are not validated assessments of real
Indore water pipelines.
"""

import os
import sys
from pathlib import Path
import pandas as pd

# Ensure the project root (parent of scripts/) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.pipeline import Pipeline


def validate_row(row: pd.Series, row_idx: int) -> None:
    """Validate data format and constraints of a pipeline row before import."""
    required_cols = [
        'pipeline_id', 'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude',
        'center_latitude', 'center_longitude', 'pipe_age_years', 'material', 'diameter_mm',
        'length_m', 'previous_failures', 'days_since_last_maintenance', 'complaints_last_30_days',
        'leakage_complaints_30d', 'failure_probability', 'risk_score', 'risk_level'
    ]
    for col in required_cols:
        if col not in row or pd.isnull(row[col]):
            raise ValueError(f"Row {row_idx}: Missing required field '{col}'")

    # Validate coordinate ranges
    for lat_col in ['start_latitude', 'end_latitude', 'center_latitude']:
        lat = float(row[lat_col])
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Row {row_idx}: {lat_col} ({lat}) out of valid range [-90, 90]")
    for lon_col in ['start_longitude', 'end_longitude', 'center_longitude']:
        lon = float(row[lon_col])
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Row {row_idx}: {lon_col} ({lon}) out of valid range [-180, 180]")

    # Validate probability, risk score, and level
    prob = float(row['failure_probability'])
    if not (0.0 <= prob <= 1.0):
        raise ValueError(f"Row {row_idx}: failure_probability ({prob}) out of valid range [0, 1]")

    score = float(row['risk_score'])
    if not (0.0 <= score <= 100.0):
        raise ValueError(f"Row {row_idx}: risk_score ({score}) out of valid range [0, 100]")

    level = str(row['risk_level']).strip()
    if level not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError(f"Row {row_idx}: Invalid risk_level '{level}'. Must be LOW, MEDIUM, or HIGH")


def import_pipelines(csv_path: str) -> None:
    """Import simulated Indore pipeline network into PostgreSQL idempotently."""
    print("="*70)
    print("AQUA-SENSE PIPELINE NETWORK IMPORT")
    print("="*70)
    print("DISCLAIMER: Simulated network for prototype demonstration only. Not official IMC municipal data.")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV prediction file not found at: {csv_path}")

    df = pd.read_csv(csv_path)
    total_csv_records = len(df)
    print(f"Loaded {total_csv_records:,d} records from {csv_path}")

    db: Session = SessionLocal()
    inserted_records = 0
    updated_records = 0
    failed_records = 0

    try:
        # Pre-fetch existing pipeline_ids to minimize individual SELECT queries inside loop
        existing_pipelines = {
            p.pipeline_id: p for p in db.query(Pipeline).all()
        }

        for idx, row in df.iterrows():
            try:
                validate_row(row, idx)
                pid = str(row['pipeline_id']).strip()

                if pid in existing_pipelines:
                    # Update existing record
                    p = existing_pipelines[pid]
                    p.start_latitude = float(row['start_latitude'])
                    p.start_longitude = float(row['start_longitude'])
                    p.end_latitude = float(row['end_latitude'])
                    p.end_longitude = float(row['end_longitude'])
                    p.center_latitude = float(row['center_latitude'])
                    p.center_longitude = float(row['center_longitude'])
                    p.pipe_age_years = float(row['pipe_age_years'])
                    p.material = str(row['material']).strip()
                    p.diameter_mm = float(row['diameter_mm'])
                    p.length_m = float(row['length_m'])
                    p.previous_failures = int(row['previous_failures'])
                    p.days_since_last_maintenance = float(row['days_since_last_maintenance'])
                    p.complaints_last_30_days = int(row['complaints_last_30_days'])
                    p.leakage_complaints_30d = int(row['leakage_complaints_30d'])
                    p.failure_probability = float(row['failure_probability'])
                    p.risk_score = float(row['risk_score'])
                    p.risk_level = str(row['risk_level']).strip()
                    updated_records += 1
                else:
                    # Insert new record
                    new_pipeline = Pipeline(
                        pipeline_id=pid,
                        start_latitude=float(row['start_latitude']),
                        start_longitude=float(row['start_longitude']),
                        end_latitude=float(row['end_latitude']),
                        end_longitude=float(row['end_longitude']),
                        center_latitude=float(row['center_latitude']),
                        center_longitude=float(row['center_longitude']),
                        pipe_age_years=float(row['pipe_age_years']),
                        material=str(row['material']).strip(),
                        diameter_mm=float(row['diameter_mm']),
                        length_m=float(row['length_m']),
                        previous_failures=int(row['previous_failures']),
                        days_since_last_maintenance=float(row['days_since_last_maintenance']),
                        complaints_last_30_days=int(row['complaints_last_30_days']),
                        leakage_complaints_30d=int(row['leakage_complaints_30d']),
                        failure_probability=float(row['failure_probability']),
                        risk_score=float(row['risk_score']),
                        risk_level=str(row['risk_level']).strip()
                    )
                    db.add(new_pipeline)
                    existing_pipelines[pid] = new_pipeline
                    inserted_records += 1

            except Exception as e:
                failed_records += 1
                print(f"[ERROR] Failed processing row {idx} ({row.get('pipeline_id', 'UNKNOWN')}): {e}")
                raise e

        db.commit()
        total_in_db = db.query(Pipeline).count()

        print("\nImport Summary:")
        print(f"   - Total CSV records:            {total_csv_records:,d}")
        print(f"   - Inserted records:             {inserted_records:,d}")
        print(f"   - Updated records:              {updated_records:,d}")
        print(f"   - Failed records:               {failed_records:,d}")
        print(f"   - Total pipelines in database:  {total_in_db:,d}")
        print("="*70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[CRITICAL ERROR] Rolling back transaction due to error: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    csv_file = os.path.join(project_root, "ml", "data", "processed", "indore_pipeline_predictions.csv")
    import_pipelines(csv_file)
