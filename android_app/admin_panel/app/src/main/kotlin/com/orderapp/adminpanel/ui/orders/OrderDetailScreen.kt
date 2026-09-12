package com.orderapp.adminpanel.ui.orders

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.LocationOn
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
fun OrderDetailScreen(
    viewModel: OrderDetailViewModel = hiltViewModel(),
    onBack: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val order = uiState.order

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (order != null) "Sipariş #${order.orderNumber}" else "Sipariş Detayı") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Geri")
                    }
                }
            )
        }
    ) { padding ->
        if (uiState.isLoading && order == null) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else if (order == null) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Sipariş bulunamadı", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Header Status Card
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "Sipariş #${order.orderNumber}",
                                    style = MaterialTheme.typography.headlineSmall,
                                    fontWeight = FontWeight.Bold
                                )
                                order.createdAt?.let {
                                    Text(
                                        text = it.take(19).replace("T", " "),
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                }
                            }
                            StatusBadge(status = order.status)
                        }
                    }
                }

                // Customer Info Card
                item {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Müşteri & Adres Bilgileri", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))

                            Text("İsim: ${uiState.customer?.name ?: "Bilinmiyor"}", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
                            Text("Telefon: ${uiState.customer?.phone ?: "-"}", style = MaterialTheme.typography.bodyMedium)

                            val addrText = order.addressText ?: uiState.address?.addressText ?: "Adres bulunamadı"
                            Text("Adres: $addrText", style = MaterialTheme.typography.bodyMedium)

                            Spacer(modifier = Modifier.height(8.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                uiState.customer?.phone?.let { phone ->
                                    OutlinedButton(
                                        onClick = {
                                            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone"))
                                            context.startActivity(intent)
                                        }
                                    ) {
                                        Icon(Icons.Default.Call, contentDescription = null, modifier = Modifier.size(18.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("Müşteriyi Ara")
                                    }
                                }

                                OutlinedButton(
                                    onClick = {
                                        val gmmIntentUri = Uri.parse("geo:0,0?q=${Uri.encode(addrText)}")
                                        val mapIntent = Intent(Intent.ACTION_VIEW, gmmIntentUri)
                                        context.startActivity(mapIntent)
                                    }
                                ) {
                                    Icon(Icons.Default.LocationOn, contentDescription = null, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Haritada Aç")
                                }
                            }
                        }
                    }
                }

                // Order Details & Notes
                item {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Ödeme & Kurye Bilgileri", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))

                            Text("Ödeme Şekli: ${getPaymentMethodLabel(order.paymentMethod)}", style = MaterialTheme.typography.bodyMedium)
                            uiState.courier?.let {
                                Text("Kurye: ${it.name}", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.primary)
                            }

                            if (!order.notes.isNullOrBlank()) {
                                Spacer(modifier = Modifier.height(4.dp))
                                Text("Sipariş Notu: ${order.notes}", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.error)
                            }
                        }
                    }
                }

                // Order Items
                item {
                    Text("Sipariş Kalemleri (${uiState.items.size})", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                }

                items(uiState.items) { item ->
                    val product = item.productId?.let { uiState.productsMap[it] }
                    val productName = product?.name ?: "Ürün"

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(text = productName, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
                                Text(
                                    text = "${item.quantity.toInt()} ${item.unit} x ₺${item.unitPrice}",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Text(
                                text = "₺${item.totalPrice}",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                // Total Summary
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Toplam Tutar", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                            Text("₺${order.totalAmount}", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }

                // Action Buttons
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        if (order.status != "delivered") {
                            Button(
                                onClick = { viewModel.updateStatus("delivered") },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Teslim Edildi İşaretle")
                            }
                        }
                        if (order.status != "cancelled") {
                            OutlinedButton(
                                onClick = { viewModel.updateStatus("cancelled") },
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
                            ) {
                                Text("İptal Et")
                            }
                        }
                    }
                }
            }
        }
    }
}

