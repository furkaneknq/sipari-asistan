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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.orderapp.adminpanel.data.api.OrderDto
import com.orderapp.adminpanel.ui.AdminViewModel
import com.orderapp.adminpanel.ui.theme.*
import com.orderapp.adminpanel.util.PhoneFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrdersScreen(
    viewModel: AdminViewModel,
    onEditOrder: (String) -> Unit,
    onCallPhone: (String) -> Unit
) {
    LaunchedEffect(Unit) {
        viewModel.loadOrders()
        viewModel.loadReferenceData()
    }

    var showCourierDialog by remember { mutableStateOf<OrderDto?>(null) }

    Column(modifier = Modifier.fillMaxSize()) {
        // Üst bar
        TopAppBar(
            title = { Text("📋 Siparişler") },
            actions = {
                IconButton(onClick = { viewModel.loadOrders() }) {
                    Icon(Icons.Default.Refresh, contentDescription = "Yenile")
                }
            }
        )

        // Hata
        viewModel.errorMessage?.let { error ->
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp)
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        error,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.weight(1f)
                    )
                    IconButton(onClick = { viewModel.clearError() }) {
                        Icon(Icons.Default.Close, contentDescription = "Kapat", modifier = Modifier.size(18.dp))
                    }
                }
            }
        }

        // Yükleniyor
        if (viewModel.isLoading) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }

        // Özet
        val total = viewModel.orders.sumOf { it.totalAmount }
        val delivered = viewModel.orders.count { it.status == "delivered" }
        val active = viewModel.orders.count { it.status != "delivered" && it.status != "cancelled" }
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            SummaryChip("Aktif", "$active", StatusNew)
            SummaryChip("Teslim", "$delivered", StatusDelivered)
            SummaryChip("Toplam", "₺${"%.0f".format(total)}", MaterialTheme.colorScheme.primary)
        }

        // Sipariş listesi
        if (viewModel.orders.isEmpty() && !viewModel.isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Sipariş bulunamadı", style = MaterialTheme.typography.bodyLarge)
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(viewModel.orders, key = { it.id }) { order ->
                    OrderCard(
                        order = order,
                        onEdit = { onEditOrder(order.id) },
                        onStatusChange = { status -> viewModel.updateOrderStatus(order.id, status) },
                        onAssignCourier = { showCourierDialog = order },
                        onCallPhone = onCallPhone
                    )
                }
                item { Spacer(modifier = Modifier.height(8.dp)) }
            }
        }
    }

    // Kurye atama dialog
    showCourierDialog?.let { order ->
        CourierAssignDialog(
            couriers = viewModel.couriers,
            currentCourierId = order.courierId,
            onDismiss = { showCourierDialog = null },
            onSelect = { courierId ->
                viewModel.assignCourier(order.id, courierId)
                showCourierDialog = null
            }
        )
    }
}

@Composable
private fun SummaryChip(label: String, value: String, color: androidx.compose.ui.graphics.Color) {
    Surface(
        shape = MaterialTheme.shapes.small,
        color = color.copy(alpha = 0.12f)
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
        ) {
            Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = color)
            Text(label, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun OrderCard(
    order: OrderDto,
    onEdit: () -> Unit,
    onStatusChange: (String) -> Unit,
    onAssignCourier: () -> Unit,
    onCallPhone: (String) -> Unit
) {
    val statusColor = when (order.status) {
        "new" -> StatusNew
        "preparing" -> StatusPreparing
        "on_way" -> StatusOnWay
        "delivered" -> StatusDelivered
        "cancelled" -> StatusCancelled
        else -> StatusNew
    }
    val statusLabel = when (order.status) {
        "new" -> "Yeni"
        "preparing" -> "Hazırlanıyor"
        "on_way" -> "Yolda"
        "delivered" -> "Teslim Edildi"
        "cancelled" -> "İptal"
        else -> order.status
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            // Üst satır: sipariş no + durum
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "#${order.orderNumber}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Surface(
                    shape = MaterialTheme.shapes.small,
                    color = statusColor.copy(alpha = 0.15f)
                ) {
                    Text(
                        statusLabel,
                        color = statusColor,
                        style = MaterialTheme.typography.labelLarge,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            // Müşteri bilgisi
            val customerName = order.customers?.name ?: "—"
            val customerPhone = order.customers?.phone?.let { PhoneFormatter.format(it) } ?: ""
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Person, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text(customerName, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                if (customerPhone.isNotBlank()) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        customerPhone,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.clickable {
                            order.customers?.phone?.let { onCallPhone(it) }
                        }
                    )
                }
            }

            // Adres
            order.customerAddresses?.addressText?.let { addr ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.LocationOn, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(addr, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }

            // Kurye
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.DeliveryDining, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    order.couriers?.name ?: "Kurye atanmadı",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (order.couriers != null) MaterialTheme.colorScheme.onSurface
                    else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
            }

            // Notlar
            if (!order.notes.isNullOrBlank()) {
                Text(
                    "📝 ${order.notes}",
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Alt satır: tutar + butonlar
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "₺${"%.2f".format(order.totalAmount)}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )

                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    // Kurye ata
                    if (order.status != "delivered" && order.status != "cancelled") {
                        IconButton(onClick = onAssignCourier, modifier = Modifier.size(36.dp)) {
                            Icon(Icons.Default.DeliveryDining, contentDescription = "Kurye Ata", modifier = Modifier.size(20.dp))
                        }
                    }

                    // Teslim edildi
                    if (order.status == "on_way") {
                        IconButton(
                            onClick = { onStatusChange("delivered") },
                            modifier = Modifier.size(36.dp)
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = "Teslim", tint = Green, modifier = Modifier.size(20.dp))
                        }
                    }

                    // Düzenle
                    IconButton(onClick = onEdit, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.Edit, contentDescription = "Düzenle", modifier = Modifier.size(20.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun CourierAssignDialog(
    couriers: List<com.orderapp.adminpanel.data.api.CourierDto>,
    currentCourierId: String?,
    onDismiss: () -> Unit,
    onSelect: (String?) -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("🏍️ Kurye Ata") },
        text = {
            LazyColumn {
                if (currentCourierId != null) {
                    item {
                        TextButton(
                            onClick = { onSelect(null) },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("❌ Kuryeyi Kaldır", color = Red)
                        }
                        HorizontalDivider()
                    }
                }
                items(couriers, key = { it.id }) { courier ->
                    TextButton(
                        onClick = { onSelect(courier.id) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(courier.name)
                            if (courier.id == currentCourierId) {
                                Text("✓", color = Green)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("İptal") }
        }
    )
}
