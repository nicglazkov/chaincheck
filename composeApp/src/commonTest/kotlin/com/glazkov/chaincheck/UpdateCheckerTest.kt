package com.glazkov.chaincheck

import com.glazkov.chaincheck.data.isNewerVersion
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class UpdateCheckerTest {
    @Test
    fun detectsNewerVersions() {
        assertTrue(isNewerVersion("0.1.2", "0.1.1"))
        assertTrue(isNewerVersion("0.2.0", "0.1.9"))
        assertTrue(isNewerVersion("1.0.0", "0.9.9"))
        assertTrue(isNewerVersion("0.1.10", "0.1.9")) // numeric, not lexical
    }

    @Test
    fun sameOrOlderIsNotNewer() {
        assertFalse(isNewerVersion("0.1.1", "0.1.1"))
        assertFalse(isNewerVersion("0.1.0", "0.1.1"))
        assertFalse(isNewerVersion("0.1.1", "0.2.0"))
    }

    @Test
    fun handlesDifferentLengthsAndBlanks() {
        assertTrue(isNewerVersion("0.1.1.1", "0.1.1"))
        assertFalse(isNewerVersion("0.1", "0.1.0"))
        assertFalse(isNewerVersion("", "0.1.1"))
        assertFalse(isNewerVersion("0.1.2", ""))
    }
}
