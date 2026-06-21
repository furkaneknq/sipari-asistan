package com.orderapp.adminpanel.ui.create

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.model.*
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CreateOrderViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _customers = MutableStateFlow<List<Customer>>(emptyList())
    val customers: StateFlow<List<Customer>> = _customers

    private val _products = MutableStateFlow<List<Product>>(emptyList())
    val products: StateFlow<List<Product>> = _products

    private val _couriers = MutableStateFlow<List<Courier>>(emptyList())
    val couriers: StateFlow<List<Courier>> = _couriers

    private val _addresses = MutableStateFlow<List<CustomerAddress>>(emptyList())
    val addresses: StateFlow<List<CustomerAddress>> = _addresses

    private val _selectedCustomer = MutableStateFlow<Customer?>(null)
    val selectedCustomer: StateFlow<Customer?> = _selectedCustomer
    
    private val _cart = MutableStateFlow<Map<Product, Double>>(emptyMap())
    val cart: StateFlow<Map<Product, Double>> = _cart
    
    private val _selectedCourier = MutableStateFlow<Courier?>(null)
    val selectedCourier: StateFlow<Courier?> = _selectedCourier
    
    private val _selectedAddress = MutableStateFlow<CustomerAddress?>(null)
    val selectedAddress: StateFlow<CustomerAddress?> = _selectedAddress

    init {
        loadInitialData()
    }

    private fun loadInitialData() {
        viewModelScope.launch {
            try {
                _customers.value = repository.getCustomers()
                _products.value = repository.getProducts()
                _couriers.value = repository.getCouriers()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun selectCustomer(customer: Customer) {
        _selectedCustomer.value = customer
        viewModelScope.launch {
            try {
                _addresses.value = repository.getAddresses(customer.id)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun selectAddress(address: CustomerAddress) {
        _selectedAddress.value = address
    }

    fun selectCourier(courier: Courier) {
        _selectedCourier.value = courier
    }

    fun addToCart(product: Product) {
        val current = _cart.value.toMutableMap()
        current[product] = (current[product] ?: 0.0) + 1.0
        _cart.value = current
    }

    fun removeFromCart(product: Product) {
        val current = _cart.value.toMutableMap()
        val qty = current[product] ?: 0.0
        if (qty > 1.0) {
            current[product] = qty - 1.0
        } else {
            current.remove(product)
        }
        _cart.value = current
    }

    fun createOrder(onSuccess: () -> Unit) {
        val customer = _selectedCustomer.value ?: return
        val items = _cart.value
        if (items.isEmpty()) return
        
        var total = 0.0
        val orderItems = items.map { (prod, qty) ->
            val rowTotal = prod.price * qty
            total += rowTotal
            CreateOrderItemRequest(
                orderId = "",
                productId = prod.id,
                quantity = qty,
                unitPrice = prod.price,
                totalPrice = rowTotal
            )
        }
        
        viewModelScope.launch {
            try {
                repository.createOrderWithItems(
                    customerId = customer.id,
                    addressId = _selectedAddress.value?.id,
                    courierId = _selectedCourier.value?.id,
                    totalAmount = total,
                    items = orderItems
                )
                onSuccess()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
