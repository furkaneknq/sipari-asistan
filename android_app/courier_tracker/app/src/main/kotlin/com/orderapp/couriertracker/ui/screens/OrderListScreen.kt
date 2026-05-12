package com.orderapp.couriertracker.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.orderapp.couriertracker.data.db.OrderEntity
import com.orderapp.couriertracker.ui.MainViewModel
import com.orderapp.couriertracker.ui.theme.StatusCancelled
import com.orderapp.couriertracker.ui.theme.StatusDelivered
import com.orderapp.couriertracker.ui.theme.StatusNew
import com.orderapp.couriertracker.ui.theme.StatusOnWay
import com.orderapp.couriertracker.ui.theme.StatusPreparing
import com.orderapp.couriertracker.util.PhoneFormatter

/**
 * Ana sipariş listesi ekranı.
 * Aktif siparişler üstte kartlarla, teslim edilenler altta compact listede.
 * Pull-to-refresh destekli. Günlük özet altta.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrderListScreen(
    viewModel: MainViewModel,
    onOrderClick: (String) -> Unit,
    onOpenMap: (OrderEntity) -> Unit,
    onLogout: () -> Unit
) {
    val activeOrders by viewModel.activeOrders.collectAsState()
    val deliveredOrders by viewModel.deliveredOrders.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(viewModel.errorMessage) {
        viewModel.errorMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearError()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Default.LocalShipping,
                            contentDescription = null,
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            text = "Merhaba, ${viewModel.courierName}",
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Yenile")
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.AutoMirrored.Filled.ExitToApp, contentDescription = "Çıkış")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = viewModel.isRefreshing,
            onRefresh = { viewModel.refresh() },
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            LazyColumn(
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                // ── Aktif Siparişlerim ───────────────────────────────
                item {
                    Text(
                        text = "Aktif Siparişlerim (${activeOrders.size})",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(vertical = 4.dp)
                    )
                }

                if (activeOrders.isEmpty()) {
                    item {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(80.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "Aktif sipariş yok",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                            )
                        }
                    }
                }

                items(activeOrders, key = { it.id }) { order ->
                    ActiveOrderCard(
                        order = order,
                        onClick = { onOrderClick(order.id) },
                        onStatusChange = { newStatus ->
                            viewModel.updateOrderStatus(order.id, newStatus)
                        },
                        onOpenMap = { onOpenMap(order) }
                    )
                }

                // ── Teslim Edilenler ─────────────────────────────────
                if (deliveredOrders.isNotEmpty()) {
                    item {
                        Spacer(Modifier.height(8.dp))
                        HorizontalDivider()
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = "Teslim Edilenler",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(vertical = 4.dp)
                        )
                    }

                    items(deliveredOrders, key = { it.id }) { order ->
                        DeliveredOrderRow(
                            order = order,
                            onClick = { onOrderClick(order.id) }
                        )
                    }
                }

                // ── Günlük Özet ──────────────────────────────────────
                item {
                    Spacer(Modifier.height(8.dp))
                    HorizontalDivider()
                    DailySummaryBar(
                        deliveredCount = viewModel.dailySummary.deliveredCount,
                        paidAmount = viewModel.dailySummary.paidAmount
                    )
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
    }
}

// ─── Aktif Sipariş Kartı ────────────────────────────────────────────

@Composable
private fun ActiveOrderCard(
    order: OrderEntity,
    onClick: () -> Unit,
    onStatusChange: (String) -> Unit,
    onOpenMap: () -> Unit
) {
    var statusMenuExpanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            // Üst satır: Sipariş no + saat
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "📦 Sipariş #${order.orderNumber}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                order.deliveryTime?.let {
                    Text(
                        text = "⏰ $it",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                }
            }

            Spacer(Modifier.height(4.dp))

            // Müşteri adı
            Text(
                text = order.customerName,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium
            )

            // Adres
            order.addressText?.let {
                Text(
                    text = "📍 $it",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Fiyat + Ödeme
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                val paymentLabel = when (order.paymentMethod) {
                    "cash" -> "Nakit"
                    "credit_card" -> "K.Kartı"
                    "iban" -> "IBAN"
                    else -> ""
                }
                Text(
                    text = "💰 ₺${"%.2f".format(order.totalAmount)} - $paymentLabel",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold
                )
                // Telefon
                Text(
                    text = PhoneFormatter.format(order.customerPhone),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            }

            Spacer(Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(Modifier.height(8.dp))

            // Alt butonlar: Durum + Konum + Detay
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Durum dropdown
                Box {
                    OutlinedButton(onClick = { statusMenuExpanded = true }) {
                        Text(
                            text = "Durum: ${statusLabel(order.status)}",
                            color = statusColor(order.status),
                            style = MaterialTheme.typography.labelLarge
                        )
                    }
                    DropdownMenu(
                        expanded = statusMenuExpanded,
                        onDismissRequest = { statusMenuExpanded = false }
                    ) {
                        statusOptions.forEach { (value, label) ->
                            DropdownMenuItem(
                                text = { Text(label, color = statusColor(value)) },
                                onClick = {
                                    statusMenuExpanded = false
                                    onStatusChange(value)
                                }
                            )
                        }
                    }
                }

                Spacer(Modifier.weight(1f))

                // Konum butonu
                if ((order.latitude != null && order.longitude != null) || !order.addressText.isNullOrBlank()) {
                    IconButton(onClick = onOpenMap) {
                        Icon(
                            Icons.Default.Map,
                            contentDescription = "Konumu Aç",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
        }
    }
}

// ─── Teslim Edilmiş Sipariş Satırı ──────────────────────────────────

@Composable
private fun DeliveredOrderRow(
    order: OrderEntity,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "#${order.orderNumber}",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = "✅",
                style = MaterialTheme.typography.bodyMedium
            )
            Text(
                text = order.customerName,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.weight(1f).padding(horizontal = 8.dp),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = "₺${"%.2f".format(order.paidAmount)}",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

// ─── Günlük Özet Barı ──────────────────────────────────────────────

@Composable
private fun DailySummaryBar(deliveredCount: Int, paidAmount: Double) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "📊 Günlük Özet",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "Teslim",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = "$deliveredCount",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "Tahsilat",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = "₺${"%.2f".format(paidAmount)}",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

// ─── Yardımcılar ────────────────────────────────────────────────────

private val statusOptions = listOf(
    "new" to "Yeni",
    "preparing" to "Hazırlanıyor",
    "on_way" to "Yolda",
    "delivered" to "Teslim Edildi"
)

@Composable
private fun statusColor(status: String) = when (status) {
    "new" -> StatusNew
    "preparing" -> StatusPreparing
    "on_way" -> StatusOnWay
    "delivered" -> StatusDelivered
    "cancelled" -> StatusCancelled
    else -> MaterialTheme.colorScheme.onSurface
}

private fun statusLabel(status: String) = when (status) {
    "new" -> "Yeni"
    "preparing" -> "Hazırlanıyor"
    "on_way" -> "Yolda"
    "delivered" -> "Teslim Edildi"
    "cancelled" -> "İptal"
    else -> status
}
