package dev.wha.app.ui.settings

import android.app.Activity
import android.content.Intent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import dev.wha.app.R

@Composable
fun SettingsScreen(vm: SettingsViewModel) {
    val state by vm.state.collectAsState()
    val context = LocalContext.current
    val resources = context.resources
    LazyColumn(Modifier.fillMaxSize().padding(8.dp)) {
        item {
            Section("Data source") {
                OutlinedTextField(
                    value = state.webhookHost,
                    onValueChange = { vm.setWebhook(it, state.webhookPort, state.webhookToken) },
                    label = { Text("Watch box host") },
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = state.webhookPort,
                    onValueChange = { vm.setWebhook(state.webhookHost, it, state.webhookToken) },
                    label = { Text("Port") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = state.webhookToken,
                    onValueChange = { vm.setWebhook(state.webhookHost, state.webhookPort, it) },
                    label = { Text("Token") },
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                )
                Row {
                    Button(onClick = vm::testBridge) { Text("Test connection") }
                    Button(onClick = vm::save, modifier = Modifier.padding(start = 8.dp)) { Text("Save") }
                }
                state.bridgeResult?.let { Text(it) }
                state.lastIngest?.let { Text("Last successful pull $it") }
                if (state.restartNeeded) {
                    Text("Takes effect when the app restarts.")
                    Button(onClick = {
                        (context as? Activity)?.let { activity ->
                            val intent = activity.packageManager
                                .getLaunchIntentForPackage(activity.packageName)
                            activity.finish()
                            if (intent != null) activity.startActivity(intent)
                        }
                    }) { Text("Restart now") }
                }
            }
        }
        item {
            Section("Contact") {
                Text("Questions arrive as notifications. Escalations use the urgent channel and stay until acknowledged.")
            }
        }
        item {
            Section("Model provider") {
                OutlinedTextField(
                    value = state.providerBaseUrl,
                    onValueChange = { vm.setProvider(it, state.providerModel, state.providerKey) },
                    label = { Text("Model address") },
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = state.providerModel,
                    onValueChange = { vm.setProvider(state.providerBaseUrl, it, state.providerKey) },
                    label = { Text("Model") },
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = state.providerKey,
                    onValueChange = { vm.setProvider(state.providerBaseUrl, state.providerModel, it) },
                    label = { Text("Key") },
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                )
                Row {
                    Button(onClick = vm::testProvider) { Text("Test provider") }
                    Button(onClick = vm::save, modifier = Modifier.padding(start = 8.dp)) { Text("Save") }
                }
                state.providerResult?.let { Text(it) }
            }
        }
        item {
            Section("How the system decides") {
                ConstantsList(state.constants)
            }
        }
        item {
            Section("Disclosures") {
                DisclosuresList(resources)
            }
        }
        item {
            Section("Diagnostics") {
                DiagnosticsList(vm)
            }
        }
        item {
            Section("Your record") {
                Button(onClick = vm::export) { Text("Export the record") }
                state.exportText?.let { text ->
                    TextButton(onClick = {
                        context.startActivity(
                            Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, text)
                            }.let { Intent.createChooser(it, null) },
                        )
                    }) { Text("Share the export") }
                }
                Text("Delete everything is not offered. Uninstalling the app removes everything it holds.")
            }
        }
        item {
            Section("About") {
                val version = remember {
                    try {
                        context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: ""
                    } catch (e: Exception) {
                        ""
                    }
                }
                val licence = remember {
                    try {
                        resources.openRawResource(R.raw.licence).bufferedReader().readLine() ?: ""
                    } catch (e: Exception) {
                        ""
                    }
                }
                val attribution = remember {
                    try {
                        val json = context.assets.open("knowledge/corpus-sources.json").bufferedReader().readText()
                        Regex("\"attribution\"\\s*:\\s*\"([^\"]+)\"").find(json)?.groupValues?.get(1) ?: ""
                    } catch (e: Exception) {
                        ""
                    }
                }
                if (version.isNotBlank()) Text("Version $version")
                if (licence.isNotBlank()) Text(licence)
                if (attribution.isNotBlank()) Text(attribution)
            }
        }
    }
}

@Composable
private fun Section(title: String, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            content()
        }
    }
}
