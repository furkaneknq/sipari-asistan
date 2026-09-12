package com.orderapp.adminpanel.ui.calls

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.PhoneCallback
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IncomingCallsScreen(
    viewModel: IncomingCallsViewModel = hiltViewModel(),
    onNavigateToCreateOrder: (String) -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    val displayedCalls = if (uiState.filterOnlyUnprocessed) {
        uiState.calls.filter { !it.isProcessed }
    } else {
        uiState.calls
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Gelen Aramalar")
                        Text(
                            text = if (uiState.isAutoPolling) "🔴 Canlı Takip (3sn oto-yenileme)" else "⏸️ Canlı Takip Duraklatıldı",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (uiState.isAutoPolling) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.loadData(showLoading = true) }) {
                        Icon(imageVector = Icons.Default.Refresh, contentDescription = "Yenile")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Yalnızca İşlenmemiş Aramalar",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                Switch(
                    checked = uiState.filterOnlyUnprocessed,
                    onCheckedChange = { viewModel.toggleFilterOnlyUnprocessed(it) }
                )
            }

            if (uiState.isLoading && displayedCalls.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else if (displayedCalls.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Arama kaydı bulunamadı", style = MaterialTheme.typography.bodyLarge)
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(displayedCalls, key = { it.id }) { call ->
                        val matchedCustomer = uiState.customersMap[call.id]
                        val customerAddresses = matchedCustomer?.id?.let { uiState.customerAddressesMap[it] }
                        val primaryAddress = customerAddresses?.firstOrNull()?.addressText

                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = when {
                                    !call.isProcessed -> MaterialTheme.colorScheme.primaryContainer
                                    call.isUnanswered -> MaterialTheme.colorScheme.errorContainer
                                    else -> MaterialTheme.colorScheme.surfaceVariant
                                }
                            )
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            imageVector = Icons.Default.PhoneCallback,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary,
                                            modifier = Modifier.size(24.dp)
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            text = call.phoneNumber,
                                            style = MaterialTheme.typography.titleLarge,
                                            fontWeight = FontWeight.Bold
                                        )
                                    }
                                    if (call.isProcessed) {
                                        AssistChip(
                                            onClick = {},
                                            label = { Text(if (call.isUnanswered) "Cevapsız" else "İşlendi") },
                                            leadingIcon = {
                                                Icon(
                                                    imageVector = Icons.Default.Check,
                                                    contentDescription = null,
                                                    modifier = Modifier.size(16.dp)
                                                )
                                            }
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(6.dp))
                                if (matchedCustomer != null) {
                                    Text(
                                        text = "👤 Müşteri: ${matchedCustomer.name}",
                                        style = MaterialTheme.typography.bodyLarge,
                                        fontWeight = FontWeight.SemiBold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                    if (!primaryAddress.isNullOrBlank()) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            modifier = Modifier.padding(top = 2.dp)
                                        ) {
                                            Icon(
                                                imageVector = Icons.Default.LocationOn,
                                                contentDescription = null,
                                                modifier = Modifier.size(16.dp),
                                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                            Spacer(modifier = Modifier.width(4.dp))
                                            Text(
                                                text = primaryAddress,
                                                style = MaterialTheme.typography.bodyMedium,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                    }
                                } else {
                                    Text(
                                        text = "⚠️ Kayıtsız Arayan (Yeni Müşteri)",
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.error
                                    )
                                }

                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "🕒 Tarih: ${call.createdAt.take(19).replace("T", " ")}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )

                                Spacer(modifier = Modifier.height(12.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Button(
                                        onClick = { onNavigateToCreateOrder(call.phoneNumber) },
                                        modifier = Modifier.weight(1f),
                                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 6.dp)
                                    ) {
                                        Icon(Icons.Default.ShoppingCart, contentDescription = null, modifier = Modifier.size(18.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("Sipariş Aç")
                                    }

                                    IconButton(
                                        onClick = {
                                            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${call.phoneNumber}"))
                                            context.startActivity(intent)
                                        }
                                    ) {
                                        Icon(Icons.Default.Call, contentDescription = "Ara", tint = MaterialTheme.colorScheme.primary)
                                    }

                                    if (!call.isProcessed) {
                                        OutlinedButton(
                                            onClick = { viewModel.markAsProcessed(call.id) },
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 6.dp)
                                        ) {
                                            Text("İşlendi")
                                        }
                                        OutlinedButton(
                                            onClick = { viewModel.markAsUnanswered(call.id) },
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 6.dp)
                                        ) {
                                            Text("Cevapsız")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
