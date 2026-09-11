package dev.wha.app.ui.common

/** What a detection level means, qualified by how well the system knows the person. */
object Wording {
    private val personalRungs = setOf("SHRINKING", "PERSONAL", "MATURE")

    fun level(value: String, rung: String?, wording: Map<String, String>): String {
        val sentence = wording["level.$value"] ?: return ""
        if (rung == null || rung in personalRungs || value == "NA") return sentence
        return sentence.replace("your usual range", "the usual range for an adult") +
            " " + (wording["level.immature_note"] ?: "")
    }

    fun rung(value: String, wording: Map<String, String>): String = wording["rung.$value"] ?: ""
}
