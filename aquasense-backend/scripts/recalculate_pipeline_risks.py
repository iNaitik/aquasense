"""Maintenance script to recalculate rolling complaint features and ML risk predictions.

Recalculates current rolling 30-day complaint counts, combines them with synthetic baseline values,
and runs the ML model to update failure probability, risk score, and risk level.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.pipeline import Pipeline
from app.services.pipeline_recalculation_service import recalculate_pipeline_risk_from_complaints


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalculate pipeline complaint-derived features and ML risk predictions."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--pipeline-id",
        type=str,
        help="Recalculate risk for a single pipeline by public ID (e.g., IND-PIPE-00001).",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Recalculate risk for all pipelines in the network (default behavior).",
    )

    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        if args.pipeline_id:
            pipelines = (
                db.query(Pipeline)
                .filter(Pipeline.pipeline_id == args.pipeline_id.strip().upper())
                .all()
            )
            if not pipelines:
                print(f"Error: Pipeline '{args.pipeline_id}' not found.")
                sys.exit(1)
        else:
            pipelines = db.query(Pipeline).order_by(Pipeline.pipeline_id).all()

        print(f"Starting recalculation for {len(pipelines)} pipeline(s)...")

        updated_count = 0
        score_changes = 0
        level_changes = 0

        for pipe in pipelines:
            old_score = pipe.risk_score
            old_level = pipe.risk_level
            old_complaints = pipe.complaints_last_30_days
            old_leakage = pipe.leakage_complaints_30d

            recalculate_pipeline_risk_from_complaints(db, pipe)

            if (
                pipe.risk_score != old_score
                or pipe.risk_level != old_level
                or pipe.complaints_last_30_days != old_complaints
                or pipe.leakage_complaints_30d != old_leakage
            ):
                updated_count += 1
                if pipe.risk_score != old_score:
                    score_changes += 1
                if pipe.risk_level != old_level:
                    level_changes += 1
                    print(
                        f"  [{pipe.pipeline_id}] Risk level changed: {old_level} -> {pipe.risk_level} "
                        f"(Score: {old_score} -> {pipe.risk_score}, Complaints: {old_complaints} -> {pipe.complaints_last_30_days})"
                    )

        db.commit()

        print("\n=== Recalculation Summary ===")
        print(f"Total pipelines processed : {len(pipelines)}")
        print(f"Pipelines with updates    : {updated_count}")
        print(f"Risk score changed        : {score_changes}")
        print(f"Risk level changed        : {level_changes}")
        print("=============================")

    finally:
        db.close()


if __name__ == "__main__":
    main()
