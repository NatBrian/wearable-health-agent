package dev.wha.app.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** Every constant with its value and where the value came from. Read only. */
@Composable
fun ConstantsList(constants: List<ConstantRow>) {
    Column {
        constants.forEach { row ->
            Column(Modifier.padding(vertical = 4.dp)) {
                Text(row.name, style = MaterialTheme.typography.bodyMedium)
                Text("${row.value} · ${row.source}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
