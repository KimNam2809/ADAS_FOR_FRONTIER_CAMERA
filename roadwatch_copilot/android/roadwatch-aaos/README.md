# RoadWatch AAOS shell

This module wraps the local RoadWatch React HMI in an Android Automotive WebView.
It is warning-only and has no steering, braking, throttle or CAN-write code.

## Emulator workflow

1. Start the Automotive emulator in Android Studio.
2. From the RoadWatch root, run `powershell -ExecutionPolicy Bypass -File scripts/configure_aaos_emulator.ps1`.
   This creates `adb reverse tcp:8000 tcp:8000` and sets mock GPS to TP.HCM
   (`10.7769, 106.7009`). The emulator command requires longitude before latitude.
3. Start RoadWatch on Windows with `powershell -ExecutionPolicy Bypass -File scripts/start.ps1`.
4. In Android Studio, open `android/roadwatch-aaos`, select the Automotive emulator and run `app`.

The WebView first uses `http://127.0.0.1:8000` through the ADB reverse tunnel,
then falls back to `http://10.0.2.2:8000`. Both URLs are deliberately HTTP for
local development. If an installed app shows `https://10.0.2.2:8000`, uninstall
the stale APK or use **Build > Clean Project**, then run the current app again.

The GPS visible in the AAOS launcher/maps belongs to the emulator, not to
RoadWatch. Re-run `configure_aaos_emulator.ps1` after an emulator data wipe or
after creating a new Automotive Virtual Device. A cold boot may be needed for a
system map application to refresh its cached camera position.

Replay controls are served by the shared RoadWatch backend and React HMI. The
AAOS WebView therefore receives the same elapsed/total time, pause/resume,
seek ±10 seconds, timeline scrubber and restart controls as the desktop web UI.

`MockVehicleAdapter` emits read-only speed/gear telemetry to the WebView as the
`roadwatch-vehicle-telemetry` browser event. It intentionally does not claim to
be a VinFast or production VHAL integration.

The development network policy permits cleartext localhost traffic. Replace it
with TLS or an isolated in-vehicle network policy before any vehicle deployment.
