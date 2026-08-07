from __future__ import annotations
import argparse
import time
from collections import defaultdict, deque
import numpy as np
from pathlib import Path
import cv2
import concurrent.futures
import torch
from ultralytics import YOLO
from .device import can_show_window, describe_runtime, select_device

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args():
    p = argparse.ArgumentParser(description="Cross-platform YOLO object detector, tracker and line counter")
    p.add_argument("--model", nargs="+", default=["models/best.pt"], help="Paths to one or more YOLO models")
    p.add_argument("--source", required=True, help="Image, video, webcam index (0), or RTSP URL")
    p.add_argument("--output", default="outputs/result.mp4")
    p.add_argument("--device", default="auto", help="auto, cpu, mps, or CUDA index such as 0")
    p.add_argument("--imgsz", type=int, default=512)
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--line", type=float, default=0.60, help="Horizontal line position from 0 to 1")
    p.add_argument("--tracker", default="bytetrack.yaml")
    p.add_argument("--classes", nargs="*", default=None, help="Class names to count")
    p.add_argument("--show", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--save", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--frame-skip", type=int, default=0)
    p.add_argument("--ground-truth", type=int, default=None,
                   help="Tổng số vật thể thật (ground truth) để tính độ chính xác đếm")
    return p.parse_args()


def normalize_source(value: str):
    return int(value) if value.isdigit() else value


def process_image(models, source, output, device, imgsz, conf, class_filter, show, save):
    import concurrent.futures
    image = cv2.imread(str(source))
    if image is None:
        raise RuntimeError(f"Cannot read image: {source}")
        
    def run_inference(model):
        return model.predict(image, device=device, imgsz=imgsz, conf=conf, verbose=False)[0]
        
    num_models = len(models)
    
    # Threading optimization
    if device == "cpu":
        torch.set_num_threads(max(1, torch.get_num_threads() // num_models))
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_models) as executor:
        results = list(executor.map(run_inference, models))
        
    canvas = image.copy()
    all_counts = []
    total_counts = defaultdict(int)
    
    for result, model in zip(results, models):
        counts = defaultdict(int)
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            cids = result.boxes.cls.int().cpu().tolist()
            confs = result.boxes.conf.cpu().tolist()
            
            for box, cid, conf_val in zip(boxes, cids, confs):
                name = model.names[cid]
                if class_filter is None or name in class_filter:
                    counts[name] += 1
                    total_counts[name] += 1
                    
                x1, y1, x2, y2 = map(int, box)
                np.random.seed(cid)
                color = tuple([int(c) for c in np.random.randint(0, 255, 3)])
                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
                
                label = f"{name} {conf_val:.2f}"
                (w_text, h_text), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(canvas, (x1, y1 - h_text - 4), (x1 + w_text, y1), color, -1)
                cv2.putText(canvas, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
        all_counts.append(dict(counts))
        
    y = 35
    cv2.putText(canvas, f"TOTAL: {sum(total_counts.values())}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, .9, (0, 165, 255), 2)
    for name, value in sorted(total_counts.items()):
        y += 30
        cv2.putText(canvas, f"{name}: {value}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
        
    if save:
        out = Path(output)
        if out.suffix.lower() not in IMAGE_EXTS:
            out = out.with_suffix(".jpg")
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), canvas)
        print(f"Saved: {out}")
    if show:
        cv2.imshow("YOLO Counter", canvas)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    print("Counts:", all_counts)


def process_stream(models, source, output, device, imgsz, conf, line_ratio, tracker, class_filter, show, save, frame_skip, ground_truth=None):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    if not source_fps or source_fps <= 0 or source_fps > 240:
        source_fps = 25.0
        
    num_models = len(models)
    
    writer = None
    if save:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), source_fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError(f"Cannot create output video: {out}")
            
    # Track states per model
    previous_y_list = [{} for _ in models]
    counted_up_list = [set() for _ in models]
    counted_down_list = [set() for _ in models]
    up_list = [defaultdict(int) for _ in models]
    down_list = [defaultdict(int) for _ in models]
    
    frame_index, processed = 0, 0
    started = time.perf_counter()
    latency_buf: deque[float] = deque(maxlen=300)
    
    # Threading optimization for CPU
    if device == "cpu":
        torch.set_num_threads(max(1, torch.get_num_threads() // num_models))
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_models) as executor:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_index += 1
                if frame_skip and frame_index % (frame_skip + 1) != 1:
                    continue
                processed += 1
                
                _t0 = time.perf_counter()
                
                def run_track(model):
                    return model.track(frame, persist=True, tracker=tracker, device=device, imgsz=imgsz, conf=conf, verbose=False)[0]
                    
                results = list(executor.map(run_track, models))
                latency_buf.append((time.perf_counter() - _t0) * 1000)  # ms
                
                canvas = frame.copy()
                fps = processed / max(time.perf_counter() - started, 1e-6)
                
                total_up = defaultdict(int)
                total_down = defaultdict(int)
                
                line_y_original = int(height * line_ratio)
                
                for idx, (result, model) in enumerate(zip(results, models)):
                    previous_y = previous_y_list[idx]
                    counted_up = counted_up_list[idx]
                    counted_down = counted_down_list[idx]
                    up = up_list[idx]
                    down = down_list[idx]
                    
                    if result.boxes is not None:
                        boxes = result.boxes.xyxy.cpu().numpy()
                        cids = result.boxes.cls.int().cpu().tolist()
                        ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(boxes)
                        confs = result.boxes.conf.cpu().tolist()
                        
                        for box, track_id, cid, conf_val in zip(boxes, ids, cids, confs):
                            name = model.names[cid]
                            if class_filter is not None and name not in class_filter:
                                continue
                                
                            # Manual drawing of Bounding Box
                            x1, y1, x2, y2 = map(int, box)
                            # Generate a unique color for the class
                            np.random.seed(cid * (idx + 1))
                            color = tuple([int(c) for c in np.random.randint(0, 255, 3)])
                            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
                            
                            # Label: [ID] Name Conf
                            id_text = f"ID:{track_id} " if track_id is not None else ""
                            label = f"{id_text}{name} {conf_val:.2f}"
                            
                            (w_text, h_text), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                            cv2.rectangle(canvas, (x1, y1 - h_text - 4), (x1 + w_text, y1), color, -1)
                            cv2.putText(canvas, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                            # Counting Logic
                            if track_id is not None:
                                cy = int((y1 + y2) / 2)
                                old_y = previous_y.get(track_id)
                                if old_y is not None:
                                    if old_y < line_y_original <= cy and track_id not in counted_down:
                                        counted_down.add(track_id); down[name] += 1
                                    elif old_y > line_y_original >= cy and track_id not in counted_up:
                                        counted_up.add(track_id); up[name] += 1
                                previous_y[track_id] = cy
                    
                    # Aggregate counts
                    for k, v in up.items(): total_up[k] += v
                    for k, v in down.items(): total_down[k] += v
                        
                if not canvas.flags.writeable:
                    canvas = canvas.copy()
                        
                cv2.line(canvas, (0, line_y_original), (width, line_y_original), (0, 255, 255), 3)
                
                labels = [f"DOWN: {sum(total_down.values())}", f"UP: {sum(total_up.values())}", f"FPS: {fps:.1f}"]
                for i, text in enumerate(labels):
                    cv2.putText(canvas, text, (20, 40 + i * 38), cv2.FONT_HERSHEY_SIMPLEX, .9, (255, 255, 255), 2)
                    
                _lat_arr = np.array(latency_buf) if latency_buf else np.array([0.0])
                p50 = float(np.percentile(_lat_arr, 50))
                p95 = float(np.percentile(_lat_arr, 95))
                    
                total_counted = sum(total_up.values()) + sum(total_down.values())
                if ground_truth is not None:
                    _correct  = min(total_counted, ground_truth)
                    _missed   = max(ground_truth - total_counted, 0)
                    _error    = abs(total_counted - ground_truth)
                    _acc_labels = [
                        f"Dung: {_correct}",
                        f"Bo sot: {_missed}",
                        f"Sai so: {_error}",
                    ]
                else:
                    _acc_labels = [
                        f"Dung: {total_counted}",
                        f"Bo sot: N/A",
                        f"Sai so: N/A",
                    ]
                _new_labels = [
                    f"P50: {p50:.1f}ms",
                    f"P95: {p95:.1f}ms",
                ] + _acc_labels
                
                _x_right = width - 260
                for j, text in enumerate(_new_labels):
                    cv2.putText(canvas, text, (_x_right, 40 + j * 38), cv2.FONT_HERSHEY_SIMPLEX, .9, (0, 255, 180), 2)
                    
                if frame_index % 30 == 0:
                    print(f"[Frame {frame_index}] FPS: {fps:.1f} | Latency P50: {p50:.1f}ms | P95: {p95:.1f}ms")
                    
                if writer is not None:
                    writer.write(canvas)
                if show:
                    display = cv2.resize(canvas, (1280, 720)) if width > 1280 else canvas
                    cv2.imshow("YOLO Counter", display)
                    if (cv2.waitKey(10) & 0xFF) in (ord("q"), 27):
                        break
    finally:
        cap.release()
        if writer is not None: writer.release()
        cv2.destroyAllWindows()
        
    print("\n=== Performance Summary ===")
    total_time = max(time.perf_counter() - started, 1e-6)
    print(f"Total Frames Processed: {processed}")
    print(f"Average FPS: {processed / total_time:.1f}")
    if latency_buf:
        _lat_arr = np.array(latency_buf)
        print(f"Overall Latency P50: {np.percentile(_lat_arr, 50):.1f}ms")
        print(f"Overall Latency P95: {np.percentile(_lat_arr, 95):.1f}ms")
    print("===========================\n")
        
    for idx, (up, down) in enumerate(zip(up_list, down_list)):
        print(f"Model {idx} UP:", dict(up))
        print(f"Model {idx} DOWN:", dict(down))


def main():
    args = parse_args()
    device = select_device(args.device)
    if args.show and not can_show_window():
        print("No graphical display detected; switching to --no-show.")
        args.show = False
    print(describe_runtime(device))
    
    models = [YOLO(m) for m in args.model]
    source = normalize_source(args.source)
    class_filter = set(args.classes) if args.classes else None
    
    if isinstance(source, str) and Path(source).suffix.lower() in IMAGE_EXTS:
        process_image(models, source, args.output, device, args.imgsz, args.conf, class_filter, args.show, args.save)
    else:
        process_stream(models, source, args.output, device, args.imgsz, args.conf, args.line, args.tracker, class_filter, args.show, args.save, args.frame_skip, args.ground_truth)

if __name__ == "__main__":
    main()
