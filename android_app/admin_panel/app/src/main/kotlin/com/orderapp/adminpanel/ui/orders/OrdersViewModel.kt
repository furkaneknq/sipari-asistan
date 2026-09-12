package com.orderapp.adminpanel.ui.orders

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.model.Courier
import com.orderapp.adminpanel.data.model.Customer
import com.orderapp.adminpanel.data.model.Order
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OrdersUiState(
    val isLoading: Boolean = false,
    val orders: List<Order> = emptyList(),
    val customersMap: Map<String, Customer> = emptyMap(),
    val couriers: List<Courier> = emptyList(),
    val selectedCourierFilter: String = "all", // "all", "unassigned", or specific courierId
    val isAutoPolling: Boolean = true,
    val errorMessage: String? = null
)

@HiltViewModel
class OrdersViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(OrdersUiState())
    val uiState: StateFlow<OrdersUiState> = _uiState.asStateFlow()

    init {
        loadData(showLoading = true)
        startAutoPolling()
    }

    private fun startAutoPolling() {
        viewModelScope.launch {
            while (isActive) {
                delay(4000) // Auto-refresh orders every 4 seconds!
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

            val ordersResult = repository.getOrders()
            ordersResult.fold(
                onSuccess = { orders ->
                    val recentOrders = orders.take(50)
                    val customerIds = recentOrders.map { it.customerId }.distinct()

                    // Batch fetch customer details in 1 single HTTP request
                    val customersList = if (customerIds.isNotEmpty()) {
                        repository.getCustomersByIds(customerIds).getOrDefault(emptyList())
                    } else emptyList()

                    val customersMap = customersList.associateBy { it.id }
                    val couriersList = repository.getCouriers().getOrDefault(emptyList())

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            orders = orders,
                            customersMap = customersMap,
                            couriers = couriersList
                        )
                    }
                },
                onFailure = { error ->
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            errorMessage = error.localizedMessage ?: "Siparişler yüklenemedi"
                        )
                    }
                }
            )
        }
    }

    fun setCourierFilter(filterKey: String) {
        _uiState.update { it.copy(selectedCourierFilter = filterKey) }
    }

    fun updateStatus(orderId: String, newStatus: String, courierId: String? = null) {
        viewModelScope.launch {
            repository.updateOrderStatus(
                id = orderId,
                status = newStatus,
                courierId = courierId
            ).onSuccess {
                loadData(showLoading = false)
            }
        }
    }

    fun updateOrderFull(
        orderId: String,
        status: String,
        courierId: String?,
        paidAmount: Double?,
        paymentStatus: String?
    ) {
        viewModelScope.launch {
            repository.updateOrderStatus(
                id = orderId,
                status = status,
                courierId = courierId,
                paidAmount = paidAmount,
                paymentStatus = paymentStatus
            ).onSuccess {
                loadData(showLoading = false)
            }
        }
    }

    fun assignCourier(orderId: String, courierId: String) {
        viewModelScope.launch {
            repository.updateOrderStatus(
                id = orderId,
                status = "on_way",
                courierId = courierId
            ).onSuccess {
                loadData(showLoading = false)
            }
        }
    }
}
