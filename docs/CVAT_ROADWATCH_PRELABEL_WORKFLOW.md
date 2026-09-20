# RoadWatch CVAT Pre-label, Review and Training Evidence

## Scope

This workflow keeps three distinct records:

1. immutable RoadWatch machine predictions;
2. current CVAT annotations after human review;
3. a reproducible comparison report used for candidate-training decisions.

Never edit an evidence directory in place and never promote a model from
unreviewed pre-labels.

## Current pilot

- CVAT project: `RW-SIGN-V3` (`446547`)
- CVAT task: `RW-SIGN-V3-CT-HN-HP-001-PILOT` (`2607579`)
- Frames: `284`
- Production detector: `roadwatch_detector_v2.onnx`
- Production speed classifier: `roadwatch_speed_digits_v2.onnx`
- CVAT job URL: `https://app.cvat.ai/tasks/2607579/jobs/4493640`

## First pre-label evidence (locked)

- Evidence directory: `evaluation/cvat/task-2607579-roadwatch-first-prelabel-full`
- Frames processed: `284/284`
- Uploaded rectangles: `37`
- Canonical label: `speed_limit_max`
- Mean local inference latency: `33.782 ms/frame` (frame download excluded)
- Exact uploaded payload SHA-256:
  `129f8055b654d3976cf81bcf05708d6c67a39709518e5cdea1e805caa5967e5c`

The server upload was made from the already-hashed evidence payload, not from a
second model run. `upload_receipt.json` and `post_upload_annotations.json` prove
that CVAT received the same 37 shapes. These numbers describe pre-label output,
not model accuracy; accuracy is measured only after human review.

## Run a bounded dry-run

```powershell
cd roadwatch
.\.venv\Scripts\python.exe -m tools.cvat_prelabel.prelabel_task `
  --project-id 446547 `
  --task-id 2607579 `
  --max-frames 10
```

This downloads ten CVAT frames, runs RoadWatch locally, and writes evidence. It
does not modify CVAT unless `--upload` is supplied.

## Pre-label and upload the full pilot

Run only after inspecting the dry-run contact sheet:

```powershell
cd roadwatch
.\.venv\Scripts\python.exe -m tools.cvat_prelabel.prelabel_task `
  --project-id 446547 `
  --task-id 2607579 `
  --upload
```

The tool refuses to run over existing annotations unless `--allow-existing` is
explicitly supplied. Do not use that flag without exporting a backup first.

## Human review in CVAT

Review all frames in order. For each predicted box:

- tighten loose boxes around the sign face only;
- delete false positives;
- add missed signs;
- correct the canonical label;
- verify `speed_value`;
- leave `scope=uncertain`, `relative_lane=unknown`, and
  `orientation=uncertain` unless the video clearly proves otherwise;
- mark unreadable or ambiguous signs as `uncertain=true` rather than guessing.

Use CVAT's Save button or `Ctrl+S` frequently. When every frame is reviewed,
set the job state to completed and export `CVAT for video` (plus YOLO/COCO when
needed for training). Keep every reviewed export outside the immutable pre-label
directory, for example `evaluation/cvat/task-2607579-human-review-v1/`.

## Compare machine predictions with reviewed ground truth

```powershell
cd roadwatch
.\.venv\Scripts\python.exe -m tools.cvat_prelabel.compare_review `
  --project-id 446547 `
  --task-id 2607579 `
  --evidence-dir evaluation\cvat\task-2607579-roadwatch-first-prelabel-full
```

The report includes:

- geometry matches at IoU 0.50;
- exact-label precision, recall and F1;
- class accuracy on geometrically matched signs;
- speed-value accuracy;
- predictions deleted by the reviewer;
- annotations added by the reviewer;
- boxes materially edited by the reviewer;
- a confusion table.

## Training decision

Do not immediately train on every corrected frame. First:

1. exclude unreadable and `ignore_training=true` signs;
2. deduplicate near-identical adjacent frames;
3. split by source video or journey, never random adjacent frames;
4. lock one journey as test-only;
5. inspect class and speed-value balance;
6. train a one-epoch pilot;
7. run a 3–5 epoch smoke test;
8. run full training only after stable loss and correct taxonomy;
9. compare candidate and V2 on the same locked event-level replay;
10. keep V2 active unless all promotion gates pass.

## Storage

CVAT Online stores the live task and annotations in CVAT-managed cloud storage.
The local evidence directories are independent copies and may be archived to
Google Drive. Do not upload `.env`, access tokens, private model weights without
authorization, or data whose license forbids redistribution.
