package vn.roadwatch.aaos

data class VehicleTelemetry(
    val speedKph: Double,
    val gear: String,
    val source: String = "mock_vhal_read_only",
    val timestampMs: Long = System.currentTimeMillis(),
) {
    fun toJson(): String =
        """{"speed_kph":$speedKph,"gear":"$gear","source":"$source","timestamp_ms":$timestampMs,"read_only":true}"""
}

interface VehicleAdapter {
    fun read(): VehicleTelemetry
    fun status(): String
}

class MockVehicleAdapter : VehicleAdapter {
    override fun read() = VehicleTelemetry(speedKph = 0.0, gear = "P")
    override fun status() = "mock_vhal_read_only"
}
