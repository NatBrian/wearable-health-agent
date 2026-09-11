package dev.wha.app

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class StringsHaveNoDigitsTest {
    @Test
    fun noUiStringContainsADigit() {
        val xml = File("src/main/res/values/strings.xml").readText()
        val offenders = Regex("<string name=\"([^\"]+)\">([^<]*)</string>").findAll(xml)
            .filter { it.groupValues[2].any(Char::isDigit) }
            .map { it.groupValues[1] }.toList()
        assertTrue("UI strings with a figure in them: $offenders", offenders.isEmpty())
    }
}
