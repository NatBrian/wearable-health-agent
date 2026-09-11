package dev.wha.app.core

import kotlinx.serialization.Serializable
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

@Serializable data class Probe(val x: Int)

class WhaResultTest {
    @Test fun payloadParsesToOk() {
        val r = WhaResult.parse<Probe>("""{"x": 3, "later_added": true}""")
        assertTrue(r is WhaResult.Ok)
        assertEquals(3, (r as WhaResult.Ok).value.x)
    }
    @Test fun envelopeParsesToErr() {
        val r = WhaResult.parse<Probe>("""{"error": {"kind": "unavailable", "message": "no webhook"}}""")
        assertTrue(r is WhaResult.Err)
        assertEquals(ErrorKind.UNAVAILABLE, (r as WhaResult.Err).kind)
        assertEquals("no webhook", r.message)
    }
    @Test fun garbageIsInternalNotACrash() {
        val r = WhaResult.parse<Probe>("not json")
        assertTrue(r is WhaResult.Err && r.kind == ErrorKind.INTERNAL)
    }
    @Test fun nullPayloadParsesToOkNull() {
        val r = WhaResult.parse<Probe?>("null")
        assertTrue(r is WhaResult.Ok && r.value == null)
    }
}
