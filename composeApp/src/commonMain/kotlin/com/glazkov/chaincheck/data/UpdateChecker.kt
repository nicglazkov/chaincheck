package com.glazkov.chaincheck.data

import io.ktor.client.call.body
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

data class ReleaseInfo(val version: String, val url: String)

@Serializable
private data class GithubRelease(
    @SerialName("tag_name") val tagName: String,
    @SerialName("html_url") val htmlUrl: String,
)

/**
 * Checks GitHub Releases for a newer sideloaded build. Uses its own bare HTTP
 * client (no App Check plugin) so the attestation token is never sent to a
 * third-party host.
 */
object UpdateChecker {
    private const val LATEST =
        "https://api.github.com/repos/nicglazkov/chaincheck/releases/latest"

    private val client by lazy {
        httpClient { install(ContentNegotiation) { json(ChainCheckApi.json) } }
    }

    suspend fun latest(): ReleaseInfo? = runCatching {
        val release: GithubRelease = client.get(LATEST) {
            header("Accept", "application/vnd.github+json")
        }.body()
        ReleaseInfo(release.tagName.removePrefix("v"), release.htmlUrl)
    }.getOrNull()
}

/** True if [remote] is a higher dotted version (e.g. "0.1.2") than [local]. */
fun isNewerVersion(remote: String, local: String): Boolean {
    if (remote.isBlank() || local.isBlank()) return false
    val r = remote.trim().split(".").map { it.toIntOrNull() ?: 0 }
    val l = local.trim().split(".").map { it.toIntOrNull() ?: 0 }
    for (i in 0 until maxOf(r.size, l.size)) {
        val rv = r.getOrElse(i) { 0 }
        val lv = l.getOrElse(i) { 0 }
        if (rv != lv) return rv > lv
    }
    return false
}
