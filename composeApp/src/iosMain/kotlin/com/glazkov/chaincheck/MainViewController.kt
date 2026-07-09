package com.glazkov.chaincheck

import androidx.compose.ui.window.ComposeUIViewController
import com.glazkov.chaincheck.data.ChainCheckApi
import com.glazkov.chaincheck.data.Repository
import com.glazkov.chaincheck.ui.App
import com.russhwolf.settings.NSUserDefaultsSettings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import platform.Foundation.NSUserDefaults

private val repository by lazy {
    Repository(
        api = ChainCheckApi(),
        settings = NSUserDefaultsSettings(NSUserDefaults.standardUserDefaults),
        scope = CoroutineScope(SupervisorJob() + Dispatchers.Main),
    ).also { it.start() }
}

@Suppress("unused", "FunctionName")
fun MainViewController() = ComposeUIViewController { App(repository) }
