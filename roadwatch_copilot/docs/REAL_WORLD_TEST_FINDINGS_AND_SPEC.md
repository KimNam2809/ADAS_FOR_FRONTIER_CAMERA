# RoadWatch ADAS: Real-World Test Findings & Bug Remediation Specification

- **Document ID:** `RW-SPEC-EVAL-20260822`
- **Target Pipeline:** Layer 1 (Detector), Layer 2 (Tracker & Geometry), Layer 3 (Decision & Rules / FSM), Sign Pipeline, HMI/TTS Engine
- **Test Session Sources:** `dashcam_vietnam_night.mp4`, `test_video5.mp4`, `video_test.mp4`, `test_video1.mp4`
- **Classification:** Safety Critical Evaluation & Regression Matrix

---

## 1. Executive Root-Cause Summary

| Category | Severity | Primary Fault Layer | Summary of Defect |
|---|:---:|---|---|
| **FCW Emergency Braking Regression** | **P0 (Blocker)** | Layer 3 (FSM / Safety Gate) | At ~30cm proximity under hard deceleration, visual hazard, audible beep, and TTS warning failed to trigger completely (silent failure). |
| **Direction Inversion & Cross vs. Cut-In Confusion** | **P1 (High)** | Layer 2 (Velocity Vector) & Layer 3 (FSM) | Heading angle determines trajectory without lateral position ($X$) context; parked/far-off vehicles trigger false "Cross-Traffic Left-to-Right" alerts. Cut-ins from right are inverted to left-to-right. |
| **Opposing Traffic / 2-Way Lane Leakage** | **P1 (High)** | Layer 2 (Lane Geometry / Boundary) | Faded median markings cause oncoming traffic lanes to be treated as ego lanes, falsely flagging stationary/oncoming vehicles as cut-in/cross-traffic hazards. |
| **Traffic Sign Backside & Lane-Binding Failures** | **P2 (Medium)** | Sign Detection & Association Pipeline | Sign detector classifies reverse/back-facing signs as active restrictions; multi-lane sign assignment fails to bind lane-specific limits (e.g. 60 km/h applied to 80 km/h ego lane). |
| **VRU / Fallen-Rider State Machine Gap** | **P1 (High)** | Layer 1 (Specialist Classifier) & Layer 3 (FSM) | Fallen motorcyclist classified as generic pedestrian cut-in; rapid fall transition dynamics and aspect ratio changes are not recognized as a `fallen_rider` event. |
| **Object Class Instability / Flickering** | **P2 (Medium)** | Layer 1 & Tracker Temporal Smoothing | Far-lane passenger car flickers to `truck`, triggering unmerited heavy-vehicle cut-in warnings across road dividers. |

---

## 2. Structured Test Cases & Engineering Specifications

```json
{
  "schema_version": "1.0.0",
  "test_suite": "RoadWatch_RealWorld_Regression_Suite",
  "cases": [
    {
      "case_id": "TC-RW-NIGHT-01",
      "source_video": "dashcam_vietnam_night.mp4",
      "timestamp_seconds": 0.06,
      "scenario": "Ego right turn with motorbike approaching from front-right",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Xe máy đang cắt ngang từ trái sang phải",
        "fault_type": "DIRECTION_INVERSION_AND_MANEUVER_MISCLASSIFICATION"
      },
      "expected_behavior": {
        "hazard_visual": true,
        "tts_text": "Xe máy phía trước bên phải có xu hướng tiếp cận",
        "fsm_state": "vru_approaching_right",
        "cross_traffic_active": false
      },
      "root_cause_subsystem": "Layer2_Trajectory_Estimator",
      "remediation_rule": "Calculate relative lateral velocity dX/dt relative to ego heading. If object is at X > 0 and moving towards center, trajectory must be classified as right_to_left or cut_in_right, never left_to_right."
    },
    {
      "case_id": "TC-RW-NIGHT-02",
      "source_video": "dashcam_vietnam_night.mp4",
      "timestamp_seconds": 0.09,
      "scenario": "Opposing 2-way road with faded lane markings; oncoming car and motorbike stopped at red light",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Ô tô bên trái có xu hướng nhập làn / Xe máy phía trước có xu hướng nhập làn",
        "fault_type": "OPPOSING_LANE_FALSE_POSITIVE"
      },
      "expected_behavior": {
        "hazard_visual": false,
        "tts_text": null,
        "fsm_state": "opposing_traffic_stationary",
        "suppression": "SUPPRESS_ONCOMING_LANE_OBJECTS"
      },
      "root_cause_subsystem": "Layer2_Lane_Geometry_Engine",
      "remediation_rule": "Implement oncoming traffic flow filtering: Objects with stationary pose on opposing side of vanishing point must not enter ego-lane cut-in state machine when median confidence is low."
    },
    {
      "case_id": "TC-RW-NIGHT-03",
      "source_video": "dashcam_vietnam_night.mp4",
      "timestamp_seconds": null,
      "scenario": "Parked cars and motorbikes on right roadside with angled wheels/head",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Xe cắt ngang từ trái sang phải",
        "fault_type": "STATIC_OBJECT_CROSS_TRAFFIC_FALSE_ALARM"
      },
      "expected_behavior": {
        "hazard_visual": false,
        "tts_text": null,
        "fsm_state": "static_roadside_object"
      },
      "root_cause_subsystem": "Layer3_Cross_Traffic_FSM",
      "remediation_rule": "Enforce minimum absolute velocity threshold (|v_lateral| > 1.5 m/s) and trajectory displacement over at least 5 consecutive frames before triggering cross-traffic alerts."
    },
    {
      "case_id": "TC-RW-V5-01",
      "source_video": "test_video5.mp4",
      "timestamp_seconds": 0.05,
      "scenario": "Back-facing traffic signs on the left (rear side facing ego camera)",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "No Stopping & No Parking / No Two or Three-wheels Vehicles",
        "fault_type": "BACK_OF_SIGN_FALSE_POSITIVE"
      },
      "expected_behavior": {
        "hazard_visual": false,
        "tts_text": null,
        "detection_filtered": true
      },
      "root_cause_subsystem": "Sign_Detection_Classifier",
      "remediation_rule": "Add back-of-sign detector or geometric feature verification (uniform gray/metallic texture, lack of symbology, pole geometry) with confidence threshold > 0.85 to reject rear-facing signs."
    },
    {
      "case_id": "TC-RW-V5-02",
      "source_video": "test_video5.mp4",
      "timestamp_seconds": 0.09,
      "scenario": "Oncoming truck in designated left lane moving correctly in opposing direction",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Xe tải đang cắt ngang từ phải sang trái phía trước",
        "fault_type": "OPPOSING_LANE_CROSS_TRAFFIC_FALSE_ALARM"
      },
      "expected_behavior": {
        "hazard_visual": false,
        "tts_text": null,
        "fsm_state": "opposing_traffic_normal"
      },
      "root_cause_subsystem": "Layer2_Lane_And_Tracking",
      "remediation_rule": "Opposing vehicles with optical flow vectors pointing downwards/towards bottom-left along oncoming lane angle must be suppressed from cross-traffic FSM."
    },
    {
      "case_id": "TC-RW-V5-03",
      "source_video": "test_video5.mp4",
      "timestamp_seconds": 0.16,
      "scenario": "Lead car in adjacent right lane enters ego lane with safe spacing",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Ô tô đang cắt ngang từ trái sang phải",
        "fault_type": "CUT_IN_MISCLASSIFIED_AS_CROSS_TRAFFIC_WITH_INVERTED_DIRECTION"
      },
      "expected_behavior": {
        "hazard_visual": true,
        "tts_text": "Ô tô bên phải có xu hướng nhập làn. Hãy chú ý",
        "fsm_state": "cut_in_warning_right"
      },
      "root_cause_subsystem": "Layer3_Maneuver_FSM",
      "remediation_rule": "If longitudinal velocity v_long > 0 and heading is parallel within ±30 deg of ego lane, classify strictly as cut_in (right-to-left), NOT cross_traffic."
    },
    {
      "case_id": "TC-RW-V5-04",
      "source_video": "test_video5.mp4",
      "timestamp_seconds": 0.18,
      "scenario": "Dual-lane highway: Inner lane limit = 60 km/h, Outer (ego) lane limit = 80 km/h",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Đã phát hiện biển giới hạn 60km/h",
        "fault_type": "LANE_SPECIFIC_SIGN_MISASSOCIATION"
      },
      "expected_behavior": {
        "hazard_visual": true,
        "tts_text": "Đã phát hiện biển giới hạn 80km/h",
        "active_speed_limit_kph": 80
      },
      "root_cause_subsystem": "Sign_To_Lane_Association_Engine",
      "remediation_rule": "Map sign horizontal coordinate X_sign to ego lane boundary polynomial. Signs mounted over or assigned to non-ego lanes must not override active ego speed limit."
    },
    {
      "case_id": "TC-RW-V5-05",
      "source_video": "test_video5.mp4",
      "timestamp_seconds": 0.33,
      "scenario": "Passenger car in innermost lane beyond solid divider",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Xe tải phía trước bên phải có xu hướng nhập làn",
        "fault_type": "CLASS_FLICKER_AND_SOLID_DIVIDER_CUT_IN_FALSE_POSITIVE"
      },
      "expected_behavior": {
        "hazard_visual": false,
        "tts_text": null,
        "object_class": "car",
        "suppression": "SOLID_DIVIDER_SUPPRESSION"
      },
      "root_cause_subsystem": "Layer1_Classifier_And_Layer3_Geometry_Gate",
      "remediation_rule": "1. Apply temporal majority voting for object class over 5-frame window. 2. Inhibit cut-in warnings if solid unbroken lane markings exist between target object and ego lane."
    },
    {
      "case_id": "TC-RW-V5-06",
      "source_video": "test_video5.mp4",
      "timestamp_seconds": 0.37,
      "scenario": "Car 10-15m ahead in right adjacent lane initiates cut-in into ego lane",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Ô tô đang cắt ngang từ phải sang trái phía trước. Hãy chú ý",
        "fault_type": "MANEUVER_TYPE_CONFUSION"
      },
      "expected_behavior": {
        "hazard_visual": true,
        "tts_text": "Ô tô bên phải có xu hướng nhập làn. Hãy chú ý",
        "fsm_state": "cut_in_right"
      },
      "root_cause_subsystem": "Layer3_FSM_Maneuver_Classifier",
      "remediation_rule": "Threshold on aspect ratio of trajectory (dx/dy). If dy >> dx, maneuver is cut_in, not cross_traffic."
    },
    {
      "case_id": "TC-RW-FALL-01",
      "source_video": "video_test.mp4",
      "timestamp_seconds": 0.13,
      "scenario": "Motorcyclist cuts in from left, remains in frame >= 2s, then falls down onto road",
      "observed_behavior": {
        "hazard_visual": true,
        "tts_text": "Người đi bộ phía trước bên trái có xu hướng nhập làn",
        "object_label": "#12 person 0.72 active",
        "fault_type": "FALLEN_RIDER_UNRECOGNIZED_AND_CLASS_ERROR"
      },
      "expected_behavior": {
        "hazard_visual": true,
        "tts_text": "Cảnh báo: Có người và phương tiện ngã phía trước!",
        "object_label": "fallen_rider / fallen_person + fallen_two_wheeler",
        "fsm_state": "fallen_rider_event"
      },
      "root_cause_subsystem": "Layer1_Specialist_Detector_And_Layer3_FSM",
      "remediation_rule": "1. Maintain dual-class detection (fallen_person, fallen_two_wheeler). 2. When tracking rider transitioning from vertical to horizontal aspect ratio (W/H > 1.2) with rapid deceleration, trigger fallen_rider temporal event."
    },
    {
      "case_id": "TC-RW-FCW-REGRESS-01",
      "source_video": "test_video1.mp4",
      "timestamp_seconds": 0.18,
      "scenario": "Ego vehicle hard braking behind stopped lead vehicle to ~30cm proximity",
      "observed_behavior": {
        "hazard_visual": false,
        "hazard_audio_beep": false,
        "tts_text": null,
        "fault_type": "CRITICAL_FCW_SAFETY_REGRESSION_SILENT_FAILURE"
      },
      "expected_behavior": {
        "hazard_visual": true,
        "hazard_audio_beep": true,
        "tts_text": "Cảnh báo va chạm phía trước!",
        "fsm_state": "fcw_critical_level_3",
        "bounding_box_style": "RED_FLASHING"
      },
      "root_cause_subsystem": "Layer3_FCW_Engine_And_Audio_Router",
      "remediation_rule": "Audit FCW trigger logic: 1. Fix TTC zero-crossing / NaN during high ego deceleration. 2. Implement proximity fail-safe: If bbox area > threshold_emergency (e.g. distance < 1.0m), force level-3 FCW alert regardless of TTC calculation."
    }
  ]
}
```

---

## 3. Detailed Technical Defect Analysis & Fix Strategies

### 3.1. Layer 3 Decision / FSM: Direction & Maneuver Logic
- **Current Defect:**
  The system evaluates the object's orientation angle in the camera plane without grounding it in the ego vehicle's coordinate frame ($X_{lat}, Y_{long}$).
  - When an object is at $X > 0$ (right side) and moves toward $X = 0$, its lateral displacement $\Delta X < 0$ (right to left). However, if the vehicle yaw is angled leftwards, the system naively emits `"left_to_right"`.
  - Static objects with non-zero yaw angles trigger cross-traffic alerts even with zero ground displacement.
- **Remediation Specification:**
  1. Compute relative velocity vector $\vec{V}_{rel} = [\dot{X}, \dot{Y}]$.
  2. Require displacement threshold: $\sqrt{\Delta X^2 + \Delta Y^2} \ge 1.0\text{ m}$ over a rolling window $N = 5$ frames.
  3. Differentiate **Cut-In** vs. **Cross-Traffic**:
     $$\text{If } |\dot{Y}| > 2.0 \cdot |\dot{X}| \text{ and } \text{angle}(\vec{V}_{obj}, \vec{V}_{ego}) < 35^\circ \implies \mathbf{Cut\text{-}In}$$
     $$\text{If } |\dot{X}| > 1.5\text{ m/s} \text{ and } \text{angle}(\vec{V}_{obj}, \vec{V}_{ego}) \in [45^\circ, 135^\circ] \implies \mathbf{Cross\text{-}Traffic}$$

---

### 3.2. Layer 2 Lane Geometry: Opposing Traffic Isolation
- **Current Defect:**
  When lane markings are faded or missing, the ego lane boundary polynomial expands across oncoming traffic lanes. Oncoming cars stopped at red lights or proceeding normally are evaluated inside the ego corridor.
- **Remediation Specification:**
  1. Integrate optical flow direction / motion vector sign:
     - Oncoming traffic has expanding optical flow vectors directed away from the vanishing point.
  2. Implement an **Oncoming Traffic Suppressor**:
     - If tracked object's heading vector $\theta_{heading} \approx 180^\circ \pm 30^\circ$ relative to ego forward vector, flag as `is_oncoming = true`.
     - Suppress `cut_in` and `cross_traffic` state transitions for all objects flagged `is_oncoming = true` unless their lateral trajectory breaches the ego center line.

---

### 3.3. Traffic Sign Engine: Rear-Facing Filter & Lane-Specific Assignment
- **Current Defect:**
  1. The sign detector fires high-confidence detections on the non-informative metallic/gray rear casing of signs facing the other direction.
  2. Multiple overhead/roadside signs with different speed limits across multiple lanes (e.g. 60 km/h lane 1 vs 80 km/h lane 2) are not resolved to the ego vehicle's current lane.
- **Remediation Specification:**
  1. **Rear-Facing Sign Filter:**
     - Add a binary orientation/texture verification head to the sign detector.
     - Require valid icon/numeric semantic parsing before activating HMI TTS.
  2. **Lane-to-Sign Spatial Binding:**
     - Calculate sign lateral anchor $X_{sign}$ relative to ego lane boundary lines $L_{left}(y), L_{right}(y)$.
     - Only assign speed limit if $L_{left}(y_{sign}) \le X_{sign} \le L_{right}(y_{sign})$ or if the sign is a global right-shoulder roadside sign with no conflicting lane-overhead gantries.

---

### 3.4. Fallen Rider & VRU Detection
- **Current Defect:**
  A motorcyclist cutting in and subsequently falling on the roadway is tracked merely as `#12 person` with a generic cut-in warning. The fall event itself triggers zero specialized safety escalation.
- **Remediation Specification:**
  1. Maintain separate detector classes: `fallen_person`, `fallen_two_wheeler`.
  2. Implement the **Fallen Rider Temporal Event FSM**:
     $$\text{rider\_normal} \xrightarrow{\text{instability / yaw drop}} \text{fall\_transition} \xrightarrow{\Delta H_{box} < 0, W/H > 1.2} \text{fallen\_persistent}$$
  3. High-priority TTS alert triggered upon entering `fallen_persistent`: `"Cảnh báo: Có người và phương tiện ngã phía trước!"`.

---

### 3.5. Critical Safety Regression: FCW Proximity Deadband (P0)
- **Current Defect:**
  At ~30cm distance behind a lead vehicle under severe deceleration, the system produces no audible alarm, visual red hazard box, or TTS warning.
- **Remediation Specification:**
  1. **TTC Calculation Audit:**
     - Formula: $\text{TTC} = \frac{D_{rel}}{-V_{rel}}$.
     - Ensure $V_{rel} \to 0$ or heavy ego deceleration does not cause division by zero, NaN, or negative suppression of warning states.
  2. **Emergency Distance Gate (Fail-Safe Override):**
     $$\text{If } D_{rel} \le 1.5\text{ m} \text{ or } \text{BBox\_Area\_Ratio} \ge 0.35 \implies \mathbf{Force\_Alert}(\text{FCW\_LEVEL\_3})$$
     - Bypasses any TTS cooldowns, lane geometry uncertainties, or model score gates.

---

## 4. Verification & Acceptance Criteria Matrix

| Test Case | Metric / Assertion | Acceptance Threshold |
|---|---|:---:|
| `TC-RW-NIGHT-01` | Direction Accuracy on Right-side VRU | 100% correct direction (`right_to_left` or `front_right`) |
| `TC-RW-NIGHT-02` | False Alarm Rate on Oncoming Stopped Vehicles | 0 false alarms / min |
| `TC-RW-NIGHT-03` | False Alarm Rate on Stationary Parked Vehicles | 0 false alarms / min |
| `TC-RW-V5-01` | Rear-Facing Sign Suppression Rate | 100% rejection (0 false TTS) |
| `TC-RW-V5-04` | Lane-Specific Speed Limit Match Accuracy | Match active ego lane limit (80 km/h) |
| `TC-RW-FALL-01` | Fallen Rider Detection & Escalation | `fallen_rider` FSM event emitted within $\le 500\text{ ms}$ of fall |
| `TC-RW-FCW-REGRESS-01` | FCW Alert Triggering at Proximity $\le 1.0\text{ m}$ | 100% trigger rate (0 silent failures) |
