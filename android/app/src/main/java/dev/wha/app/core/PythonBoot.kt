package dev.wha.app.core

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import dev.wha.app.embed.OnnxEmbedder
import dev.wha.app.notify.NotificationSink
import dev.wha.app.settings.AppSettings
import java.io.File

/** Starts Python once per process, with the working directory and environment the core expects. */
object PythonBoot {
    @Volatile private var facade: PyObject? = null

    fun ensureStarted(context: Context): PyObject {
        facade?.let { return it }
        synchronized(this) {
            facade?.let { return it }
            val root = File(context.filesDir, "wha").apply { mkdirs() }
            extractKnowledge(context, root)
            val settings = AppSettings(context)
            val env = settings.pythonEnvironment(root)
            val platform = AndroidPlatform(context)
            if (!Python.isStarted()) Python.start(platform)
            val py = Python.getInstance()
            val os = py.getModule("os")
            env.forEach { (k, v) -> os.callAttr("putenv", k, v); os.get("environ")!!.callAttr("__setitem__", k, v) }
            os.callAttr("chdir", root.absolutePath)
            val boot = py.getModule("wha_boot")
            // The sink delivers questions as notifications; the embedder runs the
            // same model the PC retrieves with. Both load lazily on first use.
            val started = boot.callAttr("boot", NotificationSink(context.applicationContext), OnnxEmbedder(context.applicationContext))
            facade = started
            return started
        }
    }

    /** data/knowledge from the APK to disk, once per app version. */
    private fun extractKnowledge(context: Context, root: File) {
        val marker = File(root, "knowledge.version")
        val version = context.packageManager.getPackageInfo(context.packageName, 0).longVersionCode.toString()
        if (marker.exists() && marker.readText() == version) return
        val target = File(root, "data/knowledge").apply { mkdirs() }
        context.assets.list("knowledge")!!.forEach { name ->
            context.assets.open("knowledge/$name").use { input ->
                File(target, name).outputStream().use { input.copyTo(it) }
            }
        }
        marker.writeText(version)
    }
}
