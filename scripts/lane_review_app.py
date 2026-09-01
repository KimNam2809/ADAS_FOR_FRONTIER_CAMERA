"""
Lane Review Web Application for RW-10 Quality Gate.
Run with:
    & "roadwatch/.venv/Scripts/python.exe" "roadwatch/scripts/lane_review_app.py"
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_review_queue_v2.json"
DEFAULT_FRAMES_DIR = ROOT / "artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames"
DEFAULT_MEDIA_DIR = ROOT / "media"
DEFAULT_BACKUP_DIR = ROOT / "evaluation/backups"

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080

app = FastAPI(title="RoadWatch Lane Review Tool (RW-10)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_queue(queue_path: Path) -> dict[str, Any]:
    if not queue_path.exists():
        raise FileNotFoundError(f"Queue file not found: {queue_path}")
    with queue_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue_path: Path, data: dict[str, Any], backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f"{queue_path.stem}_", suffix=".json", dir=queue_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, queue_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def compute_metrics(queue_data: dict[str, Any]) -> dict[str, Any]:
    records = queue_data.get("records", [])
    total = len(records)
    verified = sum(1 for r in records if r.get("review_status") == "verified")
    pending = sum(1 for r in records if r.get("review_status") == "pending")
    needs_recheck = sum(1 for r in records if r.get("review_status") == "needs_recheck")

    night_verified = sum(
        1 for r in records
        if r.get("review_status") == "verified" and "night" in r.get("conditions", [])
    )
    rain_night_verified = sum(
        1 for r in records
        if r.get("review_status") == "verified" and "rain_night" in r.get("conditions", [])
    )
    multi_lane_verified = sum(
        1 for r in records
        if r.get("review_status") == "verified" and (r.get("ground_truth_lane_count") or 0) > 1
    )
    faded_or_missing_verified = sum(
        1 for r in records
        if r.get("review_status") == "verified" and (
            r.get("uncertain") is True or r.get("visibility") in ["partial", "occluded", "not_visible"]
        )
    )

    return {
        "total_records": total,
        "verified": verified,
        "pending": pending,
        "needs_recheck": needs_recheck,
        "night_verified": night_verified,
        "rain_night_verified": rain_night_verified,
        "multi_lane_verified": multi_lane_verified,
        "faded_or_missing_verified": faded_or_missing_verified,
        "targets": {
            "verified_min": 3000,
            "night_min": 500,
            "rain_night_min": 400,
            "multi_lane_min": 1000,
            "faded_or_missing_min": 400,
            "double_review_min": 300,
        },
    }


class SaveRecordRequest(BaseModel):
    id: str
    ground_truth_lane_count: int
    ego_left_boundary: list[list[float]] = Field(default_factory=list)
    ego_right_boundary: list[list[float]] = Field(default_factory=list)
    marking_type: list[str] = Field(default_factory=lambda: ["unknown"])
    visibility: str = "clear"
    road_direction: str = "same_direction"
    uncertain: bool = False
    review_status: str = "verified"
    reviewer: str = "Human_Reviewer"
    review_notes: str = ""


@app.get("/api/queue")
def get_queue():
    queue_path = app.state.queue_path
    data = load_queue(queue_path)
    metrics = compute_metrics(data)
    # Simplify records for sidebar listing
    items = []
    for idx, r in enumerate(data.get("records", [])):
        items.append({
            "index": idx,
            "id": r.get("id"),
            "conditions": r.get("conditions", []),
            "split": r.get("split"),
            "review_status": r.get("review_status", "pending"),
            "ground_truth_lane_count": r.get("ground_truth_lane_count"),
            "uncertain": r.get("uncertain"),
        })
    return {
        "metrics": metrics,
        "items": items,
    }


@app.get("/api/record/{index}")
def get_record(index: int):
    queue_path = app.state.queue_path
    data = load_queue(queue_path)
    records = data.get("records", [])
    if index < 0 or index >= len(records):
        raise HTTPException(status_code=404, detail="Record index out of range")
    record = records[index]
    return {
        "index": index,
        "total": len(records),
        "record": record,
    }


@app.post("/api/record/{index}")
def update_record(index: int, req: SaveRecordRequest):
    queue_path = app.state.queue_path
    backup_dir = app.state.backup_dir
    data = load_queue(queue_path)
    records = data.get("records", [])
    if index < 0 or index >= len(records):
        raise HTTPException(status_code=404, detail="Record index out of range")

    rec = records[index]
    if rec.get("id") != req.id:
        raise HTTPException(status_code=400, detail="Record ID mismatch")

    # Sanity checks
    if req.review_status == "verified":
        if req.ground_truth_lane_count == 0 and (req.ego_left_boundary or req.ego_right_boundary):
            raise HTTPException(
                status_code=400,
                detail="Validation error: ground_truth_lane_count is 0 but boundaries are not empty."
            )
        # Coordinate bounds check
        for pt in req.ego_left_boundary + req.ego_right_boundary:
            if not (0 <= pt[0] <= FRAME_WIDTH and 0 <= pt[1] <= FRAME_HEIGHT):
                raise HTTPException(
                    status_code=400,
                    detail=f"Coordinate out of bounds: {pt} (Frame is {FRAME_WIDTH}x{FRAME_HEIGHT})"
                )

    rec["ground_truth_lane_count"] = req.ground_truth_lane_count
    rec["ego_left_boundary"] = [[round(p[0]), round(p[1])] for p in req.ego_left_boundary]
    rec["ego_right_boundary"] = [[round(p[0]), round(p[1])] for p in req.ego_right_boundary]
    rec["marking_type"] = req.marking_type
    rec["visibility"] = req.visibility
    rec["road_direction"] = req.road_direction
    rec["uncertain"] = req.uncertain
    rec["review_status"] = req.review_status
    rec["reviewer"] = req.reviewer.strip() or "Human_Reviewer"
    rec["review_notes"] = req.review_notes.strip()

    # Clear repair fields if now manually verified
    if req.review_status == "verified":
        rec.pop("repair_status", None)
        rec.pop("repair_notes", None)

    save_queue(queue_path, data, backup_dir)

    metrics = compute_metrics(data)
    return {
        "status": "success",
        "saved_id": req.id,
        "metrics": metrics,
    }


@app.get("/api/image/{image_name}")
def get_image(image_name: str):
    frames_dir = app.state.frames_dir
    img_path = frames_dir / image_name
    if not img_path.exists():
        # Fallback to look inside nested dirs
        found = list(frames_dir.glob(f"**/{image_name}"))
        if found:
            img_path = found[0]
        else:
            raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(img_path)


INDEX_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RoadWatch - RW-10 Lane Review Tool</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0f172a;
      --bg-card: #1e293b;
      --bg-hover: #334155;
      --border-color: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --left-boundary: #22c55e;
      --right-boundary: #3b82f6;
      --model-proposal: #fbbf24;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg-dark);
      color: var(--text-main);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    header {
      background: #111827;
      border-bottom: 1px solid var(--border-color);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 58px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 1.1rem;
    }
    .brand span.badge {
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .stats-bar {
      display: flex;
      gap: 16px;
      font-size: 0.82rem;
    }
    .stat-pill {
      background: var(--bg-card);
      padding: 4px 12px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      display: flex;
      gap: 6px;
    }
    .stat-pill .val { font-weight: 700; color: var(--primary); }
    .stat-pill.success .val { color: var(--success); }
    .stat-pill.warning .val { color: var(--warning); }
    .stat-pill.danger .val { color: var(--danger); }

    .main-container {
      display: flex;
      flex: 1;
      height: calc(100vh - 58px);
      overflow: hidden;
    }

    /* SIDEBAR */
    .sidebar {
      width: 280px;
      background: #111827;
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
    }
    .sidebar-header {
      padding: 12px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      gap: 8px;
    }
    .filter-select {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.82rem;
      width: 100%;
    }
    .frame-list {
      flex: 1;
      overflow-y: auto;
      list-style: none;
    }
    .frame-item {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 4px;
      transition: background 0.15s;
    }
    .frame-item:hover { background: var(--bg-hover); }
    .frame-item.active { background: #1e3a8a; border-left: 3px solid var(--primary); }
    .frame-item-title {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.78rem;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
    }
    .frame-item-meta {
      display: flex;
      gap: 6px;
      font-size: 0.72rem;
      color: var(--text-muted);
    }
    .badge-status {
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
    }
    .badge-status.verified { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .badge-status.pending { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; }
    .badge-status.needs_recheck { background: rgba(239, 68, 68, 0.2); color: #f87171; }

    /* WORKSPACE */
    .workspace {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: #090d16;
      position: relative;
      overflow: hidden;
    }
    .canvas-toolbar {
      background: #111827;
      padding: 8px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-color);
      font-size: 0.85rem;
    }
    .tool-group {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .btn {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn:hover { background: var(--bg-hover); }
    .btn.active {
      background: var(--primary);
      color: #0f172a;
      border-color: var(--primary);
      font-weight: 600;
    }
    .btn.btn-green.active { background: var(--left-boundary); color: #0f172a; border-color: var(--left-boundary); }
    .btn.btn-blue.active { background: var(--right-boundary); color: #fff; border-color: var(--right-boundary); }
    .btn-primary { background: var(--primary); color: #0f172a; font-weight: 600; border-color: var(--primary); }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; border-color: var(--danger); }
    .btn-danger:hover { background: var(--danger); color: #fff; }

    .canvas-viewport {
      flex: 1;
      position: relative;
      overflow: hidden;
      display: flex;
      justify-content: center;
      align-items: center;
      user-select: none;
    }
    canvas {
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      border-radius: 4px;
      cursor: crosshair;
    }

    /* RIGHT CONTROLS PANEL */
    .control-panel {
      width: 360px;
      background: #111827;
      border-left: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      padding: 16px;
      overflow-y: auto;
      gap: 16px;
    }
    .panel-section {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .section-title {
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
    }
    .quick-buttons {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
    }
    .quick-btn {
      padding: 8px 4px;
      text-align: center;
      font-size: 0.78rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: #0f172a;
      color: var(--text-main);
      cursor: pointer;
      font-weight: 600;
    }
    .quick-btn:hover { background: var(--bg-hover); }
    .quick-btn.active { background: var(--primary); color: #0f172a; }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .form-label {
      font-size: 0.78rem;
      color: var(--text-muted);
      font-weight: 500;
    }
    .form-control {
      background: #0f172a;
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 7px 10px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-family: inherit;
    }
    .form-control:focus {
      outline: none;
      border-color: var(--primary);
    }
    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
      cursor: pointer;
    }
    .checkbox-label input {
      width: 16px;
      height: 16px;
      accent-color: var(--warning);
    }
    .helper-tag {
      font-size: 0.72rem;
      color: #64748b;
    }
    .kbd {
      background: #334155;
      padding: 2px 5px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 0.72rem;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span>🚗 RoadWatch Reviewer</span>
      <span class="badge">RW-10 Quality Gate</span>
    </div>
    <div class="stats-bar" id="statsBar">
      <div class="stat-pill"><span class="lbl">Verified:</span><span class="val" id="statVerified">0/599</span></div>
      <div class="stat-pill"><span class="lbl">Night:</span><span class="val" id="statNight">0/500</span></div>
      <div class="stat-pill"><span class="lbl">Rain-Night:</span><span class="val" id="statRainNight">0/400</span></div>
      <div class="stat-pill"><span class="lbl">Multi-Lane:</span><span class="val" id="statMulti">0/1000</span></div>
      <div class="stat-pill"><span class="lbl">Faded/Uncertain:</span><span class="val" id="statFaded">0/400</span></div>
    </div>
  </header>

  <div class="main-container">
    <!-- SIDEBAR -->
    <div class="sidebar">
      <div class="sidebar-header">
        <select class="filter-select" id="filterStatus" onchange="applyFilter()">
          <option value="all">Tất cả frame (599)</option>
          <option value="pending" selected>Chưa review (Pending)</option>
          <option value="needs_recheck">Cần kiểm tra (Needs Recheck)</option>
          <option value="verified">Đã verified</option>
          <option value="rain_night">Điều kiện: rain_night</option>
          <option value="night">Điều kiện: night</option>
          <option value="dense_traffic">Điều kiện: dense_traffic</option>
          <option value="day">Điều kiện: day</option>
        </select>
      </div>
      <ul class="frame-list" id="frameList"></ul>
    </div>

    <!-- MAIN CANVAS -->
    <div class="workspace">
      <div class="canvas-toolbar">
        <div class="tool-group">
          <button class="btn" id="btnPrev" onclick="navigate(-1)">◀ Trước <span class="kbd">A / ←</span></button>
          <button class="btn" id="btnNext" onclick="navigate(1)">Sau ▶ <span class="kbd">D / →</span></button>
          <span style="color: #64748b; margin: 0 8px;">|</span>
          <button class="btn btn-green active" id="btnLeftMode" onclick="setDrawingMode('left')">Biên Trái (Ego Left) <span class="kbd">1</span></button>
          <button class="btn btn-blue" id="btnRightMode" onclick="setDrawingMode('right')">Biên Phải (Ego Right) <span class="kbd">2</span></button>
          <button class="btn" onclick="undoPoint()">Hoàn tác <span class="kbd">Z</span></button>
          <button class="btn btn-danger" onclick="clearCurrentBoundary()">Xoá biên</button>
        </div>
        <div class="tool-group">
          <label class="checkbox-label" style="font-size: 0.8rem;">
            <input type="checkbox" id="showProposal" checked onchange="redrawCanvas()"> Hiện Proposal (Vàng)
          </label>
        </div>
      </div>

      <div class="canvas-viewport" id="viewport">
        <canvas id="reviewCanvas" width="1920" height="1080"></canvas>
      </div>
    </div>

    <!-- CONTROL PANEL -->
    <div class="control-panel">
      <!-- Fast Presets -->
      <div class="panel-section">
        <div class="section-title">Gán nhanh (Presets)</div>
        <div class="quick-buttons">
          <button class="quick-btn" onclick="presetNoLane()">🚫 0 Làn (Mất vạch / Tối)</button>
          <button class="quick-btn" onclick="presetSingleLane()">🚘 1 Làn (Ego)</button>
          <button class="quick-btn" onclick="presetTwoLanes()">🚗🚗 2 Làn</button>
          <button class="quick-btn" onclick="presetThreeLanes()">🚗🚗🚗 3 Làn</button>
          <button class="quick-btn" onclick="presetCopyProposal()">📋 Lấy Proposal</button>
          <button class="quick-btn" onclick="clearAllLines()">🧹 Xoá cả 2 biên</button>
        </div>
      </div>

      <!-- Ground Truth Fields -->
      <div class="panel-section">
        <div class="section-title">Thông tin Ground Truth</div>
        <div class="form-group">
          <label class="form-label">Số làn cùng chiều (ground_truth_lane_count):</label>
          <input type="number" class="form-control" id="inputLaneCount" min="0" max="10" value="0">
          <span class="helper-tag">0: không nhìn thấy làn; 1: chỉ làn ego; 2+: làn ego + làn cùng chiều</span>
        </div>

        <div class="form-group">
          <label class="form-label">Loại vạch kẻ (marking_type) [Trái, Phải]:</label>
          <div style="display: flex; gap: 6px;">
            <select class="form-control" id="inputMarkingLeft">
              <option value="solid">Solid (Liền)</option>
              <option value="dashed">Dashed (Đứt)</option>
              <option value="double">Double (Đôi)</option>
              <option value="curb">Curb (Vỉa hè)</option>
              <option value="unknown" selected>Unknown</option>
            </select>
            <select class="form-control" id="inputMarkingRight">
              <option value="solid">Solid (Liền)</option>
              <option value="dashed">Dashed (Đứt)</option>
              <option value="double">Double (Đôi)</option>
              <option value="curb">Curb (Vỉa hè)</option>
              <option value="unknown" selected>Unknown</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Độ nhìn rõ (visibility):</label>
          <select class="form-control" id="inputVisibility">
            <option value="clear">Clear (Rõ ràng)</option>
            <option value="partial">Partial (Một phần)</option>
            <option value="occluded">Occluded (Bị xe/mưa che)</option>
            <option value="not_visible" selected>Not Visible (Không thấy)</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Hướng đường (road_direction):</label>
          <select class="form-control" id="inputRoadDir">
            <option value="same_direction" selected>same_direction</option>
            <option value="opposing">opposing</option>
            <option value="unknown">unknown</option>
          </select>
        </div>

        <div class="form-group" style="margin-top: 4px;">
          <label class="checkbox-label">
            <input type="checkbox" id="inputUncertain" checked>
            <span>Không chắc chắn (uncertain = true)</span>
          </label>
          <span class="helper-tag">Tích chọn nếu mưa, tối, phản chiếu, mờ hoặc bị che</span>
        </div>
      </div>

      <!-- Reviewer & Status -->
      <div class="panel-section">
        <div class="section-title">Trạng thái Review</div>
        <div class="form-group">
          <label class="form-label">Review Status:</label>
          <select class="form-control" id="inputReviewStatus">
            <option value="verified" selected>Verified (Đã kiểm tra)</option>
            <option value="needs_recheck">Needs Recheck (Nghi ngờ / Cần xem lại)</option>
            <option value="pending">Pending (Chưa kiểm tra)</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Tên Reviewer:</label>
          <input type="text" class="form-control" id="inputReviewer" value="Human_Reviewer">
        </div>

        <div class="form-group">
          <label class="form-label">Ghi chú (review_notes):</label>
          <input type="text" class="form-control" id="inputNotes" placeholder="Ghi chú khi có bất thường...">
        </div>

        <button class="btn btn-primary" style="padding: 10px; justify-content: center; margin-top: 6px;" onclick="saveCurrentRecord(true)">
          💾 Lưu & Sang Frame Tiếp (Space / Enter)
        </button>
      </div>

      <div style="font-size: 0.72rem; color: #64748b; line-height: 1.4;">
        💡 <b>Phím tắt:</b><br>
        • <b>1 / 2:</b> Chuyển vẽ Biên Trái / Phải<br>
        • <b>Click chuột trên ảnh:</b> Thêm điểm polyline (5-15 điểm từ xa lại gần)<br>
        • <b>Z:</b> Xoá điểm vừa vẽ | <b>Space / Enter:</b> Lưu & Tiếp
      </div>
    </div>
  </div>

  <script>
    let queueItems = [];
    let currentIdx = 0;
    let currentRecord = null;
    let drawingMode = 'left'; // 'left' | 'right'
    let egoLeft = [];
    let egoRight = [];
    let bgImage = new Image();
    let isImageLoaded = false;

    const canvas = document.getElementById('reviewCanvas');
    const ctx = canvas.getContext('2d');

    async function init() {
      await fetchQueue();
      if (queueItems.length > 0) {
        loadRecordByIndex(0);
      }
      setupCanvasEvents();
      setupKeyboardEvents();
    }

    async function fetchQueue() {
      const res = await fetch('/api/queue');
      const data = await res.json();
      queueItems = data.items;
      updateStats(data.metrics);
      renderSidebar();
    }

    function updateStats(m) {
      document.getElementById('statVerified').innerText = `${m.verified}/${m.total_records}`;
      document.getElementById('statNight').innerText = `${m.night_verified}/${m.targets.night_min}`;
      document.getElementById('statRainNight').innerText = `${m.rain_night_verified}/${m.targets.rain_night_min}`;
      document.getElementById('statMulti').innerText = `${m.multi_lane_verified}/${m.targets.multi_lane_min}`;
      document.getElementById('statFaded').innerText = `${m.faded_or_missing_verified}/${m.targets.faded_or_missing_min}`;
    }

    function renderSidebar() {
      const list = document.getElementById('frameList');
      const filter = document.getElementById('filterStatus').value;
      list.innerHTML = '';

      queueItems.forEach((item, idx) => {
        if (filter === 'pending' && item.review_status !== 'pending') return;
        if (filter === 'verified' && item.review_status !== 'verified') return;
        if (filter === 'needs_recheck' && item.review_status !== 'needs_recheck') return;
        if (['rain_night', 'night', 'dense_traffic', 'day'].includes(filter) && !item.conditions.includes(filter)) return;

        const li = document.createElement('li');
        li.className = `frame-item ${idx === currentIdx ? 'active' : ''}`;
        li.onclick = () => loadRecordByIndex(idx);

        li.innerHTML = `
          <div class="frame-item-title">
            <span>${item.id}</span>
            <span class="badge-status ${item.review_status}">${item.review_status}</span>
          </div>
          <div class="frame-item-meta">
            <span>${item.conditions.join(', ')}</span>
            <span>• L:${item.ground_truth_lane_count ?? '-'}</span>
          </div>
        `;
        list.appendChild(li);
      });
    }

    function applyFilter() {
      renderSidebar();
    }

    async function loadRecordByIndex(index) {
      currentIdx = index;
      renderSidebar();

      const res = await fetch(`/api/record/${index}`);
      const data = await res.json();
      currentRecord = data.record;

      egoLeft = (currentRecord.ego_left_boundary || []).map(p => [...p]);
      egoRight = (currentRecord.ego_right_boundary || []).map(p => [...p]);

      document.getElementById('inputLaneCount').value = currentRecord.ground_truth_lane_count ?? 0;
      const markings = currentRecord.marking_type || ['unknown', 'unknown'];
      document.getElementById('inputMarkingLeft').value = markings[0] || 'unknown';
      document.getElementById('inputMarkingRight').value = markings[1] || markings[0] || 'unknown';
      document.getElementById('inputVisibility').value = currentRecord.visibility || 'not_visible';
      document.getElementById('inputRoadDir').value = currentRecord.road_direction || 'same_direction';
      document.getElementById('inputUncertain').checked = currentRecord.uncertain ?? true;
      document.getElementById('inputReviewStatus').value = currentRecord.review_status || 'verified';
      document.getElementById('inputReviewer').value = currentRecord.reviewer || 'Human_Reviewer';
      document.getElementById('inputNotes').value = currentRecord.review_notes || '';

      const imgName = currentRecord.id + '.jpg';
      isImageLoaded = false;
      bgImage = new Image();
      bgImage.src = `/api/image/${imgName}`;
      bgImage.onload = () => {
        isImageLoaded = true;
        redrawCanvas();
      };
    }

    function setDrawingMode(mode) {
      drawingMode = mode;
      document.getElementById('btnLeftMode').className = `btn btn-green ${mode === 'left' ? 'active' : ''}`;
      document.getElementById('btnRightMode').className = `btn btn-blue ${mode === 'right' ? 'active' : ''}`;
    }

    function setupCanvasEvents() {
      canvas.addEventListener('click', (e) => {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = Math.round((e.clientX - rect.left) * scaleX);
        const y = Math.round((e.clientY - rect.top) * scaleY);

        if (x < 0 || x > 1920 || y < 0 || y > 1080) return;

        if (drawingMode === 'left') {
          egoLeft.push([x, y]);
          if (document.getElementById('inputLaneCount').value == 0) {
            document.getElementById('inputLaneCount').value = 1;
            document.getElementById('inputVisibility').value = 'partial';
            document.getElementById('inputUncertain').checked = false;
          }
        } else {
          egoRight.push([x, y]);
          if (document.getElementById('inputLaneCount').value == 0) {
            document.getElementById('inputLaneCount').value = 1;
            document.getElementById('inputVisibility').value = 'partial';
            document.getElementById('inputUncertain').checked = false;
          }
        }
        redrawCanvas();
      });
    }

    function setupKeyboardEvents() {
      window.addEventListener('keydown', (e) => {
        if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
          if (e.key === 'Enter') {
            saveCurrentRecord(true);
          }
          return;
        }
        if (e.key === '1') setDrawingMode('left');
        if (e.key === '2') setDrawingMode('right');
        if (e.key === 'z' || e.key === 'Z') undoPoint();
        if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') navigate(-1);
        if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') navigate(1);
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          saveCurrentRecord(true);
        }
      });
    }

    function undoPoint() {
      if (drawingMode === 'left' && egoLeft.length > 0) {
        egoLeft.pop();
      } else if (drawingMode === 'right' && egoRight.length > 0) {
        egoRight.pop();
      }
      redrawCanvas();
    }

    function clearCurrentBoundary() {
      if (drawingMode === 'left') egoLeft = [];
      else egoRight = [];
      redrawCanvas();
    }

    function clearAllLines() {
      egoLeft = [];
      egoRight = [];
      redrawCanvas();
    }

    function presetNoLane() {
      egoLeft = [];
      egoRight = [];
      document.getElementById('inputLaneCount').value = 0;
      document.getElementById('inputMarkingLeft').value = 'unknown';
      document.getElementById('inputMarkingRight').value = 'unknown';
      document.getElementById('inputVisibility').value = 'not_visible';
      document.getElementById('inputUncertain').checked = true;
      document.getElementById('inputReviewStatus').value = 'verified';
      redrawCanvas();
    }

    function presetSingleLane() {
      document.getElementById('inputLaneCount').value = 1;
      document.getElementById('inputVisibility').value = 'clear';
      document.getElementById('inputUncertain').checked = false;
      document.getElementById('inputReviewStatus').value = 'verified';
    }

    function presetTwoLanes() {
      document.getElementById('inputLaneCount').value = 2;
      document.getElementById('inputVisibility').value = 'clear';
      document.getElementById('inputUncertain').checked = false;
      document.getElementById('inputReviewStatus').value = 'verified';
    }

    function presetThreeLanes() {
      document.getElementById('inputLaneCount').value = 3;
      document.getElementById('inputVisibility').value = 'clear';
      document.getElementById('inputUncertain').checked = false;
      document.getElementById('inputReviewStatus').value = 'verified';
    }

    function presetCopyProposal() {
      if (!currentRecord || !currentRecord.model_proposal) return;
      const insts = currentRecord.model_proposal.lane_instances || [];
      const left = insts.find(i => i.lane_id === 1);
      const right = insts.find(i => i.lane_id === 2);
      if (left && left.points) egoLeft = left.points.map(p => [...p]);
      if (right && right.points) egoRight = right.points.map(p => [...p]);
      document.getElementById('inputLaneCount').value = (egoLeft.length > 0 || egoRight.length > 0) ? 1 : 0;
      document.getElementById('inputVisibility').value = 'partial';
      document.getElementById('inputUncertain').checked = true;
      redrawCanvas();
    }

    function redrawCanvas() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (isImageLoaded) {
        ctx.drawImage(bgImage, 0, 0, canvas.width, canvas.height);
      }

      // Draw model proposal if enabled
      if (document.getElementById('showProposal').checked && currentRecord && currentRecord.model_proposal) {
        const insts = currentRecord.model_proposal.lane_instances || [];
        insts.forEach(inst => {
          if (inst.points && inst.points.length > 0) {
            ctx.beginPath();
            ctx.strokeStyle = 'rgba(251, 191, 36, 0.6)';
            ctx.lineWidth = 3;
            ctx.setLineDash([8, 6]);
            inst.points.forEach((pt, idx) => {
              if (idx === 0) ctx.moveTo(pt[0], pt[1]);
              else ctx.lineTo(pt[0], pt[1]);
            });
            ctx.stroke();
            ctx.setLineDash([]);
          }
        });
      }

      // Draw Left Boundary (Green)
      drawPolyline(egoLeft, '#22c55e', 'L');

      // Draw Right Boundary (Blue)
      drawPolyline(egoRight, '#3b82f6', 'R');
    }

    function drawPolyline(points, color, label) {
      if (!points || points.length === 0) return;

      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 5;
      points.forEach((pt, idx) => {
        if (idx === 0) ctx.moveTo(pt[0], pt[1]);
        else ctx.lineTo(pt[0], pt[1]);
      });
      ctx.stroke();

      // Draw points
      points.forEach((pt, idx) => {
        ctx.beginPath();
        ctx.arc(pt[0], pt[1], 6, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#ffffff';
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px Inter';
        ctx.fillText(`${label}${idx+1}`, pt[0] + 8, pt[1] - 8);
      });
    }

    async function saveCurrentRecord(advance = true) {
      if (!currentRecord) return;

      const laneCount = parseInt(document.getElementById('inputLaneCount').value, 10) || 0;
      const markingLeft = document.getElementById('inputMarkingLeft').value;
      const markingRight = document.getElementById('inputMarkingRight').value;
      const visibility = document.getElementById('inputVisibility').value;
      const roadDirection = document.getElementById('inputRoadDir').value;
      const uncertain = document.getElementById('inputUncertain').checked;
      const reviewStatus = document.getElementById('inputReviewStatus').value;
      const reviewer = document.getElementById('inputReviewer').value.trim() || 'Human_Reviewer';
      const reviewNotes = document.getElementById('inputNotes').value.trim();

      // Check conflict
      if (reviewStatus === 'verified' && laneCount === 0 && (egoLeft.length > 0 || egoRight.length > 0)) {
        alert('CẢNH BÁO: Số làn = 0 nhưng đang có điểm polyline! Hãy xoá polyline hoặc tăng số làn >= 1.');
        return;
      }

      const payload = {
        id: currentRecord.id,
        ground_truth_lane_count: laneCount,
        ego_left_boundary: egoLeft,
        ego_right_boundary: egoRight,
        marking_type: [markingLeft, markingRight],
        visibility: visibility,
        road_direction: roadDirection,
        uncertain: uncertain,
        review_status: reviewStatus,
        reviewer: reviewer,
        review_notes: reviewNotes,
      };

      try {
        const res = await fetch(`/api/record/${currentIdx}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const err = await res.json();
          alert('Lỗi khi lưu: ' + (err.detail || 'Không xác định'));
          return;
        }

        const data = await res.json();
        updateStats(data.metrics);
        queueItems[currentIdx].review_status = reviewStatus;
        queueItems[currentIdx].ground_truth_lane_count = laneCount;
        queueItems[currentIdx].uncertain = uncertain;
        renderSidebar();

        if (advance) {
          navigate(1);
        }
      } catch (err) {
        alert('Lỗi mạng khi lưu: ' + err);
      }
    }

    function navigate(delta) {
      const nextIdx = currentIdx + delta;
      if (nextIdx >= 0 && nextIdx < queueItems.length) {
        loadRecordByIndex(nextIdx);
      }
    }

    init();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


def main():
    parser = argparse.ArgumentParser(description="RoadWatch RW-10 Lane Review Web Server")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--frames-dir", type=Path, default=DEFAULT_FRAMES_DIR)
    parser.add_argument("--media-dir", type=Path, default=DEFAULT_MEDIA_DIR)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    app.state.queue_path = args.queue
    app.state.frames_dir = args.frames_dir
    app.state.media_dir = args.media_dir
    app.state.backup_dir = args.backup_dir

    print(f"============================================================")
    print(f"  RoadWatch RW-10 Lane Review Tool is running!")
    print(f"  URL: http://{args.host}:{args.port}")
    print(f"  Queue: {args.queue}")
    print(f"  Frames: {args.frames_dir}")
    print(f"============================================================")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
