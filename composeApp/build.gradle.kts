import java.util.Properties
import org.jetbrains.kotlin.gradle.ExperimentalKotlinGradlePluginApi
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

fun Project.localPropsValue(key: String): String? {
    val file = rootProject.file("local.properties")
    if (!file.exists()) return null
    val props = Properties()
    file.inputStream().use { props.load(it) }
    return props.getProperty(key)
}

plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.androidApplication)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
    alias(libs.plugins.kotlinSerialization)
    alias(libs.plugins.googleServices) apply false
    alias(libs.plugins.crashlytics) apply false
}

// google-services.json is machine-local (never committed); CI builds without
// Firebase config, dev machines with one get the real FCM and Crashlytics
// wiring.
if (file("google-services.json").exists()) {
    apply(plugin = libs.plugins.googleServices.get().pluginId)
    apply(plugin = libs.plugins.crashlytics.get().pluginId)
}

kotlin {
    androidTarget {
        @OptIn(ExperimentalKotlinGradlePluginApi::class)
        compilerOptions {
            jvmTarget.set(JvmTarget.JVM_11)
        }
    }

    listOf(
        iosArm64(),
        iosSimulatorArm64(),
    ).forEach { iosTarget ->
        iosTarget.binaries.framework {
            baseName = "ComposeApp"
            isStatic = true
        }
    }

    sourceSets {
        commonMain.dependencies {
            implementation(compose.runtime)
            implementation(compose.foundation)
            implementation(compose.material3)
            implementation(compose.materialIconsExtended)
            implementation(compose.ui)
            implementation(compose.components.resources)
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.kotlinx.datetime)
            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.serialization.kotlinx.json)
            implementation(libs.multiplatform.settings)
            implementation(libs.coil.compose)
            implementation(libs.coil.network.ktor3)
        }
        commonTest.dependencies {
            implementation(libs.kotlin.test)
        }
        androidMain.dependencies {
            implementation(libs.androidx.activity.compose)
            // The ActivityResult permission launcher needs fragment >= 1.3;
            // an ancient one arrives transitively and lintVital rightly
            // fails the release build without this pin.
            implementation(libs.androidx.fragment)
            implementation(libs.kotlinx.coroutines.android)
            implementation(libs.kotlinx.coroutines.play.services)
            implementation(libs.ktor.client.okhttp)
            implementation(libs.firebase.messaging)
            implementation(libs.firebase.crashlytics)
            implementation(libs.firebase.appcheck.playintegrity)
            implementation(libs.maps.compose)
            implementation(libs.play.services.maps)
            implementation(libs.play.services.location)
        }
        iosMain.dependencies {
            implementation(libs.ktor.client.darwin)
        }
    }
}

android {
    namespace = "com.glazkov.chaincheck"
    compileSdk = libs.versions.android.compileSdk.get().toInt()

    defaultConfig {
        applicationId = "com.glazkov.chaincheck"
        minSdk = libs.versions.android.minSdk.get().toInt()
        targetSdk = libs.versions.android.targetSdk.get().toInt()
        versionCode = 3
        versionName = "0.1.2"
        // Android-restricted (package+cert) key from local.properties on dev
        // machines or the environment in the release workflow; PR CI builds
        // with an empty value and the map simply doesn't render there.
        val localProps = Properties()
        val localFile = rootProject.file("local.properties")
        if (localFile.exists()) {
            localFile.inputStream().use { stream -> localProps.load(stream) }
        }
        manifestPlaceholders["MAPS_API_KEY"] =
            localProps.getProperty("MAPS_API_KEY")
                ?: System.getenv("MAPS_API_KEY")
                ?: ""
    }
    // Release signing comes from the environment (release workflow) or
    // local.properties (this machine); the keystore itself never enters the
    // repo. Absent config leaves release builds unsigned, which is fine for
    // PR CI where only assembleDebug runs.
    val keystorePath = System.getenv("CHAINCHECK_KEYSTORE")
        ?: (rootProject.file("local.properties").takeIf { it.exists() }?.let {
            val props = Properties()
            it.inputStream().use { s -> props.load(s) }
            props.getProperty("CHAINCHECK_KEYSTORE")
        })
    if (keystorePath != null) {
        signingConfigs {
            create("release") {
                storeFile = file(keystorePath)
                storePassword = System.getenv("CHAINCHECK_KEYSTORE_PASSWORD")
                    ?: localPropsValue("CHAINCHECK_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("CHAINCHECK_KEY_ALIAS")
                    ?: localPropsValue("CHAINCHECK_KEY_ALIAS") ?: "chaincheck"
                keyPassword = System.getenv("CHAINCHECK_KEY_PASSWORD")
                    ?: localPropsValue("CHAINCHECK_KEY_PASSWORD")
            }
        }
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
    buildFeatures {
        buildConfig = true
    }
    buildTypes {
        getByName("debug") {
            // Dev override: ./gradlew installDebug -PchaincheckBaseUrl=http://10.0.2.2:8000
            val devUrl = (project.findProperty("chaincheckBaseUrl") as String?) ?: ""
            buildConfigField("String", "BASE_URL_OVERRIDE", "\"$devUrl\"")
        }
        getByName("release") {
            // Unminified on purpose for the sideload channel: no R8 risk and
            // crash stack traces need no mapping file. Revisit for the store
            // build in October.
            isMinifyEnabled = false
            buildConfigField("String", "BASE_URL_OVERRIDE", "\"\"")
            signingConfig = signingConfigs.findByName("release")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}
