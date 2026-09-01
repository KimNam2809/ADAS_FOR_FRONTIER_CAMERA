from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"


def _app_source() -> str:
    """The dashboard moved out of main.tsx when the P-162 landing route was added."""
    return "\n".join(
        (
            (FRONTEND / "main.tsx").read_text(encoding="utf-8"),
            (FRONTEND / "RoadWatchApp.tsx").read_text(encoding="utf-8"),
        )
    )


def test_video_viewport_has_explicit_aspect_ratio_contract() -> None:
    source = _app_source()
    styles = (FRONTEND / "styles.css").read_text(encoding="utf-8")

    assert 'data-aspect-ratio="16:9"' in source
    assert "aspect-ratio: 16 / 9" in styles
    assert "object-fit: contain" in styles
    assert "object-fit: cover" not in styles


def test_engineer_event_history_is_part_of_the_screen_contract() -> None:
    source = _app_source()

    assert "function EventHistory" in source
    assert "event-history-panel" in source
    assert "api.seek(token, event.source_time)" in source


def test_approved_screen_order_and_role_restore_are_present() -> None:
    source = _app_source()
    driver = source[source.index("function DriverHUD"):source.index("function EventRibbon")]
    engineer = source[source.index("function EngineerConsole"):source.index("export default function RoadWatchApp")]

    assert driver.index("<ScreenIdentity") < driver.index("<VideoStage") < driver.index("<SessionControls")
    assert engineer.index("<ScreenIdentity") < engineer.index("<div className=\"metrics-row\"") < engineer.index("<VideoStage") < engineer.index("<SessionControls")
    assert 'localStorage.getItem("roadwatch_user")' in source
    assert 'useState<"driver" | "engineer">' in source
    assert "function Header" not in source


def test_local_start_prefers_current_ui_bundle_before_legacy_dist() -> None:
    source = (ROOT / "scripts" / "start.ps1").read_text(encoding="utf-8")

    assert 'frontend\\dist-ui-v4' in source
    assert 'frontend\\dist-ui-v3' in source
    assert 'frontend\\dist-ui-v2' in source
    assert source.index('frontend\\dist-ui-v4') < source.index('frontend\\dist-ui-v3')
    assert source.index('frontend\\dist-ui-v3') < source.index('frontend\\dist-ui-v2')
    assert source.index('frontend\\dist-ui-v2') < source.index('frontend\\dist-local')
    assert 'FrontendDist' in source
    assert 'stale' in source


def test_demo_start_enables_traffic_context_v1_without_environment_setup() -> None:
    source = (ROOT / "scripts" / "start.ps1").read_text(encoding="utf-8")
    config = (ROOT / "configs" / "default.json").read_text(encoding="utf-8")

    assert '[string]$TrafficContextMode = "enforce"' in source
    assert '[ValidateSet("off", "shadow", "enforce")]' in source
    assert '$env:ROADWATCH_TRAFFIC_CONTEXT_MODE = $TrafficContextMode' in source
    assert '"mode": "enforce"' in config


def test_direct_api_start_prefers_current_ui_bundle_before_legacy_dist() -> None:
    source = (ROOT / "backend" / "roadwatch" / "api.py").read_text(encoding="utf-8")

    assert 'PROJECT_ROOT / "frontend" / "dist-ui-v4"' in source
    assert 'PROJECT_ROOT / "frontend" / "dist-ui-v3"' in source
    assert 'PROJECT_ROOT / "frontend" / "dist-ui-v2"' in source
    assert source.index('PROJECT_ROOT / "frontend" / "dist-ui-v4"') < source.index(
        'PROJECT_ROOT / "frontend" / "dist-ui-v3"'
    )
    assert source.index('PROJECT_ROOT / "frontend" / "dist-ui-v3"') < source.index(
        'PROJECT_ROOT / "frontend" / "dist-ui-v2"'
    )


def test_audio_has_single_output_owner_contract() -> None:
    source = _app_source()
    api_source = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    start = (ROOT / "scripts" / "start.ps1").read_text(encoding="utf-8")

    assert 'output_owner ?? (status.audio.enabled ? "server" : "browser")' in source
    assert 'outputOwner !== "browser"' in source
    assert 'output_owner?: "server" | "browser" | "none"' in api_source
    assert '[string]$AudioOwner = "browser"' in start
    assert '$env:ROADWATCH_AUDIO_OUTPUT = $AudioOwner' in start
    assert '$env:ROADWATCH_TTS_CACHE_NAMESPACE = "piper-v3"' in start


def test_browser_tts_activation_and_retry_contract_is_present() -> None:
    source = _app_source()
    start = (ROOT / "scripts" / "start.ps1").read_text(encoding="utf-8")

    assert "activate: () => Promise<boolean>" in source
    assert "await context.resume()" in source
    assert "onActivateAudio={browserAudio.activate}" in source
    assert "inFlightEvents.current" in source
    assert "retryAt.current.set(eventKey" in source
    assert '$env:ROADWATCH_DISABLE_AUDIO = "0"' in start


def test_traffic_context_ui_and_context_beep_contract_is_present() -> None:
    source = _app_source()
    api_source = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    styles = (FRONTEND / "styles.css").read_text(encoding="utf-8")

    assert "traffic_context" in api_source
    assert "GIAO THÔNG ĐÔNG" in source
    assert "CẢNH BÁO CHỌN LỌC" in source
    assert "ROADWATCH ALERT CONTEXT V1" in source
    assert '"context_beep"' in source
    assert "display_scope" in source
    assert ".hud-context-card" in styles


def test_hud_uses_real_assets_and_dynamic_track_telemetry() -> None:
    source = _app_source()
    styles = (FRONTEND / "styles.css").read_text(encoding="utf-8")

    assert 'src="/hud/ego-car.png"' in source
    assert "hud-track-sprite" in source
    assert "projected_x_norm" in source
    assert "proximity_score" in source
    assert ".slice(0, 5)" in source
    assert "hud-lane-center" not in source
    assert "hud-lane-center" not in styles
    assert 'className="hud-ego"' not in source


def test_hud_assets_are_small_transparent_runtime_images() -> None:
    from PIL import Image

    hud = ROOT / "frontend" / "public" / "hud"
    expected = {
        "ego-car.png",
        "traffic-car.png",
        "traffic-truck.png",
        "traffic-motorcycle.png",
        "traffic-person.png",
        "traffic-bicycle.png",
    }
    assert {item.name for item in hud.glob("*.png")} == expected
    for name in expected:
        path = hud / name
        assert path.stat().st_size < 160_000
        with Image.open(path) as image:
            assert image.mode == "RGBA"
            assert max(image.size) <= 360
            assert image.getchannel("A").getextrema()[0] == 0


def test_roadwatch_brand_is_limited_to_login_and_startup_surfaces() -> None:
    source = _app_source()
    identity = source[source.index("function ScreenIdentity"):source.index("const HudPanel")]

    assert 'className="brand-lockup hero-brand"' in source
    assert "RoadWatchBrand" not in source
    assert "brand-lockup" not in identity
