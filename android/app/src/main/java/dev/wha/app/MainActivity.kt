package dev.wha.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        val report = try {
            Python.getInstance().getModule("wha_smoke").callAttr("report").toString()
        } catch (e: Exception) {
            "SMOKE FAILED: ${e::class.java.name}: ${e.message}"
        }
        setContent { Text(report, modifier = Modifier.verticalScroll(rememberScrollState())) }
    }
}
