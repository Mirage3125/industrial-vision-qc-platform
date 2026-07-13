import argparse
from pathlib import Path

from backend.app.data_quality import DataQualityScanner, load_config
from backend.app.db.session import SessionLocal
from backend.app.schemas.domain import DataQualityReportCreate
from backend.app.services import DataQualityService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the independent data quality scanner")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/data_quality/default.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()
    artifacts = DataQualityScanner(load_config(args.config)).scan(args.dataset, args.output)
    summary = artifacts.report["summary"]
    print(f"JSON: {artifacts.json_path}")
    print(f"HTML: {artifacts.html_path}")
    print(f"Summary: {summary}")
    if args.persist:
        with SessionLocal() as session:
            report = DataQualityService(session).save_report(
                DataQualityReportCreate(
                    dataset_path=str(args.dataset.resolve()),
                    total_images=summary["total_images"],
                    duplicate_count=summary["duplicate_count"],
                    blurry_count=summary["blurry_count"],
                    overexposed_count=summary["overexposed_count"],
                    underexposed_count=summary["underexposed_count"],
                    invalid_annotation_count=summary["invalid_annotation_count"],
                    leakage_count=summary["leakage_count"],
                    image_size_statistics=artifacts.report["image_size_statistics"],
                    class_distribution=artifacts.report["class_distribution"],
                    issue_samples=artifacts.report["issues"],
                    statistics=summary,
                    report_path=str(artifacts.json_path.resolve()),
                ),
                operator="data-quality-cli",
            )
        print(f"Database report id: {report.id}")


if __name__ == "__main__":
    main()
