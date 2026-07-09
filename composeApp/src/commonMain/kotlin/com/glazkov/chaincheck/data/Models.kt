package com.glazkov.chaincheck.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class FeedHealth(
    val ok: Boolean = true,
    val stale: Boolean = false,
    @SerialName("as_of") val asOf: String? = null,
    val notes: List<String> = emptyList(),
)

@Serializable
data class CorridorSummary(
    val id: String,
    val name: String,
    val route: String,
    val description: String = "",
    val tier: Int = -1,
    @SerialName("tier_label") val tierLabel: String = "Unknown",
    @SerialName("tier_meaning") val tierMeaning: String = "",
    val controls: Int = 0,
    val closures: Int = 0,
    val incidents: Int = 0,
)

@Serializable
data class ControlPoint(
    val route: String = "",
    val direction: String = "",
    val location: String = "",
    val nearby: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    val status: String = "",
    val tier: Int = -1,
    @SerialName("tier_label") val tierLabel: String = "",
    val description: String = "",
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class ClosureItem(
    val route: String = "",
    val direction: String = "",
    val location: String = "",
    val nearby: String = "",
    val type: String = "",
    val work: String = "",
    @SerialName("lanes_closed") val lanesClosed: String = "",
    @SerialName("total_lanes") val totalLanes: Int? = null,
    @SerialName("delay_minutes") val delayMinutes: Int? = null,
    val begin: LatLonPoint = LatLonPoint(),
    val end: LatLonPoint = LatLonPoint(),
)

@Serializable
data class IncidentItem(
    val id: String = "",
    val type: String = "",
    val location: String = "",
    val area: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    @SerialName("reported_at") val reportedAt: String? = null,
)

@Serializable
data class CorridorDetail(
    val id: String,
    val name: String,
    val route: String,
    val description: String = "",
    val tier: Int = -1,
    @SerialName("tier_label") val tierLabel: String = "Unknown",
    @SerialName("tier_meaning") val tierMeaning: String = "",
    @SerialName("control_points") val controlPoints: List<ControlPoint> = emptyList(),
    @SerialName("closure_list") val closureList: List<ClosureItem> = emptyList(),
    @SerialName("incident_list") val incidentList: List<IncidentItem> = emptyList(),
    val feed: FeedHealth = FeedHealth(),
)

@Serializable
data class AlertInfo(
    val id: String = "",
    val event: String = "",
    val severity: String = "",
    val headline: String = "",
    val onset: String? = null,
    val ends: String? = null,
)

@Serializable
data class ForecastPeriod(
    val name: String = "",
    val start: String? = null,
    val end: String? = null,
    @SerialName("is_daytime") val isDaytime: Boolean = true,
    @SerialName("temperature_f") val temperatureF: Int? = null,
    val wind: String = "",
    val short: String = "",
    val detailed: String = "",
    @SerialName("precip_chance") val precipChance: Int? = null,
)

@Serializable
data class PassSummary(
    val id: String,
    val name: String,
    val route: String = "",
    val state: String = "CA",
    @SerialName("elevation_ft") val elevationFt: Int = 0,
    @SerialName("corridor_id") val corridorId: String = "",
    val lat: Double? = null,
    val lon: Double? = null,
    val alerts: List<AlertInfo> = emptyList(),
    @SerialName("forecast_ok") val forecastOk: Boolean = true,
    @SerialName("forecast_stale") val forecastStale: Boolean = false,
    @SerialName("next_period") val nextPeriod: ForecastPeriod? = null,
    @SerialName("snow_next_24h_cm") val snowNext24hCm: Double? = null,
    @SerialName("snow_next_48h_cm") val snowNext48hCm: Double? = null,
    @SerialName("snow_next_72h_cm") val snowNext72hCm: Double? = null,
    @SerialName("storm_start") val stormStart: String? = null,
    val periods: List<ForecastPeriod> = emptyList(),
)

@Serializable
data class Summary(
    val corridors: List<CorridorSummary> = emptyList(),
    val passes: List<PassSummary> = emptyList(),
    val feed: FeedHealth = FeedHealth(),
    val disclaimer: String = "",
)

@Serializable
data class ResortReport(
    val id: String,
    val name: String,
    @SerialName("snow_24h_in") val snow24hIn: Double? = null,
    @SerialName("snow_48h_in") val snow48hIn: Double? = null,
    @SerialName("snow_overnight_in") val snowOvernightIn: Double? = null,
    @SerialName("storm_total_in") val stormTotalIn: Double? = null,
    @SerialName("base_depth_in") val baseDepthIn: Double? = null,
    @SerialName("base_depth_max_in") val baseDepthMaxIn: Double? = null,
    @SerialName("season_total_in") val seasonTotalIn: Double? = null,
    @SerialName("lifts_open") val liftsOpen: Int? = null,
    @SerialName("lifts_total") val liftsTotal: Int? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    val ok: Boolean = true,
    val stale: Boolean = false,
    val error: String? = null,
    val notes: List<String> = emptyList(),
    val lat: Double? = null,
    val lon: Double? = null,
)

@Serializable
data class ResortsResponse(val resorts: List<ResortReport> = emptyList())

@Serializable
data class SubscriptionBody(
    val token: String,
    @SerialName("corridor_ids") val corridorIds: List<String>,
)

@Serializable
data class RulesQuery(
    val tier: Int,
    val drivetrain: String,
    val tires: String,
    @SerialName("over_6000_lbs") val over6000Lbs: Boolean = false,
    val towing: Boolean = false,
)

@Serializable
data class RulesAnswer(
    val requirement: String = "unknown",
    val reason: String = "",
    val disclaimer: String = "",
)

@Serializable
data class TripBriefQuery(
    @SerialName("corridor_id") val corridorId: String,
    val origin: String,
    @SerialName("departure_time") val departureTime: String? = null,
    val drivetrain: String? = null,
    val tires: String? = null,
    @SerialName("over_6000_lbs") val over6000Lbs: Boolean = false,
    val towing: Boolean = false,
)

@Serializable
data class TripBriefAnswer(
    val brief: String = "",
    val ai: Boolean = false,
    val model: String? = null,
    val cached: Boolean = false,
    val tier: Int = -1,
    @SerialName("tier_label") val tierLabel: String = "",
    @SerialName("as_of") val asOf: String? = null,
    val stale: Boolean = false,
    val disclaimer: String = "",
)

@Serializable
data class MapControl(
    val route: String = "",
    val direction: String = "",
    val location: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    val tier: Int = -1,
    @SerialName("tier_label") val tierLabel: String = "",
    val status: String = "",
    @SerialName("corridor_id") val corridorId: String = "",
)

@Serializable
data class LatLonPoint(val lat: Double = 0.0, val lon: Double = 0.0)

@Serializable
data class MapClosure(
    val route: String = "",
    val direction: String = "",
    val location: String = "",
    val type: String = "",
    val work: String = "",
    @SerialName("delay_minutes") val delayMinutes: Int? = null,
    val begin: LatLonPoint = LatLonPoint(),
    val end: LatLonPoint = LatLonPoint(),
    @SerialName("corridor_id") val corridorId: String = "",
)

@Serializable
data class MapIncident(
    val id: String = "",
    val type: String = "",
    val location: String = "",
    val area: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    @SerialName("corridor_id") val corridorId: String = "",
)

@Serializable
data class MapWebcam(
    val id: String = "",
    val name: String = "",
    val route: String = "",
    val direction: String = "",
    val nearby: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    @SerialName("image_url") val imageUrl: String = "",
)

@Serializable
data class MapPass(
    val id: String = "",
    val name: String = "",
    val route: String = "",
    val state: String = "",
    @SerialName("elevation_ft") val elevationFt: Int = 0,
    @SerialName("corridor_id") val corridorId: String = "",
    val lat: Double = 0.0,
    val lon: Double = 0.0,
)

@Serializable
data class MapResort(
    val id: String = "",
    val name: String = "",
    @SerialName("snow_24h_in") val snow24hIn: Double? = null,
    @SerialName("base_depth_in") val baseDepthIn: Double? = null,
    @SerialName("lifts_open") val liftsOpen: Int? = null,
    @SerialName("lifts_total") val liftsTotal: Int? = null,
    val ok: Boolean = true,
    val lat: Double = 0.0,
    val lon: Double = 0.0,
)

@Serializable
data class MapData(
    val corridors: List<MapCorridorLine> = emptyList(),
    val controls: List<MapControl> = emptyList(),
    val closures: List<MapClosure> = emptyList(),
    val incidents: List<MapIncident> = emptyList(),
    val webcams: List<MapWebcam> = emptyList(),
    @SerialName("webcams_attribution") val webcamsAttribution: String = "",
    val passes: List<MapPass> = emptyList(),
    val resorts: List<MapResort> = emptyList(),
    val feed: FeedHealth = FeedHealth(),
)

@Serializable
data class MapCorridorLine(
    val id: String = "",
    val route: String = "",
    val name: String = "",
    val tier: Int = -1,
    @SerialName("tier_label") val tierLabel: String = "",
    val segments: List<List<LatLonPoint>> = emptyList(),
)
