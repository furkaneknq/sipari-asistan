package com.orderapp.adminpanel.ui.customers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.model.Customer
import com.orderapp.adminpanel.data.model.CustomerAddress
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CustomerListUiState(
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val customers: List<Customer> = emptyList(),
    val searchQuery: String = "",
    val selectedCustomerAddresses: Map<String, List<CustomerAddress>> = emptyMap(),
    val errorMessage: String? = null
)

@HiltViewModel
class CustomerListViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(CustomerListUiState())
    val uiState: StateFlow<CustomerListUiState> = _uiState.asStateFlow()

    fun search(query: String) {
        _uiState.update { it.copy(searchQuery = query) }
        viewModelScope.launch {
            if (query.trim().isBlank()) {
                _uiState.update { it.copy(customers = emptyList()) }
            } else {
                _uiState.update { it.copy(isLoading = true, errorMessage = null) }
                repository.searchCustomers(query).fold(
                    onSuccess = { list ->
                        val nonGuestCustomers = list.filter { !it.isGuest }
                        _uiState.update { it.copy(isLoading = false, customers = nonGuestCustomers) }
                    },
                    onFailure = { error ->
                        _uiState.update { it.copy(isLoading = false, errorMessage = error.localizedMessage) }
                    }
                )
            }
        }
    }

    fun loadAddressesForCustomer(customerId: String) {
        viewModelScope.launch {
            repository.getAddresses(customerId).onSuccess { addresses ->
                val current = _uiState.value.selectedCustomerAddresses.toMutableMap()
                current[customerId] = addresses
                _uiState.update { it.copy(selectedCustomerAddresses = current) }
            }
        }
    }

    fun addCustomer(name: String, phone: String, addressText: String?, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true) }
            repository.createCustomer(name = name, phone = phone, isGuest = false).fold(
                onSuccess = { created ->
                    if (created != null && !addressText.isNullOrBlank()) {
                        repository.createAddress(customerId = created.id, addressText = addressText)
                    }
                    _uiState.update { it.copy(isSaving = false) }
                    search(phone)
                    onSuccess()
                },
                onFailure = { error ->
                    _uiState.update { it.copy(isSaving = false, errorMessage = error.localizedMessage) }
                }
            )
        }
    }
}
