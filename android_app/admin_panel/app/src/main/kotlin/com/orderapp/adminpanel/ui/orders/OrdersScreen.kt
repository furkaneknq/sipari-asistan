package com.orderapp.adminpanel.ui.orders

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
fun OrdersScreen(
    viewModel: OrdersViewModel = hiltViewModel(),
    onNavigateToCreateOrder: () -> Unit = {}
) {
    val orders by viewModel.orders.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Siparişler") })
        },
        floatingActionButton = {
            FloatingActionButton(onClick = onNavigateToCreateOrder) {
                Text("+")
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            items(orders) { order ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(8.dp),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(text = "Sipariş #${order.orderNumber}", style = MaterialTheme.typography.titleMedium)
                        Text(text = "Durum: ${order.status}", style = MaterialTheme.typography.bodyMedium)
                        Text(text = "Tutar: ₺${order.totalAmount}", style = MaterialTheme.typography.bodyMedium)
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (order.status == "new") {
                                Button(onClick = { viewModel.updateStatus(order.id, "preparing") }) {
                                    Text("Hazırlanıyor")
                                }
                            }
                            if (order.status == "preparing") {
                                Button(onClick = { viewModel.updateStatus(order.id, "on_way") }) {
                                    Text("Yola Çıkar")
                                }
                            }
                            if (order.status == "on_way") {
                                Button(onClick = { viewModel.updateStatus(order.id, "delivered") }) {
                                    Text("Teslim Edildi")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
