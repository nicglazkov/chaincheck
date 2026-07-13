package com.glazkov.chaincheck

import android.app.Application
import com.glazkov.chaincheck.data.ChainCheckApi
import com.glazkov.chaincheck.data.Repository
import com.russhwolf.settings.Settings
import com.russhwolf.settings.SharedPreferencesSettings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

class ChainCheckApp : Application() {
    lateinit var repository: Repository
        private set

    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.BASE_URL_OVERRIDE.isNotBlank()) {
            com.glazkov.chaincheck.data.ApiConfig.override = BuildConfig.BASE_URL_OVERRIDE
        }
        installAppCheck()
        val settings: Settings = SharedPreferencesSettings(
            getSharedPreferences("chaincheck", MODE_PRIVATE)
        )
        repository = Repository(
            api = ChainCheckApi(),
            settings = settings,
            scope = CoroutineScope(SupervisorJob() + Dispatchers.Main),
        )
        repository.start()
    }

    /**
     * Install the Play Integrity App Check provider so backend calls carry an
     * attestation token. Guarded: a build without google-services.json has no
     * Firebase, and attestation is simply absent rather than a crash. The
     * backend runs in monitoring mode, so a missing token is never fatal.
     */
    private fun installAppCheck() {
        runCatching {
            if (com.google.firebase.FirebaseApp.getApps(this).isEmpty()) return
            com.google.firebase.appcheck.FirebaseAppCheck.getInstance()
                .installAppCheckProviderFactory(
                    com.google.firebase.appcheck.playintegrity
                        .PlayIntegrityAppCheckProviderFactory.getInstance()
                )
        }
    }
}
