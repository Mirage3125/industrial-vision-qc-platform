from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.anomaly_detection.config import load_anomaly_config
from backend.app.anomaly_detection.dataset import build_manifest
from backend.app.anomaly_detection.trainer import train_padim_statistical


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the project anomaly detector")
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest", default="artifacts/datasets/mvtec-ad/manifest.json")
    args = parser.parse_args()
    config = load_anomaly_config(Path(args.config))
    manifest = build_manifest(
        config.data_root,
        config.category,
        "MVTec AD",
        Path(args.manifest),
    )
    metadata = train_padim_statistical(config)
    print(json.dumps({"manifest": manifest, "training": metadata}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
