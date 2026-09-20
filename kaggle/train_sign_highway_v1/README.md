# RoadWatch Sign Highway V1

This pipeline trains a candidate highway-sign detector without changing the
active RoadWatch V2 release. It is designed for phone-only dispatch through
GitHub Actions and Kaggle GPU.

Required classes include `speed_limit_max`, `speed_limit_min`, `no_trucks`, and
`no_vehicles`. Additional supported restriction classes are listed in the
training script. Red-ring geometry alone is never accepted as a semantic label.

Run sequence: `quality_gate` → human review of the downloaded artifact →
`pilot` → `smoke` → `full`. Every training run requires the exact dispatch input
`quality_gate_approved=PASS`. Outputs are candidates only; promotion requires a
locked, independently reviewed test split and RoadWatch replay regression.
