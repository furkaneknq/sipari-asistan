package com.orderapp.adminpanel.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.orderapp.adminpanel.data.api.IncomingCallDto
import com.orderapp.adminpanel.ui.AdminViewModel
import com.orderapp.adminpanel.ui.theme.Green
import com.orderapp.adminpanel.util.PhoneFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CallsScreen(
    viewModel: AdminViewModel,
    onCreateOrder: (String) -> Unit,
    onCallPhone: (String) -> Unit
) {
    LaunchedEffect(Unit) {
        viewModel.loadCalls()
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("📞 Gelen Aramalar") },
            actions = {
                IconButton(onClick = { viewModel.loadCalls() }) {
                    Icon(Icons.Default.Refresh, contentDescription = "Yenile")
                }
            }
        )

        if (viewModel.calls.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Henüz arama kaydı yok", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                items(viewModel.calls, key = { it.id }) { call ->
                    CallCard(
                        call = call,
                        onCreateOrder = onCreateOrder,
                        onCallPhone = onCallPhone
                    )
                }
                item { Spacer(modifier = Modifier.height(8.dp)) }
            }
        }
    }
}

@Composable
private fun CallCard(
    call: IncomingCallDto,
    onCreateOrder: (String) -> Unit,
    onCallPhone: (String) -> Unit
) {
    val hasCustomer = call.customers != null
    val displayName = call.customers?.name ?: "Kayıtsız Numara"
    val displayPhone = PhoneFormatter.format(call.phoneNumber)
    val timeStr = call.createdAt.let { ts ->
        // "2026-05-23T01:00:00+03:00" → "01:00"
        val tIndex = ts.indexOf('T')
        if (tIndex >= 0 && ts.length >= tIndex + 6) {
            ts.substring(tIndex + 1, tIndex + 6)
        } else ts
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // İkon
            Icon(
                if (hasCustomer) Icons.Default.Person else Icons.Default.PersonAdd,
                contentDescription = null,
                tint = if (hasCustomer) Green else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                modifier = Modifier.size(32.dp)
            )

            Spacer(modifier = Modifier.width(12.dp))

            // Bilgiler
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    displayName,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    displayPhone,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable { onCallPhone(call.phoneNumber) }
                )
                Text(
                    timeStr,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
            }

            // Butonlar
            if (hasCustomer) {
                FilledTonalButton(
                    onClick = { onCreateOrder(call.customers!!.id) },
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Sipariş", style = MaterialTheme.typography.bodySmall)
                }
            } else {
                // Kayıtsız numara — geri ara
                IconButton(onClick = { onCallPhone(call.phoneNumber) }) {
                    Icon(Icons.Default.Call, contentDescription = "Ara")
                }
            }
        }
    }
}
