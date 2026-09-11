package dev.wha.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import dev.wha.app.core.PythonBoot
import dev.wha.app.ui.theme.WhaTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val config = try {
            PythonBoot.ensureStarted(this).callAttr("config").toString()
        } catch (e: Exception) {
            "START FAILED: ${e::class.java.name}: ${e.message}"
        }
        setContent {
            WhaTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
                    Text(config, modifier = Modifier.verticalScroll(rememberScrollState()))
                }
            }
        }
    }
}
