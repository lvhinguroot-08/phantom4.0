"""
PHANTOM AI Copilot — Multilingual Entity Resolution Engine
Resolves camera names, camera IDs, locations, landmarks, vehicle registration plates,
districts, departments, and surveillance entities from natural language across
Hindi, Gujarati, Marathi, English, and Hinglish.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata

from app.core.logging import logger


@dataclass
class ResolvedCameraMatch:
    camera_id: str
    camera_code: str
    name: str
    district: str
    confidence: float
    match_reason: str
    raw_data: Dict[str, Any]


@dataclass
class EntityResolutionResult:
    query: str
    detected_language: str  # 'en', 'hi', 'gu', 'mr', 'hinglish'
    resolved_camera: Optional[ResolvedCameraMatch] = None
    candidate_cameras: List[ResolvedCameraMatch] = None
    is_ambiguous: bool = False
    resolved_plate: Optional[str] = None
    resolved_district: Optional[str] = None
    resolved_vehicle_color: Optional[str] = None
    resolved_vehicle_model: Optional[str] = None
    resolved_detection_type: Optional[str] = None  # 'person', 'vehicle', 'license_plate', 'all'
    requested_action: Optional[str] = None  # 'OPEN_STREAM', 'RUN_DETECTION', 'TRACE_VEHICLE', 'SHOW_HEALTH', 'NAVIGATE_MAP', etc.
    time_window: Optional[str] = None

    def __post_init__(self):
        if self.candidate_cameras is None:
            self.candidate_cameras = []


class EntityResolver:
    """Multilingual Entity & Intent Resolver for Gujarat Police Surveillance Grid."""

    # Common aliases & multilingual transcriptions for Gujarat cameras
    CAMERA_ALIASES = {
        "ongc": ["cam03", "03 O.N.G.C. Office", "o.n.g.c", "ongc office", "ઓએનજીસી", "ओएनजीसी", "ongc camera", "ongc feed"],
        "chimanbhai": ["cam01", "01 Chiman bhai Bridge", "chiman bhai", "chimanbhai bridge", "ચીમનભાઈ", "ચીમન ભાઈ", "चिमनभाई"],
        "janpath": ["cam02", "02 Janpath", "જનપથ", "जनपथ"],
        "paldi": ["cam04", "04 Paldi Circle", "પાલડી", "पालडी", "paldi circle"],
        "visat": ["cam05", "cam16", "05 Visat teen Rasta", "16 Visat P2", "વિસત", "विसत", "visat teen rasta"],
        "timbavadi": ["cam06", "06 Timbavadi gate-Junagadh", "ટિંબાવડી", "टिंबावडी"],
        "hero showroom": ["cam07", "07 hero-showroom-gir-somnath", "હીરો શોરૂમ", "हीरो शोरूम", "somnath"],
        "majewadi": ["cam08", "08 majewadi-gate-junagadh", "મજેવડી", "मजेवडी"],
        "bypass": ["cam09", "09 new-bypass-near-by-circle-junagadh-2", "બાયપાસ", "बायपास"],
        "char chowk": ["cam10", "10 char-chowk-road-2-junagadh", "ચાર ચોક", "चार चौक"],
        "dolatpara": ["cam11", "11 dolatpara-junagadh", "દોલતપરા", "दोलतपरा"],
        "adalaj": ["cam12", "12 Tri Mandir Adalaj Tollnaka", "અડાલજ", "अडालज", "tri mandir", "trimandir"],
        "cn vidhyalaya": ["cam13", "13 CN Vidhyalaya", "સીએન વિદ્યાલય", "सीएन विद्यालय", "cn school"],
        "delight": ["cam14", "14 Delight RLVD", "ડિલાઇટ", "डिलाइट"],
        "suvidha": ["cam15", "15 Suvidha park", "સુવિધા પાર્ક", "सुविधा पार्क"],
        "rajkot bus port": ["cam17", "17 Rajkot Bus Port CCTV", "રાજકોટ બસ પોર્ટ", "राजकोट बस पोर्ट"],
        "rajkot cctv": ["cam18", "18 Rajkot CCTV", "રાજકોટ સીસીટીવી", "राजकोट सीसीटीवी"],
        "khaparia": ["cam19", "19 KHAPARIA GRAM PANCHAYAT", "ખપારિયા", "खपारिया", "gandevi"],
        "mohanpura": ["cam20", "20 Mohanpura", "મોહનપુરા", "मोहनपुरा"],
        "patan": ["cam21", "23 Patan Dethali Char Rasta", "પાટણ", "पाटण", "dethali"],
        "mervada": ["cam22", "28 BK Mervada tran Rasta", "મેરવાડા", "मेरवाडा"],
        "kheram": ["cam23", "30 kheram", "ખેરામ", "खेराम"],
        "dehgam": ["cam24", "33 dehgam", "દહેગામ", "दहेज", "दहेगाम"],
        "dhanori": ["cam25", "34 dhanori", "ધાનોરી", "धानोरी"],
        "tankal": ["cam26", "35 TANKAL", "તંકલ", "तंकल"],
        "bilimora": ["cam27", "cam28", "cam29", "36 bilimora", "37 bilimora", "38 bilimora", "બીલીમોરા", "બિલીમોરા", "बिलिमोरा"],
        "gandhidham": ["cam30", "Gandhidham Rambaugh p2", "ગાંધીધામ", "गांधीधाम", "rambaugh"],
    }

    DISTRICTS = [
        "ahmedabad", "surat", "vadodara", "rajkot", "gandhinagar", "bhavnagar",
        "jamnagar", "junagadh", "kutch", "navsari", "patan", "morbi", "kheda",
        "gir somnath", "narmada", "amreli", "anand", "arvalli", "banaskantha",
        "bharuch", "botad", "chhota udepur", "dahod", "dangs", "devbhoomi dwarka",
        "mahesana", "mahisagar", "panchmahal", "porbandar", "sabarkantha", "tapi",
        "surendranagar", "valsad"
    ]

    COLORS = {
        "white": ["white", "safed", "સફેદ", "सफेद", "dhaval", "shwet"],
        "black": ["black", "kala", "kali", "કાળો", "કાળી", "કાળા", "काला", "काली", "काले"],
        "red": ["red", "lal", "લાલ", "लाल"],
        "silver": ["silver", "ruperi", "રૂપેરી", "सिल्वर", "chandi"],
        "blue": ["blue", "neela", "nilo", "વાદળી", "ભૂરો", "नीला", "नीली"],
        "grey": ["grey", "gray", "rakhodi", "રાખોડી", "ग्रे", "स्लेटी"],
        "yellow": ["yellow", "peela", "pilo", "પીળો", "પીળા", "पीला", "पीली"],
        "green": ["green", "hara", "leelo", "લીલો", "લીલા", "हरा", "हरी"],
    }

    VEHICLE_MODELS = [
        "swift", "creta", "baleno", "i20", "innova", "bolero", "scorpio",
        "alto", "activa", "pulsar", "wagonr", "city", "fortuner", "thar",
        "ertiga", "seltos", "brezza", "verna", "splendor", "jupiter"
    ]

    def __init__(self):
        pass

    def detect_language(self, text: str) -> str:
        """Identifies whether text is Gujarati, Hindi/Marathi, Hinglish, or English."""
        gu_chars = sum(1 for ch in text if '\u0a80' <= ch <= '\u0aff')
        deva_chars = sum(1 for ch in text if '\u0900' <= ch <= '\u097f')
        total_len = len(text.strip()) or 1

        if gu_chars / total_len > 0.15:
            return "gu"
        if deva_chars / total_len > 0.15:
            # Check for Marathi-specific markers
            marathi_markers = ["आहेत", "कॅमेरे", "दाखवा", "सांगा", "किती", "सध्या"]
            if any(m in text for m in marathi_markers):
                return "mr"
            return "hi"

        # Check for Hinglish markers
        hinglish_words = ["kholo", "dikha", "dikhao", "batao", "bhai", "hai", "hain", "karo", "wali", "wala", "kaunse", "abhi", "kitne", "kya", "gaadi", "chalao", "dekh"]
        words = text.lower().split()
        if any(w in words for w in hinglish_words):
            return "hinglish"

        # Check for Gujarati in Latin script
        gujlish_words = ["che", "nathi", "ketla", "aapo", "batavo", "kem", "chhe"]
        if any(w in words for w in gujlish_words):
            return "gu"

        return "en"

    def normalize_text(self, text: str) -> str:
        """Cleans and standardizes text for entity matching."""
        # Strip diacritics where appropriate
        norm = unicodedata.normalize('NFKD', text)
        # Remove extra whitespace and lower case
        norm = re.sub(r'[^\w\s\.\-]', ' ', norm, flags=re.UNICODE)
        return ' '.join(norm.lower().split())

    def extract_license_plate(self, text: str) -> Optional[str]:
        """Extracts Indian license plate pattern (e.g. GJ 01 AB 1234, GJ01AB1234, MH 12 CD 5678)."""
        # Look for standard Indian plate format
        pattern = r'\b([a-zA-Z]{2}[-\s]?[0-9]{1,2}[-\s]?[a-zA-Z]{1,3}[-\s]?[0-9]{1,4})\b'
        match = re.search(pattern, text)
        if match:
            raw = match.group(1).upper()
            # Clean spaces and hyphens for canonical form
            clean = re.sub(r'[^A-Z0-9]', '', raw)
            if len(clean) >= 6 and len(clean) <= 11:
                return clean
        return None

    def match_camera_against_inventory(
        self, query: str, camera_inventory: List[Dict[str, Any]]
    ) -> Tuple[Optional[ResolvedCameraMatch], List[ResolvedCameraMatch]]:
        """
        Matches a natural language query against the active camera catalogue.
        Uses multi-pass alias matching, exact token matching, and substring scoring.
        """
        normalized_q = self.normalize_text(query)
        q_tokens = set(normalized_q.split())

        candidates: List[ResolvedCameraMatch] = []

        # 1. First Pass: Check alias dictionary for known landmarks (ONGC, Chimanbhai, etc.)
        generic_stopwords = {
            "cctv", "camera", "feed", "office", "gate", "road", "circle", "near",
            "rasta", "park", "bridge", "show", "open", "kholo", "dikha", "wali",
            "wala", "bhai", "hai", "hain", "karo", "dikhao", "batao", "kaise",
            "kya", "aur", "and", "ane", "che", "chhe", "number", "num", "status"
        }
        matched_cam_ids_from_aliases = set()
        for alias_key, alias_targets in self.CAMERA_ALIASES.items():
            for alias in alias_targets:
                norm_alias = self.normalize_text(alias)
                alias_distinctive = [t for t in norm_alias.split() if t not in generic_stopwords and len(t) > 2]
                # Match full alias phrase or distinctive landmark keyword (e.g. ongc, chiman, janpath)
                is_match = (
                    norm_alias in normalized_q or
                    (bool(alias_distinctive) and any(t in q_tokens for t in alias_distinctive))
                )
                if is_match:
                    # Found alias reference
                    # Find all cameras matching this alias key or targets
                    for cam in camera_inventory:
                        cid = str(cam.get("camera_id") or cam.get("id") or cam.get("camera_code") or "").lower()
                        cname = str(cam.get("name") or "").lower()
                        if alias_key in cname or cid in alias_targets or any(target.lower() in cname for target in alias_targets):
                            matched_cam_ids_from_aliases.add(cid)
                            score = 0.95 if norm_alias in normalized_q else 0.85
                            # Boost exact ONGC match
                            if "ongc" in normalized_q and "o.n.g.c" in cname.lower():
                                score = 0.99
                            resolved_cid = cam.get("camera_id") or cam.get("id") or cid
                            candidates.append(ResolvedCameraMatch(
                                camera_id=resolved_cid,
                                camera_code=(cam.get("camera_code") or resolved_cid).upper(),
                                name=cam.get("name") or "Unknown Camera",
                                district=cam.get("district") or "Gujarat",
                                confidence=score,
                                match_reason=f"Matched alias '{alias}' for {alias_key.upper()}",
                                raw_data=cam,
                            ))

        # Word to number mapping for flexible camera recognition
        word_to_num = {
            "one": 1, "first": 1, "1st": 1, "ek": 1, "એક": 1, "एक": 1, "पहला": 1, "પહેલો": 1,
            "two": 2, "second": 2, "2nd": 2, "do": 2, "બે": 2, "दो": 2, "दूसरा": 2, "બીજો": 2,
            "three": 3, "third": 3, "3rd": 3, "teen": 3, "ત્રણ": 3, "तीन": 3, "तीसरा": 3, "ત્રીજો": 3,
            "four": 4, "fourth": 4, "4th": 4, "char": 4, "ચાર": 4, "चार": 4, "चौथा": 4, "ચોથો": 4,
            "five": 5, "fifth": 5, "5th": 5, "paanch": 5, "panch": 5, "પાંચ": 5, "पांच": 5, "पांचवा": 5, "પાંચમો": 5,
            "six": 6, "sixth": 6, "6th": 6, "chhe": 6, "chhah": 6, "છ": 6, "छह": 6, "छठा": 6, "છઠ્ઠો": 6,
            "seven": 7, "seventh": 7, "7th": 7, "saat": 7, "સાત": 7, "सात": 7, "सातवां": 7, "સાતમો": 7,
            "eight": 8, "eighth": 8, "8th": 8, "aath": 8, "આઠ": 8, "आठ": 8, "आठवां": 8, "આઠમો": 8,
            "nine": 9, "ninth": 9, "9th": 9, "nau": 9, "નવ": 9, "नौ": 9, "नौवां": 9, "નવમો": 9,
            "ten": 10, "tenth": 10, "10th": 10, "das": 10, "દસ": 10, "दस": 10, "दसवां": 10, "દસમો": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
            "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
            "thirty": 30,
        }

        # 2. Second Pass: Flexible ID / Code / Number matching
        # Examples: "camera 5", "cam 5", "CAM-005", "fifth camera", "5 number ka camera khol", "7 num k camera", "camera number five", "camera no 5", "5"
        cam_code_patterns = [
            r'\bcam[\-_]?\s*([0-9]{1,2})\b',
            r'\bcamera[\-_]?\s*(?:no\.?|number|num)?\s*([0-9]{1,2})\b',
            r'\b([0-9]{1,2})\s*(?:number|no\.?|num|th|st|nd|rd)?\s*(?:ka|ke|ki|k|ko|nu|walo|wala|valo)?\s*(?:camera|cam|cctv)\b',
            r'\b([0-9]{1,2})\s*(?:number|no\.?|num)\b',
            r'\bcctv[\-_]?\s*(?:no\.?|number|num)?\s*([0-9]{1,2})\b',
            r'\b([0-9]{1,2})\s*નંબર\s*(?:નો|ના|ની)?\s*(?:કેમેરો|કૅમેરો)?\b',
            r'\b([0-9]{1,2})\s*नंबर\s*(?:का|के|की)?\s*(?:कैमरा|कॅमेरा)?\b',
        ]
        matched_cam_num = None
        for pattern in cam_code_patterns:
            code_match = re.search(pattern, normalized_q)
            if code_match:
                matched_cam_num = int(code_match.group(1))
                break

        # Check word-based numbers like "fifth camera", "camera five", "paanch number camera"
        if matched_cam_num is None:
            for w, num_val in word_to_num.items():
                word_patterns = [
                    rf'\bcamera\s+(?:no\.?|number\s+)?{w}\b',
                    rf'\b{w}\s+camera\b',
                    rf'\bcam\s+{w}\b',
                    rf'\b{w}\s+(?:number|no|num)\s*(?:ka|ke|ki|k|ko|nu)?\s*camera\b',
                    rf'\b{w}\s+(?:number|no|num)\b',
                    rf'\b{w}\s+નંબર\s*(?:કેમેરો|કૅમેરો)?\b',
                ]
                if any(re.search(p, normalized_q) for p in word_patterns):
                    matched_cam_num = num_val
                    break

        # Standalone single integer query (e.g. "5", "07")
        if matched_cam_num is None and normalized_q.strip().isdigit() and 1 <= int(normalized_q.strip()) <= 30:
            matched_cam_num = int(normalized_q.strip())

        if matched_cam_num is not None:
            num_str = str(matched_cam_num).zfill(2)
            target_code = f"cam{num_str}"
            for cam in camera_inventory:
                cid = str(cam.get("camera_id") or cam.get("id") or cam.get("camera_code") or "").lower()
                cname = str(cam.get("name") or "").lower()
                # Match "cam05", "cam5", or name starting with "05 " or "5 "
                if cid == target_code or cid == f"cam{matched_cam_num}" or cname.startswith(f"{num_str} ") or cname.startswith(f"{matched_cam_num} "):
                    resolved_cid = cam.get("camera_id") or cam.get("id") or target_code
                    candidates.append(ResolvedCameraMatch(
                        camera_id=resolved_cid,
                        camera_code=(cam.get("camera_code") or resolved_cid).upper(),
                        name=cam.get("name") or "Unknown Camera",
                        district=cam.get("district") or "Gujarat",
                        confidence=0.99,
                        match_reason=f"Exact camera number match '{target_code}' ({matched_cam_num})",
                        raw_data=cam,
                    ))

        # 3. Third Pass: Substring & Token matching against name and location
        for cam in camera_inventory:
            cid = str(cam.get("camera_id") or cam.get("id") or cam.get("camera_code") or "").lower()
            cname = str(cam.get("name") or "").lower()
            cloc = str(cam.get("location") or "").lower()
            cdist = str(cam.get("district") or "").lower()

            # Clean name tokens
            name_norm = self.normalize_text(cname)
            name_tokens = set(name_norm.split())

            common_tokens = q_tokens.intersection(name_tokens) - {"cctv", "camera", "gate", "road", "circle", "near", "rasta", "park", "bridge"}
            if common_tokens:
                score = 0.70 + (0.10 * len(common_tokens))
                resolved_cid = cam.get("camera_id") or cam.get("id") or cid
                candidates.append(ResolvedCameraMatch(
                    camera_id=resolved_cid,
                    camera_code=(cam.get("camera_code") or resolved_cid).upper(),
                    name=cam.get("name") or "Unknown Camera",
                    district=cam.get("district") or "Gujarat",
                    confidence=min(0.95, score),
                    match_reason=f"Matched name keywords: {', '.join(common_tokens)}",
                    raw_data=cam,
                ))

        # Deduplicate candidates by camera_id and keep highest confidence
        unique_cands: Dict[str, ResolvedCameraMatch] = {}
        for c in candidates:
            cid = c.camera_id
            if cid not in unique_cands or c.confidence > unique_cands[cid].confidence:
                unique_cands[cid] = c

        sorted_candidates = sorted(unique_cands.values(), key=lambda x: x.confidence, reverse=True)

        if not sorted_candidates:
            return None, []

        # If top candidate is very high confidence (>0.90) and strictly higher than second candidate
        if len(sorted_candidates) == 1 or (sorted_candidates[0].confidence >= 0.90 and sorted_candidates[0].confidence - sorted_candidates[1].confidence >= 0.10):
            return sorted_candidates[0], sorted_candidates

        # If multiple candidates share high confidence (ambiguity case like "Visat" matching cam05 and cam16)
        if len(sorted_candidates) > 1 and (sorted_candidates[0].confidence - sorted_candidates[1].confidence < 0.10):
            return None, sorted_candidates

        return sorted_candidates[0], sorted_candidates

    def resolve(
        self, query: str, camera_inventory: Optional[List[Dict[str, Any]]] = None
    ) -> EntityResolutionResult:
        """Executes full multi-modal resolution over the input query."""
        lang = self.detect_language(query)
        norm_q = self.normalize_text(query)

        # 1. Resolve Vehicle License Plate
        plate = self.extract_license_plate(query)

        # 2. Resolve Vehicle Color
        found_color = None
        for canonical_color, aliases in self.COLORS.items():
            if any(alias in norm_q.split() or alias in norm_q for alias in aliases):
                found_color = canonical_color
                break

        # 3. Resolve Vehicle Model
        found_model = None
        for model in self.VEHICLE_MODELS:
            if model in norm_q:
                found_model = model.capitalize()
                break

        # 4. Resolve District
        found_district = None
        for district in self.DISTRICTS:
            if district in norm_q:
                found_district = district.capitalize()
                break

        # 5. Resolve Detection Type
        detection_type = None
        detection_keywords = {
            "person": ["person", "persons", "man", "woman", "people", "pedestrian", "insan", "aadmi", "vyakti", "વ્યક્તિ", "માણસ", "लोग", "आदमी"],
            "vehicle": ["vehicle", "vehicles", "car", "cars", "gaadi", "gadi", "gadiyan", "gadiyo", "auto", "bike", "bikes", "splendor", "splandor", "activa", "swift", "creta", "truck", "bus", "વાહન", "વાહનો", "ગાડી", "ગાડીઓ", "गाड़ी", "गाड़ियां", "वाहने"],
            "license_plate": ["anpr", "plate", "number plate", "ocr", "नंबर प्लेट", "પ્લેટ"],
            "all": ["detect", "detect karo", "detection chalao", "analysis", "ડિટેક્શન", "ડિટેક્ટ", "डिटेक्ट", "स्कैन"]
        }
        for dtype, keywords in detection_keywords.items():
            if any(k in norm_q for k in keywords):
                detection_type = dtype
                break

        # 6. Resolve Requested Action
        action = None
        if any(w in norm_q for w in ["kholo", "open", "stream", "live", "dikha", "dikhao", "batao", "khol", "kholna", "ખોલો", "બતાવો", "ખુલ્લું", "उघडा", "दाखवा"]):
            action = "OPEN_STREAM"
        if detection_type or any(w in norm_q for w in ["detect", "detection", "chalao", "analysis", "kitne vehicle", "kitni gadi", "kitne log", "ડિટેક્ટ", "ડિટેક્શન", "डिटेक्शन"]):
            action = "RUN_DETECTION"
        if any(w in norm_q for w in ["security audit", "audit report", "security report", "threat audit", "threat assessment", "ઓડિટ", "સિક્યુરિટી ઓડિટ", "सुरक्षा ऑडिट"]):
            action = "SECURITY_AUDIT"
        if any(w in norm_q for w in ["trace", "track", "route", "kaha", "kaha-kaha", "ટ્રેસ", "ટ્રેક", "ट्रेस"]):
            action = "TRACE_VEHICLE"
        if any(w in norm_q for w in ["health check", "system health", "health check karke bata", "status check", "swasthya", "તબિયત", "સ્થિતિ", "हालत"]):
            action = "SYSTEM_HEALTH"
        if any(w in norm_q for w in ["map", "gis", "location", "naksha", "મેપ", "નકશો", "नક્શા"]):
            action = "NAVIGATE_MAP"
        if any(w in norm_q for w in ["incident", "incidents", "alert", "alerts", "fir", "ઇન્સિડન્ટ", "ઇન્સિડેન્ટ", "ઘટના"]):
            action = "INCIDENT_QUERY"

        # 7. Parse Relative Time Window
        time_win = self.parse_relative_time_window(query)

        # 8. Resolve Camera if inventory is provided
        resolved_cam = None
        candidates = []
        is_ambiguous = False
        if camera_inventory:
            resolved_cam, candidates = self.match_camera_against_inventory(query, camera_inventory)
            if not resolved_cam and len(candidates) > 1:
                is_ambiguous = True

        return EntityResolutionResult(
            query=query,
            detected_language=lang,
            resolved_camera=resolved_cam,
            candidate_cameras=candidates,
            is_ambiguous=is_ambiguous,
            resolved_plate=plate,
            resolved_district=found_district,
            resolved_vehicle_color=found_color,
            resolved_vehicle_model=found_model,
            resolved_detection_type=detection_type,
            requested_action=action,
            time_window=time_win.get("label") if time_win else None,
        )

    def parse_relative_time_window(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Parses relative time expressions across English, Hindi, Gujarati, Marathi
        into exact UTC/IST start and end timestamps.
        """
        from datetime import datetime, timezone, timedelta
        now_utc = datetime.now(timezone.utc)
        norm_q = self.normalize_text(query)

        # Yesterday / Kal / ગઈકાલે / काल
        if any(w in norm_q for w in ["yesterday evening", "kal shaam", "ગઈકાલે સાંજે", "काल संध्याकाळी"]):
            start = (now_utc - timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
            end = (now_utc - timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
            return {"label": "Yesterday Evening (17:00 - 22:00)", "start_time": start.isoformat(), "end_time": end.isoformat()}

        if any(w in norm_q for w in ["last night", "kal raat", "pichli raat", "ગઈકાલે રાત્રે", "काल रात्री", "गत रात्री"]):
            start = (now_utc - timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
            end = now_utc.replace(hour=6, minute=0, second=0, microsecond=0)
            return {"label": "Last Night (20:00 - 06:00)", "start_time": start.isoformat(), "end_time": end.isoformat()}

        if any(w in norm_q for w in ["yesterday", "kal", "ગઈકાલે", "काल", "kal ka", "kal ki"]):
            start = (now_utc - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (now_utc - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
            return {"label": "Yesterday (Full Day)", "start_time": start.isoformat(), "end_time": end.isoformat()}

        # Today / Aaj / આજે / आज
        if any(w in norm_q for w in ["today", "aaj", "aaj subah", "આજે", "आज", "aaj ki"]):
            start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            return {"label": "Today (Since 00:00)", "start_time": start.isoformat(), "end_time": now_utc.isoformat()}

        # Last 24 Hours / Pichle 24 ghante / છેલ્લા 24 કલાક
        if any(w in norm_q for w in ["24 hours", "24 hour", "24 ghante", "24 ghanto", "24 કલાક", "२४ तास", "pichle 24"]):
            start = now_utc - timedelta(hours=24)
            return {"label": "Past 24 Hours", "start_time": start.isoformat(), "end_time": now_utc.isoformat()}

        # Last 2 Hours / 2 ghante pehle
        if any(w in norm_q for w in ["2 hours", "2 hour", "2 ghante", "2 કલાક", "२ तास"]):
            start = now_utc - timedelta(hours=2)
            return {"label": "Past 2 Hours", "start_time": start.isoformat(), "end_time": now_utc.isoformat()}

        # Last 1 Hour
        if any(w in norm_q for w in ["1 hour", "last hour", "1 ghanta", "ek ghanta", "૧ કલાક", "१ तास"]):
            start = now_utc - timedelta(hours=1)
            return {"label": "Past 1 Hour", "start_time": start.isoformat(), "end_time": now_utc.isoformat()}

        return None

    def extract_multiple_cameras(
        self, query: str, camera_inventory: List[Dict[str, Any]]
    ) -> List[ResolvedCameraMatch]:
        """Extracts two or more cameras mentioned for comparison (e.g. 'camera 5 aur camera 7')."""
        matches: List[ResolvedCameraMatch] = []
        seen_ids = set()

        # Find all number references in query
        numbers = re.findall(r'\b(?:cam|camera|cctv)?\s*([0-9]{1,2})\b', query, flags=re.IGNORECASE)
        for num in numbers:
            c_code = f"cam{num.zfill(2)}"
            for cam in camera_inventory:
                cid = str(cam.get("camera_id") or cam.get("id") or cam.get("camera_code") or "").lower()
                if (cid == c_code or cid == f"cam{int(num)}") and cid not in seen_ids:
                    seen_ids.add(cid)
                    resolved_cid = cam.get("camera_id") or cam.get("id") or cid
                    matches.append(ResolvedCameraMatch(
                        camera_id=resolved_cid,
                        camera_code=(cam.get("camera_code") or resolved_cid).upper(),
                        name=cam.get("name") or "Unknown Camera",
                        district=cam.get("district") or "Gujarat",
                        confidence=0.99,
                        match_reason=f"Multi-camera match {c_code}",
                        raw_data=cam,
                    ))

        return matches


# Singleton
entity_resolver = EntityResolver()
