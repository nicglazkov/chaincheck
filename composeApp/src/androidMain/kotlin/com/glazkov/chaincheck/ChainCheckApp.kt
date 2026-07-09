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
}
