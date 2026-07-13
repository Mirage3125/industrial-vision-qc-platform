from __future__ import annotations

import argparse
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.anomaly_detection.dataset import build_manifest

MVTec_URLS = {
    "metal_nut": "https://www.mvtec.com/company/research/datasets/mvtec-ad/downloads/metal_nut.tar.xz",
    "bottle": "https://www.mvtec.com/company/research/datasets/mvtec-ad/downloads/bottle.tar.xz",
    "capsule": "https://www.mvtec.com/company/research/datasets/mvtec-ad/downloads/capsule.tar.xz",
    "screw": "https://www.mvtec.com/company/research/datasets/mvtec-ad/downloads/screw.tar.xz",
}


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            file.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download one MVTec AD category")
    parser.add_argument("--category", default="metal_nut", choices=sorted(MVTec_URLS))
    parser.add_argument("--output", type=Path, default=Path("data/raw/mvtec-ad"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts/datasets/mvtec-ad/manifest.json"),
    )
    args = parser.parse_args()
    category_dir = args.output / args.category
    if not category_dir.is_dir():
        archive = args.output / "downloads" / f"{args.category}.tar.xz"
        try:
            download(MVTec_URLS[args.category], archive)
            args.output.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive) as tar:
                tar.extractall(args.output)
        except Exception as error:
            marker = {
                "status": "BLOCKED_DATA_DOWNLOAD",
                "category": args.category,
                "url": MVTec_URLS[args.category],
                "error": repr(error),
            }
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(
                json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(marker, ensure_ascii=False, indent=2))
            raise SystemExit(2) from error
    manifest = build_manifest(args.output, args.category, MVTec_URLS[args.category], args.manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
