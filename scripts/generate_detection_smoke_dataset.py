import argparse
from pathlib import Path

from backend.app.detection import generate_voc_smoke_dataset, load_detection_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tiny VOC data for pipeline smoke tests")
    parser.add_argument("--output", type=Path, default=Path("artifacts/detection/smoke-data/voc"))
    parser.add_argument("--config", type=Path, default=Path("configs/detection/neu-det.yaml"))
    args = parser.parse_args()
    config = load_detection_config(args.config)
    images, annotations = generate_voc_smoke_dataset(args.output, config.class_names)
    print(f"images={images}")
    print(f"annotations={annotations}")


if __name__ == "__main__":
    main()
