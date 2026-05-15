package com.orderapp.couriertracker.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.orderapp.couriertracker.data.api.OrderItemDto
import com.orderapp.couriertracker.data.db.OrderEntity
import com.orderapp.couriertracker.ui.MainViewModel
import com.orderapp.couriertracker.ui.theme.StatusCancelled
import com.orderapp.couriertracker.ui.theme.StatusDelivered
import com.orderapp.couriertracker.ui.theme.StatusNew
import com.orderapp.couriertracker.ui.theme.StatusOnWay
import com.orderapp.couriertracker.ui.theme.StatusPreparing
import com.orderapp.couriertracker.util.PhoneFormatter
import kotlinx.serialization.json.Json

private val json = Json { ignoreUnknownKeys = true }

/**
 * Sipariş detay ekranı.
 * Müşteri bilgisi, adres, ürünler, ödeme, durum değiştirme,
 * telefon arama ve harita açma butonları.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrderDetailScreen(
    orderId: String,
    viewModel: MainViewModel,
    onBack: () -> Unit,
    onCallPhone: (String) -> Unit,
    onOpenMap: (OrderEntity) -> Unit,
    onSaveLocation: (OrderEntity) -> Unit = {}
) {
    val order by viewModel.observeOrder(orderId).collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = order?.let { "📦 Sipariş #${it.orderNumber}" } ?: "Sipariş Detayı",
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        val o = order
        if (o == null) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center
            ) {
                Text("Sipariş bulunamadı")
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Spacer(Modifier.height(4.dp))

            // ── Müşteri Bilgisi ──────────────────────────────────────
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "👤 ${o.customerName}",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = "📞 ${PhoneFormatter.format(o.customerPhone)}",
                        style = MaterialTheme.typography.bodyLarge
                    )
                    Spacer(Modifier.height(8.dp))
                    val phoneValid = o.customerPhone.replace(Regex("[^0-9]"), "").length >= 7
                    Button(
                        onClick = { onCallPhone(o.customerPhone) },
                        enabled = phoneValid,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Phone, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Ara")
                    }
                }
            }

            // ── Adres ────────────────────────────────────────────────
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "📍 Adres",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.height(4.dp))
                    if (o.addressText.isNullOrBlank()) {
                        Text(
                            text = "Adres bilgisi yok",
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.error
                        )
                    } else {
                        Text(
                            text = o.addressText,
                            style = MaterialTheme.typography.bodyLarge
                        )
                    }
                    Spacer(Modifier.height(4.dp))
                    if (o.latitude == null || o.longitude == null) {
                        Text(
                            text = "⚠ Konum bulunamadı",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.error
                        )
                        // Konum Kaydet butonu — adres ID varsa göster
                        if (o.addressId != null) {
                            Spacer(Modifier.height(8.dp))
                            Button(
                                onClick = { onSaveLocation(o) },
                                modifier = Modifier.fillMaxWidth(),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.tertiary
                                )
                            ) {
                                Icon(Icons.Default.LocationOn, contentDescription = null)
                                Spacer(Modifier.width(8.dp))
                                Text("📍 Anlık Konumu Kaydet")
                            }
                        }
                    }
                    if ((o.latitude != null && o.longitude != null) || !o.addressText.isNullOrBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Button(
                            onClick = { onOpenMap(o) },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.secondary
                            )
                        ) {
                            Icon(Icons.Default.Map, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text(
                                if (o.latitude != null && o.longitude != null) "Haritada Göster"
                                else "Haritada Arat"
                            )
                        }
                    }
                }
            }

            // ── Ürünler ─────────────────────────────────────────────
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Ürünler",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.height(8.dp))

                    val items = try {
                        json.decodeFromString<List<OrderItemDto>>(o.itemsJson)
                    } catch (_: Exception) { emptyList() }

                    if (items.isEmpty()) {
                        Text(
                            text = "Ürün bilgisi yok",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                        )
                    }

                    items.forEach { item ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = item.productName,
                                style = MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.weight(1f)
                            )
                            // Miktar ve birim
                            val qtyText = if (item.quantity == item.quantity.toLong().toDouble()) {
                                "${item.quantity.toLong()}"
                            } else {
                                "${"%.1f".format(item.quantity)}"
                            }
                            Text(
                                text = "$qtyText${item.unit}",
                                style = MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.width(60.dp)
                            )
                            Text(
                                text = "₺${"%.2f".format(item.totalPrice)}",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Medium
                            )
                        }
                        item.notes?.takeIf { it.isNotBlank() }?.let { note ->
                            Text(
                                text = "  ↳ $note",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                            )
                        }
                    }

                    HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "TOPLAM:",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "₺${"%.2f".format(o.totalAmount)}",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            // ── Ödeme Bilgisi + Tutar Girme ─────────────────────────────
            PaidAmountSection(
                order = o,
                onUpdatePaidAmount = { amount ->
                    viewModel.updatePaidAmount(o.id, amount)
                }
            )

            // ── Sipariş Notu ─────────────────────────────────────────
            o.notes?.takeIf { it.isNotBlank() }?.let { note ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "📝 Not",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = note,
                            style = MaterialTheme.typography.bodyLarge
                        )
                    }
                }
            }

            // ── Durum Değiştir ───────────────────────────────────────
            StatusChangeSection(
                currentStatus = o.status,
                onStatusChange = { newStatus ->
                    viewModel.updateOrderStatus(o.id, newStatus)
                }
            )

            // ── Müşteri Konumunu Aç ──────────────────────────────────
            if ((o.latitude != null && o.longitude != null) || !o.addressText.isNullOrBlank()) {
                Button(
                    onClick = { onOpenMap(o) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.secondary
                    )
                ) {
                    Icon(Icons.Default.Map, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("📍 Müşteri Konumunu Aç")
                }
            }

            Spacer(Modifier.height(24.dp))
        }
    }
}

// ─── Durum Değiştirme Bölümü ────────────────────────────────────────

@Composable
private fun StatusChangeSection(
    currentStatus: String,
    onStatusChange: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Durum",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(8.dp))

            Box {
                OutlinedButton(
                    onClick = { expanded = true },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = statusLabel(currentStatus),
                        color = statusColor(currentStatus),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
                DropdownMenu(
                    expanded = expanded,
                    onDismissRequest = { expanded = false }
                ) {
                    statusOptions.forEach { (value, label) ->
                        DropdownMenuItem(
                            text = {
                                Text(
                                    label,
                                    color = statusColor(value),
                                    fontWeight = if (value == currentStatus) FontWeight.Bold else FontWeight.Normal
                                )
                            },
                            onClick = {
                                expanded = false
                                if (value != currentStatus) {
                                    onStatusChange(value)
                                }
                            }
                        )
                    }
                }
            }
        }
    }
}

// ─── Ödeme Tutarı Girme Bölümü ──────────────────────────────────────

@Composable
private fun PaidAmountSection(
    order: OrderEntity,
    onUpdatePaidAmount: (Double) -> Unit
) {
    var inputText by remember(order.id, order.paidAmount) {
        mutableStateOf(if (order.paidAmount > 0) "%.2f".format(order.paidAmount) else "")
    }
    val remaining = order.totalAmount - order.paidAmount

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            val paymentLabel = when (order.paymentMethod) {
                "cash" -> "💵 Nakit"
                "credit_card" -> "💳 Kredi Kartı"
                "iban" -> "🏦 IBAN"
                else -> "Belirtilmemiş"
            }
            Text(
                text = "Ödeme: $paymentLabel",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )

            Spacer(Modifier.height(8.dp))

            // Ödenen / Kalan bilgisi
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "Toplam: ₺${"%.2f".format(order.totalAmount)}",
                    style = MaterialTheme.typography.bodyLarge
                )
                Text(
                    text = "Ödenen: ₺${"%.2f".format(order.paidAmount)}",
                    style = MaterialTheme.typography.bodyLarge
                )
            }

            if (remaining > 0.01) {
                Text(
                    text = "💰 Kalan: ₺${"%.2f".format(remaining)}",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 4.dp)
                )
            } else if (order.paidAmount > 0) {
                Text(
                    text = "✅ Ödeme tamamlandı",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Bold,
                    color = StatusDelivered,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            Spacer(Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(Modifier.height(8.dp))

            // Ödeme girme alanı
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    label = { Text("Ödenen Tutar (₺)") },
                    placeholder = { Text("0.00") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.weight(1f)
                )
                Button(
                    onClick = {
                        val amount = inputText.replace(",", ".").toDoubleOrNull()
                        if (amount != null && amount >= 0) {
                            onUpdatePaidAmount(amount)
                        }
                    }
                ) {
                    Text("Kaydet")
                }
            }

            // Hızlı butonlar: Tamamını öde
            if (remaining > 0.01) {
                Spacer(Modifier.height(4.dp))
                OutlinedButton(
                    onClick = {
                        inputText = "%.2f".format(order.totalAmount)
                        onUpdatePaidAmount(order.totalAmount)
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Tamamını Öde (₺${"%.2f".format(order.totalAmount)})")
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
