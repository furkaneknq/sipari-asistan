package com.orderapp.adminpanel.ui.create

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.orderapp.adminpanel.data.model.Customer

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateOrderScreen(
    viewModel: CreateOrderViewModel = hiltViewModel(),
    initialPhone: String? = null,
    onBack: () -> Unit
) {
    LaunchedEffect(initialPhone) {
        if (!initialPhone.isNullOrBlank()) {
            viewModel.searchCustomers(initialPhone)
        }
    }

    val uiState by viewModel.uiState.collectAsState()
    var showAddAddressDialog by remember { mutableStateOf(false) }
    var newAddressText by remember { mutableStateOf("") }

    val filteredCustomers = uiState.searchResults


    val filteredProducts = remember(uiState.products, uiState.selectedCategory) {
        if (uiState.selectedCategory == null) {
            uiState.products
        } else {
            uiState.products.filter { it.categoryId == uiState.selectedCategory?.id }
        }
    }

    val cartTotal = uiState.cart.entries.sumOf { it.key.price * it.value }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Yeni Sipariş") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Geri")
                    }
                }
            )
        },
        bottomBar = {
            BottomAppBar(containerColor = MaterialTheme.colorScheme.surfaceVariant) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Toplam Tutar", style = MaterialTheme.typography.labelMedium)
                        Text("₺$cartTotal", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    }
                    Button(
                        onClick = { viewModel.createOrder { onBack() } },
                        enabled = !uiState.isSaving && uiState.cart.isNotEmpty()
                    ) {
                        if (uiState.isSaving) {
                            CircularProgressIndicator(modifier = Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary)
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Text("Siparişi Kaydet")
                    }
                }
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Error Message Banner
            uiState.errorMessage?.let { errorMsg ->
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                        Text(text = errorMsg, color = MaterialTheme.colorScheme.onErrorContainer, modifier = Modifier.padding(12.dp))
                    }
                }
            }

            // Customer Selection Section
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("1. Müşteri Bilgileri", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text("Tek Seferlik Misafir", style = MaterialTheme.typography.bodySmall)
                                Spacer(modifier = Modifier.width(4.dp))
                                Switch(
                                    checked = uiState.isGuestMode,
                                    onCheckedChange = { viewModel.setGuestMode(it) }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        if (uiState.isGuestMode) {
                            OutlinedTextField(
                                value = uiState.guestName,
                                onValueChange = { viewModel.updateGuestDetails(it, uiState.guestPhone, uiState.guestAddress) },
                                label = { Text("Misafir Adı (Opsiyonel)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            OutlinedTextField(
                                value = uiState.guestPhone,
                                onValueChange = { viewModel.updateGuestDetails(uiState.guestName, it, uiState.guestAddress) },
                                label = { Text("Telefon No") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            OutlinedTextField(
                                value = uiState.guestAddress,
                                onValueChange = { viewModel.updateGuestDetails(uiState.guestName, uiState.guestPhone, it) },
                                label = { Text("Teslimat Adresi") },
                                modifier = Modifier.fillMaxWidth(),
                                minLines = 2
                            )
                        } else {
                            OutlinedTextField(
                                value = uiState.searchQuery,
                                onValueChange = { viewModel.searchCustomers(it) },
                                label = { Text("Müşteri Ara (İsim veya Telefon)") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            if (uiState.selectedCustomer == null && filteredCustomers.isNotEmpty()) {
                                Spacer(modifier = Modifier.height(8.dp))
                                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                    filteredCustomers.forEach { customer ->
                                        Card(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clickable { viewModel.selectCustomer(customer) },
                                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                                        ) {
                                            Row(
                                                modifier = Modifier.padding(12.dp),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Column {
                                                    Text(customer.name, fontWeight = FontWeight.Bold)
                                                    Text(customer.phone, style = MaterialTheme.typography.bodySmall)
                                                }
                                                Text("Seç", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                                            }
                                        }
                                    }
                                }
                            } else if (uiState.selectedCustomer != null) {
                                val customer = uiState.selectedCustomer!!
                                Spacer(modifier = Modifier.height(8.dp))
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                                ) {
                                    Row(
                                        modifier = Modifier.padding(12.dp),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Column {
                                            Text(customer.name, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                                            Text(customer.phone, style = MaterialTheme.typography.bodyMedium)
                                        }
                                        OutlinedButton(onClick = { viewModel.searchCustomers("") }) {
                                            Text("Değiştir")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Customer Addresses (Registered Mode)
            if (!uiState.isGuestMode && uiState.selectedCustomer != null) {
                item {
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text("2. Adres Seçimi", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                IconButton(onClick = { showAddAddressDialog = true }) {
                                    Icon(Icons.Default.Add, contentDescription = "Yeni Adres Ekle")
                                }
                            }

                            if (uiState.addresses.isEmpty()) {
                                Text("Kayıtlı adres yok.", style = MaterialTheme.typography.bodySmall)
                                Button(onClick = { showAddAddressDialog = true }, modifier = Modifier.padding(top = 4.dp)) {
                                    Text("+ Yeni Adres Ekle")
                                }
                            } else {
                                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    uiState.addresses.forEach { addr ->
                                        val isSelected = uiState.selectedAddress?.id == addr.id
                                        Card(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clickable { viewModel.selectAddress(addr) },
                                            colors = CardDefaults.cardColors(
                                                containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                                            )
                                        ) {
                                            Row(
                                                modifier = Modifier.padding(12.dp),
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                RadioButton(
                                                    selected = isSelected,
                                                    onClick = { viewModel.selectAddress(addr) }
                                                )
                                                Spacer(modifier = Modifier.width(8.dp))
                                                Text(addr.addressText, style = MaterialTheme.typography.bodyMedium)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Categories & Products Section
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("3. Menü & Ürünler", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))

                        // Category Pills
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            item {
                                FilterChip(
                                    selected = uiState.selectedCategory == null,
                                    onClick = { viewModel.selectCategory(null) },
                                    label = { Text("Tüm Ürünler") }
                                )
                            }
                            items(uiState.categories) { category ->
                                FilterChip(
                                    selected = uiState.selectedCategory?.id == category.id,
                                    onClick = { viewModel.selectCategory(category) },
                                    label = { Text(category.name) }
                                )
                            }
                        }
                    }
                }
            }

            // Products Grid / List
            items(filteredProducts, key = { it.id }) { product ->
                val qty = uiState.cart[product] ?: 0.0
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(product.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("₺${product.price} / ${product.unit}", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                        }

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (qty > 0) {
                                OutlinedIconButton(onClick = { viewModel.removeFromCart(product) }) {
                                    Text("-", style = MaterialTheme.typography.titleLarge)
                                }
                                Text(
                                    text = "${qty.toInt()}",
                                    style = MaterialTheme.typography.titleMedium,
                                    modifier = Modifier.padding(horizontal = 12.dp),
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            IconButton(
                                onClick = { viewModel.addToCart(product) },
                                colors = IconButtonDefaults.filledIconButtonColors()
                            ) {
                                Icon(Icons.Default.Add, contentDescription = "Ekle")
                            }
                        }
                    }
                }
            }

            // Payment & Courier & Notes Section
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("4. Ödeme Yöntemi & Kurye & Not", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(8.dp))

                        // Payment Methods
                        Text("Ödeme Şekli", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                        val paymentOptions = listOf(
                            "cash" to "Nakit",
                            "credit_card" to "Kredi Kartı",
                            "iban" to "Havale/EFT",
                            "sodexo" to "Sodexo",
                            "multinet" to "Multinet",
                            "ticket" to "Ticket"
                        )
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(paymentOptions) { (key, label) ->
                                FilterChip(
                                    selected = uiState.paymentMethod == key,
                                    onClick = { viewModel.setPaymentMethod(key) },
                                    label = { Text(label) }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Courier Selection
                        Text("Kurye Atama (Opsiyonel)", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            item {
                                FilterChip(
                                    selected = uiState.selectedCourier == null,
                                    onClick = { viewModel.selectCourier(null) },
                                    label = { Text("Atanmadı") }
                                )
                            }
                            items(uiState.couriers) { courier ->
                                FilterChip(
                                    selected = uiState.selectedCourier?.id == courier.id,
                                    onClick = { viewModel.selectCourier(courier) },
                                    label = { Text(courier.name) }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Order Note
                        OutlinedTextField(
                            value = uiState.orderNote,
                            onValueChange = { viewModel.updateOrderNote(it) },
                            label = { Text("Sipariş Notu (Opsiyonel)") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }
        }
    }

    // Add Address Dialog
    if (showAddAddressDialog) {
        AlertDialog(
            onDismissRequest = { showAddAddressDialog = false },
            title = { Text("Yeni Adres Ekle") },
            text = {
                OutlinedTextField(
                    value = newAddressText,
                    onValueChange = { newAddressText = it },
                    label = { Text("Adres Metni") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newAddressText.isNotBlank()) {
                            viewModel.addNewAddressToCustomer(newAddressText) {
                                showAddAddressDialog = false
                                newAddressText = ""
                            }
                        }
                    }
                ) {
                    Text("Ekle")
                }
            },
            dismissButton = {
                TextButton(onClick = { showAddAddressDialog = false }) {
                    Text("İptal")
                }
            }
        )
    }
}

