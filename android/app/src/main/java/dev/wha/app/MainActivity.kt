package dev.wha.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import dev.wha.app.core.PythonWhaCore
import dev.wha.app.corpus.CorpusFetch
import dev.wha.app.jobs.Jobs
import dev.wha.app.settings.AppSettings
import dev.wha.app.ui.Shell
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
                        OnboardingScreen(vm) {
                            onboarded = true
                            // Consent recorded: start the schedule, the catch-up and
                            // the corpus download (Tasks 14 and 16 hook in here).
                            Jobs.enqueueAll(this@MainActivity)
                            Jobs.runCatchupNow(this@MainActivity)
                            CorpusFetch.start(this@MainActivity)
                        }
                    } else {
                        Shell(settings)
                    }
                }
            }
        }
    }
}
