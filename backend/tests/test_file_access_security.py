from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.app.core.config import PROJECT_ROOT


def _write_test_image() -> Path:
    output = PROJECT_ROOT / "artifacts" / "test-file-access" / "safe.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((16, 16, 3), 180, dtype=np.uint8)
    assert cv2.imwrite(str(output), image)
    return output


def test_serves_allowed_image(client: TestClient) -> None:
    image = _write_test_image()
    response = client.get(f"/api/v1/files?path={image.relative_to(PROJECT_ROOT).as_posix()}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_rejects_path_traversal(client: TestClient) -> None:
    response = client.get("/api/v1/files?path=artifacts/../.env")
    assert response.status_code == 403


def test_rejects_url_encoded_path_traversal(client: TestClient) -> None:
    response = client.get("/api/v1/files?path=artifacts%2F..%2F.env")
    assert response.status_code == 403


def test_rejects_absolute_path(client: TestClient) -> None:
    response = client.get(f"/api/v1/files?path={PROJECT_ROOT / '.env'}")
    assert response.status_code == 403


def test_rejects_env_file(client: TestClient) -> None:
    response = client.get("/api/v1/files?path=.env")
    assert response.status_code == 403


def test_rejects_project_external_file(client: TestClient) -> None:
    response = client.get("/api/v1/files?path=../outside.txt")
    assert response.status_code == 403
