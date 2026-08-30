# PHANTOM 2.0 — Quick Resume Guide

## State Summary
All YOLO + ANPR testing features, backend endpoints, and frontend dashboard at `http://localhost:3000` are implemented, fully tested, and committed to git (`commit 47c256b`).

---

## How to Resume & Start Services Tomorrow

### 1. Start Backend (Terminal 1)
```powershell
cd C:\Users\ASUS VIVOBOOK\Desktop\phantom2.0\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Health Check: http://localhost:8000/health

### 2. Start Frontend (Terminal 2)
```powershell
cd C:\Users\ASUS VIVOBOOK\Desktop\phantom2.0\frontend
$env:PATH = "C:\Users\ASUS VIVOBOOK\AppData\Local\Programs\nodejs;" + $env:PATH
npm run dev -- --port 3000
```
- Dashboard URL: http://localhost:3000

---

## Running Automated Tests Anytime
```powershell
cd C:\Users\ASUS VIVOBOOK\Desktop\phantom2.0
# Run End-to-End Integration Tests
python -m pytest backend/tests/integration/test_yolo_anpr_e2e.py -v

# Run All Unit Tests
python -m pytest backend/tests/unit/ -v
```
