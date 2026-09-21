import importlib.util
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def load(relative):
    spec = importlib.util.spec_from_file_location("candidate_test_module", ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_audit_canonical_nested_labels(tmp_path):
    module = load("kaggle/train_sign_highway_v1/roadwatch_train_sign_highway_v1.py")
    (tmp_path / "labels/train").mkdir(parents=True)
    (tmp_path / "labels/train/a.txt").write_text("0 0.5 0.5 0.2 0.2\n1 0.5 0.5 0.1 0.1\n")
    path = tmp_path / "data.yaml"
    path.write_text(yaml.safe_dump({"names": {0: "speed_limit_max", 1: "speed_limit_min"}}))
    assert module.audit_dataset(path, "minimum_speed")["pass"]
    assert not module.audit_dataset(path, "highway_full")["pass"]
    (tmp_path / "labels/train/a.txt").write_text("1 NaN 0.5 0.1 0.1\n")
    assert not module.audit_dataset(path, "minimum_speed")["pass"]

def test_scene_derivatives_stay_together():
    module = load("kaggle/build_minimum_speed_public_v1/script.py")
    assert module.split_for("tt100k", Path("images/train/10013.jpg")) == module.split_for("tt100k", Path("images/val/10013 (2).jpg"))

def test_minimum_taxonomy_excludes_weight():
    source = (ROOT / "kaggle/build_minimum_speed_public_v1/script.py").read_text()
    assert 're.fullmatch(r"il\\d+", name)' in source
    assert 're.fullmatch(r"pm\\d+", name)' not in source
