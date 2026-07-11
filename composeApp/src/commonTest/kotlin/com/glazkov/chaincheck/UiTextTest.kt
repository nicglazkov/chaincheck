package com.glazkov.chaincheck

import com.glazkov.chaincheck.ui.countLabel
import com.glazkov.chaincheck.ui.humanizeError
import com.glazkov.chaincheck.ui.humanizeIncidentType
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class UiTextTest {
    @Test
    fun countsReadAsWords() {
        assertEquals("1 closure", countLabel(1, "closure"))
        assertEquals("7 closures", countLabel(7, "closure"))
        assertEquals("0 incidents", countLabel(0, "incident"))
        assertEquals("1 incident", countLabel(1, "incident"))
    }

    @Test
    fun transportErrorsNeverLeakHostnames() {
        val dns = humanizeError(
            "Unable to resolve host \"chaincheck-api-55497952159.us-west1." +
                "run.app\": No address associated with hostname"
        )
        assertTrue("run.app" !in dns)
        assertTrue("offline" in dns)
        assertTrue("timed out" in humanizeError("Connect timeout has expired"))
        assertTrue(humanizeError(null).isNotBlank())
        assertTrue(humanizeError("HTTP 500").isNotBlank())
    }

    @Test
    fun chpShorthandBecomesPlainLanguage() {
        assertEquals(
            "Traffic Collision · Minor Injury",
            humanizeIncidentType("1181-Trfc Collision-Minor Inj"),
        )
        assertEquals(
            "Traffic Hazard",
            humanizeIncidentType("1125-Trfc Hazard"),
        )
        // Unknown text passes through unmangled.
        assertEquals("Closure of a Road", humanizeIncidentType("Closure of a Road"))
    }
}
