from roadwatch.signs import (
    is_speed_limit_label,
    minimum_speed_value,
    policy_for_label,
    speed_value,
)


def test_highway_speed_taxonomy_parses_maximum_and_minimum() -> None:
    assert speed_value("speed_limit_max_100") == 100
    assert minimum_speed_value("speed_limit_min_60") == 60
    assert is_speed_limit_label("speed_limit_max")
    assert is_speed_limit_label("speed_limit_min")


def test_highway_restriction_labels_require_explicit_classes() -> None:
    assert policy_for_label("no_trucks").message == "Cấm xe tải."
    assert policy_for_label("no_buses").message == "Cấm xe buýt."
    assert policy_for_label("no_vehicles").kind == "prohibition"
