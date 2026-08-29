"""
Unit Tests for YOLO26 Model Loader & Runtime Singleton
Validates singleton instantiation, compute device selection, and model weight discovery.
"""
import pytest
from app.ai.yolo26.config import YOLO26Config
from app.ai.yolo26.model_loader import YOLO26ModelLoader, get_model_loader
from app.ai.yolo26.detector import YOLO26Detector, get_detector


def test_yolo26_model_loader_singleton():
    """Verify that YOLO26ModelLoader is instantiated strictly once as a singleton."""
    loader1 = get_model_loader()
    loader2 = get_model_loader()
    assert loader1 is loader2, "YOLO26ModelLoader must be a singleton instance"


def test_yolo26_detector_singleton():
    """Verify that YOLO26Detector reuses the singleton model loader."""
    det1 = get_detector()
    det2 = get_detector()
    assert det1 is det2, "YOLO26Detector must be a singleton instance"
    assert det1.loader is det2.loader


def test_yolo26_model_loader_status():
    """Verify status dictionary contains all expected health and configuration keys."""
    loader = get_model_loader()
    status = loader.get_status()

    assert "model_name" in status
    assert "model_version" in status
    assert "is_loaded" in status
    assert "device" in status
    assert "resolved_model_path" in status
    assert "active_weights_source" in status
    assert "is_baseline_fallback" in status
    assert status["device"] in ("cpu", "cuda:0", "cuda")


def test_yolo26_config_defaults():
    """Verify default configuration mappings and threshold ranges."""
    cfg = YOLO26Config()
    assert cfg.model_name == "YOLO26"
    assert 0.0 < cfg.confidence_threshold <= 1.0
    assert 0.0 < cfg.iou_threshold <= 1.0
    assert "PERSON" in cfg.target_classes
    assert "CAR" in cfg.target_classes


def test_yolo26_detect_frame_contract():
    """Verify detect_frame returns exact dictionary structure and handles invalid inputs safely."""
    import numpy as np
    detector = get_detector()

    # 1. Invalid input tests
    assert detector.detect_frame(None) == []
    assert detector.detect_frame(np.array([])) == []

    # 2. Blank frame
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    results = detector.detect_frame(blank, confidence_threshold=0.5)
    assert isinstance(results, list)

    # 3. Verify output schema on test scene
    test_frame = np.random.randint(0, 255, (300, 400, 3), dtype=np.uint8)
    dets = detector.detect_frame(test_frame)
    for d in dets:
        assert "class_id" in d
        assert "class_name" in d
        assert "confidence" in d
        assert "bbox" in d
        bbox = d["bbox"]
        assert "x1" in bbox and "y1" in bbox and "x2" in bbox and "y2" in bbox
        assert 0 <= bbox["x1"] <= bbox["x2"] <= 400
        assert 0 <= bbox["y1"] <= bbox["y2"] <= 300

