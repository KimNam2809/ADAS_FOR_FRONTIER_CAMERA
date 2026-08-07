# RoadWatch Copilot - ADAS Implementation Plan

This plan outlines the steps to upgrade the current standalone YOLO counting script into **RoadWatch Copilot**, a multimodal edge-based ADAS warning assistant, aligning with the provided project constraints and architecture (FastAPI backend + React frontend).

## The Problem
An edge-based vision agent analyzes the front camera feed to detect crossing vehicles/motorbikes/pedestrians and provide Forward Collision Warnings (FCW), Lane Departure Warnings (LDW), speed sign recognition/reading, and safe distance monitoring. The agent synthesizes this data into natural, context-aware Vietnamese voice alerts and prioritizes alerts based on danger levels.

## Proposed Changes (Future Architecture)

The project structure will be refactored into a `backend/` and `frontend/` architecture.

### 1. Backend (FastAPI - Python)
- Expose an MJPEG video stream endpoint (`/video_feed`) for the HUD.
- Expose WebSocket endpoints (`/ws/telemetry`, `/ws/alerts`) to send real-time bounding boxes, TTC, and alert events to the frontend.
- Implement Role-based access control (Driver vs Engineer).

#### AI Engine (`backend/vision/`)
- **`yolo_manager.py`**: Handle multi-model inference (Object Detection + Traffic Signs).
- **`lane_detector.py`**: Integrate the Lane Detection model to support LDW.
- **`adas_core.py`**: Implement physics logic (Distance estimation, TTC calculations, Polygon FCW regions).

#### Alert & Audio Engine (`backend/alerts/`)
- **`alert_fusion.py`**: Rule-based logic to prioritize alerts and prevent fatigue.
- **`tts_piper.py`**: Interface with Piper TTS to generate Vietnamese audio on the fly.

### 2. Frontend (React - TypeScript)
- **Driver HUD**: A clean React interface overlaying the MJPEG stream. Displays speed, detected signs, visual warnings, and plays audio.
- **Engineer Dashboard**: View latency metrics (P50/P95), mAP, and adjust HITL thresholds (e.g., TTC warning threshold).

### 3. Deployment (Docker)
- Containerize the backend and frontend for Jetson/EC2 deployment.
