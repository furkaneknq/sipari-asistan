package com.orderapp.adminpanel.ui.customers

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomerListScreen(
    viewModel: CustomerListViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    var showAddCustomerDialog by remember { mutableStateOf(false) }
    var expandedCustomerId by remember { mutableStateOf<String?>(null) }

    var newName by remember { mutableStateOf("") }
    var newPhone by remember { mutableStateOf("") }
    var newAddress by remember { mutableStateOf("") }

    val filteredCustomers = uiState.customers

    Scaffold(
        topBar = {
            Column {
                TopAppBar(title = { Text("Müşteri Arama") })
                OutlinedTextField(
                    value = uiState.searchQuery,
                    onValueChange = { viewModel.search(it) },
                    label = { Text("Müşteri İsmi veya Telefon Ara...") },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                )
            }
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { showAddCustomerDialog = true },
                icon = { Icon(Icons.Default.Add, contentDescription = null) },
                text = { Text("Yeni Müşteri") }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (uiState.isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (uiState.searchQuery.isBlank()) {
                Column(
                    modifier = Modifier
                        .align(Alignment.Center)
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        imageVector = Icons.Default.Search,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "Müşteri veya Telefon Ara",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Aramak istediğiniz müşterinin ismini veya telefon numarasını yukarıdaki kutuya yazabilirsiniz.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }
            } else if (filteredCustomers.isEmpty()) {
                Text(
                    text = "Aramanızla eşleşen müşteri bulunamadı",
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredCustomers, key = { it.id }) { customer ->
                        val isExpanded = expandedCustomerId == customer.id
                        val addresses = uiState.selectedCustomerAddresses[customer.id]

                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    if (isExpanded) {
                                        expandedCustomerId = null
                                    } else {
                                        expandedCustomerId = customer.id
                                        viewModel.loadAddressesForCustomer(customer.id)
                                    }
                                },
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = customer.name,
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold
                                        )
                                        Text(
                                            text = customer.phone,
                                            style = MaterialTheme.typography.bodyMedium,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }

                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        IconButton(onClick = {
                                            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${customer.phone}"))
                                            context.startActivity(intent)
                                        }) {
                                            Icon(Icons.Default.Call, contentDescription = "Ara", tint = MaterialTheme.colorScheme.primary)
                                        }

                                        Icon(
                                            imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                                            contentDescription = "Detay"
                                        )
                                    }
                                }

                                if (isExpanded) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Divider()
                                    Spacer(modifier = Modifier.height(8.dp))

                                    Text("Adresler:", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)

                                    if (addresses == null) {
                                        CircularProgressIndicator(modifier = Modifier.size(20.dp).padding(top = 4.dp))
                                    } else if (addresses.isEmpty()) {
                                        Text("Kayıtlı adres bulunamadı", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    } else {
                                        addresses.forEach { addr ->
                                            Text(
                                                text = "• ${addr.addressText}",
                                                style = MaterialTheme.typography.bodyMedium,
                                                modifier = Modifier.padding(vertical = 2.dp)
                                            )
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

    // Add Customer Dialog
    if (showAddCustomerDialog) {
        AlertDialog(
            onDismissRequest = { showAddCustomerDialog = false },
            title = { Text("Yeni Müşteri Ekle") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = newName,
                        onValueChange = { newName = it },
                        label = { Text("Ad Soyad") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newPhone,
                        onValueChange = { newPhone = it },
                        label = { Text("Telefon No") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newAddress,
                        onValueChange = { newAddress = it },
                        label = { Text("Adres (Opsiyonel)") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newName.isNotBlank() && newPhone.isNotBlank()) {
                            viewModel.addCustomer(newName, newPhone, newAddress.takeIf { it.isNotBlank() }) {
                                showAddCustomerDialog = false
                                newName = ""
                                newPhone = ""
                                newAddress = ""
                            }
                        }
                    },
                    enabled = !uiState.isSaving && newName.isNotBlank() && newPhone.isNotBlank()
                ) {
                    Text("Kaydet")
                }
            },
            dismissButton = {
                TextButton(onClick = { showAddCustomerDialog = false }) {
                    Text("İptal")
                }
            }
        )
    }
}
