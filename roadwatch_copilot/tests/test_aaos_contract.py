from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AAOS = ROOT / "android/roadwatch-aaos"


def test_aaos_manifest_is_warning_only() -> None:
    manifest = (AAOS / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    assert "android.hardware.type.automotive" in manifest
    assert "distractionOptimized\" android:value=\"false" in manifest
    assert "BLUETOOTH" not in manifest
    assert "CAR_CONTROL" not in manifest


def test_aaos_uses_emulator_host_and_read_only_mock_vhal() -> None:
    gradle = (AAOS / "app/build.gradle.kts").read_text(encoding="utf-8")
    telemetry = (AAOS / "app/src/main/java/vn/roadwatch/aaos/VehicleTelemetry.kt").read_text(
        encoding="utf-8"
    )
    assert "127.0.0.1:8000" in gradle
    assert "10.0.2.2:8000" in gradle
    assert "mock_vhal_read_only" in telemetry
    assert "read_only" in telemetry


def test_aaos_setup_configures_reverse_tunnel_and_vietnam_gps() -> None:
    setup = (ROOT / "scripts/configure_aaos_emulator.ps1").read_text(encoding="utf-8")
    assert 'reverse "tcp:$Port" "tcp:$Port"' in setup
    assert "10.7769" in setup
    assert "106.7009" in setup
    assert "geo fix $Longitude $Latitude" in setup
