package com.orderapp.adminpanel.ui.orders

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.orderapp.adminpanel.data.model.Courier
import com.orderapp.adminpanel.data.model.Order

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditOrderDialog(
    order: Order,
    couriers: List<Courier>,
    onDismiss: () -> Unit,
    onSave: (
        status: String,
        courierId: String?,
        paymentMethod: String?,
        paymentStatus: String?,
        paidAmount: Double?,
        notes: String?
    ) -> Unit
) {
    var selectedStatus by remember { mutableStateOf(order.status) }
    var selectedCourierId by remember { mutableStateOf(order.courierId) }
    var selectedPaymentMethod by remember { mutableStateOf(order.paymentMethod ?: "cash") }
    var selectedPaymentStatus by remember { mutableStateOf(order.paymentStatus ?: "pending") }
    var paidAmountText by remember { mutableStateOf(order.paidAmount.toString()) }
    var notesText by remember { mutableStateOf(order.notes ?: "") }

    val statusOptions = listOf(
        "new" to "Yeni",
        "preparing" to "Hazırlanıyor",
        "on_way" to "Yolda",
        "delivered" to "Teslim Edildi",
        "cancelled" to "İptal"
    )

    val paymentOptions = listOf(
        "cash" to "Nakit",
        "credit_card" to "Kredi Kartı",
        "iban" to "Havale / EFT",
        "sodexo" to "Sodexo",
        "multinet" to "Multinet",
        "ticket" to "Ticket"
    )

    val paymentStatusOptions = listOf(
        "pending" to "Ödeme Bekliyor",
        "paid" to "Ödendi",
        "partial" to "Kısmi Ödeme"
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text("Sipariş #${order.orderNumber} Düzenle", fontWeight = FontWeight.Bold)
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Status Selection
                Text("Sipariş Durumu", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(statusOptions) { (key, label) ->
                        FilterChip(
                            selected = selectedStatus == key,
                            onClick = { selectedStatus = key },
                            label = { Text(label) }
                        )
                    }
                }

                Divider()

                // Courier Assignment
                Text("Kurye Atama", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    item {
                        FilterChip(
                            selected = selectedCourierId == null,
                            onClick = { selectedCourierId = null },
                            label = { Text("Kuryesiz") }
                        )
                    }
                    items(couriers) { courier ->
                        FilterChip(
                            selected = selectedCourierId == courier.id,
                            onClick = { selectedCourierId = courier.id },
                            label = { Text(courier.name) }
                        )
                    }
                }

                Divider()

                // Payment Method
                Text("Ödeme Yöntemi", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(paymentOptions) { (key, label) ->
                        FilterChip(
                            selected = selectedPaymentMethod == key,
                            onClick = { selectedPaymentMethod = key },
                            label = { Text(label) }
                        )
                    }
                }

                // Payment Status
                Text("Ödeme Durumu", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(paymentStatusOptions) { (key, label) ->
                        FilterChip(
                            selected = selectedPaymentStatus == key,
                            onClick = {
                                selectedPaymentStatus = key
                                if (key == "paid") {
                                    paidAmountText = order.totalAmount.toString()
                                }
                            },
                            label = { Text(label) }
                        )
                    }
                }

                // Paid Amount TextField
                OutlinedTextField(
                    value = paidAmountText,
                    onValueChange = { paidAmountText = it },
                    label = { Text("Ödenen Tutar (₺)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                // Notes TextField
                OutlinedTextField(
                    value = notesText,
                    onValueChange = { notesText = it },
                    label = { Text("Sipariş Notu") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 2
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val parsedPaidAmount = paidAmountText.toDoubleOrNull() ?: 0.0
                    onSave(
                        selectedStatus,
                        selectedCourierId,
                        selectedPaymentMethod,
                        selectedPaymentStatus,
                        parsedPaidAmount,
                        notesText
                    )
                }
            ) {
                Text("Kaydet")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("İptal")
            }
        }
    )
}
