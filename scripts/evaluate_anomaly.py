from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.anomaly_detection.config import load_anomaly_config
from backend.app.anomaly_detection.evaluator import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate anomaly detector on MVTec AD test set")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    metrics = evaluate(load_anomaly_config(args.config))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
