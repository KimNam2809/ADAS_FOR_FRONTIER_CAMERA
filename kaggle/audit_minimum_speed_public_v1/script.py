from pathlib import Path
import shutil
import json
import random
from PIL import Image, ImageDraw

source = Path("/kaggle/input")
target = Path("/kaggle/working/minimum_speed_public_v1_evidence")
target.mkdir(parents=True, exist_ok=True)

required = ("dataset_audit.json", "source_manifest.json", "sample_manifest.jsonl")
for name in required:
    matches = list(source.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {name}, found {matches}")
    shutil.copy2(matches[0], target / name)

contact_sheets = list(source.rglob("quality_gate/*.jpg"))
if not contact_sheets:
    raise RuntimeError("No quality-gate contact sheets found")
review = target / "quality_gate"
review.mkdir(exist_ok=True)
for path in contact_sheets:
    shutil.copy2(path, review / path.name)

print(f"evidence_files={len(required) + len(contact_sheets)}")

# Zoomed crops are required: full-scene sheets cannot prove small-sign semantics.
records = [json.loads(line) for line in (target / "sample_manifest.jsonl").read_text().splitlines()]
random.Random(162).shuffle(records)
hash_splits = {}
for record in records:
    hash_splits.setdefault(record["sha256"], set()).add(record["split"])
overlap = [key for key, splits in hash_splits.items() if len(splits) > 1]
(target / "leakage_audit.json").write_text(json.dumps({
    "cross_split_exact_duplicate_hashes": len(overlap),
    "pass": not overlap,
    "review_status": "needs_human_semantic_review",
    "near_duplicate_audit": "not_completed",
}, indent=2))
root = matches[0].parent
for name, cid in (("minimum", 1), ("maximum", 0)):
    tiles = []
    selected_records = []
    for record in records:
        image_path = root / record["image"]
        label_path = root / record["label"]
        if not image_path.exists():
            continue
        for line in label_path.read_text().splitlines():
            c, x, y, w, h = map(float, line.split())
            if int(c) != cid:
                continue
            with Image.open(image_path) as im:
                iw, ih = im.size
                crop = im.crop(((x-w/2)*iw, (y-h/2)*ih, (x+w/2)*iw, (y+h/2)*ih)).convert("RGB")
                crop.thumbnail((140, 140))
                tiles.append(crop.copy())
                selected_records.append({"tile": len(tiles), "image": record["image"], "split": record["split"], "source_image": record["source_image"]})
            if len(tiles) >= 48:
                break
        if len(tiles) >= 48:
            break
    sheet = Image.new("RGB", (8*150, 6*150), "#333333")
    for i, crop in enumerate(tiles):
        sheet.paste(crop, ((i%8)*150, (i//8)*150))
        ImageDraw.Draw(sheet).text(((i%8)*150+2, (i//8)*150+135), str(i+1), fill="white")
    sheet.save(target / f"crops_{name}.jpg")
    (target / f"crops_{name}_index.json").write_text(json.dumps(selected_records, indent=2))
