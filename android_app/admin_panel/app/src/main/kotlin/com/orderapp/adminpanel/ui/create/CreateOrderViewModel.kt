package com.orderapp.adminpanel.ui.create

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

data class CreateOrderUiState(
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val customers: List<Customer> = emptyList(),
    val searchResults: List<Customer> = emptyList(),
    val categories: List<Category> = emptyList(),
    val products: List<Product> = emptyList(),
    val couriers: List<Courier> = emptyList(),
    val addresses: List<CustomerAddress> = emptyList(),
    val searchQuery: String = "",
    val selectedCustomer: Customer? = null,
    val selectedAddress: CustomerAddress? = null,
    val selectedCourier: Courier? = null,
    val selectedCategory: Category? = null,
    val cart: Map<Product, Double> = emptyMap(),
    val paymentMethod: String = "cash",
    val orderNote: String = "",
    val isGuestMode: Boolean = false,
    val guestName: String = "",
    val guestPhone: String = "",
    val guestAddress: String = "",
    val errorMessage: String? = null
)

@HiltViewModel
class CreateOrderViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(CreateOrderUiState())
    val uiState: StateFlow<CreateOrderUiState> = _uiState.asStateFlow()

    init {
        loadInitialData()
    }

    fun loadInitialData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            val categoriesResult = repository.getCategories()
            val productsResult = repository.getProducts()
            val couriersResult = repository.getCouriers()

            val categories = categoriesResult.getOrDefault(emptyList())
            val products = productsResult.getOrDefault(emptyList())
            val couriers = couriersResult.getOrDefault(emptyList())

            _uiState.update {
                it.copy(
                    isLoading = false,
                    categories = categories,
                    products = products,
                    couriers = couriers,
                    selectedCategory = categories.firstOrNull()
                )
            }
        }
    }

    fun searchCustomers(query: String) {
        _uiState.update { it.copy(searchQuery = query) }
        viewModelScope.launch {
            if (query.isBlank()) {
                _uiState.update { it.copy(searchResults = emptyList()) }
            } else {
                val results = repository.searchCustomers(query).getOrDefault(emptyList()).filter { !it.isGuest }
                val matched = results.find { it.phone.endsWith(query.takeLast(10)) || it.phone == query }
                _uiState.update {
                    it.copy(
                        searchResults = results,
                        guestPhone = if (matched == null && query.any { c -> c.isDigit() }) query else it.guestPhone
                    )
                }
                if (matched != null && _uiState.value.selectedCustomer == null) {
                    selectCustomer(matched)
                }
            }
        }
    }


    fun selectCustomer(customer: Customer) {
        _uiState.update { it.copy(selectedCustomer = customer, isGuestMode = false) }
        viewModelScope.launch {
            val addresses = repository.getAddresses(customer.id).getOrDefault(emptyList())
            _uiState.update {
                it.copy(
                    addresses = addresses,
                    selectedAddress = addresses.firstOrNull { a -> a.isDefault } ?: addresses.firstOrNull()
                )
            }
        }
    }

    fun selectAddress(address: CustomerAddress) {
        _uiState.update { it.copy(selectedAddress = address) }
    }

    fun addNewAddressToCustomer(addressText: String, onComplete: () -> Unit) {
        val customer = _uiState.value.selectedCustomer ?: return
        viewModelScope.launch {
            repository.createAddress(customerId = customer.id, addressText = addressText).onSuccess {
                selectCustomer(customer)
                onComplete()
            }
        }
    }

    fun setGuestMode(isGuest: Boolean) {
        _uiState.update { it.copy(isGuestMode = isGuest, selectedCustomer = if (isGuest) null else it.selectedCustomer) }
    }

    fun updateGuestDetails(name: String, phone: String, address: String) {
        _uiState.update {
            it.copy(
                guestName = name,
                guestPhone = phone,
                guestAddress = address
            )
        }
    }

    fun selectCategory(category: Category?) {
        _uiState.update { it.copy(selectedCategory = category) }
    }

    fun selectCourier(courier: Courier?) {
        _uiState.update { it.copy(selectedCourier = courier) }
    }

    fun setPaymentMethod(method: String) {
        _uiState.update { it.copy(paymentMethod = method) }
    }

    fun updateOrderNote(note: String) {
        _uiState.update { it.copy(orderNote = note) }
    }

    fun addToCart(product: Product) {
        val current = _uiState.value.cart.toMutableMap()
        current[product] = (current[product] ?: 0.0) + 1.0
        _uiState.update { it.copy(cart = current) }
    }

    fun removeFromCart(product: Product) {
        val current = _uiState.value.cart.toMutableMap()
        val qty = current[product] ?: 0.0
        if (qty > 1.0) {
            current[product] = qty - 1.0
        } else {
            current.remove(product)
        }
        _uiState.update { it.copy(cart = current) }
    }

    fun createOrder(onSuccess: () -> Unit) {
        val currentState = _uiState.value
        val cartItems = currentState.cart
        if (cartItems.isEmpty()) {
            _uiState.update { it.copy(errorMessage = "Lütfen en az bir ürün seçin") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, errorMessage = null) }

            val customerId: String
            val addressId: String?
            val addressText: String?

            if (currentState.isGuestMode) {
                val name = currentState.guestName.ifBlank { "Misafir Müşteri" }
                val phone = currentState.guestPhone.ifBlank { "GUEST_${System.currentTimeMillis()}" }
                
                val createdCustomer = repository.createCustomer(
                    name = name,
                    phone = phone,
                    notes = "Telefondan Tek Seferlik Misafir",
                    isGuest = true
                ).getOrNull()

                if (createdCustomer == null) {
                    _uiState.update { it.copy(isSaving = false, errorMessage = "Misafir müşteri oluşturulamadı") }
                    return@launch
                }
                customerId = createdCustomer.id
                addressId = null
                addressText = currentState.guestAddress.ifBlank { "Misafir Adresi" }
            } else {
                val customer = currentState.selectedCustomer
                if (customer == null) {
                    _uiState.update { it.copy(isSaving = false, errorMessage = "Lütfen bir müşteri seçin veya Misafir modunu kullanın") }
                    return@launch
                }
                customerId = customer.id
                addressId = currentState.selectedAddress?.id
                addressText = currentState.selectedAddress?.addressText ?: "Adres belirtilmedi"
            }

            var total = 0.0
            val orderItems = cartItems.map { (prod, qty) ->
                val rowTotal = prod.price * qty
                total += rowTotal
                CreateOrderItemRequest(
                    orderId = null,
                    productId = prod.id,
                    quantity = qty,
                    unit = prod.unit,
                    unitPrice = prod.price,
                    totalPrice = rowTotal
                )
            }

            repository.createOrderWithItems(
                customerId = customerId,
                addressId = addressId,
                addressText = addressText,
                courierId = currentState.selectedCourier?.id,
                totalAmount = total,
                paymentMethod = currentState.paymentMethod,
                notes = currentState.orderNote.takeIf { it.isNotBlank() },
                items = orderItems
            ).fold(
                onSuccess = {
                    _uiState.update { it.copy(isSaving = false) }
                    onSuccess()
                },
                onFailure = { error ->
                    _uiState.update { it.copy(isSaving = false, errorMessage = error.localizedMessage ?: "Sipariş kaydedilemedi") }
                }
            )
        }
    }
}

