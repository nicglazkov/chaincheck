package com.glazkov.chaincheck.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.glazkov.chaincheck.data.Repository
import com.glazkov.chaincheck.push.currentPushToken
import com.glazkov.chaincheck.push.requestNotificationPermission

@Composable
fun AlertsScreen(repository: Repository, modifier: Modifier = Modifier) {
    val state by repository.home.collectAsState()
    val corridors = state.summary?.corridors ?: emptyList()
    var watched by remember { mutableStateOf(repository.watchedCorridors) }
    var pushToken by remember { mutableStateOf<String?>(null) }
    var saved by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        requestNotificationPermission()
        pushToken = currentPushToken()
    }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("Alerts", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Watch a route to get a push the moment its chain control tier changes, " +
                "a closure goes up, or a winter storm warning lands on its pass. " +
                "Only your watched routes - never anything promotional.",
            style = MaterialTheme.typography.bodyMedium,
        )

        if (pushToken == null) {
            Text(
                "Push isn't available on this device yet (no notification permission " +
                    "or no Play services). Choices are saved locally.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error,
            )
        }

        corridors.forEach { corridor ->
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Checkbox(
                    checked = corridor.id in watched,
                    onCheckedChange = { checked ->
                        watched = if (checked) watched + corridor.id else watched - corridor.id
                        saved = false
                    },
                )
                Column {
                    Text(corridor.name)
                    Text(
                        corridor.description,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        Button(
            onClick = {
                repository.saveWatched(watched, pushToken)
                saved = true
            },
            modifier = Modifier.padding(top = 8.dp),
        ) { Text(if (saved) "Saved" else "Save alerts") }
    }
}
