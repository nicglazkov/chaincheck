package com.glazkov.chaincheck.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Article
import androidx.compose.material.icons.filled.AcUnit
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Route
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.glazkov.chaincheck.data.Repository

enum class Tab(val label: String) {
    Home("Home"),
    Routes("Routes"),
    Resorts("Resorts"),
    Brief("Brief"),
    Alerts("Alerts"),
}

const val DISCLAIMER_TEXT =
    "ChainCheck shows official Caltrans, CHP, and NWS data but is not affiliated " +
        "with any government agency. Conditions change faster than any app; verify " +
        "before you drive (dial 511 or check quickmap.dot.ca.gov). Whether it is " +
        "safe to drive is always your decision."

@Composable
fun App(repository: Repository) {
    ChainCheckTheme {
        var tab by remember { mutableStateOf(Tab.Home) }
        var openCorridor by remember { mutableStateOf<String?>(null) }
        var disclaimerSeen by remember { mutableStateOf(repository.disclaimerAccepted) }

        if (!disclaimerSeen) {
            AlertDialog(
                onDismissRequest = {},
                title = { Text("Before you drive") },
                text = { Text(DISCLAIMER_TEXT) },
                confirmButton = {
                    TextButton(onClick = {
                        repository.disclaimerAccepted = true
                        disclaimerSeen = true
                    }) { Text("I understand") }
                },
            )
        }

        Scaffold(
            bottomBar = {
                NavigationBar {
                    Tab.entries.forEach { item ->
                        NavigationBarItem(
                            selected = tab == item,
                            onClick = {
                                tab = item
                                openCorridor = null
                            },
                            icon = {
                                Icon(
                                    when (item) {
                                        Tab.Home -> Icons.Filled.Home
                                        Tab.Routes -> Icons.Filled.Route
                                        Tab.Resorts -> Icons.Filled.AcUnit
                                        Tab.Brief -> Icons.AutoMirrored.Filled.Article
                                        Tab.Alerts -> Icons.Filled.Notifications
                                    },
                                    contentDescription = item.label,
                                )
                            },
                            label = { Text(item.label) },
                        )
                    }
                }
            },
        ) { padding ->
            val modifier = Modifier.padding(padding)
            when {
                openCorridor != null -> RouteDetailScreen(
                    corridorId = openCorridor!!,
                    repository = repository,
                    onBack = { openCorridor = null },
                    modifier = modifier,
                )

                tab == Tab.Home -> HomeScreen(
                    repository = repository,
                    onOpenRoute = { openCorridor = it },
                    modifier = modifier,
                )

                tab == Tab.Routes -> RoutesScreen(
                    repository = repository,
                    onOpenRoute = { openCorridor = it },
                    modifier = modifier,
                )

                tab == Tab.Resorts -> ResortsScreen(repository, modifier)
                tab == Tab.Brief -> BriefScreen(repository, modifier)
                else -> AlertsScreen(repository, modifier)
            }
        }
    }
}
