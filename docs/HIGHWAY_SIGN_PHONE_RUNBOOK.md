# RoadWatch Highway Sign V1 — Phone-only Runbook

## One-time GitHub setup

In the GitHub mobile app or mobile browser, open repository Settings → Secrets
and variables → Actions.

Create repository secrets:

- `KAGGLE_USERNAME`: Kaggle account username.
- `KAGGLE_KEY`: Kaggle API token value. Never put this in a variable, issue,
  workflow input, log, or repository file.

No second Kaggle key is required for this workflow. Use a second account only
when training a separate model concurrently, with a separate repository or
environment secret scope.

## Prepare the dataset

1. Finish independent CVAT review. Delete false positives, add missed signs,
   correct classes and mark uncertain samples.
2. Export Ultralytics YOLO.
3. Upload the ZIP as a private Kaggle Dataset.
4. Record its slug, for example `lekimnam/roadwatch-highway-sign-v1`.
5. The dataset must contain exactly one `data.yaml` or `dataset.yaml` and include
   at least `speed_limit_max`, `speed_limit_min`, `no_trucks`, and `no_vehicles`.

## Run from a phone

Open GitHub → Actions → `RoadWatch Sign Highway V1` → Run workflow.

### Run 1 — quality gate

- `run_mode`: `quality_gate`
- `quality_gate_approved`: `NOT_REVIEWED`
- `dataset_slug`: the private Kaggle dataset slug
- `kernel_slug`: `roadwatch-sign-highway-v1-qg`

After completion, download the GitHub Artifact and inspect:

- `preflight.json`: GPU exists and the expected dataset mounted.
- `dataset_audit.json`: class names, instance counts, invalid rows, and required
  classes. `pass` must be true.
- `job_status.json`: must be `QUALITY_GATE_READY`.

Do not type PASS merely because the workflow is green. Check sample labels in
CVAT/Kaggle and verify that red-ring prohibition signs are not speed signs.

### Run 2 — one-epoch pilot

- `run_mode`: `pilot`
- `quality_gate_approved`: `PASS`
- kernel slug: `roadwatch-sign-highway-v1-pilot`

Accept only when one epoch finishes on GPU, losses are finite, `best.pt` and
`best.onnx` exist, and `job_status.json` is `TRAINING_COMPLETE`.

### Run 3 — five-epoch smoke test

Use `smoke`, `PASS`, and a new kernel slug. Inspect results curves, validation
predictions, class coverage, and memory stability. This is not a promotion gate.

### Run 4 — full candidate

Use `full`, `PASS`, and a new kernel slug only after smoke review. The default is
50 epochs. Download and preserve the GitHub Artifact before starting another run.

## Promotion gate

The workflow intentionally does not promote a model. Candidate promotion needs:

- an independently reviewed, journey-separated highway test split;
- per-class precision and recall for minimum speed and every restriction class;
- small-sign recall and false speed alerts per minute;
- RoadWatch event replay with no regression on existing 60/80 test videos;
- acceptable latency on the target runtime;
- model and config hashes;
- explicit human approval.

Until all gates pass, `roadwatch_detector_v2.onnx` remains active.
