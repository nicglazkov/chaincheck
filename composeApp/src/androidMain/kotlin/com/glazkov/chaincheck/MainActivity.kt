package com.glazkov.chaincheck

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.glazkov.chaincheck.push.NotificationPermission
import com.glazkov.chaincheck.ui.App

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        NotificationPermission.register(this)
        val repository = (application as ChainCheckApp).repository
        setContent { App(repository) }
    }
}
