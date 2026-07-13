from pathlib import Path

import cv2
import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper

from backend.app.benchmark import benchmark_onnx, write_benchmark_reports
from backend.app.inference import OnnxYoloDetector, TensorRTDetector, available_providers
from backend.app.inference.yolo_postprocess import LetterboxInfo, postprocess_yolo


def _average_model(path: Path) -> None:
    input_info = helper.make_tensor_value_info("images", TensorProto.FLOAT, ["batch", 3, 32, 32])
    output_info = helper.make_tensor_value_info("features", TensorProto.FLOAT, ["batch", 3, 1, 1])
    graph = helper.make_graph(
        [helper.make_node("GlobalAveragePool", ["images"], ["features"])],
        "average-smoke",
        [input_info],
        [output_info],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 10
    onnx.checker.check_model(model)
    onnx.save(model, path)


def _detection_model(path: Path) -> None:
    input_info = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 64, 64])
    output_info = helper.make_tensor_value_info("detections", TensorProto.FLOAT, [1, 1, 6])
    values = helper.make_tensor("constant", TensorProto.FLOAT, [1, 1, 6], [10, 12, 40, 44, 0.9, 0])
    graph = helper.make_graph(
        [helper.make_node("Constant", [], ["detections"], value=values)],
        "detector-smoke",
        [input_info],
        [output_info],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 10
    onnx.save(model, path)


def test_onnx_model_and_cpu_benchmark_reports(tmp_path: Path) -> None:
    model_path = tmp_path / "average.onnx"
    _average_model(model_path)
    onnx.checker.check_model(onnx.load(model_path), full_check=True)

    report = benchmark_onnx(model_path, "cpu", [1, 4], warmup=2, iterations=5)
    json_path, markdown_path = write_benchmark_reports(report, tmp_path, "cpu")

    assert report["actual_provider"] == "CPUExecutionProvider"
    assert report["results"][0]["p95_latency_ms"] >= 0
    assert report["results"][0]["fps"] > 0
    assert report["results"][1]["throughput_images_per_second"] > 0
    assert json_path.is_file() and markdown_path.is_file()


def test_onnx_detector_uses_shared_postprocessing(tmp_path: Path) -> None:
    model_path = tmp_path / "detector.onnx"
    image_path = tmp_path / "surface.png"
    _detection_model(model_path)
    assert cv2.imwrite(str(image_path), np.full((64, 64, 3), 180, dtype=np.uint8))

    result = OnnxYoloDetector(model_path, ["scratch"], provider="cpu").predict(image_path)

    assert result.detector_type == "yolo_onnx_cpu"
    assert result.defect_count == 1
    assert result.regions[0].class_name == "scratch"
    assert result.regions[0].confidence == pytest.approx(0.9)


def test_postprocessing_applies_confidence_and_nms() -> None:
    output = np.array(
        [[[10, 10, 30, 30, 0.9, 0], [11, 11, 31, 31, 0.8, 0], [1, 1, 2, 2, 0.1, 0]]],
        dtype=np.float32,
    )
    info = LetterboxInfo(1.0, 0, 0, 64, 64)

    regions = postprocess_yolo(output, info, ["scratch"], 0.25, 0.5)

    assert len(regions) == 1
    assert regions[0].bounding_box.x1 == 10


def test_provider_and_tensorrt_contract(tmp_path: Path) -> None:
    assert "CPUExecutionProvider" in available_providers()
    with pytest.raises(RuntimeError, match="not been validated"):
        TensorRTDetector().predict(tmp_path / "unused.jpg")
