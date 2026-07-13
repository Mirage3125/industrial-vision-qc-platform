# Architecture decisions

## Stage 7 anomaly detection algorithm

- Selected algorithm: PaDiM-style statistical anomaly detection.
- Reason: PaDiM is stable for one-class industrial anomaly detection, can produce image-level scores and pixel-level anomaly maps, and does not require retraining the already accepted YOLO model.
- Why not PatchCore now: a production PatchCore implementation needs a nearest-neighbor memory bank and feature backbone dependency choices that are heavier to validate on this Windows workstation.
- Why not EfficientAD now: EfficientAD requires a teacher/student training stack and more dependency/version management than this stage should impose on the already accepted YOLO and ONNX environments.
- GPU and speed consideration: the current implementation uses OpenCV/NumPy statistics and is deterministic. It avoids installing anomalib/lightning into the YOLO environment. A future deep-feature PaDiM or PatchCore backend can be added behind the same predictor interface.
- Known limitation: this implementation is a practical PaDiM-style baseline using color and gradient local statistics rather than ImageNet CNN embeddings. Formal completion still requires real MVTec AD data, real training, and real evaluation metrics.

## Stage 11 documentation and release posture

- README and public-facing docs use `padim_statistical`, not "complete PaDiM reproduction".
- ONNX CPU is verified from JSON reports; ONNX CUDA is explicitly limited because actual provider fell back to CPU.
- TensorRT, Docker GPU, automatic training and automatic model publishing are treated as future work.
- Dataset archives, model weights, local databases, build caches and environment files are ignored for GitHub publication.
