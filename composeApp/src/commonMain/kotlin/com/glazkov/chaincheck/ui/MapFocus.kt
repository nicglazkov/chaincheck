package com.glazkov.chaincheck.ui

/** A point the map should fly to; carried when any list row is tapped. */
data class MapFocus(
    val lat: Double,
    val lon: Double,
    val zoom: Float = 11f,
    val label: String? = null,
)

/** Which marker layers are visible; keeps the map readable, not pin soup. */
data class MapLayers(
    val roads: Boolean = true,   // controls + closures + incidents
    val webcams: Boolean = true,
    val resorts: Boolean = true,
)
