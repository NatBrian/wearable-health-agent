package dev.wha.app.ui.onboarding

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import dev.wha.app.R
import kotlinx.coroutines.launch

@Composable
fun OnboardingScreen(vm: OnboardingViewModel, onFinished: () -> Unit) {
    val state by vm.state.collectAsState()
    val pager = rememberPagerState(pageCount = { 4 })
    val scope = rememberCoroutineScope()
    if (state.finished) onFinished()

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        HorizontalPager(state = pager, modifier = Modifier.weight(1f), userScrollEnabled = false) { page ->
            when (page) {
                0 -> WhatItIsPage()
                1 -> CannotDoPage(
                    ticked = state.disclaimerTicked,
                    onTick = vm::tickDisclaimer,
                )
                2 -> ConnectionsPage(state = state, vm = vm)
                3 -> NotificationsPage(onFinish = vm::finish, canFinish = state.canFinish)
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            OutlinedButton(
                onClick = { scope.launch { pager.animateScrollToPage((pager.currentPage - 1).coerceAtLeast(0)) } },
                enabled = pager.currentPage > 0,
            ) { Text("Back") }
            Button(
                onClick = { scope.launch { pager.animateScrollToPage((pager.currentPage + 1).coerceAtMost(3)) } },
                enabled = pager.currentPage < 3 && (pager.currentPage != 1 || state.disclaimerTicked),
            ) { Text(if (pager.currentPage == 2) "Continue" else "Next") }
        }
    }
}

@Composable
private fun WhatItIsPage() {
    Column(Modifier.verticalScroll(rememberScrollState())) {
        Text("What this is", style = MaterialTheme.typography.headlineSmall)
        Text("Your watch notices when your body changes. This app looks into why: it compares each night against your own normal, and only when something is worth explaining does it investigate, ask you a question, or tell you to see somebody.")
        Spacer(Modifier.height(8.dp))
        Text("It can watch your nights, work out your normal, and explain what it did in plain words.")
    }
}

@Composable
private fun CannotDoPage(ticked: Boolean, onTick: (Boolean) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val disclaimer = remember {
        try {
            context.resources.openRawResource(R.raw.disclaimer).bufferedReader().readText()
        } catch (e: Exception) {
            "The disclaimer could not be loaded. It ships with the app; reinstall it before continuing."
        }
    }
    Column(Modifier.verticalScroll(rememberScrollState())) {
        Text("What it cannot do", style = MaterialTheme.typography.headlineSmall)
        Text("It has never been tested on a patient. It does not diagnose. If you feel unwell, see a clinician regardless of what this screen says.")
        TextButton(onClick = { expanded = !expanded }) {
            Text(if (expanded) "Hide the disclaimer" else "Read the disclaimer")
        }
        if (expanded) Text(disclaimer)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = ticked, onCheckedChange = onTick)
            Text("I have read this")
        }
    }
}

@Composable
private fun ConnectionsPage(state: OnboardingUiState, vm: OnboardingViewModel) {
    Column(Modifier.verticalScroll(rememberScrollState())) {
        Text("Connections", style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(value = state.webhookHost, onValueChange = { vm.setWebhook(it, state.webhookPort, state.webhookToken) }, label = { Text("Watch box host") })
        OutlinedTextField(
            value = state.webhookPort, onValueChange = { vm.setWebhook(state.webhookHost, it, state.webhookToken) },
            label = { Text("Port") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        )
        OutlinedTextField(
            value = state.webhookToken, onValueChange = { vm.setWebhook(state.webhookHost, state.webhookPort, it) },
            label = { Text("Token") }, visualTransformation = PasswordVisualTransformation(),
        )
        Row {
            Button(onClick = vm::testBridge) { Text("Test connection") }
            if (state.bridgeResult != null) Text(state.bridgeResult, modifier = Modifier.padding(start = 8.dp))
        }
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = state.providerBaseUrl, onValueChange = { vm.setProvider(it, state.providerModel, state.providerKey) }, label = { Text("Model address") })
        OutlinedTextField(value = state.providerModel, onValueChange = { vm.setProvider(state.providerBaseUrl, it, state.providerKey) }, label = { Text("Model") })
        OutlinedTextField(
            value = state.providerKey, onValueChange = { vm.setProvider(state.providerBaseUrl, state.providerModel, it) },
            label = { Text("Key") }, visualTransformation = PasswordVisualTransformation(),
        )
        Row {
            Button(onClick = vm::testProvider) { Text("Test model") }
            if (state.providerResult != null) Text(state.providerResult, modifier = Modifier.padding(start = 8.dp))
        }
        Spacer(Modifier.height(8.dp))
        Text("Without the watch box, no readings arrive. Without the model, investigations cannot run, but readings are still watched.")
    }
}

@Composable
private fun NotificationsPage(onFinish: () -> Unit, canFinish: Boolean) {
    val context = LocalContext.current
    val granted = Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(
        context, Manifest.permission.POST_NOTIFICATIONS,
    ) == PackageManager.PERMISSION_GRANTED
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }
    Column(Modifier.verticalScroll(rememberScrollState())) {
        Text("Notifications and health library", style = MaterialTheme.typography.headlineSmall)
        Text("Questions arrive as notifications with one tap per answer. General health information downloads in the background; until then the assistant says so.")
        if (!granted) {
            Button(onClick = {
                if (Build.VERSION.SDK_INT >= 33) launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }) { Text("Allow notifications") }
        }
        Spacer(Modifier.height(8.dp))
        Button(onClick = onFinish, enabled = canFinish) { Text("Finish") }
    }
}
