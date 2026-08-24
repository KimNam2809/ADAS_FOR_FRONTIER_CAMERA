plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "vn.roadwatch.aaos"
    compileSdk = 35

    defaultConfig {
        applicationId = "vn.roadwatch.aaos"
        minSdk = 28
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        // Primary path uses `adb reverse`, which works even when RoadWatch is
        // bound to host loopback. The emulator gateway remains a fallback.
        buildConfigField("String", "ROADWATCH_URL", "\"http://127.0.0.1:8000\"")
        buildConfigField("String", "ROADWATCH_FALLBACK_URL", "\"http://10.0.2.2:8000\"")
    }
    buildFeatures { buildConfig = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
}
