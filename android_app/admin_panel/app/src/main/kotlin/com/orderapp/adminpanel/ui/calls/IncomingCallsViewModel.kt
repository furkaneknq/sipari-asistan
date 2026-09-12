package com.orderapp.adminpanel.ui.calls

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.model.Customer
import com.orderapp.adminpanel.data.model.CustomerAddress
import com.orderapp.adminpanel.data.model.IncomingCall
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.isActive
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CallsUiState(
    val isLoading: Boolean = false,
    val calls: List<IncomingCall> = emptyList(),
    val customersMap: Map<String, Customer> = emptyMap(), // Key: call.id
    val customerAddressesMap: Map<String, List<CustomerAddress>> = emptyMap(), // Key: customer.id
    val filterOnlyUnprocessed: Boolean = false,
    val isAutoPolling: Boolean = true,
    val errorMessage: String? = null
)

@HiltViewModel
class IncomingCallsViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(CallsUiState())
    val uiState: StateFlow<CallsUiState> = _uiState.asStateFlow()

    init {
        loadData(showLoading = true)
        startAutoPolling()
    }

    private fun startAutoPolling() {
        viewModelScope.launch {
            while (isActive) {
                delay(3000) // Auto-refresh incoming calls every 3 seconds!
                if (_uiState.value.isAutoPolling) {
                    loadData(showLoading = false)
                }
            }
        }
    }

    fun loadData(showLoading: Boolean = true) {
        viewModelScope.launch {
            if (showLoading) {
                _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            }

            val callsResult = repository.getIncomingCalls()
            callsResult.fold(
                onSuccess = { calls ->
                    val recentCalls = calls.take(40)
                    val customerIds = recentCalls.mapNotNull { it.customerId }.filter { it.isNotBlank() }

                    // Batch fetch known customers by ID
                    val knownCustomersList = if (customerIds.isNotEmpty()) {
                        repository.getCustomersByIds(customerIds).getOrDefault(emptyList())
                    } else emptyList()

                    val knownCustomersMap = knownCustomersList.associateBy { it.id }

                    // Batch match for remaining calls using phone number lookup
                    val customersMap = mutableMapOf<String, Customer>()
                    val allMatchedCustomerIds = mutableListOf<String>()

                    recentCalls.forEach { call ->
                        val known = call.customerId?.let { knownCustomersMap[it] }
                        if (known != null) {
                            customersMap[call.id] = known
                            allMatchedCustomerIds.add(known.id)
                        } else {
                            val matched = repository.matchCustomerForPhone(call.phoneNumber, call.customerId)
                            if (matched != null) {
                                customersMap[call.id] = matched
                                allMatchedCustomerIds.add(matched.id)
                            }
                        }
                    }

                    // Batch fetch addresses in one single HTTP request
                    val addressesList = if (allMatchedCustomerIds.isNotEmpty()) {
                        repository.getAddressesByCustomerIds(allMatchedCustomerIds).getOrDefault(emptyList())
                    } else emptyList()

                    val addressesMap = addressesList.groupBy { it.customerId }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            calls = calls,
                            customersMap = customersMap,
                            customerAddressesMap = addressesMap
                        )
                    }
                },
                onFailure = { error ->
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            errorMessage = error.localizedMessage ?: "Gelen aramalar yüklenemedi"
                        )
                    }
                }
            )
        }
    }

    fun markAsProcessed(id: String) {
        viewModelScope.launch {
            repository.markCallProcessed(id).onSuccess {
                loadData(showLoading = false)
            }
        }
    }

    fun markAsUnanswered(id: String) {
        viewModelScope.launch {
            repository.markCallUnanswered(id).onSuccess {
                loadData(showLoading = false)
            }
        }
    }

    fun toggleFilterOnlyUnprocessed(onlyUnprocessed: Boolean) {
        _uiState.update { it.copy(filterOnlyUnprocessed = onlyUnprocessed) }
    }

    fun toggleAutoPolling(enabled: Boolean) {
        _uiState.update { it.copy(isAutoPolling = enabled) }
    }
}
