import os
import sys
from typing import Any, Dict, List, Optional
import torch

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False


def detect_execution_environment() -> Dict[str, Any]:
    """
    Detect available computing hardware (CUDA GPU, MPS, CPU, ONNX runtime)
    and return configuration recommendations for production AI hardening.
    """
    cuda_available = torch.cuda.is_available()
    device_type = "cpu"
    device_name = "CPU"
    gpu_memory_gb = 0.0

    if cuda_available:
        device_type = "cuda"
        device_name = torch.cuda.get_device_name(0)
        try:
            gpu_memory_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
        except Exception:
            gpu_memory_gb = 0.0
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device_type = "mps"
        device_name = "Apple Silicon GPU (MPS)"

    onnx_providers: List[str] = []
    if HAS_ONNX:
        try:
            onnx_providers = ort.get_available_providers()
        except Exception:
            onnx_providers = ["CPUExecutionProvider"]

    cpu_count = os.cpu_count() or 4

    # Recommendation for ANPR OCR inference
    # EasyOCR on CPU benefits from 4-8 threads without overwhelming other stream pipelines
    recommended_threads = min(8, max(2, cpu_count // 2))
    recommended_batch_size = 8 if cuda_available else 1

    return {
        "device": device_type,
        "device_name": device_name,
        "cuda_available": cuda_available,
        "gpu_memory_gb": gpu_memory_gb,
        "onnx_available": HAS_ONNX,
        "onnx_providers": onnx_providers,
        "cpu_count": cpu_count,
        "recommended_threads": recommended_threads,
        "recommended_batch_size": recommended_batch_size,
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
    }


def optimize_runtime_threads() -> None:
    """Apply thread optimization for PyTorch CPU inference if running without GPU."""
    env = detect_execution_environment()
    if not env["cuda_available"]:
        threads = env["recommended_threads"]
        try:
            torch.set_num_threads(threads)
        except Exception:
            pass
