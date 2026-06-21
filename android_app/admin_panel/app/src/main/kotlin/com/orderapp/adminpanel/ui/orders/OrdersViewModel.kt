package com.orderapp.adminpanel.ui.orders

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.model.Order
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class OrdersViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _orders = MutableStateFlow<List<Order>>(emptyList())
    val orders: StateFlow<List<Order>> = _orders

    init {
        fetchOrders()
    }

    fun fetchOrders() {
        viewModelScope.launch {
            try {
                val list = repository.getOrders()
                _orders.value = list
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun updateStatus(id: String, newStatus: String) {
        viewModelScope.launch {
            try {
                repository.updateOrderStatus(id, newStatus)
                fetchOrders()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
