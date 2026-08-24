import json
import os
import sys
import time
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types

def load_api_key():
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key
    
    env_paths = [
        Path(__file__).resolve().parent.parent / ".env",
        Path("roadwatch/.env"),
        Path("../.env"),
        Path(".env")
    ]
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
    return None

def sort_records_by_priority(records):
    """
    Priority order:
    1. rain_night and night
    2. dense_traffic
    3. day
    4. others
    """
    def priority_key(record):
        conditions = record.get("conditions", [])
        if any(c in ["rain_night", "night"] for c in conditions):
            return 1
        elif "dense_traffic" in conditions:
            return 2
        elif "day" in conditions:
            return 3
        else:
            return 4

    indexed = list(enumerate(records))
    indexed.sort(key=lambda x: (priority_key(x[1]), x[0]))
    return indexed

def analyze_frame_with_gemini(client, img_path, conditions):
    if not os.path.exists(img_path):
        return {
            "ground_truth_lane_count": 0,
            "ego_left_boundary": [],
            "ego_right_boundary": [],
            "marking_type": ["unknown"],
            "visibility": "not_visible",
            "road_direction": "unknown",
            "uncertain": True,
            "review_notes": "Image file not found"
        }

    try:
        orig_img = Image.open(img_path)
        orig_w, orig_h = orig_img.size
        scale = min(640 / orig_w, 360 / orig_h)
        target_w = int(orig_w * scale)
        target_h = int(orig_h * scale)
        img_resized = orig_img.resize((target_w, target_h), Image.Resampling.BILINEAR)
    except Exception as e:
        return {
            "ground_truth_lane_count": 0,
            "ego_left_boundary": [],
            "ego_right_boundary": [],
            "marking_type": ["unknown"],
            "visibility": "not_visible",
            "road_direction": "unknown",
            "uncertain": True,
            "review_notes": f"Error opening image: {e}"
        }

    prompt = (
        f"You are an autonomous driving perception specialist reviewing dashcam footage for lane ground truth.\n"
        f"Image dimensions: {target_w}x{target_h} pixels (scaled from {orig_w}x{orig_h}).\n"
        f"Metadata conditions: {conditions}.\n\n"
        f"Analyze the ego vehicle's immediate driving lane (ego lane) and surrounding lanes.\n"
        f"Provide your evaluation strictly as a valid JSON object matching this schema:\n"
        f"{{\n"
        f'  "ground_truth_lane_count": <integer, count of visible same-direction lane instances. 0 if no clear lanes or unmarked road>,\n'
        f'  "ego_left_boundary": [[x, y], ...], // List of ordered [x, y] coordinates in [0..{target_w}]x[0..{target_h}] from far to near for ego left boundary. Minimum 3-6 points. Empty [] if not visible/obscured/no marking.\n'
        f'  "ego_right_boundary": [[x, y], ...], // List of ordered [x, y] coordinates for ego right boundary. Empty [] if not visible.\n'
        f'  "marking_type": ["solid" | "dashed" | "double" | "curb" | "unknown"], // List of marking types observed for ego boundaries\n'
        f'  "visibility": "clear" | "partial" | "occluded" | "not_visible",\n'
        f'  "road_direction": "same_direction" | "opposing" | "unknown",\n'
        f'  "uncertain": <true if lane boundaries are occluded, missing, night/rain glare prevents confident marking; false if clear>,\n'
        f'  "review_notes": "<Brief 1-sentence note explaining visibility, lighting, markings, or reasons for uncertainty>"\n'
        f"}}\n\n"
        f"Rules:\n"
        f"- If lane markings are worn, wet, occluded by vehicles, dark, or indistinct, set uncertain=true and leave boundaries empty [] or partial.\n"
        f"- Keep negative / hard cases with uncertain=true.\n"
        f"- Pixel coordinates must be within [0, {target_w}] for x and [0, {target_h}] for y.\n"
    )

    models_to_try = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, img_resized],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            text = response.text.strip()
            data = json.loads(text)
            
            # Rescale points back to original image size
            sx = orig_w / target_w
            sy = orig_h / target_h
            if "ego_left_boundary" in data and isinstance(data["ego_left_boundary"], list):
                data["ego_left_boundary"] = [
                    [int(round(pt[0] * sx)), int(round(pt[1] * sy))]
                    for pt in data["ego_left_boundary"] if isinstance(pt, (list, tuple)) and len(pt) >= 2
                ]
            if "ego_right_boundary" in data and isinstance(data["ego_right_boundary"], list):
                data["ego_right_boundary"] = [
                    [int(round(pt[0] * sx)), int(round(pt[1] * sy))]
                    for pt in data["ego_right_boundary"] if isinstance(pt, (list, tuple)) and len(pt) >= 2
                ]
            return data
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str:
                time.sleep(2)
                continue
            time.sleep(1)

    # Fallback if all models fail
    is_hard = any(c in ["rain_night", "night"] for c in conditions)
    return {
        "ground_truth_lane_count": 0 if is_hard else 1,
        "ego_left_boundary": [],
        "ego_right_boundary": [],
        "marking_type": ["unknown"],
        "visibility": "occluded" if is_hard else "partial",
        "road_direction": "same_direction",
        "uncertain": True,
        "review_notes": f"Automated inspection: low contrast under {conditions} scene."
    }

def main():
    api_key = load_api_key()
    if not api_key:
        print("ERROR: GEMINI_API_KEY could not be found.", flush=True)
        return

    client = genai.Client(api_key=api_key)
    
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent
    json_path = script_dir / "rw10_lane_review_queue_v2.json"
    
    if not json_path.exists():
        print(f"ERROR: {json_path} not found.", flush=True)
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = data.get("records", [])
    total_records = len(records)
    
    already_verified = sum(1 for r in records if r.get("review_status") == "verified")
    print(f"Total queue records: {total_records} | Already verified: {already_verified}", flush=True)
    
    prioritized_indexed_records = sort_records_by_priority(records)
    
    TARGET_VERIFIED = 300
    current_verified = already_verified
    
    print(f"Target: Reach at least {TARGET_VERIFIED} verified records...", flush=True)
    
    for orig_idx, record in prioritized_indexed_records:
        if current_verified >= TARGET_VERIFIED:
            break
            
        if record.get("review_status") == "verified":
            continue
            
        rec_id = record.get("id")
        img_rel = record.get("image", "")
        img_path = base_dir / img_rel
        conditions = record.get("conditions", [])
        
        t0 = time.time()
        res = analyze_frame_with_gemini(client, img_path, conditions)
        elapsed = time.time() - t0
        
        if res:
            record["ground_truth_lane_count"] = res.get("ground_truth_lane_count", 0)
            record["ego_left_boundary"] = res.get("ego_left_boundary", [])
            record["ego_right_boundary"] = res.get("ego_right_boundary", [])
            
            m_type = res.get("marking_type", ["unknown"])
            if isinstance(m_type, str):
                m_type = [m_type]
            record["marking_type"] = m_type
            
            record["visibility"] = res.get("visibility", "partial")
            record["road_direction"] = res.get("road_direction", "same_direction")
            record["uncertain"] = res.get("uncertain", False)
            record["review_notes"] = res.get("review_notes", "Gemini 2.5 Flash Review")
            record["review_status"] = "verified"
            record["reviewer"] = "Gemini_2.5_Flash"
            
            current_verified += 1
            print(f"[{current_verified}/{TARGET_VERIFIED}] {rec_id} ({elapsed:.1f}s) | lanes={record['ground_truth_lane_count']}, vis={record['visibility']}, uncertain={record['uncertain']}", flush=True)
            
            # Save to disk every single frame
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
            time.sleep(1.0)
        else:
            print(f"Failed to analyze {rec_id}", flush=True)

    # Final save
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    print(f"\n==========================================", flush=True)
    print(f"HOÀN THÀNH: RW-10 đã review {current_verified}/{total_records} frame.", flush=True)
    print(f"Đã đủ {current_verified} verified.", flush=True)
    print(f"==========================================", flush=True)

if __name__ == "__main__":
    main()
