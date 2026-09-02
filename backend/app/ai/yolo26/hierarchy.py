"""
PHANTOM Vision Intelligence V2 — Hierarchical Vision & Taxonomy Engine
======================================================================
Defines the authoritative 3-tier surveillance taxonomy, grounded confidence tiers,
and strict uncertainty handling.

Taxonomy Structure:
Level 1: Broad Category (PERSON, TWO_WHEELER, CAR, AUTO_RICKSHAW, BUS, TRUCK, VAN, BICYCLE, OTHER_VEHICLE)
Level 2: Sub-category (e.g. TWO_WHEELER -> SCOOTER / MOTORCYCLE; CAR -> HATCHBACK_TALLBOY / HATCHBACK_SPORT / SEDAN / SUV)
Level 3: Specific Make & Model (e.g. Honda Activa, Hero Splendor, Maruti Suzuki WagonR, Maruti Suzuki Swift, Bajaj Compact Auto)

Confidence & Uncertainty Philosophy:
- Never force a specific make/model when visual evidence or resolution is low.
- Output UNCERTAIN / UNKNOWN status instead of generating overly confident incorrect labels.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ClassificationStatus(str, Enum):
    """Human-readable classification confidence status."""
    CONFIDENT = "CONFIDENT"      # High certainty (>= 0.78 confidence with strong structural evidence)
    LIKELY = "LIKELY"            # Probable classification (0.55 <= score < 0.78)
    UNCERTAIN = "UNCERTAIN"      # Low margin between candidates (< 0.55 or ambiguous silhouette)
    UNKNOWN = "UNKNOWN"          # Generic category detected, but sub-type/model unknown


class EventLifecycle(str, Enum):
    """Lifecycle state of a detected surveillance track."""
    DETECTED = "DETECTED"        # Initial raw detection (1-2 frames)
    TRACKING = "TRACKING"        # Active tracking (3+ frames)
    CONFIRMED = "CONFIRMED"      # Temporally confirmed event (high persistence & anatomical/physical validity)
    ENDED = "ENDED"              # Track exited or lost


@dataclass
class HierarchicalClassificationResult:
    """Structured hierarchical classification with explicit uncertainty state."""
    # Level 1: Broad Category
    category: str                           # "PERSON", "TWO_WHEELER", "CAR", "AUTO_RICKSHAW", "BUS", "TRUCK", "VAN", "BICYCLE"
    category_confidence: float              # 0.0 to 1.0

    # Level 2: Sub-type
    subtype: Optional[str] = None           # "SCOOTER", "MOTORCYCLE", "HATCHBACK_TALLBOY", "HATCHBACK_SPORT", "SEDAN", "SUV", etc.
    subtype_confidence: Optional[float] = None

    # Level 3: Fine-Grained Make & Model
    make: Optional[str] = None              # "Honda", "Hero", "Maruti Suzuki", "Hyundai", "Bajaj", "Tata Motors"
    model: Optional[str] = None             # "Activa 6G", "Splendor+", "WagonR", "Swift", "Compact Auto", "Starbus"
    model_confidence: Optional[float] = None

    # Uncertainty & Presentation
    classification_status: ClassificationStatus = ClassificationStatus.UNKNOWN
    display_label: str = ""
    candidate_scores: Dict[str, float] = field(default_factory=dict)
    rejection_reason: Optional[str] = None
    is_hard_negative: bool = False          # True if filtered as pole/streetlight/static fixture

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "category_confidence": round(self.category_confidence, 4),
            "subtype": self.subtype,
            "subtype_confidence": round(self.subtype_confidence, 4) if self.subtype_confidence is not None else None,
            "make": self.make,
            "model": self.model,
            "model_confidence": round(self.model_confidence, 4) if self.model_confidence is not None else None,
            "classification_status": self.classification_status.value,
            "display_label": self.display_label,
            "candidate_scores": {k: round(v, 4) for k, v in self.candidate_scores.items()},
            "is_hard_negative": self.is_hard_negative,
            "rejection_reason": self.rejection_reason,
        }


class VisionTaxonomy:
    """Master Authoritative Class Taxonomy for PHANTOM AI Surveillance Platform."""

    # Authoritative Level 1 Broad Classes
    BROAD_CATEGORIES = {
        "PERSON",
        "TWO_WHEELER",
        "CAR",
        "AUTO_RICKSHAW",
        "BUS",
        "TRUCK",
        "VAN",
        "BICYCLE",
        "OTHER_VEHICLE",
        "LICENSE_PLATE",
    }

    # Two-Wheeler Hierarchy
    TWO_WHEELER_SUBTYPES = {"SCOOTER", "MOTORCYCLE"}
    SCOOTER_MODELS = {
        "Honda Activa": {"brand": "Honda", "model": "Activa 6G"},
        "Suzuki Access": {"brand": "Suzuki", "model": "Access 125"},
        "TVS Jupiter": {"brand": "TVS", "model": "Jupiter"},
        "Hero Pleasure": {"brand": "Hero", "model": "Pleasure+"},
    }
    MOTORCYCLE_MODELS = {
        "Hero Splendor": {"brand": "Hero", "model": "Splendor+"},
        "Honda Shine": {"brand": "Honda", "model": "Shine 125"},
        "Bajaj Pulsar": {"brand": "Bajaj", "model": "Pulsar 150"},
        "Royal Enfield Classic": {"brand": "Royal Enfield", "model": "Classic 350"},
        "TVS Apache": {"brand": "TVS", "model": "Apache RTR"},
        "Hero HF Deluxe": {"brand": "Hero", "model": "HF Deluxe"},
    }

    # Car Hierarchy
    CAR_SUBTYPES = {"HATCHBACK_TALLBOY", "HATCHBACK_SPORT", "SEDAN", "SUV", "MUV"}
    TALLBOY_MODELS = {
        "Maruti Suzuki WagonR": {"brand": "Maruti Suzuki", "model": "WagonR"},
        "Hyundai Santro": {"brand": "Hyundai", "model": "Santro"},
    }
    SPORT_HATCHBACK_MODELS = {
        "Maruti Suzuki Swift": {"brand": "Maruti Suzuki", "model": "Swift"},
        "Maruti Suzuki Baleno": {"brand": "Maruti Suzuki", "model": "Baleno"},
        "Hyundai i20": {"brand": "Hyundai", "model": "i20"},
        "Tata Tiago": {"brand": "Tata Motors", "model": "Tiago"},
        "Maruti Suzuki Alto": {"brand": "Maruti Suzuki", "model": "Alto K10"},
    }
    SEDAN_MODELS = {
        "Maruti Suzuki Dzire": {"brand": "Maruti Suzuki", "model": "Dzire"},
        "Honda City": {"brand": "Honda", "model": "City"},
        "Hyundai Verna": {"brand": "Hyundai", "model": "Verna"},
        "Hyundai Aura": {"brand": "Hyundai", "model": "Aura"},
    }
    SUV_MODELS = {
        "Hyundai Creta": {"brand": "Hyundai", "model": "Creta"},
        "Tata Nexon": {"brand": "Tata Motors", "model": "Nexon"},
        "Mahindra Scorpio": {"brand": "Mahindra", "model": "Scorpio-N"},
        "Kia Seltos": {"brand": "Kia", "model": "Seltos"},
        "Toyota Fortuner": {"brand": "Toyota", "model": "Fortuner"},
    }

    # Commercial & 3-Wheeler Hierarchy
    AUTO_RICKSHAW_MODELS = {
        "Bajaj Compact Auto": {"brand": "Bajaj", "model": "Compact Auto Rickshaw"},
        "Piaggio Ape City": {"brand": "Piaggio", "model": "Ape City Plus"},
        "Mahindra Alfa": {"brand": "Mahindra", "model": "Alfa Auto"},
    }
    TRUCK_MODELS = {
        "Tata Heavy Truck": {"brand": "Tata Motors", "model": "1613 Heavy Truck"},
        "Ashok Leyland Ecomet": {"brand": "Ashok Leyland", "model": "Ecomet Truck"},
        "Tata Ace Mini Truck": {"brand": "Tata Motors", "model": "Ace Gold Mini-Truck"},
        "Mahindra Bolero Maxi Truck": {"brand": "Mahindra", "model": "Bolero Maxi Truck"},
    }
    BUS_MODELS = {
        "Tata Starbus": {"brand": "Tata Motors", "model": "Starbus Urban"},
        "Ashok Leyland GSRTC": {"brand": "Ashok Leyland", "model": "JanBus BRTS"},
        "Volvo Intercity": {"brand": "Volvo", "model": "9400 B11R Multi-Axle"},
    }

    @classmethod
    def format_tactical_label(
        cls,
        category: str,
        subtype: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        confidence: float = 0.0,
        status: ClassificationStatus = ClassificationStatus.UNKNOWN,
        track_id: Optional[int] = None,
    ) -> str:
        """
        Builds a truthful, non-hallucinating tactical HUD label.
        Examples:
        - Confident: "Car #1042 | Maruti WagonR (84%)"
        - Likely: "Two-Wheeler #31 | Likely Scooter (68%)"
        - Uncertain: "Car #77 | Model Uncertain (52%)"
        - Unknown: "Two-Wheeler #12 | Model Unknown (92%)"
        """
        pct = int(round(confidence * 100))
        track_str = f" #{track_id}" if track_id is not None else ""
        cat_disp = category.replace("_", " ").title()

        if status == ClassificationStatus.CONFIDENT and make and model:
            return f"{cat_disp}{track_str} | {make} {model} ({pct}%)"
        elif status == ClassificationStatus.LIKELY and model:
            return f"{cat_disp}{track_str} | Likely {model} ({pct}%)"
        elif status == ClassificationStatus.LIKELY and subtype:
            sub_disp = subtype.replace("_", " ").title()
            return f"{cat_disp}{track_str} | Likely {sub_disp} ({pct}%)"
        elif status == ClassificationStatus.UNCERTAIN:
            return f"{cat_disp}{track_str} | Model Uncertain ({pct}%)"
        else:
            return f"{cat_disp}{track_str} | {pct}%"
