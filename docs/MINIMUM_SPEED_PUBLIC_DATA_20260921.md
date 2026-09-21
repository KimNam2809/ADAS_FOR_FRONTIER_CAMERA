# RoadWatch: public data for minimum-speed signs

## Objective and status

Prepare a research candidate that distinguishes red-ring maximum-speed signs
from blue circular minimum-speed signs (Vietnam R.306). Production Sign V2
remains active. No training is authorized by a successful builder run alone.

Builder: https://www.kaggle.com/code/lekimnam/roadwatch-build-minimum-speed-public-v1

Evidence exporter: https://www.kaggle.com/code/lekimnam/roadwatch-audit-minimum-speed-public-v1

Versions 1 and 2 are rejected: V1 failed mount discovery, V2 used an incorrect
TT100K mapping. `pm`/`pm*` denotes mass restriction, **not minimum speed**.
The corrected builder uses `il50`, `il60`, `il70`, `il80`, `il90`, `il100`,
and `il110`. Machine completion does not establish label correctness.

## Sources and use

| Source | Use | Limitation |
|---|---|---|
| https://www.kaggle.com/datasets/braunge/tt100k | Real street images, il* minimum and pl* maximum signs | Mirror license unknown; upstream CC BY-NC; research only; augmented derivatives |
| https://www.kaggle.com/datasets/lapnguyen2003/traffic-sign-detection-vietnam | Existing Vietnamese maximum-speed replay and non-speed red-ring negatives | Class semantics require visual review; known historical mislabeled speed subclasses |
| https://www.kaggle.com/datasets/maitam/vietnamese-traffic-signs | Existing digit-training source; not added to builder | 40/50/60/80 maximum speeds, no new minimum-speed supervision |
| https://www.kaggle.com/datasets/meowmeowmeowmeowmeow/gtsrb-german-traffic-sign | Existing classifier source; not added to builder | Does not solve blue minimum-speed domain shift |

Upstream TT100K license and dataset: https://cg.cs.tsinghua.edu.cn/traffic-sign/
Do not interpret a third-party mirror's license as permission overriding the
original dataset. This combined candidate must be reviewed before business use.

## Vietnam scope

QCVN 41:2024/BGTVT distinguishes R.306 (minimum), R.307 (end minimum), P.127
(maximum), P.127b/c (lane/vehicle-related maximum limits), and end-limit signs.
R.306 applies under favourable, safe traffic conditions; RoadWatch must never
instruct acceleration solely because a minimum-speed sign is detected.

Reference regulation:
https://files.thuvienphapluat.vn/uploads/DOC2HTM/TC_921296.htm

The Directorate for Roads' published Hanoi–Hai Phong lane pilot described
120/90, 120/80 and 100/60 km/h maximum/minimum limits for lanes 1/2/3,
with specific vehicle restrictions and exceptions in lane 1:
https://drvn.gov.vn/tin-tuc/hoat-dong-nganh-duong-bo/tu-15-8-thi-diem-phan-lan-duong-toc-do-xe-hai-tuyen-cao-toc-ha-noi-hai-phong-va-phap-van-cau-gie.html

This dated traffic-organization notice is not a live guarantee for every section.
Use observed signs and current route decisions, not hard-coded route speeds.
Broader highway coverage will also need no-entry/vehicle restrictions, height,
width, weight, lane use, exit/entry, merging, distance, works and end restrictions.
The initial two-class candidate does not claim recognition of all these signs.

## Gates

1. Schema: finite YOLO boxes, exact names, decoded images, matched labels.
2. Semantics: inspect zoomed crops. Blue arrows, parking signs, mass signs and
   end-minimum signs must not become minimum-speed positives.
3. Split: group TT100K derivatives by original image ID across source splits.
   Grouping IDs reduces leakage; independent near-duplicate review remains needed.
4. Human review: minimum 20 train / 5 val instances is only a technical floor,
   not sufficient evidence for production quality. Review coverage and diversity.
5. Train: one-epoch pilot, reviewed five-epoch smoke, then full candidate.
6. Evaluate detector type and digit reading separately. Review 60/80/90 on
   independent Hanoi–Hai Phong crops and lane applicability on held-out video.

The existing digit classifier was trained predominantly on maximum-speed crops.
A correct blue-sign detection does not prove it reads white digits correctly.
Collect minimum-speed crops with independently reviewed numeric labels before
promoting the combined detector/classifier pipeline.

## Phone workflow

Open https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA/actions/workflows/roadwatch-sign-highway-v1.yml

Use `dataset_profile=minimum_speed`, `source_type=kernel_output`, and
`dataset_slug=lekimnam/roadwatch-build-minimum-speed-public-v1` after the corrected
builder completes and the visual gate is reviewed. This reads the prepared data
directly from private Kaggle notebook output, without a laptop download/upload.
First dispatch
`quality_gate`, `quality_gate_approved=NOT_REVIEWED`, and a new kernel slug.
Inspect dataset_audit.json, preflight.json and visual evidence. Only after your
review, dispatch `pilot` with PASS, then smoke and full after each review.

No new secret is necessary. Keep tokens in repository secrets; never paste them
into workflow inputs. If Kaggle supplied a KGAT token, use token authentication.
