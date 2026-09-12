package com.orderapp.adminpanel.ui.orders

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.model.*
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OrderDetailUiState(
    val isLoading: Boolean = false,
    val order: Order? = null,
    val items: List<OrderItem> = emptyList(),
    val customer: Customer? = null,
    val address: CustomerAddress? = null,
    val courier: Courier? = null,
    val productsMap: Map<String, Product> = emptyMap(),
    val errorMessage: String? = null
)

@HiltViewModel
class OrderDetailViewModel @Inject constructor(
    private val repository: AdminRepository,
    savedStateHandle: SavedStateHandle
) : ViewModel() {

    private val orderId: String = checkNotNull(savedStateHandle["orderId"])

    private val _uiState = MutableStateFlow(OrderDetailUiState())
    val uiState: StateFlow<OrderDetailUiState> = _uiState.asStateFlow()

    init {
        loadData()
    }

    fun loadData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }

            val orderResult = repository.getOrderById(orderId)
            val order = orderResult.getOrNull()

            if (order == null) {
                _uiState.update { it.copy(isLoading = false, errorMessage = "Sipariş bulunamadı") }
                return@launch
            }

            val items = repository.getOrderItems(orderId).getOrDefault(emptyList())
            val customers = repository.getCustomers().getOrDefault(emptyList())
            val customer = customers.find { it.id == order.customerId }

            val addresses = repository.getAddresses(order.customerId).getOrDefault(emptyList())
            val address = addresses.find { it.id == order.addressId }

            val couriers = repository.getCouriers().getOrDefault(emptyList())
            val courier = couriers.find { it.id == order.courierId }

            val productsMap = repository.getProducts().getOrDefault(emptyList()).associateBy { it.id }

            _uiState.update {
                it.copy(
                    isLoading = false,
                    order = order,
                    items = items,
                    customer = customer,
                    address = address,
                    courier = courier,
                    productsMap = productsMap
                )
            }
        }
    }

    fun updateStatus(newStatus: String) {
        viewModelScope.launch {
            repository.updateOrderStatus(orderId, newStatus).onSuccess {
                loadData()
            }
        }
    }
}

