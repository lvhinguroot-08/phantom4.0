"""
YOLO26 Utility Functions
Bounding box parsing, class mapping, tensor transformations, and image preprocessing.
"""
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

COCO_TO_PHANTOM_CLASSES: Dict[Union[int, str], str] = {
    0: "PERSON",
    "person": "PERSON",
    "pedestrian": "PERSON",
    1: "BICYCLE",
    "bicycle": "BICYCLE",
    "bike": "BICYCLE",
    2: "CAR",
    "car": "CAR",
    "sedan": "CAR",
    "suv": "CAR",
    "hatchback": "CAR",
    "taxi": "CAR",
    3: "MOTORCYCLE",
    "motorcycle": "MOTORCYCLE",
    "motorbike": "MOTORCYCLE",
    "scooter": "MOTORCYCLE",
    "two_wheeler": "MOTORCYCLE",
    5: "BUS",
    "bus": "BUS",
    "minibus": "BUS",
    "transit_bus": "BUS",
    7: "TRUCK",
    "truck": "TRUCK",
    "lorry": "TRUCK",
    "pickup": "TRUCK",
    "van": "VAN",
    "auto_rickshaw": "AUTO_RICKSHAW",
    "autorickshaw": "AUTO_RICKSHAW",
    "rickshaw": "AUTO_RICKSHAW",
    "tuk_tuk": "AUTO_RICKSHAW",
    "tuktuk": "AUTO_RICKSHAW",
    "three_wheeler": "AUTO_RICKSHAW",
    "license_plate": "LICENSE_PLATE",
    "licence_plate": "LICENSE_PLATE",
    "plate": "LICENSE_PLATE",
}


def normalize_class_name(raw_name: Union[int, str]) -> str:
    if isinstance(raw_name, int) or (isinstance(raw_name, str) and raw_name.isdigit()):
        return COCO_TO_PHANTOM_CLASSES.get(int(raw_name), "OTHER_VEHICLE")
    
    token = str(raw_name).strip().lower().replace("-", "_").replace(" ", "_")
    return COCO_TO_PHANTOM_CLASSES.get(token, token.upper())


def format_bounding_box(xyxy: List[float], width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, float]:
    x1, y1, x2, y2 = [float(v) for v in xyxy]
    if width and height:
        x1 = max(0.0, min(float(width), x1))
        y1 = max(0.0, min(float(height), y1))
        x2 = max(0.0, min(float(width), x2))
        y2 = max(0.0, min(float(height), y2))
    return {
        "x1": round(x1, 2),
        "y1": round(y1, 2),
        "x2": round(x2, 2),
        "y2": round(y2, 2),
        "width": round(abs(x2 - x1), 2),
        "height": round(abs(y2 - y1), 2),
    }


def preprocess_image(image_input: Any) -> Optional[np.ndarray]:
    if image_input is None:
        return None
    if isinstance(image_input, np.ndarray):
        return image_input
    if hasattr(image_input, "read"):
        import cv2
        data = image_input.read()
        nparr = np.frombuffer(data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return None
