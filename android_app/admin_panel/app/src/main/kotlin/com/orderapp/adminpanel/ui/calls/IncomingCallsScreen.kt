package com.orderapp.adminpanel.ui.calls

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IncomingCallsScreen(
    viewModel: IncomingCallsViewModel = hiltViewModel()
) {
    val calls by viewModel.calls.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Gelen Aramalar") })
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            items(calls) { call ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(8.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (call.isProcessed) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(text = "Tel: ${call.phoneNumber}", style = MaterialTheme.typography.titleMedium)
                        Text(text = "Zaman: ${call.createdAt}", style = MaterialTheme.typography.bodySmall)
                        Spacer(modifier = Modifier.height(8.dp))
                        if (!call.isProcessed) {
                            Button(onClick = { viewModel.markAsProcessed(call.id) }) {
                                Text("İşlendi İşaretle")
                            }
                        } else {
                            Text("İşlendi", color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
        }
    }
}
