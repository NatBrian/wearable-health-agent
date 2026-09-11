package dev.wha.app.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.wha.app.core.ErrorKind
import dev.wha.app.core.WhaResult

/** What went wrong, in words, with what to do next. Never a crash, never a code. */
@Composable
fun ErrorCard(err: WhaResult.Err, onRetry: () -> Unit, onOpenSettings: () -> Unit) {
    Card(modifier = Modifier.padding(8.dp)) {
        Column(Modifier.padding(16.dp)) {
            val (title, body) = when (err.kind) {
                ErrorKind.UNAVAILABLE -> Pair(
                    "Not available right now",
                    "This could not be reached. Check the connection, then try again.",
                )
                ErrorKind.INVALID -> Pair(
                    "Not understood",
                    "What was sent could not be used. Trying again will not help; the connection may need setting up again.",
                )
                ErrorKind.INTERNAL -> Pair(
                    "Something went wrong",
                    "This did not work and the reason is not known. Trying again sometimes helps.",
                )
            }
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body, modifier = Modifier.padding(top = 4.dp))
            Button(onClick = onRetry, modifier = Modifier.padding(top = 8.dp)) { Text("Try again") }
            if (err.kind != ErrorKind.INTERNAL) {
                TextButton(onClick = onOpenSettings) { Text("Open settings") }
            }
        }
    }
}
