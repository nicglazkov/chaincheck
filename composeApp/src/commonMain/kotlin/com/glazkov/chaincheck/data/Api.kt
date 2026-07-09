package com.glazkov.chaincheck.data

import io.ktor.client.HttpClient
import io.ktor.client.HttpClientConfig
import io.ktor.client.call.body
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

/** Platform HTTP engine (OkHttp on Android, Darwin on iOS). */
expect fun httpClient(config: HttpClientConfig<*>.() -> Unit = {}): HttpClient

object ApiConfig {
    /**
     * Backend base URL. Debug builds may override via [override] (e.g. an
     * emulator pointing at a local uvicorn on http://10.0.2.2:8000).
     */
    var override: String? = null
    const val DEFAULT: String = "https://chaincheck-api-55497952159.us-west1.run.app"
    val baseUrl: String get() = override ?: DEFAULT
}

class ChainCheckApi(private val client: HttpClient = defaultClient()) {

    suspend fun summary(): Summary = client.get("${ApiConfig.baseUrl}/v1/summary").body()

    suspend fun routeDetail(corridorId: String): CorridorDetail =
        client.get("${ApiConfig.baseUrl}/v1/routes/$corridorId").body()

    suspend fun passDetail(passId: String): PassSummary =
        client.get("${ApiConfig.baseUrl}/v1/passes/$passId").body()

    suspend fun resorts(): ResortsResponse =
        client.get("${ApiConfig.baseUrl}/v1/resorts").body()

    suspend fun evaluateRules(query: RulesQuery): RulesAnswer =
        client.post("${ApiConfig.baseUrl}/v1/rules/evaluate") {
            contentType(ContentType.Application.Json)
            setBody(query)
        }.body()

    suspend fun tripBrief(query: TripBriefQuery): TripBriefAnswer =
        client.post("${ApiConfig.baseUrl}/v1/tripbrief") {
            contentType(ContentType.Application.Json)
            setBody(query)
        }.body()

    suspend fun saveSubscription(token: String, corridorIds: List<String>) {
        client.put("${ApiConfig.baseUrl}/v1/subscriptions") {
            contentType(ContentType.Application.Json)
            setBody(SubscriptionBody(token, corridorIds))
        }
    }

    suspend fun deleteSubscription(token: String) {
        client.delete("${ApiConfig.baseUrl}/v1/subscriptions/$token")
    }

    companion object {
        val json = Json {
            ignoreUnknownKeys = true
            explicitNulls = false
        }

        fun defaultClient(): HttpClient = httpClient {
            install(ContentNegotiation) { json(json) }
        }
    }
}
