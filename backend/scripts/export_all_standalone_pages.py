"""
PHANTOM 4.8 // Standalone Page & High-Resolution Asset Exporter
Generates edge-to-edge individual standalone HTML, PNG (300 DPI equivalent), and PDF files
for all 17 architecture pages into docs/architecture/diagrams_redesigned/.
"""

import os
from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "docs" / "architecture"
OUTPUT_DIR = DOCS_DIR / "diagrams_redesigned"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

from generate_redesigned_master_pdf import (
    DIAGRAM_PAGES,
    generate_cover_page,
    generate_summary_page,
    generate_diagram_page,
    get_base64_image,
    EMBLEM_PATH
)

def build_standalone_html(page_body: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    @page {{
      size: 1240px 1754px;
      margin: 0;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html, body {{
      width: 1240px;
      height: 1754px;
      background: #070414;
      color: #FFFFFF;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      line-height: 1.4;
      overflow: hidden;
    }}

    /* EXACT 1240x1754 EDGE-TO-EDGE CANVAS */
    .a4-page {{
      width: 1240px;
      height: 1754px;
      max-height: 1754px;
      min-height: 1754px;
      background: #070414;
      padding: 40px 52px 30px 52px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
      position: relative;
    }}

    /* HEADER */
    .page-header {{
      height: 110px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 2px solid #6D28D9;
      padding-bottom: 12px;
      margin-bottom: 10px;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .header-logo {{
      width: 64px;
      height: 64px;
      object-fit: contain;
      filter: drop-shadow(0 0 10px rgba(168, 85, 247, 0.45));
    }}

    .header-text-block {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .header-title {{
      color: #FFFFFF;
      font-size: 20pt;
      font-weight: 800;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}

    .header-sub {{
      color: #C084FC;
      font-size: 11pt;
      font-weight: 700;
      letter-spacing: 1.5px;
    }}

    .header-right {{
      display: flex;
      align-items: center;
    }}

    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 6px;
      background: #140828;
      border: 1.5px solid #7C3AED;
      color: #E9D5FF;
      font-size: 11pt;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}

    .status-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #10B981;
      box-shadow: 0 0 8px #10B981;
    }}

    /* HERO DIAGRAM (OCCUPIES 72-76% OF USABLE CANVAS) */
    .diagram-viewport {{
      width: 100%;
      height: 1200px;
      max-height: 1200px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 8px 0;
      background: #090417;
      border-radius: 10px;
      overflow: hidden;
      border: 1.5px solid #4C1D95;
    }}

    .diagram-viewport svg {{
      width: 100%;
      height: 100%;
      display: block;
    }}

    /* TECHNICAL NOTES (OCCUPIES 15-18% OF USABLE CANVAS) */
    .page-notes-card {{
      height: 270px;
      max-height: 270px;
      background: #100624;
      border: 2px solid #6D28D9;
      border-radius: 8px;
      padding: 16px 22px;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 10px;
    }}

    .notes-header {{
      color: #C084FC;
      font-size: 12pt;
      font-weight: 800;
      letter-spacing: 1px;
      text-transform: uppercase;
      border-bottom: 1px solid #2E1065;
      padding-bottom: 8px;
    }}

    .notes-list {{
      list-style-type: none;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .notes-list li {{
      color: #F3E8FF;
      font-size: 11.5pt;
      line-height: 1.4;
      position: relative;
      padding-left: 20px;
    }}

    .notes-list li::before {{
      content: "•";
      color: #A855F7;
      font-weight: 900;
      font-size: 14pt;
      position: absolute;
      left: 2px;
      top: -2px;
    }}

    .notes-list strong {{
      color: #FFFFFF;
      font-weight: 700;
    }}

    /* FOOTER */
    .page-footer {{
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1.5px solid #3B1668;
      padding-top: 8px;
      color: #94A3B8;
      font-size: 10.5pt;
      font-weight: 600;
      letter-spacing: 0.5px;
    }}

    .footer-left {{
      color: #EF4444;
      font-weight: 700;
    }}

    .footer-center {{
      color: #A78BFA;
    }}

    .footer-right {{
      color: #FFFFFF;
      font-weight: 800;
    }}

    /* COVER STYLES */
    .cover-page {{
      background: radial-gradient(circle at 50% 25%, #1D0C44 0%, #080316 65%, #04010A 100%);
      padding: 60px 80px 40px 80px;
    }}

    .cover-inner {{
      height: 1530px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      text-align: center;
    }}

    .cover-police-header {{
      display: flex;
      gap: 16px;
      align-items: center;
    }}

    .police-pill {{
      background: #180933;
      border: 1.5px solid #7C3AED;
      color: #E9D5FF;
      font-size: 12pt;
      font-weight: 800;
      padding: 8px 24px;
      border-radius: 24px;
      letter-spacing: 1.5px;
    }}

    .c2-pill {{
      background: #10B981;
      color: #04020A;
      font-size: 12pt;
      font-weight: 900;
      padding: 8px 24px;
      border-radius: 24px;
      letter-spacing: 1.5px;
    }}

    .cover-logo-container {{
      margin-top: 40px;
      margin-bottom: 20px;
    }}

    .cover-emblem {{
      width: 220px;
      height: 220px;
      object-fit: contain;
      filter: drop-shadow(0 0 35px rgba(168, 85, 247, 0.7));
    }}

    .cover-title {{
      color: #FFFFFF;
      font-size: 56pt;
      font-weight: 900;
      letter-spacing: 3px;
      line-height: 1.1;
      text-shadow: 0 0 40px rgba(168, 85, 247, 0.6);
    }}

    .cover-subtitle {{
      color: #C084FC;
      font-size: 22pt;
      font-weight: 800;
      letter-spacing: 1.5px;
      margin-top: 10px;
    }}

    .cover-line {{
      width: 280px;
      height: 4px;
      background: linear-gradient(90deg, transparent, #A855F7, transparent);
      margin: 16px auto;
    }}

    .cover-desc {{
      color: #DDD6FE;
      font-size: 14pt;
      max-width: 950px;
      line-height: 1.6;
    }}

    .cover-metrics-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 18px;
      width: 100%;
      margin: 30px 0;
    }}

    .c-metric-card {{
      background: rgba(22, 10, 48, 0.85);
      border: 2px solid #6D28D9;
      border-radius: 10px;
      padding: 20px 10px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
    }}

    .c-metric-num {{
      color: #FFFFFF;
      font-size: 28pt;
      font-weight: 900;
      line-height: 1;
    }}

    .c-metric-label {{
      color: #06B6D4;
      font-size: 10.5pt;
      font-weight: 800;
      letter-spacing: 0.8px;
      margin-top: 4px;
    }}

    .c-metric-sub {{
      color: #A78BFA;
      font-size: 9.5pt;
    }}

    .cover-footer-meta {{
      width: 100%;
      background: #0D041E;
      border: 1.5px solid #4C1D95;
      border-radius: 10px;
      padding: 16px 24px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px 24px;
      text-align: left;
    }}

    .meta-item {{
      display: flex;
      justify-content: space-between;
      font-size: 10.5pt;
      border-bottom: 1px solid #1E0C40;
      padding-bottom: 6px;
    }}

    .meta-k {{
      color: #A78BFA;
      font-weight: 700;
    }}

    .meta-v {{
      color: #FFFFFF;
      font-weight: 700;
    }}

    /* SUMMARY STYLES */
    .summary-content-block {{
      height: 1200px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      margin: 8px 0;
    }}

    .summary-card {{
      background: #0E0522;
      border: 2px solid #6D28D9;
      border-radius: 10px;
      padding: 16px 20px;
    }}

    .summary-card-header {{
      color: #C084FC;
      font-size: 13pt;
      font-weight: 800;
      letter-spacing: 0.8px;
      text-transform: uppercase;
      margin-bottom: 10px;
      border-bottom: 1px solid #2B1055;
      padding-bottom: 6px;
    }}

    .spec-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10pt;
    }}

    .spec-table th {{
      background: #180938;
      color: #06B6D4;
      text-align: left;
      padding: 8px 12px;
      border: 1px solid #3E1674;
      font-weight: 800;
    }}

    .spec-table td {{
      padding: 7px 12px;
      border: 1px solid #230B48;
      color: #E2E8F0;
    }}

    .spec-table tr:nth-child(even) {{
      background: #090317;
    }}

    .summary-dual-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}

    .half-card {{
      height: 480px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .latency-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 10.5pt;
      margin-bottom: 10px;
    }}

    .l-phase {{
      width: 42%;
      color: #F1F5F9;
      font-weight: 600;
    }}

    .l-bar {{
      width: 36%;
      height: 10px;
      background: #1C0A36;
      border-radius: 5px;
      overflow: hidden;
      display: inline-block;
    }}

    .l-fill {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, #7C3AED, #06B6D4);
      border-radius: 5px;
    }}

    .l-val {{
      width: 20%;
      text-align: right;
      color: #38BDF8;
      font-weight: 700;
      font-family: monospace;
    }}

    .latency-total {{
      background: #180938;
      border: 1.5px solid #10B981;
      border-radius: 6px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      font-size: 11pt;
      font-weight: 700;
    }}

    .test-stat-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      text-align: center;
      margin-bottom: 10px;
    }}

    .test-stat {{
      background: #14072E;
      border: 1.5px solid #3B1668;
      border-radius: 8px;
      padding: 10px 4px;
    }}

    .t-num {{
      font-size: 18pt;
      font-weight: 900;
      display: block;
    }}

    .t-label {{
      font-size: 8pt;
      color: #94A3B8;
      font-weight: 700;
    }}

    .test-breakdown {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 10pt;
    }}

    .t-row {{
      display: flex;
      justify-content: space-between;
      border-bottom: 1px solid #1D0B3C;
      padding-bottom: 4px;
      color: #CBD5E1;
    }}

    .t-ok {{
      color: #10B981;
      font-weight: 800;
      font-family: monospace;
    }}
  </style>
</head>
<body>
  {page_body}
</body>
</html>
"""

def main():
    print("Exporting individual standalone assets for all 17 pages...")
    emblem_b64 = get_base64_image(EMBLEM_PATH)
    total_pages = 17
    
    pages = []
    
    # 1. Cover
    cov_html = build_standalone_html(generate_cover_page(emblem_b64), "PHANTOM 4.8 // Cover Page")
    cov_file = OUTPUT_DIR / "page_01_cover.html"
    cov_file.write_text(cov_html, encoding="utf-8")
    pages.append((cov_file, OUTPUT_DIR / "page_01_cover.png"))
    
    # 2. 15 Diagram Pages
    for i, spec in enumerate(DIAGRAM_PAGES):
        page_num = i + 2
        diag_body = generate_diagram_page(spec, page_num, total_pages, emblem_b64)
        page_html = build_standalone_html(diag_body, f"PHANTOM 4.8 // {spec['id']}")
        f_base = f"page_{page_num:02d}_{spec['id']}"
        h_file = OUTPUT_DIR / f"{f_base}.html"
        h_file.write_text(page_html, encoding="utf-8")
        pages.append((h_file, OUTPUT_DIR / f"{f_base}.png"))
        
    # 3. Summary
    sum_body = generate_summary_page(emblem_b64)
    sum_html = build_standalone_html(sum_body, "PHANTOM 4.8 // Technical Summary & Verification")
    sum_file = OUTPUT_DIR / "page_17_technical_summary.html"
    sum_file.write_text(sum_html, encoding="utf-8")
    pages.append((sum_file, OUTPUT_DIR / "page_17_technical_summary.png"))
    
    print(f"Generated {len(pages)} standalone HTML pages.")
    
    edge_bin = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_bin):
        edge_bin = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        
    print("Rendering high-resolution PNG screenshots (1240x1754 edge-to-edge)...")
    for h_file, p_file in pages:
        uri = f"file:///{h_file.resolve().as_posix()}"
        cmd_png = [
            edge_bin,
            "--headless=new",
            "--disable-gpu",
            "--window-size=1240,1754",
            f"--screenshot={p_file.resolve()}",
            uri
        ]
        # Run with DEVNULL so python does not wait on Edge pipe closure
        proc = subprocess.Popen(cmd_png, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        sz_kb = round(p_file.stat().st_size / 1024, 1) if p_file.exists() else 0
        print(f"-> Rendered PNG: {p_file.name} ({sz_kb} KB)")

    print("Rendering individual single-page PDFs...")
    for h_file, p_file in pages:
        pdf_file = p_file.with_suffix(".pdf")
        uri = f"file:///{h_file.resolve().as_posix()}"
        cmd_pdf = [
            edge_bin,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf_file.resolve()}",
            uri
        ]
        proc = subprocess.Popen(cmd_pdf, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        sz_kb = round(pdf_file.stat().st_size / 1024, 1) if pdf_file.exists() else 0
        print(f"-> Rendered PDF: {pdf_file.name} ({sz_kb} KB)")

if __name__ == "__main__":
    main()
