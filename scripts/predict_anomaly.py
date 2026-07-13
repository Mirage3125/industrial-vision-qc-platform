from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.anomaly_detection.predictor import PaDiMStyleAnomalyDetector


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict one image with anomaly detector")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/anomaly_predictions"))
    args = parser.parse_args()
    result = PaDiMStyleAnomalyDetector(args.model).predict_anomaly(args.image, args.output)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
