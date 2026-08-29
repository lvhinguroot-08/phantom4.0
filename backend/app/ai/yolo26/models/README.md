# YOLO26 Model Weights Directory

Place your custom trained YOLO26 weights here:
- Recommended primary weight file: `yolo26.pt` (or `yolo26n.pt` / `yolo26s.pt` / `yolo26m.pt`)
- Supported formats: `.pt` (PyTorch Checkpoint), `.onnx` (ONNX Runtime), `.engine` (TensorRT)

Configurable via environment variable:
`YOLO26_MODEL_PATH=backend/app/ai/yolo26/models/yolo26.pt`

If no weights are placed here, the engine automatically checks for baseline `yolov8n.pt` or runs in deterministic synthetic mode.
