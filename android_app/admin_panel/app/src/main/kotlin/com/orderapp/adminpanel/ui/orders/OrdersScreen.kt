package com.orderapp.adminpanel.ui.orders

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.orderapp.adminpanel.data.model.Courier
import com.orderapp.adminpanel.data.model.Order

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrdersScreen(
    viewModel: OrdersViewModel = hiltViewModel(),
    onNavigateToCreateOrder: () -> Unit = {},
    onNavigateToDetail: (String) -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    var editingOrder by remember { mutableStateOf<Order?>(null) }
    var courierAssignOrderId by remember { mutableStateOf<String?>(null) }

    val filteredOrders = remember(uiState.orders, uiState.selectedCourierFilter) {
        when (uiState.selectedCourierFilter) {
            "all" -> uiState.orders
            "unassigned" -> uiState.orders.filter { it.courierId.isNullOrBlank() }
            else -> uiState.orders.filter { it.courierId == uiState.selectedCourierFilter }
        }
    }

    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = { Text("Sipariş Yönetimi") },
                    actions = {
                        IconButton(onClick = { viewModel.loadData() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Yenile")
                        }
                    }
                )
                LazyRow(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    item {
                        FilterChip(
                            selected = uiState.selectedCourierFilter == "all",
                            onClick = { viewModel.setCourierFilter("all") },
                            label = {
                                Text(
                                    text = "Tümü",
                                    fontWeight = if (uiState.selectedCourierFilter == "all") FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        )
                    }
                    item {
                        FilterChip(
                            selected = uiState.selectedCourierFilter == "unassigned",
                            onClick = { viewModel.setCourierFilter("unassigned") },
                            label = {
                                Text(
                                    text = "Atanmamış",
                                    fontWeight = if (uiState.selectedCourierFilter == "unassigned") FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        )
                    }
                    items(uiState.couriers, key = { it.id }) { courier ->
                        FilterChip(
                            selected = uiState.selectedCourierFilter == courier.id,
                            onClick = { viewModel.setCourierFilter(courier.id) },
                            label = {
                                Text(
                                    text = courier.name,
                                    fontWeight = if (uiState.selectedCourierFilter == courier.id) FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        )
                    }
                }
            }
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onNavigateToCreateOrder,
                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                text = { Text("Yeni Sipariş") }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (uiState.isLoading && filteredOrders.isEmpty()) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (filteredOrders.isEmpty()) {
                Text(
                    text = "Sipariş kaydı bulunamadı",
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredOrders, key = { it.id }) { order ->
                        val customer = uiState.customersMap[order.customerId]
                        val courierMap = uiState.couriers.associateBy { it.id }
                        val courier = order.courierId?.let { courierMap[it] }

                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onNavigateToDetail(order.id) },
                            elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(
                                            text = "Sipariş #${order.orderNumber}",
                                            style = MaterialTheme.typography.titleLarge,
                                            fontWeight = FontWeight.Bold
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        IconButton(onClick = { editingOrder = order }) {
                                            Icon(Icons.Default.Edit, contentDescription = "Düzenle", tint = MaterialTheme.colorScheme.primary)
                                        }
                                    }
                                    StatusBadge(status = order.status)
                                }

                                Spacer(modifier = Modifier.height(6.dp))

                                customer?.let {
                                    Text(
                                        text = "👤 Müşteri: ${it.name}",
                                        style = MaterialTheme.typography.bodyLarge,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                }

                                val addressText = order.addressText ?: "Adres belirtilmedi"
                                Text(
                                    text = "📍 Adres: $addressText",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )

                                courier?.let {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "🏍️ Kurye: ${it.name}",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.primary,
                                        fontWeight = FontWeight.Bold
                                    )
                                }

                                if (!order.notes.isNullOrBlank()) {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "📝 Not: ${order.notes}",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.error
                                    )
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                HorizontalDivider()
                                Spacer(modifier = Modifier.height(8.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(
                                            text = "Toplam: ₺${order.totalAmount}",
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                        Text(
                                            text = "Ödeme: ${getPaymentMethodLabel(order.paymentMethod)} (${getPaymentStatusLabel(order.paymentStatus)})",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }

                                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                        customer?.phone?.let { phone ->
                                            IconButton(onClick = {
                                                val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone"))
                                                context.startActivity(intent)
                                            }) {
                                                Icon(Icons.Default.Call, contentDescription = "Ara", tint = MaterialTheme.colorScheme.primary)
                                            }
                                        }

                                        order.addressText?.let { addr ->
                                            IconButton(onClick = {
                                                val gmmIntentUri = Uri.parse("geo:0,0?q=${Uri.encode(addr)}")
                                                val mapIntent = Intent(Intent.ACTION_VIEW, gmmIntentUri)
                                                context.startActivity(mapIntent)
                                            }) {
                                                Icon(Icons.Default.LocationOn, contentDescription = "Harita", tint = MaterialTheme.colorScheme.secondary)
                                            }
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))

                                // Quick Actions Row
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    OutlinedButton(
                                        onClick = { editingOrder = order },
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(16.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("Düzenle")
                                    }

                                    if (order.status == "new") {
                                        Button(
                                            onClick = { courierAssignOrderId = order.id },
                                            modifier = Modifier.weight(1f)
                                        ) {
                                            Text("Kurye Ata")
                                        }
                                    } else if (order.status == "on_way") {
                                        Button(
                                            onClick = { viewModel.updateStatus(order.id, "delivered") },
                                            modifier = Modifier.weight(1f),
                                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
                                        ) {
                                            Text("Teslim Et")
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

    // Edit Order Full Dialog
    editingOrder?.let { order ->
        EditOrderDialog(
            order = order,
            couriers = uiState.couriers,
            onDismiss = { editingOrder = null },
            onSave = { status, courierId, paymentMethod, paymentStatus, paidAmount, notes ->
                viewModel.updateOrderFull(
                    orderId = order.id,
                    status = status,
                    courierId = courierId,
                    paidAmount = paidAmount,
                    paymentStatus = paymentStatus
                )
                editingOrder = null
            }
        )
    }

    // Quick Courier Assignment Dialog
    courierAssignOrderId?.let { orderId ->
        AlertDialog(
            onDismissRequest = { courierAssignOrderId = null },
            title = { Text("Kurye Seçin & Yola Çıkar") },
            text = {
                Column {
                    if (uiState.couriers.isEmpty()) {
                        Text("Kayıtlı kurye bulunamadı.")
                    } else {
                        uiState.couriers.forEach { courier ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp)
                                    .clickable {
                                        viewModel.assignCourier(orderId, courier.id)
                                        courierAssignOrderId = null
                                    },
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                            ) {
                                Text(
                                    text = courier.name,
                                    modifier = Modifier.padding(16.dp),
                                    style = MaterialTheme.typography.bodyLarge,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }
                }
            },
            confirmButton = {},
            dismissButton = {
                TextButton(onClick = { courierAssignOrderId = null }) {
                    Text("İptal")
                }
            }
        )
    }
}

@Composable
fun StatusBadge(status: String) {
    val (label, bgColor, contentColor) = when (status) {
        "new" -> Triple("Yeni", Color(0xFFFFF3E0), Color(0xFFE65100))
        "preparing" -> Triple("Hazırlanıyor", Color(0xFFFFF8E1), Color(0xFFF57F17))
        "on_way" -> Triple("Yolda", Color(0xFFE8EAF6), Color(0xFF1A237E))
        "delivered" -> Triple("Teslim Edildi", Color(0xFFE8F5E9), Color(0xFF1B5E20))
        "cancelled" -> Triple("İptal", Color(0xFFFFEBEE), Color(0xFFB71C1C))
        else -> Triple(status, Color.LightGray, Color.Black)
    }

    Surface(
        color = bgColor,
        contentColor = contentColor,
        shape = MaterialTheme.shapes.small
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold
        )
    }
}

fun getPaymentMethodLabel(method: String?): String {
    return when (method) {
        "cash" -> "Nakit"
        "credit_card" -> "Kredi Kartı"
        "iban" -> "Havale / EFT"
        "sodexo" -> "Sodexo"
        "multinet" -> "Multinet"
        "ticket" -> "Ticket"
        else -> method ?: "Nakit"
    }
}

fun getPaymentStatusLabel(status: String?): String {
    return when (status) {
        "paid" -> "Ödendi"
        "pending" -> "Ödeme Bekliyor"
        "partial" -> "Kısmi Ödeme"
        else -> "Bekliyor"
    }
}
