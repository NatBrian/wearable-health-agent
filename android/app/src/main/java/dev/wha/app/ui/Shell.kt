package dev.wha.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import dev.wha.app.core.PythonWhaCore
import dev.wha.app.settings.AppSettings
import dev.wha.app.ui.history.HistoryScreen
import dev.wha.app.ui.history.HistoryViewModel
import dev.wha.app.ui.investigation.InvestigationScreen
import dev.wha.app.ui.investigation.InvestigationViewModel
import dev.wha.app.ui.record.RecordScreen
import dev.wha.app.ui.record.RecordViewModel
import dev.wha.app.ui.settings.SettingsScreen
import dev.wha.app.ui.settings.SettingsViewModel
import dev.wha.app.ui.today.TodayScreen
import dev.wha.app.ui.today.TodayViewModel

/** Bottom bar over the four tabs. Record and History arrive in Tasks 18 and 19; their slots wait here. */
@Composable
fun Shell(settings: AppSettings, appSettings: AppSettings = settings) {
    val nav = rememberNavController()
    val context = LocalContext.current
    var recordDate by remember { mutableStateOf<String?>(null) }
    val tabs = listOf(
        Triple("today", "Today", Icons.Filled.Home),
        Triple("history", "History", Icons.Filled.DateRange),
        Triple("record", "Record", Icons.Filled.List),
        Triple("settings", "Settings", Icons.Filled.Settings),
    )
    Scaffold(
        bottomBar = {
            NavigationBar {
                val entry by nav.currentBackStackEntryAsState()
                val current = entry?.destination?.route
                tabs.forEach { (route, label, icon) ->
                    NavigationBarItem(
                        selected = current == route,
                        onClick = {
                            nav.navigate(route) {
                                popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(icon, contentDescription = null) },
                        label = { Text(label) },
                    )
                }
            }
        },
    ) { inner ->
        NavHost(nav, startDestination = "today", modifier = Modifier.padding(inner)) {
            composable("today") {
                val vm = remember {
                    TodayViewModel(PythonWhaCore(context), appSettings.subject)
                }
                TodayScreen(
                    vm,
                    onOpenSettings = { nav.navigate("settings") },
                    onOpenRecord = { date ->
                        recordDate = date
                        nav.navigate("record")
                    },
                    onOpenInvestigation = { id -> nav.navigate("investigation/$id") },
                )
            }
            composable("history") {
                val vm = remember {
                    HistoryViewModel(PythonWhaCore(context), appSettings.subject)
                }
                HistoryScreen(
                    vm,
                    onOpenRecord = { date ->
                        recordDate = date
                        nav.navigate("record")
                    },
                    onOpenSettings = { nav.navigate("settings") },
                )
            }
            composable("record") {
                val vm = remember(recordDate) {
                    RecordViewModel(PythonWhaCore(context), appSettings.subject, recordDate)
                }
                RecordScreen(vm, onOpenSettings = { nav.navigate("settings") })
            }
            composable(
                "investigation/{id}",
                arguments = listOf(navArgument("id") { type = NavType.StringType }),
            ) { entry ->
                val id = entry.arguments?.getString("id") ?: return@composable
                val vm = remember(id) {
                    InvestigationViewModel(PythonWhaCore(context), id, appSettings.subject)
                }
                InvestigationScreen(vm, onOpenSettings = { nav.navigate("settings") })
            }
            composable("settings") {
                val vm = remember {
                    SettingsViewModel(PythonWhaCore(context), AppSettings(context))
                }
                SettingsScreen(vm)
            }
        }
    }
}
