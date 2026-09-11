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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import dev.wha.app.core.PythonBoot
import dev.wha.app.core.PythonWhaCore
import dev.wha.app.settings.AppSettings
import dev.wha.app.ui.onboarding.OnboardingScreen
import dev.wha.app.ui.onboarding.OnboardingViewModel
import dev.wha.app.ui.theme.WhaTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val settings = AppSettings(this)
        setContent {
            WhaTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
                    var onboarded by remember { mutableStateOf(settings.onboarded) }
                    if (!onboarded) {
                        val context = LocalContext.current
                        val vm = remember {
                            OnboardingViewModel(PythonWhaCore(context), settings)
                        }
                        OnboardingScreen(vm) { onboarded = true }
                    } else {
                        val config = remember {
                            try {
                                PythonBoot.ensureStarted(this@MainActivity).callAttr("config").toString()
                            } catch (e: Exception) {
                                "START FAILED: ${e::class.java.name}: ${e.message}"
                            }
                        }
                        Text(config, modifier = Modifier.verticalScroll(rememberScrollState()))
                    }
                }
            }
        }
    }
}
