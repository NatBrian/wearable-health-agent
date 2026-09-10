plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.chaquo.python")
}

android {
    namespace = "dev.wha.app"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.wha.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        ndk { abiFilters += listOf("arm64-v8a") }
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        pip {
            // Our own Android wheels first (Task 2), then Chaquopy's index and PyPI.
            options("--find-links", file("../wheels").absolutePath)
            // Smoke only: the real requirement list arrives in Task 11.
            // No scipy: the only scipy import in src/wha is eval/metrics.py
            // (beta.ppf for confidence intervals), and wha.eval is PC-only,
            // so the phone never needs it. Chaquopy's index has no scipy
            // wheel for Python 3.11 or later in any case.
            install("numpy")
            install("pandas")
            install("lxml")
            install("pyyaml")
            install("pydantic==2.13.5")
            install("pydantic-core==2.46.5")
            install("orjson==3.12.0")
            install("ormsgpack==1.12.2")
            install("xxhash==4.0.1")
            // uuid-utils was missed by the Task 2 wheel analysis: langchain-core
            // and langsmith both need it, and it is Rust with no Chaquopy wheel.
            install("uuid-utils==0.17.0")
            // langgraph itself, without langgraph-checkpoint-sqlite, whose declared
            // sqlite-vec dependency has no Android build and is never imported (see
            // android/wheels/BUILD.md). Task 11 installs the checkpointer with --no-deps.
            install("langgraph==1.2.11")
        }
    }
    sourceSets { getByName("main") { srcDir("src/main/python") } }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.core:core-ktx:1.15.0")
}
