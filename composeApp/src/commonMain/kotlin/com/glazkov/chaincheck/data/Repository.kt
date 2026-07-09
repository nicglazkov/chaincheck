package com.glazkov.chaincheck.data

import com.russhwolf.settings.Settings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/**
 * One shared state holder for everything the screens show.
 *
 * Offline resilience: the last good summary/resorts payloads are persisted
 * as JSON and rehydrated on start, so a dead-zone drive still shows state
 * with its honest "as of" timestamp instead of a blank screen.
 */
class Repository(
    private val api: ChainCheckApi,
    private val settings: Settings,
    private val scope: CoroutineScope,
) {
    data class HomeState(
        val summary: Summary? = null,
        val loading: Boolean = false,
        val error: String? = null,
        val fromCache: Boolean = false,
    )

    data class ResortsState(
        val resorts: List<ResortReport> = emptyList(),
        val loading: Boolean = false,
        val error: String? = null,
        val fromCache: Boolean = false,
    )

    private val _home = MutableStateFlow(HomeState())
    val home: StateFlow<HomeState> = _home

    private val _resorts = MutableStateFlow(ResortsState())
    val resorts: StateFlow<ResortsState> = _resorts

    val watchedCorridors: Set<String>
        get() = settings.getString(KEY_WATCHED, "").split(",").filter { it.isNotBlank() }.toSet()

    var disclaimerAccepted: Boolean
        get() = settings.getBoolean(KEY_DISCLAIMER, false)
        set(value) = settings.putBoolean(KEY_DISCLAIMER, value)

    var selectedCorridor: String
        get() = settings.getString(KEY_SELECTED, "i80")
        set(value) = settings.putString(KEY_SELECTED, value)

    fun start() {
        rehydrate()
        refreshHome()
        refreshResorts()
    }

    private fun rehydrate() {
        settings.getStringOrNull(KEY_SUMMARY)?.let { cached ->
            runCatching { ChainCheckApi.json.decodeFromString<Summary>(cached) }
                .onSuccess { _home.value = HomeState(summary = it, fromCache = true) }
        }
        settings.getStringOrNull(KEY_RESORTS)?.let { cached ->
            runCatching { ChainCheckApi.json.decodeFromString<ResortsResponse>(cached) }
                .onSuccess {
                    _resorts.value = ResortsState(resorts = it.resorts, fromCache = true)
                }
        }
    }

    fun refreshHome() {
        _home.value = _home.value.copy(loading = true, error = null)
        scope.launch {
            runCatching { api.summary() }
                .onSuccess { summary ->
                    _home.value = HomeState(summary = summary)
                    settings.putString(
                        KEY_SUMMARY, ChainCheckApi.json.encodeToString(Summary.serializer(), summary)
                    )
                }
                .onFailure { err ->
                    _home.value = _home.value.copy(
                        loading = false,
                        error = err.message ?: "network error",
                        fromCache = _home.value.summary != null,
                    )
                }
        }
    }

    fun refreshResorts() {
        _resorts.value = _resorts.value.copy(loading = true, error = null)
        scope.launch {
            runCatching { api.resorts() }
                .onSuccess { response ->
                    _resorts.value = ResortsState(resorts = response.resorts)
                    settings.putString(
                        KEY_RESORTS,
                        ChainCheckApi.json.encodeToString(ResortsResponse.serializer(), response),
                    )
                }
                .onFailure { err ->
                    _resorts.value = _resorts.value.copy(
                        loading = false,
                        error = err.message ?: "network error",
                        fromCache = _resorts.value.resorts.isNotEmpty(),
                    )
                }
        }
    }

    fun saveWatched(corridorIds: Set<String>, pushToken: String?) {
        settings.putString(KEY_WATCHED, corridorIds.joinToString(","))
        if (pushToken == null) return
        scope.launch {
            runCatching {
                if (corridorIds.isEmpty()) api.deleteSubscription(pushToken)
                else api.saveSubscription(pushToken, corridorIds.toList())
            }
        }
    }

    private companion object {
        const val KEY_SUMMARY = "cache.summary"
        const val KEY_RESORTS = "cache.resorts"
        const val KEY_WATCHED = "alerts.watched"
        const val KEY_DISCLAIMER = "disclaimer.accepted"
        const val KEY_SELECTED = "home.selected"
    }
}
