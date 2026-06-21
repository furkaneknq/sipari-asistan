package com.orderapp.adminpanel.ui.create

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateOrderScreen(
    viewModel: CreateOrderViewModel = hiltViewModel(),
    onBack: () -> Unit
) {
    val customers by viewModel.customers.collectAsState()
    val products by viewModel.products.collectAsState()
    val couriers by viewModel.couriers.collectAsState()
    val addresses by viewModel.addresses.collectAsState()

    val selectedCustomer by viewModel.selectedCustomer.collectAsState()
    val cart by viewModel.cart.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Sipariş Oluştur") })
        },
        bottomBar = {
            val total = cart.entries.sumOf { it.key.price * it.value }
            BottomAppBar {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Tutar: ₺$total", style = MaterialTheme.typography.titleMedium)
                    Button(onClick = { viewModel.createOrder { onBack() } }) {
                        Text("Kaydet")
                    }
                }
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp)
        ) {
            item {
                Text("Müşteri Seçin", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(vertical = 8.dp))
            }
            items(customers.take(5)) { customer ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp)
                        .clickable { viewModel.selectCustomer(customer) },
                    colors = CardDefaults.cardColors(
                        containerColor = if (selectedCustomer?.id == customer.id) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Text(text = customer.name, modifier = Modifier.padding(16.dp))
                }
            }
            
            if (addresses.isNotEmpty()) {
                item {
                    Text("Adres Seçin", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(vertical = 8.dp))
                }
                items(addresses) { address ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                            .clickable { viewModel.selectAddress(address) }
                    ) {
                        Text(text = address.addressText, modifier = Modifier.padding(16.dp))
                    }
                }
            }

            item {
                Text("Ürünler", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(vertical = 8.dp))
            }
            items(products) { product ->
                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(text = product.name, style = MaterialTheme.typography.bodyLarge)
                            Text(text = "₺${product.price}", style = MaterialTheme.typography.bodySmall)
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val qty = cart[product] ?: 0.0
                            if (qty > 0) {
                                IconButton(onClick = { viewModel.removeFromCart(product) }) { Text("-") }
                                Text("$qty")
                            }
                            IconButton(onClick = { viewModel.addToCart(product) }) { Text("+") }
                        }
                    }
                }
            }
        }
    }
}
