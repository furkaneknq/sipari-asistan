package com.orderapp.adminpanel.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.orderapp.adminpanel.data.api.*
import com.orderapp.adminpanel.ui.AdminViewModel
import com.orderapp.adminpanel.ui.OrderItemInput
import com.orderapp.adminpanel.ui.theme.Red

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrderEditScreen(
    viewModel: AdminViewModel,
    orderId: String?,
    preselectedCustomerId: String?,
    onDone: () -> Unit
) {
    val isEdit = orderId != null

    // Sipariş bilgisi (düzenleme)
    val existingOrder = if (isEdit) viewModel.orders.find { it.id == orderId } else null

    // Seçili müşteri
    var selectedCustomer by remember { mutableStateOf<CustomerDto?>(null) }
    var selectedAddress by remember { mutableStateOf<AddressDto?>(null) }
    var selectedCourier by remember { mutableStateOf<CourierDto?>(null) }
    var paymentMethod by remember { mutableStateOf<String?>(null) }
    var notes by remember { mutableStateOf("") }
    var items by remember { mutableStateOf<List<OrderItemInput>>(emptyList()) }

    // Dialogs
    var showCustomerPicker by remember { mutableStateOf(false) }
    var showAddressPicker by remember { mutableStateOf(false) }
    var showCourierPicker by remember { mutableStateOf(false) }
    var showProductPicker by remember { mutableStateOf(false) }
    var showPaymentPicker by remember { mutableStateOf(false) }

    // Referans verileri yükle
    LaunchedEffect(Unit) {
        viewModel.loadReferenceData()
        if (preselectedCustomerId != null) {
            viewModel.searchCustomers("")
        }
    }

    // Düzenleme modunda mevcut verileri yükle
    LaunchedEffect(existingOrder) {
        if (existingOrder != null) {
            existingOrder.customers?.let { c ->
                selectedCustomer = c
                viewModel.loadCustomerAddresses(c.id)
            }
            existingOrder.customerAddresses?.let { a ->
                selectedAddress = a
            }
            existingOrder.couriers?.let { c ->
                selectedCourier = c
            }
            paymentMethod = existingOrder.paymentMethod
            notes = existingOrder.notes ?: ""
            viewModel.loadOrderItems(existingOrder.id)
        }
    }

    // Preselected müşteri yükle
    LaunchedEffect(preselectedCustomerId, viewModel.customers) {
        if (preselectedCustomerId != null && selectedCustomer == null) {
            viewModel.customers.find { it.id == preselectedCustomerId }?.let { c ->
                selectedCustomer = c
                viewModel.loadCustomerAddresses(c.id)
            }
        }
    }

    // Düzenleme: kalemleri yükle
    LaunchedEffect(viewModel.orderItems) {
        if (isEdit && viewModel.orderItems.isNotEmpty() && items.isEmpty()) {
            items = viewModel.orderItems.map { oi ->
                OrderItemInput(
                    productId = oi.productId ?: "",
                    productName = oi.products?.name ?: "Ürün",
                    quantity = oi.quantity,
                    unit = oi.unit,
                    unitPrice = oi.unitPrice
                )
            }
        }
    }

    // Adresler yüklenince varsayılan seç
    LaunchedEffect(viewModel.addresses) {
        if (selectedAddress == null && viewModel.addresses.isNotEmpty()) {
            selectedAddress = viewModel.addresses.find { it.isDefault } ?: viewModel.addresses.first()
        }
    }

    val totalAmount = items.sumOf { it.quantity * it.unitPrice }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text(if (isEdit) "✏️ Sipariş Düzenle" else "➕ Yeni Sipariş") },
            navigationIcon = {
                IconButton(onClick = onDone) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                }
            }
        )

        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // ─── Müşteri ────────────────────────────────────────────
            Text("Müşteri", style = MaterialTheme.typography.titleMedium)
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showCustomerPicker = true }
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Person, contentDescription = null)
                    Spacer(modifier = Modifier.width(12.dp))
                    if (selectedCustomer != null) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(selectedCustomer!!.name, fontWeight = FontWeight.Medium)
                            Text(selectedCustomer!!.phone, style = MaterialTheme.typography.bodySmall)
                        }
                    } else {
                        Text("Müşteri Seç...", modifier = Modifier.weight(1f),
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
                    }
                    Icon(Icons.Default.ChevronRight, contentDescription = null)
                }
            }

            // ─── Adres ──────────────────────────────────────────────
            if (selectedCustomer != null && viewModel.addresses.isNotEmpty()) {
                Text("Adres", style = MaterialTheme.typography.titleMedium)
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { showAddressPicker = true }
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.LocationOn, contentDescription = null)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            selectedAddress?.addressText ?: "Adres Seç...",
                            modifier = Modifier.weight(1f),
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 2
                        )
                        Icon(Icons.Default.ChevronRight, contentDescription = null)
                    }
                }
            }

            // ─── Ürünler ────────────────────────────────────────────
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Ürünler", style = MaterialTheme.typography.titleMedium)
                FilledTonalButton(onClick = { showProductPicker = true }) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Ekle")
                }
            }

            if (items.isEmpty()) {
                Text(
                    "Henüz ürün eklenmedi",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
            }

            items.forEachIndexed { index, item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(item.productName, fontWeight = FontWeight.Medium)
                            Text(
                                "${item.quantity} ${item.unit} × ₺${"%.2f".format(item.unitPrice)}",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        Text(
                            "₺${"%.2f".format(item.quantity * item.unitPrice)}",
                            fontWeight = FontWeight.Bold
                        )
                        IconButton(
                            onClick = { items = items.toMutableList().also { it.removeAt(index) } },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(Icons.Default.Close, contentDescription = "Kaldır", tint = Red, modifier = Modifier.size(18.dp))
                        }
                    }
                }
            }

            // ─── Kurye ──────────────────────────────────────────────
            Text("Kurye", style = MaterialTheme.typography.titleMedium)
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showCourierPicker = true }
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.DeliveryDining, contentDescription = null)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        selectedCourier?.name ?: "Kurye Seç (isteğe bağlı)",
                        modifier = Modifier.weight(1f),
                        color = if (selectedCourier != null) MaterialTheme.colorScheme.onSurface
                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                    )
                    Icon(Icons.Default.ChevronRight, contentDescription = null)
                }
            }

            // ─── Ödeme ──────────────────────────────────────────────
            Text("Ödeme Yöntemi", style = MaterialTheme.typography.titleMedium)
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showPaymentPicker = true }
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Payment, contentDescription = null)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        when (paymentMethod) {
                            "cash" -> "Nakit"
                            "credit_card" -> "Kredi Kartı"
                            "iban" -> "IBAN / Havale"
                            else -> "Seç (isteğe bağlı)"
                        },
                        modifier = Modifier.weight(1f),
                        color = if (paymentMethod != null) MaterialTheme.colorScheme.onSurface
                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                    )
                    Icon(Icons.Default.ChevronRight, contentDescription = null)
                }
            }

            // ─── Not ────────────────────────────────────────────────
            OutlinedTextField(
                value = notes,
                onValueChange = { notes = it },
                label = { Text("Sipariş Notu") },
                modifier = Modifier.fillMaxWidth(),
                maxLines = 3
            )

            // ─── Toplam ─────────────────────────────────────────────
            if (items.isNotEmpty()) {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    ),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Toplam", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "₺${"%.2f".format(totalAmount)}",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }

        // ─── Kaydet Butonu ──────────────────────────────────────────
        Button(
            onClick = {
                if (selectedCustomer == null) return@Button
                if (isEdit) {
                    viewModel.updateOrder(
                        orderId = orderId!!,
                        customerId = selectedCustomer!!.id,
                        addressId = selectedAddress?.id,
                        courierId = selectedCourier?.id,
                        paymentMethod = paymentMethod,
                        notes = notes,
                        items = items,
                        onSuccess = onDone
                    )
                } else {
                    viewModel.createOrder(
                        customerId = selectedCustomer!!.id,
                        addressId = selectedAddress?.id,
                        courierId = selectedCourier?.id,
                        paymentMethod = paymentMethod,
                        notes = notes,
                        items = items,
                        onSuccess = onDone
                    )
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            enabled = selectedCustomer != null && !viewModel.isLoading
        ) {
            if (viewModel.isLoading) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(if (isEdit) "Güncelle" else "Sipariş Oluştur")
        }
    }

    // ─── Müşteri Seçim Dialog'u ──────────────────────────────────────
    if (showCustomerPicker) {
        CustomerPickerDialog(
            viewModel = viewModel,
            onDismiss = { showCustomerPicker = false },
            onSelect = { customer ->
                selectedCustomer = customer
                selectedAddress = null
                viewModel.loadCustomerAddresses(customer.id)
                showCustomerPicker = false
            }
        )
    }

    // ─── Adres Seçim Dialog'u ────────────────────────────────────────
    if (showAddressPicker) {
        AddressPickerDialog(
            addresses = viewModel.addresses,
            currentAddressId = selectedAddress?.id,
            onDismiss = { showAddressPicker = false },
            onSelect = { addr ->
                selectedAddress = addr
                showAddressPicker = false
            }
        )
    }

    // ─── Kurye Seçim Dialog'u ────────────────────────────────────────
    if (showCourierPicker) {
        CourierPickerDialog(
            couriers = viewModel.couriers,
            currentCourierId = selectedCourier?.id,
            onDismiss = { showCourierPicker = false },
            onSelect = { courier ->
                selectedCourier = courier
                showCourierPicker = false
            }
        )
    }

    // ─── Ürün Seçim Dialog'u ─────────────────────────────────────────
    if (showProductPicker) {
        ProductPickerDialog(
            categories = viewModel.categories,
            products = viewModel.products.filter { it.isActive },
            onDismiss = { showProductPicker = false },
            onAdd = { product, qty ->
                items = items + OrderItemInput(
                    productId = product.id,
                    productName = product.name,
                    quantity = qty,
                    unit = product.unit,
                    unitPrice = product.price
                )
                showProductPicker = false
            }
        )
    }

    // ─── Ödeme Yöntemi Dialog'u ──────────────────────────────────────
    if (showPaymentPicker) {
        AlertDialog(
            onDismissRequest = { showPaymentPicker = false },
            title = { Text("Ödeme Yöntemi") },
            text = {
                Column {
                    listOf(
                        null to "Belirtilmedi",
                        "cash" to "💵 Nakit",
                        "credit_card" to "💳 Kredi Kartı",
                        "iban" to "🏦 IBAN / Havale"
                    ).forEach { (method, label) ->
                        TextButton(
                            onClick = {
                                paymentMethod = method
                                showPaymentPicker = false
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(label)
                                if (paymentMethod == method) {
                                    Text("✓", color = MaterialTheme.colorScheme.primary)
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {},
            dismissButton = {
                TextButton(onClick = { showPaymentPicker = false }) { Text("İptal") }
            }
        )
    }
}

// ─── Alt Dialog'lar ──────────────────────────────────────────────────

@Composable
private fun CustomerPickerDialog(
    viewModel: AdminViewModel,
    onDismiss: () -> Unit,
    onSelect: (CustomerDto) -> Unit
) {
    var searchText by remember { mutableStateOf("") }

    LaunchedEffect(searchText) {
        viewModel.searchCustomers(searchText)
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("👥 Müşteri Seç") },
        text = {
            Column(modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(
                    value = searchText,
                    onValueChange = { searchText = it },
                    placeholder = { Text("Ad veya telefon ara...") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) }
                )
                Spacer(modifier = Modifier.height(8.dp))
                LazyColumn(modifier = Modifier.heightIn(max = 350.dp)) {
                    items(viewModel.customers, key = { it.id }) { customer ->
                        TextButton(
                            onClick = { onSelect(customer) },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalAlignment = Alignment.Start
                            ) {
                                Text(customer.name, fontWeight = FontWeight.Medium)
                                Text(
                                    customer.phone,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                )
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

@Composable
private fun AddressPickerDialog(
    addresses: List<AddressDto>,
    currentAddressId: String?,
    onDismiss: () -> Unit,
    onSelect: (AddressDto) -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("📍 Adres Seç") },
        text = {
            LazyColumn {
                items(addresses, key = { it.id }) { addr ->
                    TextButton(
                        onClick = { onSelect(addr) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    addr.title ?: "Adres",
                                    fontWeight = FontWeight.Medium
                                )
                                Text(
                                    addr.addressText,
                                    style = MaterialTheme.typography.bodySmall,
                                    maxLines = 2
                                )
                            }
                            if (addr.id == currentAddressId) {
                                Text("✓", color = MaterialTheme.colorScheme.primary)
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

@Composable
private fun CourierPickerDialog(
    couriers: List<CourierDto>,
    currentCourierId: String?,
    onDismiss: () -> Unit,
    onSelect: (CourierDto?) -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("🏍️ Kurye Seç") },
        text = {
            LazyColumn {
                item {
                    TextButton(
                        onClick = { onSelect(null) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Kuryesiz", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
                    }
                }
                items(couriers, key = { it.id }) { courier ->
                    TextButton(
                        onClick = { onSelect(courier) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(courier.name)
                            if (courier.id == currentCourierId) {
                                Text("✓", color = MaterialTheme.colorScheme.primary)
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

@Composable
private fun ProductPickerDialog(
    categories: List<CategoryDto>,
    products: List<ProductDto>,
    onDismiss: () -> Unit,
    onAdd: (ProductDto, Double) -> Unit
) {
    var selectedCategoryId by remember {
        mutableStateOf(categories.firstOrNull()?.id ?: "")
    }
    var selectedProduct by remember { mutableStateOf<ProductDto?>(null) }
    var quantity by remember { mutableStateOf("1") }

    if (selectedProduct != null) {
        // Miktar giriş ekranı
        AlertDialog(
            onDismissRequest = { selectedProduct = null },
            title = { Text(selectedProduct!!.name) },
            text = {
                Column {
                    Text(
                        "Fiyat: ₺${"%.2f".format(selectedProduct!!.price)}",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = quantity,
                        onValueChange = { quantity = it },
                        label = { Text("Miktar") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val qty = quantity.toDoubleOrNull() ?: 1.0
                        onAdd(selectedProduct!!, qty)
                    }
                ) { Text("Ekle") }
            },
            dismissButton = {
                TextButton(onClick = { selectedProduct = null }) { Text("İptal") }
            }
        )
    } else {
        // Kategori + ürün seçimi
        AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text("📦 Ürün Ekle") },
            text = {
                Column(modifier = Modifier.fillMaxWidth()) {
                    // Kategori sekmeleri
                    if (categories.size > 1) {
                        ScrollableTabRow(
                            selectedTabIndex = categories.indexOfFirst { it.id == selectedCategoryId }
                                .coerceAtLeast(0)
                        ) {
                            categories.forEach { cat ->
                                Tab(
                                    selected = cat.id == selectedCategoryId,
                                    onClick = { selectedCategoryId = cat.id },
                                    text = { Text(cat.name, maxLines = 1) }
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                    }

                    // Ürün listesi
                    val filteredProducts = products.filter {
                        it.categoryId == selectedCategoryId || categories.isEmpty()
                    }
                    LazyColumn(modifier = Modifier.heightIn(max = 300.dp)) {
                        items(filteredProducts, key = { it.id }) { product ->
                            TextButton(
                                onClick = {
                                    selectedProduct = product
                                    quantity = "1"
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(product.name)
                                    Text(
                                        "₺${"%.2f".format(product.price)}",
                                        color = MaterialTheme.colorScheme.primary
                                    )
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
}
