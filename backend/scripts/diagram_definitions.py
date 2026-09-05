"""
PHANTOM 4.8 // Master Architecture Diagram Definitions
Contains the vector SVG generator routines for all 16 architecture and workflow exhibits,
natively designed for A4 Portrait canvas (860x820 viewport) with large high-contrast fonts.
"""

# Common palette
BG = "#070414"
CARD = "#120826"
BORDER = "#6D28D9"
BORDER_LIGHT = "#9333EA"
PURPLE_LIGHT = "#C084FC"
WHITE = "#FFFFFF"
MUTED = "#C4B5FD"
TEXT_MUTED = "#C4B5FD"
DIM = "#94A3B8"
GREEN = "#10B981"
AMBER = "#F59E0B"
RED = "#EF4444"
CYAN = "#06B6D4"

COMMON_DEFS = f"""
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0E0522" />
      <stop offset="50%" stop-color="#14092E" />
      <stop offset="100%" stop-color="#080316" />
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1A0D3B" />
      <stop offset="100%" stop-color="#100624" />
    </linearGradient>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#7C3AED" />
      <stop offset="100%" stop-color="#4C1D95" />
    </linearGradient>
    <linearGradient id="purpleGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#A855F7" />
      <stop offset="100%" stop-color="#6B21A8" />
    </linearGradient>
    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#06B6D4" />
      <stop offset="100%" stop-color="#0284C7" />
    </linearGradient>
    <linearGradient id="greenGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10B981" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <linearGradient id="redGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#EF4444" />
      <stop offset="100%" stop-color="#B91C1C" />
    </linearGradient>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.65" />
    </filter>
    <filter id="subtleGlow" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
    <marker id="arr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{PURPLE_LIGHT}" />
    </marker>
    <marker id="arr-green" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{GREEN}" />
    </marker>
    <marker id="arr-cyan" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{CYAN}" />
    </marker>
    <marker id="arr-red" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{RED}" />
    </marker>
  </defs>
"""

def wrap_svg(content: str, width: int = 860, height: int = 820) -> str:
    grid_x = ''.join(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" />' for x in range(0, width, 40))
    grid_y = ''.join(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" />' for y in range(0, height, 40))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
  {COMMON_DEFS}
  <!-- Base Background -->
  <rect width="{width}" height="{height}" fill="url(#bgGrad)" rx="8" />
  
  <!-- Precision Technical Grid -->
  <g opacity="0.03" stroke="#A855F7" stroke-width="1">
    {grid_x}
    {grid_y}
  </g>
  <rect width="{width}" height="{height}" fill="none" stroke="{BORDER}" stroke-width="1.5" rx="8" />
  
  <!-- Diagram Content -->
  {content}
</svg>"""

def make_box(x, y, w, h, title, subtitle="", badge="", badge_color=BORDER_LIGHT, border=BORDER, fill="url(#cardGrad)", rx=6):
    b_text = f"""<rect x="{x + w - len(badge)*8 - 18}" y="{y + 8}" width="{len(badge)*8 + 10}" height="18" rx="4" fill="{badge_color}" fill-opacity="0.2" stroke="{badge_color}" stroke-width="1"/>
    <text x="{x + w - (len(badge)*8 + 18)/2 - 4}" y="{y + 21}" fill="{badge_color}" font-size="9" font-weight="700" text-anchor="middle">{badge}</text>""" if badge else ""
    
    sub_text = f"""<text x="{x + 14}" y="{y + 36}" fill="{MUTED}" font-size="10" font-weight="400">{subtitle}</text>""" if subtitle else ""
    
    return f"""
    <g filter="url(#shadow)">
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{border}" stroke-width="1.5" />
      <text x="{x + 14}" y="{y + (20 if subtitle else 24)}" fill="{WHITE}" font-size="12.5" font-weight="700">{title}</text>
      {sub_text}
      {b_text}
    </g>"""

# ==============================================================================
# Diagram 01A: 7-Layer High-Level System Architecture Overview
# ==============================================================================
def gen_svg_01A():
    layers = [
        ("LAYER A: VIDEO INGESTION & EDGE TRANSPORT", "RTSP over TCP • WebRTC (WHEP) • Dynamic Sentinel Ingest (/api/ingest) • H.264/H.265 HW Decode • 1-Slot Ring Buffer", "INGESTION", CYAN),
        ("LAYER B: AI VISION & MULTI-MODEL INFERENCE", "Shared YOLO26 Backbone Core • 3-Tier Hierarchy (L1 Cat, L2 Subtype, L3 Model) • Specialized 2W/Car • EasyOCR Gujarat ANPR", "INFERENCE", PURPLE_LIGHT),
        ("LAYER C: STREAM GATEWAY & LOAD PACING", "Dynamic Stream Proxy • Profile Manager: LOW (500k), MED (1.5M), HIGH (2.5M), BURST_TRACKING (4M) • WebSocket HUD Multiplexer", "GATEWAY", BORDER_LIGHT),
        ("LAYER D: CORE DOMAIN & INCIDENT SERVICES", "Alert Rule Engine • 60s Anti-Storm Cooldown • Incident Lifecycle FSM (OPEN -> CLOSED) • SHA-256 Hashing • FastAPI v1 Routers", "SERVICES", RED),
        ("LAYER E: SPATIAL INTELLIGENCE & GIS MAP", "CCTV Geographic FOV Coverage Wedges • PostGIS GIST Spatial Index • Multi-Camera Trajectory Interception • Intercept ETA", "SPATIAL", GREEN),
        ("LAYER F: AI COPILOT & AUTONOMOUS AGENT", "SurveillanceCopilot Autonomous Agent • Multilingual NLP (English, Hindi, Gujarati) • 40+ Grounded Deterministic Surveillance Tools", "AI AGENT", PURPLE_LIGHT),
        ("LAYER G: STORAGE, CACHING & EVENT BUS", "PostgreSQL 16 + PostGIS Spatial DB • Redis Real-Time Hot Cache & Alert Bus • Multi-Broker Apache Kafka Event Streaming Grid", "STORAGE", CYAN)
    ]
    
    body = ""
    y = 20
    for i, (title, desc, badge, color) in enumerate(layers):
        body += f"""
        <g transform="translate(30, {y})">
          <rect width="800" height="92" rx="8" fill="url(#cardGrad)" stroke="{color}" stroke-width="1.8" filter="url(#shadow)" />
          
          <!-- Layer Indicator Pill -->
          <rect x="16" y="14" width="85" height="22" rx="4" fill="{color}" fill-opacity="0.2" stroke="{color}" stroke-width="1.2" />
          <text x="58" y="29" fill="{color}" font-size="10" font-weight="800" text-anchor="middle">{badge}</text>
          
          <!-- Layer Title -->
          <text x="115" y="30" fill="{WHITE}" font-size="14.5" font-weight="800">{title}</text>
          
          <!-- Latency Badge -->
          <rect x="700" y="14" width="84" height="22" rx="4" fill="#070414" stroke="{BORDER}" stroke-width="1" />
          <text x="742" y="29" fill="{MUTED}" font-size="9.5" font-weight="700" text-anchor="middle">LAYER {chr(65+i)}</text>
          
          <!-- Description / Subsystems -->
          <rect x="16" y="44" width="768" height="36" rx="4" fill="#090317" stroke="#2E1065" stroke-width="1" />
          <text x="26" y="66" fill="{TEXT_MUTED}" font-size="11" font-weight="500">{desc}</text>
        </g>"""
        if i < len(layers) - 1:
            body += f"""
            <line x1="430" y1="{y + 92}" x2="430" y2="{y + 112}" stroke="{BORDER_LIGHT}" stroke-width="2.5" stroke-dasharray="4,3" marker-end="url(#arr)" />"""
        y += 112
        
    return body

# ==============================================================================
# Diagram 01B: Subsystem Layer Matrix & Concrete Interconnect
# ==============================================================================
def gen_svg_01B():
    cards = [
        (30, 20, 385, 235, "INGESTION & GATEWAY SUBSYSTEM", "backend/app/services/stream_gateway_service.py", [
            ("Dynamic Ingestion", "Corp8SourceAdapter querying /api/ingest dynamically", GREEN),
            ("RTSP TCP Receiver", "OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp", CYAN),
            ("WebRTC WHEP Proxy", "Sub-35ms browser video preview pipeline", PURPLE_LIGHT),
            ("Ring Buffer Thread", "1-slot decoupled latest frame; 0 queue buildup", AMBER)
        ]),
        (445, 20, 385, 235, "AI VISION & CLASSIFICATION CORE", "backend/app/ai/yolo26/ & specialized_classifiers.py", [
            ("Shared YOLO26 Core", "Singleton weights with CUDA stream separation", CYAN),
            ("3-Tier Hierarchy", "L1 Category -> L2 Subtype -> L3 Make/Model", PURPLE_LIGHT),
            ("Specialized Models", "Activa/Splendor (2W) and WagonR/Swift (Car)", GREEN),
            ("Gujarat ANPR", "Bilateral filter + EasyOCR + GJ01-GJ38 regex", AMBER)
        ]),
        (30, 280, 385, 245, "SURVEILLANCE SERVICES & FSM", "backend/app/services/alert_engine.py & incidents.py", [
            ("Anti-Storm Cooldown", "60s sliding window suppresses redundant alerts", RED),
            ("Incident Lifecycle", "FSM: OPEN -> INVESTIGATING -> RESOLVED -> CLOSED", AMBER),
            ("SHA-256 Hashing", "hashlib.sha256(crop_bytes) generated at capture", GREEN),
            ("FastAPI Routers", "23 modular routers with dependencies & auth", CYAN)
        ]),
        (445, 280, 385, 245, "SPATIAL GIS & COPILOT AGENT", "backend/app/core/cctv_gis_data.py & copilot.py", [
            ("CCTV FOV Wedges", "Trigonometric wedge: (lat + d*sin θ, lon + d*cos θ)", GREEN),
            ("PostGIS Spatial", "GIST spatial index on cameras & sightings", CYAN),
            ("SurveillanceCopilot", "Autonomous agent with 40+ deterministic tools", PURPLE_LIGHT),
            ("Multilingual NLP", "Native support for English, Hindi, and Gujarati", AMBER)
        ]),
        (30, 550, 800, 230, "ENTERPRISE DATA FABRIC & KAFKA EVENT STREAMING", "PostgreSQL 16 HA + Redis Sentinel + Apache Kafka Multi-Broker Grid", [
            ("PostgreSQL 16 + PostGIS", "Master-replica cluster with Patroni & etcd failover; temporal partitioning", CYAN),
            ("Redis 7 Hot Storage", "Sub-millisecond alert cache, active token blacklist, and rate-limiting sliding log", RED),
            ("Apache Kafka Cluster", "Topics: cctv.detections, cctv.alerts, cctv.telemetry (154 Mbps aggregate egress)", PURPLE_LIGHT),
            ("WebSocket Egress", "25-30 FPS bounding box and metadata broadcast to Netram C2 HUD", GREEN)
        ])
    ]
    
    body = ""
    for x, y, w, h, title, sub, items in cards:
        body += f"""
        <g transform="translate({x}, {y})" filter="url(#shadow)">
          <rect width="{w}" height="{h}" rx="8" fill="url(#cardGrad)" stroke="{BORDER}" stroke-width="1.5" />
          <rect x="0" y="0" width="{w}" height="38" rx="8" fill="#1C0E3F" />
          <text x="16" y="24" fill="{WHITE}" font-size="12.5" font-weight="700">{title}</text>
          <text x="16" y="52" fill="{MUTED}" font-size="9.5" font-weight="400">{sub}</text>
        """
        iy = 64
        for iname, idesc, icolor in items:
            body += f"""
            <g transform="translate(12, {iy})">
              <rect width="{w-24}" height="35" rx="4" fill="#0B0418" stroke="#2D1160" stroke-width="1" />
              <circle cx="12" cy="17" r="4" fill="{icolor}" />
              <text x="24" y="16" fill="{WHITE}" font-size="10.5" font-weight="700">{iname}:</text>
              <text x="24" y="28" fill="{MUTED}" font-size="9.5">{idesc}</text>
            </g>"""
            iy += 40
        body += "</g>"
        
    return body

# ==============================================================================
# Diagram 02: End-to-End Operational Surveillance Workflow
# ==============================================================================
def gen_svg_02():
    steps = [
        ("1. CCTV Camera Grid", "RTSP Video over TCP (1080p @ 25 FPS)", "CAPTURE", CYAN),
        ("2. Stream Gateway & PTS Check", "Validate frame timestamps; detect PTS loop resets", "INGEST", GREEN),
        ("3. Decoupled 1-Slot Ring Buffer", "Overwrite latest slot; drop stale frames (0 lag)", "BUFFER", AMBER),
        ("4. Shared YOLO26 Detection Core", "Batch inference on TensorRT GPU; detect objects", "DETECTION", PURPLE_LIGHT),
        ("5. 3-Tier Classification Hierarchy", "Classify Category -> Subtype -> Make/Model (Activa/WagonR)", "CLASSIFY", PURPLE_LIGHT),
        ("6. Gujarat ANPR Localization & OCR", "Extract bumper plate; bilateral filter; GJ01-GJ38 regex", "ANPR", CYAN),
        ("7. Watchlist Correlation & Match", "Check plate / vehicle model against police watchlists", "MATCH", RED),
        ("8. 60s Anti-Storm Cooldown & Hash", "Deduplicate alerts; generate SHA-256 cryptographic hash", "COOLDOWN", AMBER),
        ("9. Egress: WebSocket HUD & BURST Mode", "Broadcast to Netram HUD; trigger BURST_TRACKING stream", "ALERT EGRESS", GREEN)
    ]
    
    body = ""
    y = 25
    for i, (title, desc, badge, color) in enumerate(steps):
        body += f"""
        <g transform="translate(40, {y})">
          <rect width="780" height="66" rx="8" fill="url(#cardGrad)" stroke="{color}" stroke-width="1.5" filter="url(#shadow)" />
          
          <!-- Step Number -->
          <circle cx="34" cy="33" r="18" fill="#1B0E3D" stroke="{color}" stroke-width="1.8" />
          <text x="34" y="38" fill="{WHITE}" font-size="12" font-weight="800" text-anchor="middle">{i+1}</text>
          
          <!-- Text -->
          <text x="68" y="28" fill="{WHITE}" font-size="13" font-weight="700">{title}</text>
          <text x="68" y="48" fill="{MUTED}" font-size="10.5">{desc}</text>
          
          <!-- Badge -->
          <rect x="660" y="21" width="104" height="24" rx="4" fill="{color}" fill-opacity="0.2" stroke="{color}" stroke-width="1" />
          <text x="712" y="37" fill="{color}" font-size="9.5" font-weight="700" text-anchor="middle">{badge}</text>
        </g>"""
        if i < len(steps) - 1:
            body += f"""
            <path d="M 430 {y + 66} L 430 {y + 85}" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />"""
        y += 85
        
    return body

# ==============================================================================
# Diagram 03: AI Vision 3-Tier Hierarchy & Specialized Classifiers
# ==============================================================================
def gen_svg_03():
    return f"""
    <!-- Root Frame Input -->
    <g transform="translate(230, 20)" filter="url(#shadow)">
      <rect width="400" height="52" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="2" />
      <text x="200" y="26" fill="{WHITE}" font-size="14" font-weight="800" text-anchor="middle">RAW CCTV VIDEO FRAME / RTSP FEED</text>
      <text x="200" y="42" fill="{CYAN}" font-size="10.5" font-weight="600" text-anchor="middle">H.264 / H.265 Decode @ 1080p Resolution</text>
    </g>
    
    <path d="M 430 72 L 430 105" stroke="{PURPLE_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Shared YOLO26 Backbone -->
    <g transform="translate(180, 105)" filter="url(#shadow)">
      <rect width="500" height="54" rx="8" fill="#1C0E3F" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <text x="250" y="28" fill="{WHITE}" font-size="13.5" font-weight="800" text-anchor="middle">SHARED YOLO26 BACKBONE DETECTOR (FP16 TensorRT)</text>
      <text x="250" y="45" fill="{MUTED}" font-size="10.5" font-weight="500" text-anchor="middle">Bounding Box Localization + Preliminary Class Logits (Confidence &gt; 0.45)</text>
    </g>
    
    <!-- Branch to Level 1 Categories -->
    <path d="M 430 159 L 430 185" stroke="{PURPLE_LIGHT}" stroke-width="2" />
    <path d="M 130 185 L 730 185" stroke="{PURPLE_LIGHT}" stroke-width="2" />
    <path d="M 130 185 L 130 215" stroke="{PURPLE_LIGHT}" stroke-width="2" marker-end="url(#arr)" />
    <path d="M 330 185 L 330 215" stroke="{PURPLE_LIGHT}" stroke-width="2" marker-end="url(#arr)" />
    <path d="M 530 185 L 530 215" stroke="{PURPLE_LIGHT}" stroke-width="2" marker-end="url(#arr)" />
    <path d="M 730 185 L 730 215" stroke="{PURPLE_LIGHT}" stroke-width="2" marker-end="url(#arr)" />
    
    <!-- Level 1 Category Cards -->
    <!-- Col 1: Person & Pole Filter -->
    <g transform="translate(40, 215)" filter="url(#shadow)">
      <rect width="180" height="50" rx="6" fill="#120826" stroke="{CYAN}" stroke-width="1.5" />
      <text x="90" y="24" fill="{WHITE}" font-size="11.5" font-weight="700" text-anchor="middle">L1: PERSON</text>
      <text x="90" y="40" fill="{CYAN}" font-size="9.5" text-anchor="middle">Pedestrian Candidate</text>
      
      <path d="M 90 50 L 90 85" stroke="{CYAN}" stroke-width="2" marker-end="url(#arr)" />
      
      <rect y="85" width="180" height="90" rx="6" fill="#1B0E38" stroke="{AMBER}" stroke-width="1.5" />
      <text x="90" y="106" fill="{AMBER}" font-size="10.5" font-weight="700" text-anchor="middle">Hard-Negative Filter</text>
      <text x="90" y="124" fill="{MUTED}" font-size="9" text-anchor="middle">Aspect Ratio &gt; 3.2</text>
      <text x="90" y="140" fill="{MUTED}" font-size="9" text-anchor="middle">Optical Flow = 0.0</text>
      <text x="90" y="160" fill="{GREEN}" font-size="9" font-weight="700" text-anchor="middle">Filters Streetlight Poles</text>
    </g>
    
    <!-- Col 2: Two-Wheeler Classifier -->
    <g transform="translate(240, 215)" filter="url(#shadow)">
      <rect width="180" height="50" rx="6" fill="#120826" stroke="{PURPLE_LIGHT}" stroke-width="1.5" />
      <text x="90" y="24" fill="{WHITE}" font-size="11.5" font-weight="700" text-anchor="middle">L1: TWO-WHEELER</text>
      <text x="90" y="40" fill="{PURPLE_LIGHT}" font-size="9.5" text-anchor="middle">L2: Scooter / Motorcycle</text>
      
      <path d="M 90 50 L 90 85" stroke="{PURPLE_LIGHT}" stroke-width="2" marker-end="url(#arr)" />
      
      <rect y="85" width="180" height="180" rx="6" fill="#1B0E38" stroke="{PURPLE_LIGHT}" stroke-width="1.5" />
      <text x="90" y="106" fill="{WHITE}" font-size="11" font-weight="700" text-anchor="middle">Specialized 2W Classifier</text>
      <text x="90" y="122" fill="{MUTED}" font-size="9" text-anchor="middle">Geometry + Chassis Scan</text>
      
      <rect x="10" y="132" width="160" height="55" rx="4" fill="#0C041C" stroke="{GREEN}" stroke-width="1" />
      <text x="16" y="148" fill="{GREEN}" font-size="10" font-weight="700">HONDA ACTIVA (Scooter)</text>
      <text x="16" y="162" fill="{MUTED}" font-size="8.5">Step-through chassis profile</text>
      <text x="16" y="176" fill="{MUTED}" font-size="8.5">Small 10/12-inch wheels</text>
      
      <rect x="10" y="195" width="160" height="55" rx="4" fill="#0C041C" stroke="{CYAN}" stroke-width="1" />
      <text x="16" y="211" fill="{CYAN}" font-size="10" font-weight="700">HERO SPLENDOR (Bike)</text>
      <text x="16" y="225" fill="{MUTED}" font-size="8.5">Exposed central fuel tank</text>
      <text x="16" y="239" fill="{MUTED}" font-size="8.5">18-inch spoked wheels</text>
    </g>
    
    <!-- Col 3: Car Classifier -->
    <g transform="translate(440, 215)" filter="url(#shadow)">
      <rect width="180" height="50" rx="6" fill="#120826" stroke="{GREEN}" stroke-width="1.5" />
      <text x="90" y="24" fill="{WHITE}" font-size="11.5" font-weight="700" text-anchor="middle">L1: VEHICLE (CAR)</text>
      <text x="90" y="40" fill="{GREEN}" font-size="9.5" text-anchor="middle">L2: Hatchback / Sedan / SUV</text>
      
      <path d="M 90 50 L 90 85" stroke="{GREEN}" stroke-width="2" marker-end="url(#arr)" />
      
      <rect y="85" width="180" height="180" rx="6" fill="#1B0E38" stroke="{GREEN}" stroke-width="1.5" />
      <text x="90" y="106" fill="{WHITE}" font-size="11" font-weight="700" text-anchor="middle">Specialized Car Classifier</text>
      <text x="90" y="122" fill="{MUTED}" font-size="9" text-anchor="middle">Roofline &amp; Aspect Ratio</text>
      
      <rect x="10" y="132" width="160" height="55" rx="4" fill="#0C041C" stroke="{AMBER}" stroke-width="1" />
      <text x="16" y="148" fill="{AMBER}" font-size="10" font-weight="700">MARUTI WAGON-R</text>
      <text x="16" y="162" fill="{MUTED}" font-size="8.5">Aspect Ratio &lt; 0.95</text>
      <text x="16" y="176" fill="{MUTED}" font-size="8.5">Vertical tall-boy roofline</text>
      
      <rect x="10" y="195" width="160" height="55" rx="4" fill="#0C041C" stroke="{CYAN}" stroke-width="1" />
      <text x="16" y="211" fill="{CYAN}" font-size="10" font-weight="700">MARUTI SWIFT</text>
      <text x="16" y="225" fill="{MUTED}" font-size="8.5">Aspect Ratio &gt; 1.05</text>
      <text x="16" y="239" fill="{MUTED}" font-size="8.5">Swept aerodynamic curve</text>
    </g>
    
    <!-- Col 4: Auto-Rickshaw -->
    <g transform="translate(640, 215)" filter="url(#shadow)">
      <rect width="180" height="50" rx="6" fill="#120826" stroke="{AMBER}" stroke-width="1.5" />
      <text x="90" y="24" fill="{WHITE}" font-size="11.5" font-weight="700" text-anchor="middle">L1: THREE-WHEELER</text>
      <text x="90" y="40" fill="{AMBER}" font-size="9.5" text-anchor="middle">L2: Auto-Rickshaw</text>
      
      <path d="M 90 50 L 90 85" stroke="{AMBER}" stroke-width="2" marker-end="url(#arr)" />
      
      <rect y="85" width="180" height="180" rx="6" fill="#1B0E38" stroke="{AMBER}" stroke-width="1.5" />
      <text x="90" y="106" fill="{WHITE}" font-size="11" font-weight="700" text-anchor="middle">Auto Disambiguator</text>
      <text x="90" y="122" fill="{MUTED}" font-size="9" text-anchor="middle">Apron &amp; Cabin Structure</text>
      
      <rect x="10" y="132" width="160" height="118" rx="4" fill="#0C041C" stroke="{GREEN}" stroke-width="1" />
      <text x="16" y="152" fill="{GREEN}" font-size="10.5" font-weight="700">BAJAJ COMPACT AUTO</text>
      <text x="16" y="172" fill="{MUTED}" font-size="9">• Delta 3-wheel geometry</text>
      <text x="16" y="190" fill="{MUTED}" font-size="9">• Soft canvas canopy roof</text>
      <text x="16" y="208" fill="{MUTED}" font-size="9">• Open passenger cabin</text>
      <text x="16" y="226" fill="{CYAN}" font-size="8.5">Prevents mini-truck mixup</text>
    </g>
    
    <!-- Convergence to Temporal Track Fusion -->
    <path d="M 130 380 L 130 520 L 330 520 L 330 545" stroke="{BORDER_LIGHT}" stroke-width="2" />
    <path d="M 330 485 L 330 545" stroke="{BORDER_LIGHT}" stroke-width="2" />
    <path d="M 530 485 L 530 545" stroke="{BORDER_LIGHT}" stroke-width="2" />
    <path d="M 730 485 L 730 520 L 530 520 L 530 545" stroke="{BORDER_LIGHT}" stroke-width="2" marker-end="url(#arr)" />
    
    <g transform="translate(100, 545)" filter="url(#shadow)">
      <rect width="660" height="110" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <text x="330" y="28" fill="{WHITE}" font-size="13.5" font-weight="800" text-anchor="middle">TEMPORAL TRACK FUSION &amp; TRAJECTORY SMOOTHING</text>
      
      <g transform="translate(15, 42)">
        <rect width="200" height="54" rx="4" fill="#0B0318" stroke="{BORDER}" stroke-width="1" />
        <text x="100" y="22" fill="{CYAN}" font-size="10" font-weight="700" text-anchor="middle">Multi-Frame IoU Matching</text>
        <text x="100" y="40" fill="{MUTED}" font-size="9" text-anchor="middle">Persistent Track ID Assignment</text>
      </g>
      
      <g transform="translate(230, 42)">
        <rect width="200" height="54" rx="4" fill="#0B0318" stroke="{BORDER}" stroke-width="1" />
        <text x="100" y="22" fill="{GREEN}" font-size="10" font-weight="700" text-anchor="middle">Label Probability Voting</text>
        <text x="100" y="40" fill="{MUTED}" font-size="9" text-anchor="middle">Hysteresis filters flickering classes</text>
      </g>
      
      <g transform="translate(445, 42)">
        <rect width="200" height="54" rx="4" fill="#0B0318" stroke="{BORDER}" stroke-width="1" />
        <text x="100" y="22" fill="{AMBER}" font-size="10" font-weight="700" text-anchor="middle">Kalman Velocity Vector</text>
        <text x="100" y="40" fill="{MUTED}" font-size="9" text-anchor="middle">Spatial heading &amp; speed calc</text>
      </g>
    </g>
    
    <path d="M 430 655 L 430 685" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Output Egress -->
    <g transform="translate(160, 685)" filter="url(#shadow)">
      <rect width="540" height="55" rx="8" fill="#1C0E3F" stroke="{GREEN}" stroke-width="1.8" />
      <text x="270" y="26" fill="{WHITE}" font-size="12.5" font-weight="800" text-anchor="middle">STRUCTURED DETECTION PAYLOAD &amp; WEBSOCKET HUD EGRESS</text>
      <text x="270" y="44" fill="{GREEN}" font-size="10.5" font-weight="600" text-anchor="middle">Class, Model, Confidence, BBox, Velocity &amp; Persistent Track ID</text>
    </g>"""

# ==============================================================================
# Diagram 04: Gujarat ANPR Pipeline & RTO Normalization
# ==============================================================================
def gen_svg_04():
    return f"""
    <!-- Step 1: Vehicle Detection -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="240" height="110" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="1.5" />
      <rect x="0" y="0" width="240" height="28" rx="8" fill="#180B38" />
      <text x="12" y="19" fill="{CYAN}" font-size="11" font-weight="700">1. BUMPER LOCALIZATION</text>
      <text x="12" y="48" fill="{WHITE}" font-size="11.5" font-weight="700">Vehicle Bounding Box</text>
      <text x="12" y="66" fill="{MUTED}" font-size="9.5">• Lower 35% bounding crop</text>
      <text x="12" y="82" fill="{MUTED}" font-size="9.5">• Aspect ratio check (2.5 - 5.5)</text>
      <text x="12" y="98" fill="{GREEN}" font-size="9.5">Plate candidate isolated</text>
    </g>
    
    <path d="M 270 75 L 310 75" stroke="{PURPLE_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Step 2: Preprocessing -->
    <g transform="translate(310, 20)" filter="url(#shadow)">
      <rect width="240" height="110" rx="8" fill="url(#cardGrad)" stroke="{PURPLE_LIGHT}" stroke-width="1.5" />
      <rect x="0" y="0" width="240" height="28" rx="8" fill="#180B38" />
      <text x="12" y="19" fill="{PURPLE_LIGHT}" font-size="11" font-weight="700">2. IMAGE ENHANCEMENT</text>
      <text x="12" y="48" fill="{WHITE}" font-size="11.5" font-weight="700">Bilateral &amp; Perspective</text>
      <text x="12" y="66" fill="{MUTED}" font-size="9.5">• Perspective deskewing</text>
      <text x="12" y="82" fill="{MUTED}" font-size="9.5">• Bilateral edge-preserv. filter</text>
      <text x="12" y="98" fill="{MUTED}" font-size="9.5">• Otsu adaptive thresholding</text>
    </g>
    
    <path d="M 550 75 L 590 75" stroke="{PURPLE_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Step 3: OCR Engine -->
    <g transform="translate(590, 20)" filter="url(#shadow)">
      <rect width="240" height="110" rx="8" fill="url(#cardGrad)" stroke="{GREEN}" stroke-width="1.5" />
      <rect x="0" y="0" width="240" height="28" rx="8" fill="#180B38" />
      <text x="12" y="19" fill="{GREEN}" font-size="11" font-weight="700">3. CHARACTER EXTRACTION</text>
      <text x="12" y="48" fill="{WHITE}" font-size="11.5" font-weight="700">EasyOCR Neural Engine</text>
      <text x="12" y="66" fill="{MUTED}" font-size="9.5">• High-contrast font segmentation</text>
      <text x="12" y="82" fill="{MUTED}" font-size="9.5">• Character confidence scores</text>
      <text x="12" y="98" fill="{CYAN}" font-size="9.5">Raw Text: "GJO1AB1234"</text>
    </g>
    
    <!-- Down Arrow -->
    <path d="M 710 130 L 710 165 L 430 165 L 430 190" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Step 4: Gujarat RTO Normalization & Parsing (Big Center Box) -->
    <g transform="translate(30, 190)" filter="url(#shadow)">
      <rect width="800" height="340" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="38" rx="8" fill="#1D0E42" />
      <text x="20" y="25" fill="{WHITE}" font-size="13.5" font-weight="800">4. GUJARAT RTO REGIONAL REGEX NORMALIZER (GJ01 - GJ38 &amp; 22BH)</text>
      
      <!-- Regex Rules Card -->
      <g transform="translate(20, 52)">
        <rect width="760" height="64" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{CYAN}" font-size="11" font-weight="700">STANDARDIZED REGEX PATTERNS APPLIED:</text>
        <text x="16" y="42" fill="{WHITE}" font-family="monospace" font-size="11">Gujarat Standard: ^(GJ)[ -]?([0-3][0-9])[ -]?([A-Z]{{1,3}})[ -]?([0-9]{{4}})$</text>
        <text x="16" y="58" fill="{WHITE}" font-family="monospace" font-size="11">Bharat Series:    ^(2[1-5]BH)[ -]?([0-9]{{4}})[ -]?([A-Z]{{1,2}})$</text>
      </g>
      
      <!-- RTO Districts Grid (3 columns) -->
      <g transform="translate(20, 126)">
        <!-- Col 1 -->
        <g transform="translate(0, 0)">
          <rect width="245" height="190" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
          <text x="14" y="22" fill="{GREEN}" font-size="10.5" font-weight="700">MAJOR DISTRICT CODES</text>
          <text x="14" y="42" fill="{WHITE}" font-size="10">GJ-01: Ahmedabad (City)</text>
          <text x="14" y="60" fill="{WHITE}" font-size="10">GJ-02: Mehsana</text>
          <text x="14" y="78" fill="{WHITE}" font-size="10">GJ-03: Rajkot</text>
          <text x="14" y="96" fill="{WHITE}" font-size="10">GJ-04: Bhavnagar</text>
          <text x="14" y="114" fill="{WHITE}" font-size="10">GJ-05: Surat (City)</text>
          <text x="14" y="132" fill="{WHITE}" font-size="10">GJ-06: Vadodara (City)</text>
          <text x="14" y="150" fill="{WHITE}" font-size="10">GJ-07: Kheda / Nadiad</text>
          <text x="14" y="168" fill="{WHITE}" font-size="10">GJ-08: Banaskantha (Palanpur)</text>
        </g>
        
        <!-- Col 2 -->
        <g transform="translate(258, 0)">
          <rect width="245" height="190" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
          <text x="14" y="22" fill="{CYAN}" font-size="10.5" font-weight="700">DISTRICT CODES (CONT.)</text>
          <text x="14" y="42" fill="{WHITE}" font-size="10">GJ-09: Sabarkantha (Himmatnagar)</text>
          <text x="14" y="60" fill="{WHITE}" font-size="10">GJ-10: Jamnagar</text>
          <text x="14" y="78" fill="{WHITE}" font-size="10">GJ-11: Junagadh</text>
          <text x="14" y="96" fill="{WHITE}" font-size="10">GJ-12: Kutch (Bhuj)</text>
          <text x="14" y="114" fill="{WHITE}" font-size="10">GJ-13: Surendranagar</text>
          <text x="14" y="132" fill="{WHITE}" font-size="10">GJ-14: Amreli</text>
          <text x="14" y="150" fill="{WHITE}" font-size="10">GJ-18: Gandhinagar (State Capital)</text>
          <text x="14" y="168" fill="{WHITE}" font-size="10">GJ-27: Ahmedabad (Rural)</text>
        </g>
        
        <!-- Col 3: BH Series & Rules -->
        <g transform="translate(515, 0)">
          <rect width="245" height="190" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
          <text x="14" y="22" fill="{AMBER}" font-size="10.5" font-weight="700">SPECIAL &amp; BHARAT SERIES</text>
          <text x="14" y="42" fill="{WHITE}" font-size="10">22BH...AA: Defence &amp; PSU</text>
          <text x="14" y="60" fill="{WHITE}" font-size="10">GJ-28 to GJ-38: New Districts</text>
          <text x="14" y="78" fill="{MUTED}" font-size="9.5">• Botad, Gir Somnath, Morbi</text>
          <text x="14" y="94" fill="{MUTED}" font-size="9.5">• Chhota Udepur, Mahisagar</text>
          <text x="14" y="118" fill="{GREEN}" font-size="10" font-weight="700">NORMALIZATION OUTPUT:</text>
          <text x="14" y="138" fill="{WHITE}" font-size="11" font-weight="800">"GJ-01-AB-1234"</text>
          <text x="14" y="156" fill="{MUTED}" font-size="9">Spaces &amp; hyphens unified</text>
          <text x="14" y="172" fill="{CYAN}" font-size="9">O/0 and I/1 ambiguity resolved</text>
        </g>
      </g>
    </g>
    
    <!-- Down Arrow -->
    <path d="M 430 530 L 430 560" stroke="{RED}" stroke-width="2.5" marker-end="url(#arr-red)" />
    
    <!-- Step 5: Watchlist Matching -->
    <g transform="translate(30, 560)" filter="url(#shadow)">
      <rect width="800" height="185" rx="8" fill="url(#cardGrad)" stroke="{RED}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#2E0A1E" />
      <text x="20" y="23" fill="{RED}" font-size="12.5" font-weight="800">5. REAL-TIME WATCHLIST CORRELATION &amp; THREAT ESCALATION</text>
      
      <g transform="translate(20, 48)">
        <rect width="365" height="118" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="22" fill="{WHITE}" font-size="11" font-weight="700">WATCHLIST DATABASE QUERY</text>
        <text x="16" y="40" fill="{MUTED}" font-size="9.5">• Queries active PostgreSQL Watchlist table</text>
        <text x="16" y="56" fill="{MUTED}" font-size="9.5">• Exact Plate Match + Fuzzy Levenshtein (dist &lt;= 1)</text>
        <text x="16" y="74" fill="{MUTED}" font-size="9.5">• Categories: STOLEN_VEHICLE, WANTED_SUSPECT,</text>
        <text x="16" y="90" fill="{MUTED}" font-size="9.5">  TRAFFIC_VIOLATOR, SURVEILLANCE_TARGET</text>
        <text x="16" y="108" fill="{GREEN}" font-size="9.5" font-weight="700">Query Latency: &lt; 2.8ms indexed</text>
      </g>
      
      <g transform="translate(415, 48)">
        <rect width="365" height="118" rx="6" fill="#0C041C" stroke="{RED}" stroke-width="1" />
        <text x="16" y="22" fill="{RED}" font-size="11" font-weight="700">MATCH ACTION &amp; ALERT DISPATCH</text>
        <text x="16" y="40" fill="{WHITE}" font-size="9.5">• Immediate WebSocket Alert push to Netram HUD</text>
        <text x="16" y="56" fill="{WHITE}" font-size="9.5">• Audio alarm trigger on Command Center console</text>
        <text x="16" y="74" fill="{WHITE}" font-size="9.5">• Auto-promotes camera stream to BURST_TRACKING</text>
        <text x="16" y="90" fill="{WHITE}" font-size="9.5">• Creates Incident FSM entry in OPEN state</text>
        <text x="16" y="108" fill="{AMBER}" font-size="9.5" font-weight="700">60s anti-storm cooldown suppresses spam</text>
      </g>
    </g>"""

# ==============================================================================
# Diagram 05: Camera Discovery & Streaming Lifecycle
# ==============================================================================
def gen_svg_05():
    return f"""
    <!-- Row 1: Sentinel Ingestion Discovery -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="145" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#14082E" />
      <text x="20" y="23" fill="{CYAN}" font-size="13" font-weight="800">1. DYNAMIC SENTINEL CATALOGUE INGESTION (/api/ingest)</text>
      
      <g transform="translate(20, 46)">
        <rect width="365" height="85" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="22" fill="{WHITE}" font-size="11" font-weight="700">Corp8SourceAdapter Dynamic Sync</text>
        <text x="16" y="40" fill="{MUTED}" font-size="9.5">• Zero hard-coded cameras; polls external registry</text>
        <text x="16" y="56" fill="{MUTED}" font-size="9.5">• Reconciles camera state: Active, Inactive, Maintenance</text>
        <text x="16" y="72" fill="{GREEN}" font-size="9.5" font-weight="700">Sync cycle: Every 60s background async loop</text>
      </g>
      
      <g transform="translate(415, 46)">
        <rect width="365" height="85" rx="6" fill="#0C041C" stroke="{AMBER}" stroke-width="1" />
        <text x="16" y="22" fill="{AMBER}" font-size="11" font-weight="700">5-Stage Exponential Backoff on Failure</text>
        <text x="16" y="40" fill="{WHITE}" font-size="9.5">On HTTP 502 / Connection Timeout:</text>
        <text x="16" y="56" fill="{WHITE}" font-size="10.5" font-family="monospace">2s -> 4s -> 8s -> 16s -> 30s (Max)</text>
        <text x="16" y="72" fill="{MUTED}" font-size="9.5">Enters DEGRADED state; preserves cached GIS data</text>
      </g>
    </g>
    
    <path d="M 430 165 L 430 195" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Row 2: Camera State Machine Lifecycle -->
    <g transform="translate(30, 195)" filter="url(#shadow)">
      <rect width="800" height="155" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1A0D3D" />
      <text x="20" y="23" fill="{WHITE}" font-size="13" font-weight="800">2. CAMERA STREAMING STATE MACHINE &amp; PROTOCOL RESOLUTION</text>
      
      <!-- FSM Nodes -->
      <g transform="translate(25, 52)">
        <rect width="125" height="85" rx="6" fill="#0C041C" stroke="{MUTED}" stroke-width="1.5" />
        <text x="62" y="26" fill="{WHITE}" font-size="11" font-weight="700" text-anchor="middle">DISCOVERED</text>
        <text x="62" y="44" fill="{MUTED}" font-size="8.5" text-anchor="middle">Found in /api/ingest</text>
        <text x="62" y="60" fill="{MUTED}" font-size="8.5" text-anchor="middle">Validating RTSP URI</text>
      </g>
      
      <path d="M 150 94 L 180 94" stroke="{PURPLE_LIGHT}" stroke-width="2" marker-end="url(#arr)" />
      
      <g transform="translate(180, 52)">
        <rect width="125" height="85" rx="6" fill="#0C041C" stroke="{CYAN}" stroke-width="1.5" />
        <text x="62" y="26" fill="{CYAN}" font-size="11" font-weight="700" text-anchor="middle">PROBING</text>
        <text x="62" y="44" fill="{MUTED}" font-size="8.5" text-anchor="middle">RTSP over TCP test</text>
        <text x="62" y="60" fill="{MUTED}" font-size="8.5" text-anchor="middle">Hardware PTS check</text>
      </g>
      
      <path d="M 305 94 L 335 94" stroke="{GREEN}" stroke-width="2" marker-end="url(#arr-green)" />
      
      <g transform="translate(335, 52)">
        <rect width="145" height="85" rx="6" fill="#0C041C" stroke="{GREEN}" stroke-width="2" />
        <circle cx="20" cy="20" r="5" fill="{GREEN}" filter="url(#subtleGlow)" />
        <text x="80" y="24" fill="{GREEN}" font-size="11" font-weight="800" text-anchor="middle">ACTIVE_STREAM</text>
        <text x="72" y="44" fill="{WHITE}" font-size="8.5" text-anchor="middle">1-Slot Ring Buffer Open</text>
        <text x="72" y="58" fill="{MUTED}" font-size="8.5" text-anchor="middle">YOLO26 Inference Running</text>
        <text x="72" y="72" fill="{CYAN}" font-size="8.5" text-anchor="middle">WHEP Browser Preview</text>
      </g>
      
      <path d="M 480 94 L 510 94" stroke="{RED}" stroke-width="2" marker-end="url(#arr-red)" />
      
      <g transform="translate(510, 52)">
        <rect width="125" height="85" rx="6" fill="#0C041C" stroke="{RED}" stroke-width="1.5" />
        <text x="62" y="26" fill="{RED}" font-size="11" font-weight="700" text-anchor="middle">OFFLINE</text>
        <text x="62" y="44" fill="{MUTED}" font-size="8.5" text-anchor="middle">Timeout &gt; 5.0s</text>
        <text x="62" y="60" fill="{MUTED}" font-size="8.5" text-anchor="middle">Packet loss detected</text>
      </g>
      
      <path d="M 635 94 L 665 94" stroke="{AMBER}" stroke-width="2" marker-end="url(#arr)" />
      
      <g transform="translate(665, 52)">
        <rect width="115" height="85" rx="6" fill="#0C041C" stroke="{AMBER}" stroke-width="1.5" />
        <text x="57" y="26" fill="{AMBER}" font-size="11" font-weight="700" text-anchor="middle">RETRYING</text>
        <text x="57" y="44" fill="{MUTED}" font-size="8.5" text-anchor="middle">Exponential backoff</text>
        <text x="57" y="60" fill="{MUTED}" font-size="8.5" text-anchor="middle">Max 30s interval</text>
      </g>
    </g>
    
    <path d="M 430 350 L 430 380" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr-green)" />
    
    <!-- Row 3: Dynamic Load Pacing Profiles (4 Profiles) -->
    <g transform="translate(30, 380)" filter="url(#shadow)">
      <rect width="800" height="380" rx="8" fill="url(#cardGrad)" stroke="{GREEN}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#0F2B1C" />
      <text x="20" y="23" fill="{GREEN}" font-size="13" font-weight="800">3. ADAPTIVE LOAD PACING &amp; BANDWIDTH ALLOCATION PROFILES</text>
      
      <!-- 4 Profile Cards -->
      <!-- Profile 1: LOW -->
      <g transform="translate(20, 50)">
        <rect width="175" height="310" rx="6" fill="#0C041C" stroke="{MUTED}" stroke-width="1.5" />
        <rect x="0" y="0" width="175" height="36" rx="6" fill="#140828" />
        <text x="87" y="24" fill="{WHITE}" font-size="12" font-weight="800" text-anchor="middle">PROFILE: LOW</text>
        
        <text x="16" y="60" fill="{MUTED}" font-size="10.5" font-weight="700">Bitrate: 500 kbps</text>
        <text x="16" y="78" fill="{MUTED}" font-size="10.5" font-weight="700">Framerate: 5 FPS</text>
        <text x="16" y="96" fill="{MUTED}" font-size="10.5" font-weight="700">Resolution: 720p</text>
        
        <rect x="12" y="115" width="151" height="180" rx="4" fill="#070314" stroke="#25104A" stroke-width="1" />
        <text x="20" y="135" fill="{WHITE}" font-size="10" font-weight="700">OPERATIONAL USE:</text>
        <text x="20" y="155" fill="{MUTED}" font-size="9">• Rural highway stretches</text>
        <text x="20" y="172" fill="{MUTED}" font-size="9">• Low-activity perimeters</text>
        <text x="20" y="189" fill="{MUTED}" font-size="9">• Zero watchlist presence</text>
        <text x="20" y="215" fill="{CYAN}" font-size="9.5" font-weight="700">COMPUTE SAVINGS:</text>
        <text x="20" y="232" fill="{GREEN}" font-size="9.5">83% GPU cycle reduction</text>
        <text x="20" y="250" fill="{MUTED}" font-size="8.5">Background polling only</text>
      </g>
      
      <!-- Profile 2: MEDIUM -->
      <g transform="translate(210, 50)">
        <rect width="175" height="310" rx="6" fill="#0C041C" stroke="{CYAN}" stroke-width="1.5" />
        <rect x="0" y="0" width="175" height="36" rx="6" fill="#0C2030" />
        <text x="87" y="24" fill="{CYAN}" font-size="12" font-weight="800" text-anchor="middle">PROFILE: MEDIUM</text>
        
        <text x="16" y="60" fill="{CYAN}" font-size="10.5" font-weight="700">Bitrate: 1500 kbps</text>
        <text x="16" y="78" fill="{CYAN}" font-size="10.5" font-weight="700">Framerate: 15 FPS</text>
        <text x="16" y="96" fill="{CYAN}" font-size="10.5" font-weight="700">Resolution: 1080p</text>
        
        <rect x="12" y="115" width="151" height="180" rx="4" fill="#070314" stroke="#103040" stroke-width="1" />
        <text x="20" y="135" fill="{WHITE}" font-size="10" font-weight="700">OPERATIONAL USE:</text>
        <text x="20" y="155" fill="{MUTED}" font-size="9">• Standard municipal grid</text>
        <text x="20" y="172" fill="{MUTED}" font-size="9">• Moderate urban traffic</text>
        <text x="20" y="189" fill="{MUTED}" font-size="9">• Baseline ANPR active</text>
        <text x="20" y="215" fill="{CYAN}" font-size="9.5" font-weight="700">DEFAULT STATE:</text>
        <text x="20" y="232" fill="{WHITE}" font-size="9.5">48 streams per L40S</text>
        <text x="20" y="250" fill="{MUTED}" font-size="8.5">Nominal state-wide profile</text>
      </g>
      
      <!-- Profile 3: HIGH -->
      <g transform="translate(400, 50)">
        <rect width="175" height="310" rx="6" fill="#0C041C" stroke="{BORDER_LIGHT}" stroke-width="1.5" />
        <rect x="0" y="0" width="175" height="36" rx="6" fill="#240D4A" />
        <text x="87" y="24" fill="{PURPLE_LIGHT}" font-size="12" font-weight="800" text-anchor="middle">PROFILE: HIGH</text>
        
        <text x="16" y="60" fill="{PURPLE_LIGHT}" font-size="10.5" font-weight="700">Bitrate: 2500 kbps</text>
        <text x="16" y="78" fill="{PURPLE_LIGHT}" font-size="10.5" font-weight="700">Framerate: 25 FPS</text>
        <text x="16" y="96" fill="{PURPLE_LIGHT}" font-size="10.5" font-weight="700">Resolution: 1080p</text>
        
        <rect x="12" y="115" width="151" height="180" rx="4" fill="#070314" stroke="#35105A" stroke-width="1" />
        <text x="20" y="135" fill="{WHITE}" font-size="10" font-weight="700">OPERATIONAL USE:</text>
        <text x="20" y="155" fill="{MUTED}" font-size="9">• Major highway tolls</text>
        <text x="20" y="172" fill="{MUTED}" font-size="9">• Dense city junctions</text>
        <text x="20" y="189" fill="{MUTED}" font-size="9">• Active manual viewing</text>
        <text x="20" y="215" fill="{CYAN}" font-size="9.5" font-weight="700">HIGH PRECISION:</text>
        <text x="20" y="232" fill="{WHITE}" font-size="9.5">Full ANPR + 2W/Car</text>
        <text x="20" y="250" fill="{MUTED}" font-size="8.5">Fast-moving traffic</text>
      </g>
      
      <!-- Profile 4: BURST_TRACKING -->
      <g transform="translate(590, 50)">
        <rect width="190" height="310" rx="6" fill="#0C041C" stroke="{RED}" stroke-width="2" />
        <rect x="0" y="0" width="190" height="36" rx="6" fill="#3D0B1C" />
        <circle cx="16" cy="18" r="4" fill="{RED}" filter="url(#subtleGlow)" />
        <text x="100" y="24" fill="{RED}" font-size="11.5" font-weight="800" text-anchor="middle">BURST_TRACKING</text>
        
        <text x="16" y="60" fill="{RED}" font-size="10.5" font-weight="700">Bitrate: 4000 kbps</text>
        <text x="16" y="78" fill="{RED}" font-size="10.5" font-weight="700">Framerate: 30 FPS</text>
        <text x="16" y="96" fill="{RED}" font-size="10.5" font-weight="700">Resolution: 1080p HQ</text>
        
        <rect x="12" y="115" width="166" height="180" rx="4" fill="#070314" stroke="#501020" stroke-width="1" />
        <text x="18" y="135" fill="{WHITE}" font-size="10" font-weight="700">TRIGGER CONDITIONS:</text>
        <text x="18" y="155" fill="{WHITE}" font-size="9">• Watchlist match hit</text>
        <text x="18" y="172" fill="{WHITE}" font-size="9">• Suspect vehicle pursuit</text>
        <text x="18" y="189" fill="{WHITE}" font-size="9">• VIP escort corridor</text>
        <text x="18" y="215" fill="{AMBER}" font-size="9.5" font-weight="700">AUTO-DEESCALATION:</text>
        <text x="18" y="232" fill="{MUTED}" font-size="9">Reverts to MEDIUM after</text>
        <text x="18" y="250" fill="{MUTED}" font-size="9">120s of no target sighting</text>
      </g>
    </g>"""

# ==============================================================================
# Diagram 06: Alert Deduplication & Incident FSM
# ==============================================================================
def gen_svg_06():
    return f"""
    <!-- Part 1: Alert Deduplication Pipeline -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="235" rx="8" fill="url(#cardGrad)" stroke="{AMBER}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#2E1B0A" />
      <text x="20" y="23" fill="{AMBER}" font-size="13" font-weight="800">1. ALERT DEDUPLICATION &amp; 60-SECOND ANTI-STORM COOLDOWN</text>
      
      <!-- Pipeline Steps -->
      <g transform="translate(20, 50)">
        <rect width="230" height="165" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{WHITE}" font-size="11" font-weight="700">DETECTION INGESTION</text>
        <text x="16" y="44" fill="{MUTED}" font-size="9.5">• Ingests YOLO26 detection</text>
        <text x="16" y="60" fill="{MUTED}" font-size="9.5">• Persistent Track ID</text>
        <text x="16" y="76" fill="{MUTED}" font-size="9.5">• Normalized Plate string</text>
        <text x="16" y="92" fill="{MUTED}" font-size="9.5">• Vehicle Class &amp; Make</text>
        <text x="16" y="116" fill="{CYAN}" font-size="9.5" font-weight="700">Generates Sighting Key:</text>
        <text x="16" y="134" fill="{WHITE}" font-family="monospace" font-size="9">key = f"{{cam}}:{{track_id}}"</text>
      </g>
      
      <path d="M 250 132 L 290 132" stroke="{AMBER}" stroke-width="2.5" marker-end="url(#arr)" />
      
      <g transform="translate(290, 50)">
        <rect width="250" height="165" rx="6" fill="#0C041C" stroke="{AMBER}" stroke-width="1.5" />
        <text x="16" y="24" fill="{AMBER}" font-size="11" font-weight="700">60s SLIDING COOLDOWN WINDOW</text>
        <text x="16" y="44" fill="{WHITE}" font-size="9.5">• Checks in-memory Redis/Dict:</text>
        <text x="16" y="62" fill="{MUTED}" font-size="9.5">  if (now - last_alert) &lt; 60.0s:</text>
        <text x="16" y="80" fill="{RED}" font-size="10" font-weight="700">  -> SUPPRESS (Drop Alert)</text>
        <text x="16" y="98" fill="{MUTED}" font-size="9.5">  else:</text>
        <text x="16" y="116" fill="{GREEN}" font-size="10" font-weight="700">  -> EMIT &amp; UPDATE TIMESTAMP</text>
        <text x="16" y="140" fill="{MUTED}" font-size="8.5">Eliminates 98.4% alert storm spam</text>
      </g>
      
      <path d="M 540 132 L 580 132" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr-green)" />
      
      <g transform="translate(580, 50)">
        <rect width="200" height="165" rx="6" fill="#0C041C" stroke="{GREEN}" stroke-width="1" />
        <text x="16" y="24" fill="{GREEN}" font-size="11" font-weight="700">CRYPTOGRAPHIC EVIDENCE</text>
        <text x="16" y="44" fill="{WHITE}" font-size="9.5">SHA-256 Hashing:</text>
        <text x="16" y="62" fill="{CYAN}" font-size="9" font-family="monospace">hashlib.sha256(crop)</text>
        <text x="16" y="82" fill="{MUTED}" font-size="9.5">• Binds crop to alert</text>
        <text x="16" y="98" fill="{MUTED}" font-size="9.5">• Tamper-evident proof</text>
        <text x="16" y="116" fill="{MUTED}" font-size="9.5">• Section 65B compliant</text>
        <text x="16" y="140" fill="{WHITE}" font-size="8.5">Stored in Alert Record</text>
      </g>
    </g>
    
    <path d="M 430 255 L 430 285" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Part 2: Incident Lifecycle Finite State Machine (FSM) -->
    <g transform="translate(30, 285)" filter="url(#shadow)">
      <rect width="800" height="475" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1C0E42" />
      <text x="20" y="23" fill="{WHITE}" font-size="13" font-weight="800">2. FORMAL INCIDENT LIFECYCLE FINITE STATE MACHINE (FSM)</text>
      
      <!-- State 1: OPEN -->
      <g transform="translate(35, 60)">
        <rect width="165" height="145" rx="8" fill="#160826" stroke="{RED}" stroke-width="2" />
        <circle cx="24" cy="24" r="7" fill="{RED}" filter="url(#subtleGlow)" />
        <text x="82" y="28" fill="{RED}" font-size="13" font-weight="800" text-anchor="middle">OPEN</text>
        
        <text x="14" y="56" fill="{WHITE}" font-size="9.5" font-weight="700">Initial Trigger State</text>
        <text x="14" y="74" fill="{MUTED}" font-size="9">• Watchlist match hit</text>
        <text x="14" y="90" fill="{MUTED}" font-size="9">• Audio alarm ringing</text>
        <text x="14" y="106" fill="{MUTED}" font-size="9">• Dispatch unassigned</text>
        <text x="14" y="126" fill="{AMBER}" font-size="9" font-weight="700">SLA: &lt; 30s response</text>
      </g>
      
      <!-- Transition 1 -> 2 -->
      <path d="M 200 132 L 240 132" stroke="{CYAN}" stroke-width="2.5" marker-end="url(#arr-cyan)" />
      <text x="220" y="124" fill="{CYAN}" font-size="9" font-weight="700" text-anchor="middle">ASSIGN</text>
      
      <!-- State 2: INVESTIGATING -->
      <g transform="translate(240, 60)">
        <rect width="165" height="145" rx="8" fill="#160826" stroke="{CYAN}" stroke-width="2" />
        <circle cx="24" cy="24" r="7" fill="{CYAN}" filter="url(#subtleGlow)" />
        <text x="95" y="28" fill="{CYAN}" font-size="12" font-weight="800" text-anchor="middle">INVESTIGATING</text>
        
        <text x="14" y="56" fill="{WHITE}" font-size="9.5" font-weight="700">Officer Review Active</text>
        <text x="14" y="74" fill="{MUTED}" font-size="9">• Officer assigned</text>
        <text x="14" y="90" fill="{MUTED}" font-size="9">• Live stream preview</text>
        <text x="14" y="106" fill="{MUTED}" font-size="9">• Trajectory tracking</text>
        <text x="14" y="126" fill="{GREEN}" font-size="9" font-weight="700">BURST stream active</text>
      </g>
      
      <!-- Transition 2 -> 3 -->
      <path d="M 405 132 L 445 132" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr-green)" />
      <text x="425" y="124" fill="{GREEN}" font-size="9" font-weight="700" text-anchor="middle">RESOLVE</text>
      
      <!-- State 3: RESOLVED -->
      <g transform="translate(445, 60)">
        <rect width="165" height="145" rx="8" fill="#160826" stroke="{GREEN}" stroke-width="2" />
        <circle cx="24" cy="24" r="7" fill="{GREEN}" filter="url(#subtleGlow)" />
        <text x="90" y="28" fill="{GREEN}" font-size="12" font-weight="800" text-anchor="middle">RESOLVED</text>
        
        <text x="14" y="56" fill="{WHITE}" font-size="9.5" font-weight="700">Field Action Complete</text>
        <text x="14" y="74" fill="{MUTED}" font-size="9">• Vehicle intercepted OR</text>
        <text x="14" y="90" fill="{MUTED}" font-size="9">• False positive marked</text>
        <text x="14" y="106" fill="{MUTED}" font-size="9">• Mandatory notes filed</text>
        <text x="14" y="126" fill="{WHITE}" font-size="9" font-weight="700">Officer Badge Logged</text>
      </g>
      
      <!-- Transition 3 -> 4 -->
      <path d="M 610 132 L 640 132" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
      <text x="625" y="124" fill="{PURPLE_LIGHT}" font-size="9" font-weight="700" text-anchor="middle">CLOSE</text>
      
      <!-- State 4: CLOSED -->
      <g transform="translate(640, 60)">
        <rect width="135" height="145" rx="8" fill="#160826" stroke="{MUTED}" stroke-width="2" />
        <circle cx="20" cy="24" r="7" fill="{MUTED}" />
        <text x="75" y="28" fill="{WHITE}" font-size="12" font-weight="800" text-anchor="middle">CLOSED</text>
        
        <text x="12" y="56" fill="{WHITE}" font-size="9.5" font-weight="700">Case Archived</text>
        <text x="12" y="74" fill="{MUTED}" font-size="9">• Dossier exported</text>
        <text x="12" y="90" fill="{MUTED}" font-size="9">• Evidence sealed</text>
        <text x="12" y="106" fill="{MUTED}" font-size="9">• Read-only audit</text>
        <text x="12" y="126" fill="{GREEN}" font-size="9" font-weight="700">Immutable record</text>
      </g>
      
      <!-- Feedback / Reopen Transition -->
      <path d="M 527 205 L 527 235 L 117 235 L 117 205" stroke="{AMBER}" stroke-width="1.8" stroke-dasharray="4,3" marker-end="url(#arr)" />
      <text x="322" y="230" fill="{AMBER}" font-size="9" font-weight="700" text-anchor="middle">RE-OPEN ON NEW SIGHTING OR DISPUTE</text>
      
      <!-- FSM Rules & Security Controls Matrix (Bottom half) -->
      <g transform="translate(20, 255)">
        <rect width="760" height="200" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{CYAN}" font-size="11.5" font-weight="800">GOVERNANCE &amp; AUDIT ENFORCEMENT RULES:</text>
        
        <g transform="translate(16, 38)">
          <rect width="350" height="70" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
          <text x="12" y="20" fill="{WHITE}" font-size="10" font-weight="700">Role-Based Mutation Restrictions</text>
          <text x="12" y="36" fill="{MUTED}" font-size="9">• Only POLICE_OFFICER or INVESTIGATOR can resolve</text>
          <text x="12" y="50" fill="{MUTED}" font-size="9">• VIEWER and AUDITOR roles cannot alter FSM state</text>
          <text x="12" y="64" fill="{GREEN}" font-size="9">Enforced via FastAPI Depends(require_role)</text>
        </g>
        
        <g transform="translate(385, 38)">
          <rect width="360" height="70" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
          <text x="12" y="20" fill="{WHITE}" font-size="10" font-weight="700">Mandatory Officer Justification Notes</text>
          <text x="12" y="36" fill="{MUTED}" font-size="9">• RESOLVED state requires min 20 character note</text>
          <text x="12" y="50" fill="{MUTED}" font-size="9">• Captures officer ID, timestamp, and field unit ID</text>
          <text x="12" y="64" fill="{AMBER}" font-size="9">Rejects empty resolution requests with HTTP 422</text>
        </g>
        
        <g transform="translate(16, 118)">
          <rect width="730" height="68" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
          <text x="12" y="20" fill="{WHITE}" font-size="10" font-weight="700">Cryptographic Audit Chain &amp; Section 65B Evidence Certificate</text>
          <text x="12" y="36" fill="{MUTED}" font-size="9">• Every FSM transition generates a cryptographic audit log with request SHA-256 hash and operator IP</text>
          <text x="12" y="52" fill="{MUTED}" font-size="9">• Closing an incident locks all sightings into an immutable forensic dossier PDF compliant with Indian Evidence Act</text>
        </g>
      </g>
    </g>"""

# ==============================================================================
# Diagram 07: GIS Spatial Intelligence & CCTV Coverage Wedges
# ==============================================================================
def gen_svg_07():
    return f"""
    <!-- Part 1: Trigonometric CCTV Coverage Wedge Model -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="340" rx="8" fill="url(#cardGrad)" stroke="{GREEN}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#0C2618" />
      <text x="20" y="23" fill="{GREEN}" font-size="13" font-weight="800">1. CCTV COVERAGE WEDGE GEOMETRY &amp; POSTGIS SPATIAL PROJECTION</text>
      
      <!-- Visual Trigonometric Wedge Graphic (Left) -->
      <g transform="translate(30, 50)">
        <rect width="360" height="270" rx="6" fill="#0A0416" stroke="{BORDER}" stroke-width="1" />
        
        <!-- Camera Node Origin -->
        <circle cx="80" cy="200" r="12" fill="#7C3AED" stroke="{WHITE}" stroke-width="2" filter="url(#subtleGlow)" />
        <text x="80" y="228" fill="{WHITE}" font-size="10" font-weight="700" text-anchor="middle">CAMERA (x0, y0)</text>
        <text x="80" y="242" fill="{CYAN}" font-size="9" text-anchor="middle">Lat: 23.0225, Lon: 72.5714</text>
        
        <!-- Optical Heading Axis -->
        <line x1="80" y1="200" x2="280" y2="70" stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="4,4" />
        <text x="250" y="60" fill="{MUTED}" font-size="9.5">Heading Vector (θ = 45°)</text>
        
        <!-- Wedge Polygon Fill -->
        <path d="M 80 200 L 260 40 A 240 240 0 0 1 310 140 Z" fill="{GREEN}" fill-opacity="0.18" stroke="{GREEN}" stroke-width="2" />
        
        <!-- Distance Arc (d) -->
        <line x1="80" y1="200" x2="310" y2="140" stroke="{GREEN}" stroke-width="1.5" />
        <text x="180" y="195" fill="{GREEN}" font-size="9.5" font-weight="700">Detection Range (d = 120m)</text>
        
        <!-- FOV Angle Arc -->
        <path d="M 140 160 A 70 70 0 0 1 155 185" fill="none" stroke="{AMBER}" stroke-width="2" />
        <text x="165" y="175" fill="{AMBER}" font-size="9.5" font-weight="700">FOV (α = 70°)</text>
      </g>
      
      <!-- Mathematical Formulation & PostGIS Details (Right) -->
      <g transform="translate(410, 50)">
        <rect width="365" height="270" rx="6" fill="#0A0416" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{WHITE}" font-size="11.5" font-weight="800">TRIGONOMETRIC FORMULATION</text>
        
        <text x="16" y="46" fill="{CYAN}" font-size="9.5" font-weight="700">Coverage Wedge Apex Coordinates:</text>
        <text x="16" y="64" fill="{WHITE}" font-family="monospace" font-size="10">P1 = (x0 + d·sin(θ - α/2), y0 + d·cos(θ - α/2))</text>
        <text x="16" y="82" fill="{WHITE}" font-family="monospace" font-size="10">P2 = (x0 + d·sin(θ + α/2), y0 + d·cos(θ + α/2))</text>
        
        <rect x="12" y="98" width="341" height="158" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
        <text x="20" y="118" fill="{GREEN}" font-size="10" font-weight="700">POSTGIS SPATIAL QUERY INTEGRATION:</text>
        <text x="20" y="136" fill="{MUTED}" font-size="9">• Stored as native PostGIS POLYGON geometry</text>
        <text x="20" y="152" fill="{MUTED}" font-size="9">• GIST Spatial Index on coverage_polygon</text>
        <text x="20" y="168" fill="{MUTED}" font-size="9">• Queries: ST_Within(vehicle_pt, coverage_wedge)</text>
        <text x="20" y="186" fill="{WHITE}" font-size="9.5" font-weight="700">Automatic Blindspot Detection:</text>
        <text x="20" y="202" fill="{MUTED}" font-size="9">• ST_Difference detects uncovered highway gaps</text>
        <text x="20" y="218" fill="{CYAN}" font-size="9">• Spatial Query Latency: &lt; 1.9ms over 80K nodes</text>
      </g>
    </g>
    
    <path d="M 430 360 L 430 390" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Part 2: Multi-Camera Highway Trajectory Reconstruction -->
    <g transform="translate(30, 390)" filter="url(#shadow)">
      <rect width="800" height="370" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1D0E42" />
      <text x="20" y="23" fill="{WHITE}" font-size="13" font-weight="800">2. MULTI-CAMERA TRAJECTORY RECONSTRUCTION &amp; INTERCEPT PREDICTION</text>
      
      <!-- Trajectory Corridor Map Visual -->
      <g transform="translate(20, 48)">
        <!-- Highway Base Ribbon -->
        <rect width="760" height="175" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        
        <!-- Road Line -->
        <path d="M 40 100 Q 220 50 400 110 T 720 70" fill="none" stroke="#25104A" stroke-width="24" />
        <path d="M 40 100 Q 220 50 400 110 T 720 70" fill="none" stroke="{BORDER_LIGHT}" stroke-width="2" stroke-dasharray="8,6" />
        
        <!-- Sighting 1 -->
        <g transform="translate(60, 50)">
          <circle cx="20" cy="50" r="14" fill="{GREEN}" stroke="{WHITE}" stroke-width="2" filter="url(#subtleGlow)" />
          <text x="20" y="55" fill="{WHITE}" font-size="11" font-weight="800" text-anchor="middle">1</text>
          <rect x="-35" y="70" width="110" height="42" rx="4" fill="#15082E" stroke="{GREEN}" stroke-width="1" />
          <text x="20" y="84" fill="{WHITE}" font-size="9" font-weight="700" text-anchor="middle">SG Highway Junction</text>
          <text x="20" y="96" fill="{GREEN}" font-size="8.5" text-anchor="middle">Cam #01 • 14:02:11</text>
          <text x="20" y="106" fill="{MUTED}" font-size="8" text-anchor="middle">GJ01AB1234 (Swift)</text>
        </g>
        
        <!-- Sighting 2 -->
        <g transform="translate(360, 60)">
          <circle cx="20" cy="50" r="14" fill="{CYAN}" stroke="{WHITE}" stroke-width="2" filter="url(#subtleGlow)" />
          <text x="20" y="55" fill="{WHITE}" font-size="11" font-weight="800" text-anchor="middle">2</text>
          <rect x="-40" y="70" width="120" height="42" rx="4" fill="#15082E" stroke="{CYAN}" stroke-width="1" />
          <text x="20" y="84" fill="{WHITE}" font-size="9" font-weight="700" text-anchor="middle">Sanand Crossroad</text>
          <text x="20" y="96" fill="{CYAN}" font-size="8.5" text-anchor="middle">Cam #04 • 14:07:45</text>
          <text x="20" y="106" fill="{MUTED}" font-size="8" text-anchor="middle">Speed: ~62 km/h</text>
        </g>
        
        <!-- Sighting 3 (Predicted Intercept) -->
        <g transform="translate(640, 20)">
          <circle cx="20" cy="50" r="16" fill="{RED}" stroke="{WHITE}" stroke-width="2.5" filter="url(#subtleGlow)" />
          <text x="20" y="55" fill="{WHITE}" font-size="12" font-weight="800" text-anchor="middle">3</text>
          <rect x="-55" y="72" width="150" height="52" rx="4" fill="#2E0A1E" stroke="{RED}" stroke-width="1.5" />
          <text x="20" y="86" fill="{RED}" font-size="9.5" font-weight="800" text-anchor="middle">PREDICTED INTERCEPT</text>
          <text x="20" y="98" fill="{WHITE}" font-size="9" text-anchor="middle">Bavla Toll Plaza (Cam #09)</text>
          <text x="20" y="110" fill="{AMBER}" font-size="8.5" font-weight="700" text-anchor="middle">ETA: 14:14:30 (In 6.5 mins)</text>
          <text x="20" y="120" fill="{MUTED}" font-size="8" text-anchor="middle">Distance: 6.8 km</text>
        </g>
      </g>
      
      <!-- Operational Intercept Panel -->
      <g transform="translate(20, 235)">
        <rect width="760" height="120" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{AMBER}" font-size="11" font-weight="800">AUTOMATED POLICE DISPATCH &amp; INTERCEPT PROTOCOL:</text>
        
        <g transform="translate(16, 36)">
          <rect width="350" height="70" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
          <text x="12" y="20" fill="{WHITE}" font-size="9.5" font-weight="700">Toll Gate Auto-Barricade Pre-Alert</text>
          <text x="12" y="36" fill="{MUTED}" font-size="9">• Transmits alert payload to Bavla Toll Plaza C2 node</text>
          <text x="12" y="50" fill="{MUTED}" font-size="9">• Fast-lane boom barrier hold configured</text>
          <text x="12" y="64" fill="{GREEN}" font-size="9">Target lane camera promoted to BURST_TRACKING</text>
        </g>
        
        <g transform="translate(385, 36)">
          <rect width="360" height="70" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
          <text x="12" y="20" fill="{WHITE}" font-size="9.5" font-weight="700">Nearest PCR Interceptor Unit Alert</text>
          <text x="12" y="36" fill="{MUTED}" font-size="9">• Dispatches GPS coordinates to PCR Van #14 (2.1 km away)</text>
          <text x="12" y="50" fill="{MUTED}" font-size="9">• Live tactical HUD with vehicle color, make &amp; plate</text>
          <text x="12" y="64" fill="{CYAN}" font-size="9">Sub-second notification via Netram Mobile Gateway</text>
        </g>
      </g>
    </g>"""

# ==============================================================================
# Diagram 08: Multi-Camera Ring Buffer & Thread Isolation
# ==============================================================================
def gen_svg_08():
    return f"""
    <!-- Title Card -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="85" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="1.8" />
      <text x="20" y="32" fill="{WHITE}" font-size="14.5" font-weight="800">DECOUPLED 1-SLOT LATEST FRAME RING BUFFER ARCHITECTURE</text>
      <text x="20" y="52" fill="{MUTED}" font-size="11">Eliminates inference lag accumulation, guarantees zero buffer bloat, and provides complete camera thread isolation</text>
      <text x="20" y="70" fill="{CYAN}" font-size="10.5" font-weight="600">MultiStreamYOLO26Manager (`backend/app/services/multi_stream_yolo26_manager.py`)</text>
    </g>
    
    <!-- Camera 1 Stream Pipeline -->
    <g transform="translate(30, 125)" filter="url(#shadow)">
      <rect width="800" height="175" rx="8" fill="url(#cardGrad)" stroke="{BORDER}" stroke-width="1.5" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#1A0D3D" />
      <text x="16" y="20" fill="{WHITE}" font-size="11.5" font-weight="700">CAMERA STREAM 01 // AHMEDABAD SG HIGHWAY (ACTIVE &amp; HEALTHY)</text>
      
      <!-- Thread 1: Ingest -->
      <g transform="translate(20, 45)">
        <rect width="200" height="110" rx="6" fill="#0C041C" stroke="{GREEN}" stroke-width="1.5" />
        <text x="14" y="22" fill="{GREEN}" font-size="10.5" font-weight="700">CAPTURE THREAD #1</text>
        <text x="14" y="40" fill="{WHITE}" font-size="9">• RTSP over TCP Reader</text>
        <text x="14" y="56" fill="{WHITE}" font-size="9">• 25 FPS continuous pull</text>
        <text x="14" y="72" fill="{MUTED}" font-size="8.5">• Hardware PTS tracking</text>
        <text x="14" y="94" fill="{GREEN}" font-size="9" font-weight="700">Status: HEALTHY (25 fps)</text>
      </g>
      
      <path d="M 220 100 L 265 100" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr-green)" />
      
      <!-- 1-Slot Buffer -->
      <g transform="translate(265, 45)">
        <rect width="240" height="110" rx="6" fill="#0C041C" stroke="{AMBER}" stroke-width="2" />
        <text x="14" y="22" fill="{AMBER}" font-size="10.5" font-weight="800">1-SLOT RING BUFFER #1</text>
        
        <rect x="14" y="32" width="212" height="42" rx="4" fill="#1C1004" stroke="{AMBER}" stroke-width="1" />
        <text x="120" y="48" fill="{WHITE}" font-size="10" font-weight="700" text-anchor="middle">LATEST FRAME SLOT</text>
        <text x="120" y="64" fill="{AMBER}" font-size="8.5" text-anchor="middle">Always holds frame N (Silent Overwrite)</text>
        
        <text x="14" y="90" fill="{MUTED}" font-size="8.5">• Queue length = EXACTLY 1</text>
        <text x="14" y="103" fill="{GREEN}" font-size="8.5" font-weight="700">• ZERO BUFFER BLOAT (Sub-20ms)</text>
      </g>
      
      <path d="M 505 100 L 550 100" stroke="{PURPLE_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
      
      <!-- Worker Thread -->
      <g transform="translate(550, 45)">
        <rect width="230" height="110" rx="6" fill="#0C041C" stroke="{PURPLE_LIGHT}" stroke-width="1.5" />
        <text x="14" y="22" fill="{PURPLE_LIGHT}" font-size="10.5" font-weight="700">INFERENCE WORKER THREAD</text>
        <text x="14" y="40" fill="{WHITE}" font-size="9">• Grabs latest frame from slot</text>
        <text x="14" y="56" fill="{WHITE}" font-size="9">• Executes YOLO26 + ANPR</text>
        <text x="14" y="72" fill="{MUTED}" font-size="8.5">• Inference latency: 16.4ms</text>
        <text x="14" y="94" fill="{CYAN}" font-size="9" font-weight="700">Egress: WebSocket Broadcast</text>
      </g>
    </g>
    
    <!-- Camera 2 Stream Pipeline (Demonstrating Thread Isolation on Failure) -->
    <g transform="translate(30, 320)" filter="url(#shadow)">
      <rect width="800" height="175" rx="8" fill="url(#cardGrad)" stroke="{RED}" stroke-width="1.5" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#330A1C" />
      <text x="16" y="20" fill="{WHITE}" font-size="11.5" font-weight="700">CAMERA STREAM 02 // SURAT RING ROAD (PACKET DROP / NETWORK TIMEOUT)</text>
      
      <!-- Thread 2: Timeout -->
      <g transform="translate(20, 45)">
        <rect width="200" height="110" rx="6" fill="#0C041C" stroke="{RED}" stroke-width="1.5" />
        <text x="14" y="22" fill="{RED}" font-size="10.5" font-weight="700">CAPTURE THREAD #2</text>
        <text x="14" y="40" fill="{RED}" font-size="9">• Network Socket Timeout</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• 5.0s read deadline reached</text>
        <text x="14" y="72" fill="{AMBER}" font-size="8.5">• Backoff retry 2s -> 4s</text>
        <text x="14" y="94" fill="{RED}" font-size="9" font-weight="700">Status: RECONNECTING</text>
      </g>
      
      <path d="M 220 100 L 265 100" stroke="{RED}" stroke-width="2" stroke-dasharray="4,4" />
      
      <!-- 1-Slot Buffer Discard -->
      <g transform="translate(265, 45)">
        <rect width="240" height="110" rx="6" fill="#0C041C" stroke="{RED}" stroke-width="1.5" />
        <text x="14" y="22" fill="{RED}" font-size="10.5" font-weight="800">1-SLOT BUFFER ISOLATION</text>
        
        <rect x="14" y="32" width="212" height="42" rx="4" fill="#200610" stroke="{RED}" stroke-width="1" />
        <text x="120" y="48" fill="{RED}" font-size="10" font-weight="700" text-anchor="middle">STALE SLOT DROPPED</text>
        <text x="120" y="64" fill="{MUTED}" font-size="8.5" text-anchor="middle">Zero frames queued; no stall</text>
        
        <text x="14" y="90" fill="{MUTED}" font-size="8.5">• Thread sleeps peacefully</text>
        <text x="14" y="103" fill="{GREEN}" font-size="8.5" font-weight="700">• ZERO IMPACT ON CAM 01 OR 03</text>
      </g>
      
      <path d="M 505 100 L 550 100" stroke="{MUTED}" stroke-width="2" stroke-dasharray="4,4" />
      
      <!-- Worker Thread unaffected -->
      <g transform="translate(550, 45)">
        <rect width="230" height="110" rx="6" fill="#0C041C" stroke="{GREEN}" stroke-width="1.5" />
        <text x="14" y="22" fill="{GREEN}" font-size="10.5" font-weight="700">SHARED GPU WORKER POOL</text>
        <text x="14" y="40" fill="{WHITE}" font-size="9">• Unaffected by Cam 02 drop</text>
        <text x="14" y="56" fill="{WHITE}" font-size="9">• Processes other 47 streams</text>
        <text x="14" y="72" fill="{MUTED}" font-size="8.5">• No deadlock, no GPU freeze</text>
        <text x="14" y="94" fill="{GREEN}" font-size="9" font-weight="700">Worker health: 100% NOMINAL</text>
      </g>
    </g>
    
    <!-- Part 3: PTS Discontinuity Detection & Track Pool Reset -->
    <g transform="translate(30, 515)" filter="url(#shadow)">
      <rect width="800" height="245" rx="8" fill="url(#cardGrad)" stroke="{AMBER}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#2E1805" />
      <text x="20" y="23" fill="{AMBER}" font-size="13" font-weight="800">HARDWARE PTS DELTA DISCONTINUITY DETECTION &amp; TRACK POOL RESET</text>
      
      <g transform="translate(20, 48)">
        <rect width="365" height="180" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{WHITE}" font-size="11" font-weight="700">THE VIDEO LOOP / PTS DRIFT PROBLEM</text>
        <text x="16" y="44" fill="{MUTED}" font-size="9.5">• Synthetic camera feeds or looped MP4/RTSP streams</text>
        <text x="16" y="60" fill="{MUTED}" font-size="9.5">  jump presentation timestamp (PTS) back to 0.0s</text>
        <text x="16" y="76" fill="{MUTED}" font-size="9.5">• In legacy systems, this causes severe identity drift:</text>
        <text x="16" y="92" fill="{RED}" font-size="9.5">  Old vehicle track IDs fuse into newly looped cars</text>
        <text x="16" y="112" fill="{MUTED}" font-size="9.5">• Generates false trajectory alerts and corrupted dossiers</text>
        <text x="16" y="136" fill="{AMBER}" font-size="10" font-weight="700">PHANTOM Delta Trigger:</text>
        <text x="16" y="154" fill="{WHITE}" font-family="monospace" font-size="9.5">if (current_pts - last_pts) &lt; -1.0s:</text>
      </g>
      
      <g transform="translate(415, 48)">
        <rect width="365" height="180" rx="6" fill="#0C041C" stroke="{GREEN}" stroke-width="1" />
        <text x="16" y="24" fill="{GREEN}" font-size="11" font-weight="700">AUTOMATIC TRACK POOL FLUSH</text>
        <text x="16" y="44" fill="{WHITE}" font-size="9.5">1. Timestamp Discontinuity Flagged:</text>
        <text x="16" y="60" fill="{CYAN}" font-size="9">   logger.warning("PTS jump detected on camera %s", cam_id)</text>
        
        <text x="16" y="82" fill="{WHITE}" font-size="9.5">2. Clears Active Track Pool:</text>
        <text x="16" y="98" fill="{MUTED}" font-size="9">   tracker.reset_tracks(camera_id)</text>
        
        <text x="16" y="120" fill="{WHITE}" font-size="9.5">3. Fresh Track IDs Allocated:</text>
        <text x="16" y="136" fill="{MUTED}" font-size="9">   Next frame initiates clean tracking sequence</text>
        <text x="16" y="160" fill="{GREEN}" font-size="9.5" font-weight="700">Result: ZERO identity drift across looped feeds</text>
      </g>
    </g>"""

# ==============================================================================
# Diagram 09: Forensic Investigation & Certified Dossier Workflow
# ==============================================================================
def gen_svg_09():
    return f"""
    <!-- Step 1: Investigation Query Input -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="110" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#130B2E" />
      <text x="20" y="20" fill="{CYAN}" font-size="12" font-weight="800">1. MULTI-MODAL INVESTIGATION QUERY DISPATCH</text>
      
      <g transform="translate(20, 42)">
        <rect width="365" height="56" rx="4" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">QUERY PATH A: DIRECT LICENSE PLATE</text>
        <text x="14" y="40" fill="{GREEN}" font-family="monospace" font-size="10">GET /api/v1/investigations/search?plate=GJ01AB1234</text>
      </g>
      
      <g transform="translate(415, 42)">
        <rect width="365" height="56" rx="4" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">QUERY PATH B: MAKE / MODEL / COLOR HEURISTIC</text>
        <text x="14" y="40" fill="{PURPLE_LIGHT}" font-family="monospace" font-size="10">search?vehicle_make=Swift&amp;color=Red&amp;district=Ahmedabad</text>
      </g>
    </g>
    
    <path d="M 430 130 L 430 155" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Step 2: Sighting Graph Retrieval -->
    <g transform="translate(30, 155)" filter="url(#shadow)">
      <rect width="800" height="130" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#1D0E42" />
      <text x="20" y="20" fill="{WHITE}" font-size="12" font-weight="800">2. TEMPORAL SIGHTING GRAPH &amp; EVIDENCE RETRIEVAL</text>
      
      <!-- 3 Sightings Visual -->
      <g transform="translate(20, 42)">
        <rect width="240" height="75" rx="4" fill="#0C041C" stroke="{CYAN}" stroke-width="1" />
        <text x="12" y="20" fill="{CYAN}" font-size="10" font-weight="700">SIGHTING 1 // 14:02:11</text>
        <text x="12" y="36" fill="{WHITE}" font-size="9">SG Highway Junction (Cam #01)</text>
        <text x="12" y="52" fill="{MUTED}" font-size="8.5">Plate Crop: crop_01_sg.jpg</text>
        <text x="12" y="66" fill="{GREEN}" font-size="8.5">Plate Confidence: 94.2%</text>
      </g>
      
      <g transform="translate(280, 42)">
        <rect width="240" height="75" rx="4" fill="#0C041C" stroke="{CYAN}" stroke-width="1" />
        <text x="12" y="20" fill="{CYAN}" font-size="10" font-weight="700">SIGHTING 2 // 14:07:45</text>
        <text x="12" y="36" fill="{WHITE}" font-size="9">Sanand Crossroad (Cam #04)</text>
        <text x="12" y="52" fill="{MUTED}" font-size="8.5">Plate Crop: crop_04_sanand.jpg</text>
        <text x="12" y="66" fill="{GREEN}" font-size="8.5">Plate Confidence: 91.8%</text>
      </g>
      
      <g transform="translate(540, 42)">
        <rect width="240" height="75" rx="4" fill="#0C041C" stroke="{CYAN}" stroke-width="1" />
        <text x="12" y="20" fill="{CYAN}" font-size="10" font-weight="700">SIGHTING 3 // 14:14:30</text>
        <text x="12" y="36" fill="{WHITE}" font-size="9">Bavla Toll Plaza (Cam #09)</text>
        <text x="12" y="52" fill="{MUTED}" font-size="8.5">Plate Crop: crop_09_bavla.jpg</text>
        <text x="12" y="66" fill="{RED}" font-size="8.5">BURST Stream Captured</text>
      </g>
    </g>
    
    <path d="M 430 285 L 430 310" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr-green)" />
    
    <!-- Step 3: SHA-256 Cryptographic Verification -->
    <g transform="translate(30, 310)" filter="url(#shadow)">
      <rect width="800" height="155" rx="8" fill="url(#cardGrad)" stroke="{GREEN}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#0E2E18" />
      <text x="20" y="20" fill="{GREEN}" font-size="12" font-weight="800">3. CRYPTOGRAPHIC SHA-256 EVIDENCE CHAIN-OF-CUSTODY VERIFICATION</text>
      
      <g transform="translate(20, 42)">
        <rect width="365" height="98" rx="4" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="20" fill="{WHITE}" font-size="10" font-weight="700">Endpoint: POST /api/v1/investigations/verify</text>
        <text x="14" y="38" fill="{MUTED}" font-size="9">• Re-computes SHA-256 digest of stored crop</text>
        <text x="14" y="54" fill="{MUTED}" font-size="9">• Compares against immutable alert hash</text>
        <text x="14" y="70" fill="{WHITE}" font-family="monospace" font-size="8.5">stored_hash == hashlib.sha256(raw_bytes)</text>
        <text x="14" y="88" fill="{GREEN}" font-size="9" font-weight="700">VALID: Zero bit-rot or tampering</text>
      </g>
      
      <g transform="translate(415, 42)">
        <rect width="365" height="98" rx="4" fill="#0C041C" stroke="{GREEN}" stroke-width="1" />
        <text x="14" y="20" fill="{GREEN}" font-size="10" font-weight="700">Digital Watermark Stamp Applied</text>
        <text x="14" y="38" fill="{MUTED}" font-size="9">• Hardware GPS Coordinates embedded</text>
        <text x="14" y="54" fill="{MUTED}" font-size="9">• NTP Microsecond Hardware Timestamp</text>
        <text x="14" y="70" fill="{MUTED}" font-size="9">• Camera Hardware Serial Hash</text>
        <text x="14" y="88" fill="{CYAN}" font-size="9" font-weight="700">Meets Section 65B Admissibility Rules</text>
      </g>
    </g>
    
    <path d="M 430 465 L 430 490" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Step 4: Certified Forensic Dossier PDF Generation -->
    <g transform="translate(30, 490)" filter="url(#shadow)">
      <rect width="800" height="270" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1C0E42" />
      <text x="20" y="23" fill="{WHITE}" font-size="13" font-weight="800">4. CERTIFIED SECTION 65B COURT-ADMISSIBLE FORENSIC DOSSIER PDF</text>
      
      <!-- Dossier Document Graphic Mockup -->
      <g transform="translate(30, 50)">
        <rect width="200" height="200" rx="4" fill="#0C041C" stroke="{WHITE}" stroke-width="1.5" />
        
        <!-- Header of PDF -->
        <rect x="10" y="10" width="180" height="24" rx="2" fill="#24104D" />
        <text x="100" y="26" fill="{WHITE}" font-size="8" font-weight="700" text-anchor="middle">GUJARAT POLICE NETRAM C2</text>
        
        <!-- Red Seal -->
        <circle cx="165" cy="55" r="14" fill="{RED}" fill-opacity="0.3" stroke="{RED}" stroke-width="1.5" />
        <text x="165" y="58" fill="{RED}" font-size="6" font-weight="800" text-anchor="middle">SEC 65B</text>
        
        <text x="16" y="50" fill="{CYAN}" font-size="8" font-weight="700">CASE DOSSIER #GJ-2026-881</text>
        <text x="16" y="62" fill="{MUTED}" font-size="7">Target: GJ01AB1234 (Swift)</text>
        
        <!-- Timeline snippet in mockup -->
        <line x1="16" y1="72" x2="184" y2="72" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="84" fill="{WHITE}" font-size="7">• 14:02:11 SG Highway (Cam #01)</text>
        <text x="16" y="96" fill="{WHITE}" font-size="7">• 14:07:45 Sanand Rd (Cam #04)</text>
        <text x="16" y="108" fill="{WHITE}" font-size="7">• 14:14:30 Bavla Toll (Cam #09)</text>
        
        <!-- Evidence Hashes snippet -->
        <line x1="16" y1="116" x2="184" y2="116" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="128" fill="{GREEN}" font-size="6.5">SHA-256: 9e107d9d372bb6826bd81e35...</text>
        <text x="16" y="138" fill="{GREEN}" font-size="6.5">SHA-256: 4b227777d4dd1fc61c6f884f...</text>
        
        <!-- Officer Signature -->
        <rect x="16" y="150" width="168" height="38" rx="2" fill="#140828" stroke="#3D1870" stroke-width="1" />
        <text x="22" y="162" fill="{MUTED}" font-size="6.5">Digitally Signed By:</text>
        <text x="22" y="172" fill="{WHITE}" font-size="7" font-weight="700">Inspector R. K. Jadeja, Netram C2</text>
        <text x="22" y="182" fill="{CYAN}" font-size="6">Cert Hash: a891f03d5c... Verified</text>
      </g>
      
      <!-- Dossier Features (Right) -->
      <g transform="translate(250, 50)">
        <rect width="525" height="200" rx="6" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{WHITE}" font-size="11" font-weight="700">MANDATORY INDIAN EVIDENCE ACT STATUTORY INCLUSIONS:</text>
        
        <text x="16" y="46" fill="{MUTED}" font-size="9.5">1. Complete chronological multi-camera trajectory map with GIS coordinates</text>
        <text x="16" y="64" fill="{MUTED}" font-size="9.5">2. High-resolution raw bounding box crops with uncompressed plate crops</text>
        <text x="16" y="82" fill="{MUTED}" font-size="9.5">3. Immutable cryptographic SHA-256 hash printed alongside each exhibit</text>
        <text x="16" y="100" fill="{MUTED}" font-size="9.5">4. Section 65B Electronic Record Certificate signed by authorized officer</text>
        <text x="16" y="118" fill="{MUTED}" font-size="9.5">5. Hardware device serial number, MAC address, and firmware revision hash</text>
        <text x="16" y="136" fill="{MUTED}" font-size="9.5">6. Exact UTC &amp; IST synchronized NTP time stamps (microsecond precision)</text>
        
        <rect x="16" y="152" width="493" height="36" rx="4" fill="#16082A" stroke="{GREEN}" stroke-width="1" />
        <text x="26" y="174" fill="{GREEN}" font-size="10" font-weight="700">Generated instantaneously via ReportLab PDF engine: &lt; 850ms per dossier</text>
      </g>
    </g>"""

# ==============================================================================
# Diagram 10: Security, RBAC Matrix & Governance Architecture
# ==============================================================================
def gen_svg_10():
    roles = [
        ("SYSTEM_ADMIN", "Full system config, camera onboarding, user provisioning, global audit logs", RED),
        ("POLICE_OFFICER", "Live video monitoring, watchlist management, incident escalation, PCR dispatch", PURPLE_LIGHT),
        ("INVESTIGATOR", "Case dossier generation, historical ANPR search, certified court evidence export", CYAN),
        ("ANALYST", "Statistical dashboards, traffic density heatmaps, model accuracy reviews", GREEN),
        ("VIEWER", "Read-only live video grid and GIS map viewing (zero mutation or export rights)", DIM),
        ("AUDITOR", "Immutable security audit trail inspection and compliance reporting", AMBER),
        ("AI_WORKER", "Machine-to-machine inference ingestion and real-time telemetry broadcast", MUTED)
    ]
    
    body = """
    <!-- Top Security Perimeter -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="90" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="1.8" />
      <text x="20" y="30" fill="{WHITE}" font-size="13.5" font-weight="800">ZERO-TRUST PERIMETER DEFENSE &amp; AUTHENTICATION LIFECYCLE</text>
      
      <g transform="translate(20, 42)">
        <rect width="240" height="38" rx="4" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="120" y="24" fill="{CYAN}" font-size="10" font-weight="700" text-anchor="middle">JWT (HS256) Access Tokens (15m)</text>
      </g>
      <g transform="translate(280, 42)">
        <rect width="240" height="38" rx="4" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="120" y="24" fill="{GREEN}" font-size="10" font-weight="700" text-anchor="middle">Argon2id Password Hashing</text>
      </g>
      <g transform="translate(540, 42)">
        <rect width="240" height="38" rx="4" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="120" y="24" fill="{RED}" font-size="10" font-weight="700" text-anchor="middle">SSRF Metadata IP Protection</text>
      </g>
    </g>
    
    <!-- Role-Based Access Control (RBAC) 7 Roles Matrix -->
    <g transform="translate(30, 125)" filter="url(#shadow)">
      <rect width="800" height="425" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1C0E42" />
      <text x="20" y="23" fill="{WHITE}" font-size="13" font-weight="800">7-ROLE GRANULAR ROLE-BASED ACCESS CONTROL (RBAC) MATRIX</text>
    """
    
    y = 45
    for role, scope, color in roles:
        body += f"""
        <g transform="translate(20, {y})">
          <rect width="760" height="48" rx="4" fill="#0C041C" stroke="{color}" stroke-width="1.2" />
          
          <rect x="12" y="10" width="150" height="28" rx="4" fill="{color}" fill-opacity="0.2" stroke="{color}" stroke-width="1" />
          <text x="87" y="28" fill="{color}" font-size="10.5" font-weight="800" text-anchor="middle">{role}</text>
          
          <text x="175" y="29" fill="{WHITE}" font-size="10.5">{scope}</text>
        </g>"""
        y += 54
        
    body += f"""
    </g>
    
    <!-- Tamper-Evident Audit Logging -->
    <g transform="translate(30, 565)" filter="url(#shadow)">
      <rect width="800" height="195" rx="8" fill="url(#cardGrad)" stroke="{GREEN}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#0E2E18" />
      <text x="20" y="23" fill="{GREEN}" font-size="13" font-weight="800">SECTION 65B IMMUTABLE AUDIT TRAIL &amp; SSRF PROTECTION</text>
      
      <g transform="translate(20, 48)">
        <rect width="365" height="130" rx="4" fill="#0C041C" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="22" fill="{WHITE}" font-size="11" font-weight="700">Cryptographic Audit Logging</text>
        <text x="16" y="40" fill="{MUTED}" font-size="9">• Logs every API mutation, login, and export</text>
        <text x="16" y="56" fill="{MUTED}" font-size="9">• Captures Officer ID, Client IP, Timestamp</text>
        <text x="16" y="72" fill="{MUTED}" font-size="9">• Cryptographic request body hash verification</text>
        <text x="16" y="90" fill="{WHITE}" font-family="monospace" font-size="8.5">audit_hash = sha256(user + action + ts + req)</text>
        <text x="16" y="112" fill="{GREEN}" font-size="9" font-weight="700">Immutable append-only DB table</text>
      </g>
      
      <g transform="translate(415, 48)">
        <rect width="365" height="130" rx="4" fill="#0C041C" stroke="{RED}" stroke-width="1" />
        <text x="16" y="22" fill="{RED}" font-size="11" font-weight="700">SSRF &amp; Infrastructure Protection</text>
        <text x="16" y="40" fill="{WHITE}" font-size="9">• Blocks cloud metadata IP: 169.254.169.254</text>
        <text x="16" y="56" fill="{WHITE}" font-size="9">• Blocks localhost / 127.0.0.1 stream injection</text>
        <text x="16" y="72" fill="{WHITE}" font-size="9">• Strictly validates RTSP &amp; WHEP schemes</text>
        <text x="16" y="90" fill="{MUTED}" font-size="9">• Enforces CORS origin whitelisting</text>
        <text x="16" y="112" fill="{AMBER}" font-size="9" font-weight="700">SlowAPI rate limits: 120 req/min per IP</text>
      </g>
    </g>"""
    return body

# ==============================================================================
# Diagram 11: 80,000-Camera State-Wide Scalability Architecture (HERO)
# ==============================================================================
def gen_svg_11():
    return f"""
    <!-- HERO METRICS BANNER (BIG BOLD NUMBERS) -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="135" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2.5" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#1F0D45" />
      <text x="400" y="21" fill="{WHITE}" font-size="12" font-weight="800" text-anchor="middle">GUJARAT STATE-WIDE SURVEILLANCE SCALE // EXECUTIVE COMPUTATION MATRIX</text>
      
      <!-- 4 Huge Metric Cards -->
      <g transform="translate(15, 40)">
        <rect width="180" height="80" rx="6" fill="#0A0318" stroke="{CYAN}" stroke-width="1.8" />
        <text x="90" y="38" fill="{WHITE}" font-size="24" font-weight="900" text-anchor="middle">80,000</text>
        <text x="90" y="56" fill="{CYAN}" font-size="10" font-weight="800" text-anchor="middle">CCTV CAMERAS</text>
        <text x="90" y="70" fill="{MUTED}" font-size="8.5" text-anchor="middle">Across 33 Gujarat Districts</text>
      </g>
      
      <g transform="translate(210, 40)">
        <rect width="180" height="80" rx="6" fill="#0A0318" stroke="{RED}" stroke-width="1.8" />
        <text x="90" y="38" fill="{RED}" font-size="24" font-weight="900" text-anchor="middle">200 Gbps</text>
        <text x="90" y="56" fill="{RED}" font-size="10" font-weight="800" text-anchor="middle">RAW VIDEO STREAM</text>
        <text x="90" y="70" fill="{MUTED}" font-size="8.5" text-anchor="middle">80K x 2.5 Mbps uncompressed</text>
      </g>
      
      <g transform="translate(405, 40)">
        <rect width="180" height="80" rx="6" fill="#0A0318" stroke="{GREEN}" stroke-width="2" />
        <text x="90" y="38" fill="{GREEN}" font-size="24" font-weight="900" text-anchor="middle">99.92%</text>
        <text x="90" y="56" fill="{GREEN}" font-size="10" font-weight="800" text-anchor="middle">BANDWIDTH REDUCTION</text>
        <text x="90" y="70" fill="{WHITE}" font-size="8.5" font-weight="700" text-anchor="middle">WAN load drops to 154 Mbps</text>
      </g>
      
      <g transform="translate(600, 40)">
        <rect width="185" height="80" rx="6" fill="#0A0318" stroke="{AMBER}" stroke-width="1.8" />
        <text x="92" y="38" fill="{AMBER}" font-size="24" font-weight="900" text-anchor="middle">1,667</text>
        <text x="92" y="56" fill="{AMBER}" font-size="10" font-weight="800" text-anchor="middle">NVIDIA L40S GPUs</text>
        <text x="92" y="70" fill="{MUTED}" font-size="8.5" text-anchor="middle">~50.5 GPUs per District CCC</text>
      </g>
    </g>
    
    <!-- 3-Tier Hierarchical Topology Diagram -->
    <!-- Tier 1: 33 District Edge AI Clusters -->
    <g transform="translate(30, 175)" filter="url(#shadow)">
      <rect width="800" height="175" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#0F1836" />
      <text x="20" y="20" fill="{CYAN}" font-size="12" font-weight="800">TIER 1: 33 DISTRICT EDGE NETRAM COMMAND CLUSTERS (EDGE INFERENCE)</text>
      
      <!-- District Cards Mockup -->
      <g transform="translate(20, 42)">
        <rect width="235" height="118" rx="6" fill="#080316" stroke="{CYAN}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">Ahmedabad Netram CCC</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• Ingests 25,000 CCTV feeds</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• 520x NVIDIA L40S GPUs</text>
        <text x="14" y="72" fill="{MUTED}" font-size="9">• 1-Slot decoupled frame buffers</text>
        <text x="14" y="90" fill="{GREEN}" font-size="9">Local YOLO26 &amp; ANPR inference</text>
        <text x="14" y="106" fill="{CYAN}" font-size="8.5">Metadata only pushed upstream</text>
      </g>
      
      <g transform="translate(280, 42)">
        <rect width="235" height="118" rx="6" fill="#080316" stroke="{CYAN}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">Surat Netram CCC</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• Ingests 18,000 CCTV feeds</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• 375x NVIDIA L40S GPUs</text>
        <text x="14" y="72" fill="{MUTED}" font-size="9">• Local incident state machine</text>
        <text x="14" y="90" fill="{GREEN}" font-size="9">Sub-25ms glass-to-detection</text>
        <text x="14" y="106" fill="{CYAN}" font-size="8.5">District FOV wedge spatial map</text>
      </g>
      
      <g transform="translate(540, 42)">
        <rect width="240" height="118" rx="6" fill="#080316" stroke="{CYAN}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">31 Other District CCCs</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• Vadodara, Rajkot, Bhavnagar...</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• 772x GPUs distributed</text>
        <text x="14" y="72" fill="{MUTED}" font-size="9">• Autonomous air-gapped run</text>
        <text x="14" y="90" fill="{GREEN}" font-size="9">Survives central WAN severed</text>
        <text x="14" y="106" fill="{CYAN}" font-size="8.5">Local Redis buffer (10K alerts)</text>
      </g>
    </g>
    
    <!-- Connector Arrow -->
    <path d="M 430 350 L 430 380" stroke="{GREEN}" stroke-width="3" marker-end="url(#arr-green)" />
    <rect x="340" y="357" width="180" height="20" rx="4" fill="#0C041C" stroke="{GREEN}" stroke-width="1" />
    <text x="430" y="371" fill="{GREEN}" font-size="9" font-weight="800" text-anchor="middle">METADATA ONLY: 153.6 Mbps</text>
    
    <!-- Tier 2: Regional Hubs / Zone Gateways -->
    <g transform="translate(30, 385)" filter="url(#shadow)">
      <rect width="800" height="140" rx="8" fill="url(#cardGrad)" stroke="{PURPLE_LIGHT}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="30" rx="8" fill="#1C0E42" />
      <text x="20" y="20" fill="{PURPLE_LIGHT}" font-size="12" font-weight="800">TIER 2: REGIONAL ZONE GATEWAYS (APACHE KAFKA &amp; REDIS CLUSTERS)</text>
      
      <g transform="translate(20, 42)">
        <rect width="365" height="85" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">North &amp; Central Zone Gateway (Ahmedabad)</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• 5-Broker Apache Kafka Cluster (cctv.events topic)</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• Redis Sentinel hot cache for cross-district plate match</text>
        <text x="14" y="72" fill="{CYAN}" font-size="9">Aggregates 45,000 camera event streams</text>
      </g>
      
      <g transform="translate(415, 42)">
        <rect width="365" height="85" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">South &amp; Saurashtra Zone Gateway (Surat)</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• 5-Broker Apache Kafka Cluster (cctv.events topic)</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• Redis Sentinel hot cache for coastal &amp; highway alert bus</text>
        <text x="14" y="72" fill="{CYAN}" font-size="9">Aggregates 35,000 camera event streams</text>
      </g>
    </g>
    
    <!-- Connector Arrow -->
    <path d="M 430 525 L 430 555" stroke="{BORDER_LIGHT}" stroke-width="3" marker-end="url(#arr)" />
    
    <!-- Tier 3: Central State Police Headquarters / Netram State CCC -->
    <g transform="translate(30, 555)" filter="url(#shadow)">
      <rect width="800" height="215" rx="8" fill="url(#cardGrad)" stroke="{AMBER}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#2E1805" />
      <text x="20" y="23" fill="{AMBER}" font-size="13" font-weight="800">TIER 3: CENTRAL STATE COMMAND &amp; CONTROL CENTER (GANDHINAGAR CCC)</text>
      
      <g transform="translate(20, 48)">
        <rect width="240" height="150" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">Master Database Grid</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• PostgreSQL 16 + PostGIS</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• Patroni HA (3-Node cluster)</text>
        <text x="14" y="72" fill="{MUTED}" font-size="9">• Temporal table partitioning</text>
        <text x="14" y="88" fill="{MUTED}" font-size="9">• 80,000 camera GIS index</text>
        <text x="14" y="106" fill="{GREEN}" font-size="9" font-weight="700">Sub-10ms spatial queries</text>
        <text x="14" y="126" fill="{CYAN}" font-size="8.5">Global Watchlist sync</text>
      </g>
      
      <g transform="translate(280, 48)">
        <rect width="240" height="150" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">State AI Copilot &amp; BI</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• SurveillanceCopilot Agent</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• 40+ Grounded tools active</text>
        <text x="14" y="72" fill="{MUTED}" font-size="9">• Multilingual NLP (EN, HI, GU)</text>
        <text x="14" y="88" fill="{MUTED}" font-size="9">• Cross-district trajectory solver</text>
        <text x="14" y="106" fill="{PURPLE_LIGHT}" font-size="9" font-weight="700">High-level threat reasoning</text>
        <text x="14" y="126" fill="{CYAN}" font-size="8.5">Certified dossier builder</text>
      </g>
      
      <g transform="translate(540, 48)">
        <rect width="240" height="150" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="10.5" font-weight="700">Command HUD &amp; Dispatch</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• State-wide executive wall</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• WebSocket alert multiplexer</text>
        <text x="14" y="72" fill="{MUTED}" font-size="9">• Cross-district PCR dispatch</text>
        <text x="14" y="88" fill="{MUTED}" font-size="9">• Incident FSM master sync</text>
        <text x="14" y="106" fill="{AMBER}" font-size="9" font-weight="700">Zero duplicate alerts</text>
        <text x="14" y="126" fill="{RED}" font-size="8.5">Real-time threat interception</text>
      </g>
    </g>"""

# ==============================================================================
# Diagram 12A: Master Component & API Gateway Integration Map
# ==============================================================================
def gen_svg_12A():
    clusters = [
        ("AUTHENTICATION & USER RBAC", "/api/v1/auth & /api/v1/users", "JWT tokens, Argon2id, 7-role granular authorization matrix, session revoke", CYAN),
        ("CAMERA DISCOVERY & REGISTRY", "/api/v1/cameras", "Sentinel /api/ingest sync, Corp8SourceAdapter, health ping, CRUD camera records", GREEN),
        ("VIDEO STREAMING GATEWAY", "/api/v1/streams", "WebRTC WHEP preview, RTSP over TCP proxy, HLS fallback, load pacing profiles", PURPLE_LIGHT),
        ("ALERT ENGINE & WATCHLISTS", "/api/v1/alerts & /api/v1/watchlists", "60s anti-storm cooldown, severity scoring, plate registration, vehicle alerts", RED),
        ("INCIDENT FSM & AUDIT LOGS", "/api/v1/incidents & /api/v1/audit", "FSM: OPEN -> CLOSED, officer notes, tamper-evident Section 65B audit trail", AMBER),
        ("FORENSICS & SIGHTING GRAPH", "/api/v1/investigations & /api/v1/dossiers", "Plate & make search, SHA-256 evidence verification, certified PDF dossier", CYAN),
        ("GIS MAP & TRAJECTORY", "/api/v1/gis", "CCTV FOV coverage wedges, PostGIS geometries, multi-camera intercept prediction", GREEN),
        ("AI COPILOT AGENT INTERFACE", "/api/v1/copilot", "Multilingual conversational agent (EN, HI, GU) with 40+ deterministic grounded tools", PURPLE_LIGHT)
    ]
    
    body = """
    <!-- Top Bar: FastAPI Gateway Core -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="85" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="28" rx="8" fill="#13082E" />
      <text x="400" y="19" fill="{WHITE}" font-size="11.5" font-weight="800" text-anchor="middle">FASTAPI V1 ASYNC API GATEWAY // 23 LOGICALLY GROUPED ROUTERS</text>
      <text x="20" y="48" fill="{MUTED}" font-size="10">Middleware Pipeline: CORS Policy • SSRF Metadata Filter • SlowAPI Rate Limiting • Correlation ID • Audit Logger</text>
      <text x="20" y="68" fill="{CYAN}" font-size="10" font-weight="700">Async SQLAlchemy Session Pooling • Pydantic v2 Schema Validation • OpenAPI 3.1 Interactive Docs</text>
    </g>
    
    <!-- 8 Router Clusters Grid -->
    """
    
    y = 120
    for i, (title, endpoints, desc, color) in enumerate(clusters):
        body += f"""
        <g transform="translate(30, {y})" filter="url(#shadow)">
          <rect width="800" height="70" rx="6" fill="url(#cardGrad)" stroke="{color}" stroke-width="1.5" />
          
          <rect x="14" y="12" width="190" height="24" rx="4" fill="{color}" fill-opacity="0.2" stroke="{color}" stroke-width="1.2" />
          <text x="109" y="28" fill="{color}" font-size="9.5" font-weight="800" text-anchor="middle">{title}</text>
          
          <text x="215" y="28" fill="{WHITE}" font-size="11.5" font-weight="700">{endpoints}</text>
          
          <rect x="14" y="42" width="772" height="20" rx="3" fill="#0A0316" />
          <text x="24" y="56" fill="{MUTED}" font-size="9.5">{desc}</text>
        </g>"""
        y += 78
        
    return body

# ==============================================================================
# Diagram 12B: Data Flow, Event Streaming & State Synchronization
# ==============================================================================
def gen_svg_12B():
    return f"""
    <!-- Part 1: Event Streaming Fabric -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="235" rx="8" fill="url(#cardGrad)" stroke="{PURPLE_LIGHT}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1E0E45" />
      <text x="20" y="23" fill="{PURPLE_LIGHT}" font-size="13" font-weight="800">1. ASYNCHRONOUS EVENT STREAMING &amp; PUBSUB BROADCASTER</text>
      
      <!-- EventPublisher Box -->
      <g transform="translate(20, 48)">
        <rect width="230" height="165" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="14" y="22" fill="{WHITE}" font-size="11" font-weight="700">EventPublisher Engine</text>
        <text x="14" y="40" fill="{MUTED}" font-size="9">• Singleton async dispatcher</text>
        <text x="14" y="56" fill="{MUTED}" font-size="9">• Zero thread contention</text>
        <text x="14" y="72" fill="{MUTED}" font-size="9">• Emits detection envelopes</text>
        <text x="14" y="88" fill="{MUTED}" font-size="9">• Non-blocking background worker</text>
        <text x="14" y="112" fill="{CYAN}" font-size="9" font-weight="700">Dispatch latency: &lt; 0.4ms</text>
        <text x="14" y="130" fill="{WHITE}" font-size="8.5">Bypasses DB on raw telemetry</text>
      </g>
      
      <path d="M 250 130 L 290 130" stroke="{PURPLE_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
      
      <!-- Kafka Topics -->
      <g transform="translate(290, 48)">
        <rect width="250" height="165" rx="6" fill="#080316" stroke="{CYAN}" stroke-width="1.5" />
        <text x="14" y="22" fill="{CYAN}" font-size="11" font-weight="700">Apache Kafka Topics</text>
        
        <rect x="10" y="32" width="230" height="32" rx="4" fill="#130826" stroke="{BORDER}" stroke-width="1" />
        <text x="18" y="52" fill="{WHITE}" font-size="9.5" font-family="monospace">cctv.detections (High vol)</text>
        
        <rect x="10" y="70" width="230" height="32" rx="4" fill="#130826" stroke="{RED}" stroke-width="1" />
        <text x="18" y="90" fill="{RED}" font-size="9.5" font-family="monospace">cctv.alerts (Priority 0)</text>
        
        <rect x="10" y="108" width="230" height="32" rx="4" fill="#130826" stroke="{BORDER}" stroke-width="1" />
        <text x="18" y="128" fill="{MUTED}" font-size="9.5" font-family="monospace">cctv.telemetry (5s pings)</text>
        
        <text x="14" y="156" fill="{GREEN}" font-size="8.5">Partitioned by camera_district</text>
      </g>
      
      <path d="M 540 130 L 580 130" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr-green)" />
      
      <!-- Redis + WebSocket -->
      <g transform="translate(580, 48)">
        <rect width="200" height="165" rx="6" fill="#080316" stroke="{GREEN}" stroke-width="1" />
        <text x="14" y="22" fill="{GREEN}" font-size="11" font-weight="700">WebSocket Multiplexer</text>
        <text x="14" y="40" fill="{WHITE}" font-size="9">• FastAPI WebSocket endpoint</text>
        <text x="14" y="56" fill="{WHITE}" font-size="9">• Channel multiplexing</text>
        <text x="14" y="72" fill="{MUTED}" font-size="8.5">• Client room subscription</text>
        <text x="14" y="88" fill="{MUTED}" font-size="8.5">• 25-30 FPS bounding boxes</text>
        <text x="14" y="112" fill="{CYAN}" font-size="9" font-weight="700">Redis Hot Cache sync</text>
        <text x="14" y="130" fill="{MUTED}" font-size="8.5">Sub-5ms browser delivery</text>
      </g>
    </g>
    
    <path d="M 430 255 L 430 285" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Part 2: React 18 Frontend State Synchronization -->
    <g transform="translate(30, 285)" filter="url(#shadow)">
      <rect width="800" height="475" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1A0D3D" />
      <text x="20" y="23" fill="{WHITE}" font-size="13" font-weight="800">2. FRONTEND CLIENT STATE ARCHITECTURE (REACT 18 + ZUSTAND + TANSTACK QUERY)</text>
      
      <!-- 4 Frontend Stores -->
      <g transform="translate(20, 50)">
        <rect width="365" height="190" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{CYAN}" font-size="11.5" font-weight="800">useCameraStore (Zustand)</text>
        <text x="16" y="44" fill="{MUTED}" font-size="9.5">• Active camera inventory &amp; filter states</text>
        <text x="16" y="60" fill="{MUTED}" font-size="9.5">• Selected stream resolutions &amp; WHEP URLs</text>
        <text x="16" y="76" fill="{MUTED}" font-size="9.5">• Grid layout presets: 1x1, 2x2, 3x3, 4x4 wall</text>
        <text x="16" y="92" fill="{MUTED}" font-size="9.5">• Camera status: ONLINE, OFFLINE, DEGRADED</text>
        <rect x="14" y="110" width="337" height="65" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
        <text x="22" y="130" fill="{WHITE}" font-size="9" font-weight="700">Live WebRTC Canvas HUD Sync:</text>
        <text x="22" y="146" fill="{GREEN}" font-size="8.5">• Coordinates overlays without DOM re-renders</text>
        <text x="22" y="160" fill="{CYAN}" font-size="8.5">• Smooth bounding box interpolation @ 60 FPS</text>
      </g>
      
      <g transform="translate(415, 50)">
        <rect width="365" height="190" rx="6" fill="#080316" stroke="{RED}" stroke-width="1" />
        <text x="16" y="24" fill="{RED}" font-size="11.5" font-weight="800">useAlertStore (Zustand)</text>
        <text x="16" y="44" fill="{MUTED}" font-size="9.5">• Real-time incoming threat queue</text>
        <text x="16" y="60" fill="{MUTED}" font-size="9.5">• Sound synthesizer alarm dispatch (Web Audio API)</text>
        <text x="16" y="76" fill="{MUTED}" font-size="9.5">• Severity filtering: CRITICAL, HIGH, MEDIUM, LOW</text>
        <text x="16" y="92" fill="{MUTED}" font-size="9.5">• Deduplication tracker in client session</text>
        <rect x="14" y="110" width="337" height="65" rx="4" fill="#130826" stroke="#501020" stroke-width="1" />
        <text x="22" y="130" fill="{WHITE}" font-size="9" font-weight="700">One-Click Threat Escalation:</text>
        <text x="22" y="146" fill="{RED}" font-size="8.5">• Instantly dispatches PCR vehicle to junction</text>
        <text x="22" y="160" fill="{AMBER}" font-size="8.5">• Spawns incident modal with pre-populated evidence</text>
      </g>
      
      <g transform="translate(20, 255)">
        <rect width="365" height="195" rx="6" fill="#080316" stroke="{GREEN}" stroke-width="1" />
        <text x="16" y="24" fill="{GREEN}" font-size="11.5" font-weight="800">GIS &amp; Leaflet Overlays Engine</text>
        <text x="16" y="44" fill="{MUTED}" font-size="9.5">• Renders 80,000 camera pins via Canvas markers</text>
        <text x="16" y="60" fill="{MUTED}" font-size="9.5">• Dynamic FOV wedge polygon rendering</text>
        <text x="16" y="76" fill="{MUTED}" font-size="9.5">• Multi-camera vehicle trajectory polyline</text>
        <text x="16" y="92" fill="{MUTED}" font-size="9.5">• District boundary GeoJSON layer toggles</text>
        <rect x="14" y="112" width="337" height="65" rx="4" fill="#130826" stroke="#104020" stroke-width="1" />
        <text x="22" y="132" fill="{WHITE}" font-size="9" font-weight="700">Zero Map Stutter Optimization:</text>
        <text x="22" y="148" fill="{GREEN}" font-size="8.5">• Spatial clustering over zoom levels 8 to 18</text>
        <text x="22" y="162" fill="{CYAN}" font-size="8.5">• Viewport bounding box culling</text>
      </g>
      
      <g transform="translate(415, 255)">
        <rect width="365" height="195" rx="6" fill="#080316" stroke="{PURPLE_LIGHT}" stroke-width="1" />
        <text x="16" y="24" fill="{PURPLE_LIGHT}" font-size="11.5" font-weight="800">AICopilotDrawer &amp; Tool Orchestrator</text>
        <text x="16" y="44" fill="{MUTED}" font-size="9.5">• Sliding conversational drawer (EN, HI, GU)</text>
        <text x="16" y="60" fill="{MUTED}" font-size="9.5">• Markdown &amp; structured card message rendering</text>
        <text x="16" y="76" fill="{MUTED}" font-size="9.5">• Direct tool execution preview &amp; confirm</text>
        <text x="16" y="92" fill="{MUTED}" font-size="9.5">• Interactive map panning triggered by LLM responses</text>
        <rect x="14" y="112" width="337" height="65" rx="4" fill="#130826" stroke="#3D1565" stroke-width="1" />
        <text x="22" y="132" fill="{WHITE}" font-size="9" font-weight="700">40+ Grounded Tools Integration:</text>
        <text x="22" y="148" fill="{PURPLE_LIGHT}" font-size="8.5">• Fast query resolution without hallucinations</text>
        <text x="22" y="162" fill="{CYAN}" font-size="8.5">• Section 65B certified PDF export on demand</text>
      </g>
    </g>"""

# ==============================================================================
# Diagram 13: Deployment Topology & Hardware Engineering Specification
# ==============================================================================
def gen_svg_13():
    return f"""
    <!-- Part 1: 33 District Command Center Edge Rack Specs -->
    <g transform="translate(30, 20)" filter="url(#shadow)">
      <rect width="800" height="345" rx="8" fill="url(#cardGrad)" stroke="{CYAN}" stroke-width="1.8" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#101838" />
      <text x="20" y="23" fill="{CYAN}" font-size="13" font-weight="800">1. DISTRICT EDGE COMPUTE TOPOLOGY (33 DISTRICT NETRAM CCC SITES)</text>
      
      <!-- Rack Graphic (Left) -->
      <g transform="translate(30, 50)">
        <rect width="250" height="275" rx="6" fill="#0A0416" stroke="{BORDER}" stroke-width="1.5" />
        <rect x="10" y="10" width="230" height="25" rx="4" fill="#180C33" />
        <text x="125" y="27" fill="{CYAN}" font-size="10" font-weight="700" text-anchor="middle">42U STANDARD SERVER RACK</text>
        
        <!-- Servers in Rack -->
        <g transform="translate(15, 45)">
          <rect width="220" height="22" rx="3" fill="#1E0D45" stroke="{BORDER_LIGHT}" stroke-width="1" />
          <circle cx="12" cy="11" r="3" fill="{GREEN}" />
          <text x="25" y="15" fill="{WHITE}" font-size="8.5">Dell PowerEdge R760xa #1 (8x L40S)</text>
        </g>
        <g transform="translate(15, 72)">
          <rect width="220" height="22" rx="3" fill="#1E0D45" stroke="{BORDER_LIGHT}" stroke-width="1" />
          <circle cx="12" cy="11" r="3" fill="{GREEN}" />
          <text x="25" y="15" fill="{WHITE}" font-size="8.5">Dell PowerEdge R760xa #2 (8x L40S)</text>
        </g>
        <g transform="translate(15, 99)">
          <rect width="220" height="22" rx="3" fill="#1E0D45" stroke="{BORDER_LIGHT}" stroke-width="1" />
          <circle cx="12" cy="11" r="3" fill="{GREEN}" />
          <text x="25" y="15" fill="{WHITE}" font-size="8.5">Dell PowerEdge R760xa #3 (8x L40S)</text>
        </g>
        <g transform="translate(15, 126)">
          <rect width="220" height="22" rx="3" fill="#1E0D45" stroke="{BORDER_LIGHT}" stroke-width="1" />
          <circle cx="12" cy="11" r="3" fill="{GREEN}" />
          <text x="25" y="15" fill="{WHITE}" font-size="8.5">Dell PowerEdge R760xa #4 (8x L40S)</text>
        </g>
        <g transform="translate(15, 153)">
          <rect width="220" height="22" rx="3" fill="#1E0D45" stroke="{BORDER_LIGHT}" stroke-width="1" />
          <circle cx="12" cy="11" r="3" fill="{GREEN}" />
          <text x="25" y="15" fill="{WHITE}" font-size="8.5">Dell PowerEdge R760xa #5 (8x L40S)</text>
        </g>
        <g transform="translate(15, 180)">
          <rect width="220" height="22" rx="3" fill="#1E0D45" stroke="{BORDER_LIGHT}" stroke-width="1" />
          <circle cx="12" cy="11" r="3" fill="{GREEN}" />
          <text x="25" y="15" fill="{WHITE}" font-size="8.5">Dell PowerEdge R760xa #6 (8x L40S)</text>
        </g>
        <g transform="translate(15, 207)">
          <rect width="220" height="22" rx="3" fill="#140828" stroke="{AMBER}" stroke-width="1" />
          <circle cx="12" cy="11" r="3" fill="{AMBER}" />
          <text x="25" y="15" fill="{WHITE}" font-size="8.5">Redundant 25GbE ToR Switches</text>
        </g>
        <g transform="translate(15, 234)">
          <rect width="220" height="28" rx="3" fill="#100520" stroke="{CYAN}" stroke-width="1" />
          <text x="110" y="18" fill="{CYAN}" font-size="9" font-weight="700" text-anchor="middle">100TB NVMe Gen4 Storage Pool</text>
        </g>
      </g>
      
      <!-- Specifications Detail (Right) -->
      <g transform="translate(300, 50)">
        <rect width="475" height="275" rx="6" fill="#0A0416" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="24" fill="{WHITE}" font-size="11.5" font-weight="800">HARDWARE ENGINEERING SPECIFICATION PER DISTRICT</text>
        
        <text x="16" y="46" fill="{CYAN}" font-size="10" font-weight="700">• Server Model:</text>
        <text x="120" y="46" fill="{WHITE}" font-size="10">8x 2U Dell PowerEdge R760xa AI Servers</text>
        
        <text x="16" y="66" fill="{CYAN}" font-size="10" font-weight="700">• Accelerators:</text>
        <text x="120" y="66" fill="{WHITE}" font-size="10">50x NVIDIA L40S 48GB Ada Lovelace GPUs</text>
        
        <text x="16" y="86" fill="{CYAN}" font-size="10" font-weight="700">• Processors:</text>
        <text x="120" y="86" fill="{WHITE}" font-size="10">Dual Intel Xeon Platinum 8480+ (112 Cores)</text>
        
        <text x="16" y="106" fill="{CYAN}" font-size="10" font-weight="700">• System RAM:</text>
        <text x="120" y="106" fill="{WHITE}" font-size="10">512 GB ECC DDR5-4800 MHz per server</text>
        
        <text x="16" y="126" fill="{CYAN}" font-size="10" font-weight="700">• Networking:</text>
        <text x="120" y="126" fill="{WHITE}" font-size="10">Dual 25GbE Mellanox ConnectX-6 NICs</text>
        
        <rect x="14" y="142" width="447" height="118" rx="4" fill="#130826" stroke="#2B1050" stroke-width="1" />
        <text x="22" y="162" fill="{GREEN}" font-size="10" font-weight="700">DISTRICT COMPUTATIONAL CAPACITY:</text>
        <text x="22" y="180" fill="{MUTED}" font-size="9">• 50 GPUs x 48 streams = 2,400 concurrent 1080p RTSP feeds</text>
        <text x="22" y="196" fill="{MUTED}" font-size="9">• Local buffer retention: 7 days full event metadata + crop snapshots</text>
        <text x="22" y="212" fill="{MUTED}" font-size="9">• Air-gapped police WAN isolation; zero dependencies on internet</text>
        <text x="22" y="230" fill="{CYAN}" font-size="9" font-weight="700">Power &amp; Cooling: 18.5 kW per rack (Redundant 2N UPS)</text>
      </g>
    </g>
    
    <path d="M 430 365 L 430 395" stroke="{BORDER_LIGHT}" stroke-width="2.5" marker-end="url(#arr)" />
    
    <!-- Part 2: Central State Command High Availability Topology -->
    <g transform="translate(30, 395)" filter="url(#shadow)">
      <rect width="800" height="365" rx="8" fill="url(#cardGrad)" stroke="{BORDER_LIGHT}" stroke-width="2" />
      <rect x="0" y="0" width="800" height="34" rx="8" fill="#1C0E42" />
      <text x="20" y="23" fill="{WHITE}" font-size="13" font-weight="800">2. CENTRAL STATE CCC HIGH AVAILABILITY CLUSTER (GANDHINAGAR HQ)</text>
      
      <!-- 3 Central Nodes -->
      <g transform="translate(20, 50)">
        <rect width="235" height="175" rx="6" fill="#080316" stroke="{CYAN}" stroke-width="1.5" />
        <text x="14" y="24" fill="{CYAN}" font-size="11" font-weight="800">POSTGRESQL 16 HA</text>
        <text x="14" y="44" fill="{WHITE}" font-size="9.5">• 3-Node Patroni HA Cluster</text>
        <text x="14" y="60" fill="{MUTED}" font-size="9">• etcd consensus engine</text>
        <text x="14" y="76" fill="{MUTED}" font-size="9">• Synchronous replication</text>
        <text x="14" y="92" fill="{MUTED}" font-size="9">• Auto-failover &lt; 3.0 seconds</text>
        <text x="14" y="108" fill="{MUTED}" font-size="9">• PgBouncer connection pool</text>
        <text x="14" y="130" fill="{GREEN}" font-size="9.5" font-weight="700">PostGIS Spatial indexing</text>
        <text x="14" y="148" fill="{CYAN}" font-size="8.5">Temporal partitioning active</text>
      </g>
      
      <g transform="translate(280, 50)">
        <rect width="235" height="175" rx="6" fill="#080316" stroke="{PURPLE_LIGHT}" stroke-width="1.5" />
        <text x="14" y="24" fill="{PURPLE_LIGHT}" font-size="11" font-weight="800">APACHE KAFKA GRID</text>
        <text x="14" y="44" fill="{WHITE}" font-size="9.5">• 5-Broker Distributed Cluster</text>
        <text x="14" y="60" fill="{MUTED}" font-size="9">• KRaft consensus (ZooKeeper-less)</text>
        <text x="14" y="76" fill="{MUTED}" font-size="9">• Replication factor = 3</text>
        <text x="14" y="92" fill="{MUTED}" font-size="9">• Min in-sync replicas = 2</text>
        <text x="14" y="108" fill="{MUTED}" font-size="9">• Zero event drop guarantee</text>
        <text x="14" y="130" fill="{GREEN}" font-size="9.5" font-weight="700">154 Mbps sustained stream</text>
        <text x="14" y="148" fill="{CYAN}" font-size="8.5">Event retention: 30 days</text>
      </g>
      
      <g transform="translate(540, 50)">
        <rect width="240" height="175" rx="6" fill="#080316" stroke="{GREEN}" stroke-width="1.5" />
        <text x="14" y="24" fill="{GREEN}" font-size="11" font-weight="800">REDIS SENTINEL CACHE</text>
        <text x="14" y="44" fill="{WHITE}" font-size="9.5">• 3-Node Sentinel Quorum</text>
        <text x="14" y="60" fill="{MUTED}" font-size="9">• Sub-millisecond alert bus</text>
        <text x="14" y="76" fill="{MUTED}" font-size="9">• JWT token revocation list</text>
        <text x="14" y="92" fill="{MUTED}" font-size="9">• 60s cooldown sliding log</text>
        <text x="14" y="108" fill="{MUTED}" font-size="9">• Pub/Sub to WebSockets</text>
        <text x="14" y="130" fill="{GREEN}" font-size="9.5" font-weight="700">Zero data loss replication</text>
        <text x="14" y="148" fill="{CYAN}" font-size="8.5">AOF persistence enabled</text>
      </g>
      
      <!-- Container & Orchestration Runtime -->
      <g transform="translate(20, 240)">
        <rect width="760" height="105" rx="6" fill="#080316" stroke="{BORDER}" stroke-width="1" />
        <text x="16" y="22" fill="{WHITE}" font-size="11" font-weight="700">CONTAINERIZATION &amp; ORCHESTRATION RUNTIME STACK</text>
        
        <text x="16" y="42" fill="{MUTED}" font-size="9.5">• Operating System: Ubuntu 22.04 LTS (Kernel 5.15+ with real-time PREEMPT_RT patch)</text>
        <text x="16" y="58" fill="{MUTED}" font-size="9.5">• GPU Container Toolkit: NVIDIA Container Toolkit v1.14 + CUDA 12.2 + TensorRT 10.0</text>
        <text x="16" y="74" fill="{MUTED}" font-size="9.5">• Kubernetes Orchestration: RKE2 Government-Certified Air-Gapped K8s with NVIDIA GPU Operator</text>
        <text x="16" y="92" fill="{GREEN}" font-size="9.5" font-weight="700">100% On-Premise Air-Gapped Compliance // Zero Cloud External Dependency</text>
      </g>
    </g>"""

# Dictionary linking diagram IDs to generation functions
DIAGRAM_MAP = {
    "PHANTOM_01A_High_Level_Architecture": gen_svg_01A,
    "PHANTOM_01B_Subsystem_Layer_Matrix": gen_svg_01B,
    "PHANTOM_02_End_to_End_Surveillance_Workflow": gen_svg_02,
    "PHANTOM_03_AI_Vision_Hierarchy_Pipeline": gen_svg_03,
    "PHANTOM_04_Vehicle_Classification_ANPR_Workflow": gen_svg_04,
    "PHANTOM_05_Camera_Onboarding_Streaming_Lifecycle": gen_svg_05,
    "PHANTOM_06_Alert_Deduplication_Incident_Response": gen_svg_06,
    "PHANTOM_07_GIS_Spatial_Intelligence_Trajectory": gen_svg_07,
    "PHANTOM_08_Multi_Camera_Buffer_Orchestration": gen_svg_08,
    "PHANTOM_09_Forensic_Investigation_Dossier_Workflow": gen_svg_09,
    "PHANTOM_10_Security_RBAC_Governance": gen_svg_10,
    "PHANTOM_11_80K_Camera_Scalability_Architecture": gen_svg_11,
    "PHANTOM_12A_Master_Component_Integration_Map": gen_svg_12A,
    "PHANTOM_12B_Data_Flow_Event_Streaming": gen_svg_12B,
    "PHANTOM_13_Deployment_Topology_Hardware_Spec": gen_svg_13,
}
