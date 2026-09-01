from roadwatch.vehicle_io import DisabledVehicleAdapter


def test_vehicle_adapter_is_read_only_and_has_no_actuator_api() -> None:
    adapter = DisabledVehicleAdapter()
    assert adapter.status()["read_only"] is True
    assert adapter.status()["actuator_api"] is False
    assert adapter.read().speed_kph is None
    assert not hasattr(adapter, "brake")
    assert not hasattr(adapter, "steer")
