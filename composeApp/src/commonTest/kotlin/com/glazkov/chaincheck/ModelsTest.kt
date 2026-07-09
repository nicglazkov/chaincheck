package com.glazkov.chaincheck

import com.glazkov.chaincheck.data.ChainCheckApi
import com.glazkov.chaincheck.data.CorridorDetail
import com.glazkov.chaincheck.data.ResortsResponse
import com.glazkov.chaincheck.data.Summary
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ModelsTest {

    @Test
    fun summaryParsesBackendShape() {
        val json = """
            {
              "corridors": [
                {"id": "i80", "name": "I-80 Donner Summit", "route": "I-80",
                 "description": "Sac to Truckee", "tier": 2, "tier_label": "R2",
                 "tier_meaning": "Chains required...", "controls": 3,
                 "closures": 1, "incidents": 0}
              ],
              "passes": [
                {"id": "donner", "name": "Donner Summit", "route": "I-80",
                 "state": "CA", "elevation_ft": 7239, "corridor_id": "i80",
                 "alerts": [], "forecast_ok": true,
                 "snow_next_24h_cm": 30.5, "storm_start": null,
                 "unknown_future_field": 42}
              ],
              "feed": {"ok": true, "stale": false, "as_of": "2026-12-12T15:00:00+00:00",
                       "notes": []},
              "disclaimer": "not affiliated"
            }
        """.trimIndent()
        val summary = ChainCheckApi.json.decodeFromString<Summary>(json)
        assertEquals(1, summary.corridors.size)
        assertEquals("R2", summary.corridors[0].tierLabel)
        assertEquals(2, summary.corridors[0].tier)
        assertEquals(30.5, summary.passes[0].snowNext24hCm)
        assertNull(summary.passes[0].stormStart)
        assertTrue(summary.feed.ok)
    }

    @Test
    fun corridorDetailParses() {
        val json = """
            {"id": "us50", "name": "US-50 Echo Summit", "route": "US-50",
             "tier": 1, "tier_label": "R1", "tier_meaning": "...",
             "control_points": [
               {"route": "US-50", "direction": "East", "location": "Twin Bridges",
                "nearby": "", "lat": 38.8, "lon": -120.1, "status": "R-1",
                "tier": 1, "tier_label": "R1", "description": "", "updated_at": null}
             ],
             "closure_list": [], "incident_list": [],
             "feed": {"ok": true, "stale": true, "as_of": null, "notes": ["d3: late"]}}
        """.trimIndent()
        val detail = ChainCheckApi.json.decodeFromString<CorridorDetail>(json)
        assertEquals("Twin Bridges", detail.controlPoints[0].location)
        assertTrue(detail.feed.stale)
    }

    @Test
    fun resortNullsStayNull() {
        val json = """
            {"resorts": [
              {"id": "donner", "name": "Donner Ski Ranch", "snow_24h_in": null,
               "base_depth_in": null, "lifts_open": 2, "lifts_total": 6,
               "ok": true, "stale": false, "error": null,
               "notes": ["resort publishes no structured snow totals"]}
            ]}
        """.trimIndent()
        val resorts = ChainCheckApi.json.decodeFromString<ResortsResponse>(json)
        assertNull(resorts.resorts[0].snow24hIn)
        assertEquals(2, resorts.resorts[0].liftsOpen)
    }
}
