from pathlib import Path

import cv2
import numpy as np


def generate_voc_smoke_dataset(root: Path, class_names: list[str]) -> tuple[Path, Path]:
    """Generate tiny geometric VOC samples for pipeline tests, never model metrics."""

    images_dir = root / "images"
    annotations_dir = root / "annotations"
    images_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)
    for index in range(8):
        class_name = class_names[index % len(class_names)]
        image = np.full((96, 128, 3), 210, dtype=np.uint8)
        x1, y1 = 10 + index, 20
        x2, y2 = 48 + index, 60
        cv2.rectangle(image, (x1, y1), (x2, y2), (25, 25, 25), -1)
        filename = f"smoke_{index:02d}.jpg"
        cv2.imwrite(str(images_dir / filename), image)
        xml = f"""<annotation><filename>{filename}</filename><size><width>128</width>
<height>96</height><depth>3</depth></size><object><name>{class_name}</name>
<bndbox><xmin>{x1}</xmin><ymin>{y1}</ymin><xmax>{x2}</xmax><ymax>{y2}</ymax>
</bndbox></object></annotation>"""
        (annotations_dir / f"smoke_{index:02d}.xml").write_text(xml, encoding="utf-8")
    return images_dir, annotations_dir
