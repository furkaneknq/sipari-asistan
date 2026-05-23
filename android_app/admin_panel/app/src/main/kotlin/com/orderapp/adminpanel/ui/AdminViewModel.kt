package com.orderapp.adminpanel.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.AdminPanelApp
import com.orderapp.adminpanel.data.api.*
import kotlinx.coroutines.launch

class AdminViewModel : ViewModel() {

    private val prefs = AdminPanelApp.get().container.prefs

    // ─── UI State ────────────────────────────────────────────────────

    var isLoading by mutableStateOf(false)
        private set

    var errorMessage by mutableStateOf<String?>(null)
        private set

    // Siparişler
    var orders by mutableStateOf<List<OrderDto>>(emptyList())
        private set

    // Gelen aramalar
    var calls by mutableStateOf<List<IncomingCallDto>>(emptyList())
        private set

    // Müşteriler (arama sonucu)
    var customers by mutableStateOf<List<CustomerDto>>(emptyList())
        private set

    // Adresler (seçili müşteri için)
    var addresses by mutableStateOf<List<AddressDto>>(emptyList())
        private set

    // Ürünler & Kategoriler
    var categories by mutableStateOf<List<CategoryDto>>(emptyList())
        private set
    var products by mutableStateOf<List<ProductDto>>(emptyList())
        private set

    // Kuryeler
    var couriers by mutableStateOf<List<CourierDto>>(emptyList())
        private set

    // Sipariş kalemleri (düzenleme için)
    var orderItems by mutableStateOf<List<OrderItemDto>>(emptyList())
        private set

    // ─── API Helpers ─────────────────────────────────────────────────

    private suspend fun api(): SupabaseApi {
        val url = prefs.getUrlNow()
        return ApiClient.api(url)
    }

    private suspend fun key(): String = prefs.getKeyNow()
    private suspend fun auth(): String = "Bearer ${prefs.getKeyNow()}"

    // ─── Sipariş İşlemleri ───────────────────────────────────────────

    fun loadOrders(dateFilter: String? = null) {
        viewModelScope.launch {
            isLoading = true
            errorMessage = null
            try {
                val k = key()
                val a = auth()
                orders = if (dateFilter != null) {
                    api().getOrders(k, a, orderDate = "eq.$dateFilter")
                } else {
                    api().getOrders(k, a)
                }
            } catch (e: Exception) {
                errorMessage = "Siparişler yüklenemedi: ${e.message}"
            }
            isLoading = false
        }
    }

    fun updateOrderStatus(orderId: String, status: String) {
        viewModelScope.launch {
            try {
                val body = mutableMapOf<String, Any?>("status" to status)
                // Kurye atanmışsa ve durum on_way ise otomatik
                api().updateOrder(key(), auth(), id = "eq.$orderId", body = body)
                loadOrders()
            } catch (e: Exception) {
                errorMessage = "Durum güncellenemedi: ${e.message}"
            }
        }
    }

    fun assignCourier(orderId: String, courierId: String?) {
        viewModelScope.launch {
            try {
                val body = mutableMapOf<String, Any?>(
                    "courier_id" to courierId
                )
                if (courierId != null) {
                    body["status"] = "on_way"
                }
                api().updateOrder(key(), auth(), id = "eq.$orderId", body = body)
                loadOrders()
            } catch (e: Exception) {
                errorMessage = "Kurye atanamadı: ${e.message}"
            }
        }
    }

    fun updatePaidAmount(orderId: String, paidAmount: Double) {
        viewModelScope.launch {
            try {
                val body = mapOf<String, Any?>("paid_amount" to paidAmount)
                api().updateOrder(key(), auth(), id = "eq.$orderId", body = body)
                loadOrders()
            } catch (e: Exception) {
                errorMessage = "Ödeme güncellenemedi: ${e.message}"
            }
        }
    }

    // ─── Sipariş Oluşturma/Düzenleme ────────────────────────────────

    fun loadOrderItems(orderId: String) {
        viewModelScope.launch {
            try {
                orderItems = api().getOrderItems(key(), auth(), orderId = "eq.$orderId")
            } catch (e: Exception) {
                errorMessage = "Kalemler yüklenemedi: ${e.message}"
            }
        }
    }

    fun createOrder(
        customerId: String,
        addressId: String?,
        courierId: String?,
        paymentMethod: String?,
        notes: String?,
        items: List<OrderItemInput>,
        onSuccess: () -> Unit
    ) {
        viewModelScope.launch {
            isLoading = true
            try {
                val body = mutableMapOf<String, Any?>(
                    "customer_id" to customerId,
                    "status" to if (courierId != null) "on_way" else "new"
                )
                if (addressId != null) body["address_id"] = addressId
                if (courierId != null) body["courier_id"] = courierId
                if (paymentMethod != null) body["payment_method"] = paymentMethod
                if (!notes.isNullOrBlank()) body["notes"] = notes

                val created = api().createOrder(key(), auth(), body = body)
                val orderId = created.firstOrNull()?.id
                if (orderId != null && items.isNotEmpty()) {
                    val itemBodies = items.map { item ->
                        mutableMapOf<String, Any?>(
                            "order_id" to orderId,
                            "product_id" to item.productId,
                            "quantity" to item.quantity,
                            "unit" to item.unit,
                            "unit_price" to item.unitPrice
                        )
                    }
                    api().createOrderItems(key(), auth(), body = itemBodies)
                }
                loadOrders()
                onSuccess()
            } catch (e: Exception) {
                errorMessage = "Sipariş oluşturulamadı: ${e.message}"
            }
            isLoading = false
        }
    }

    fun updateOrder(
        orderId: String,
        customerId: String,
        addressId: String?,
        courierId: String?,
        paymentMethod: String?,
        notes: String?,
        items: List<OrderItemInput>,
        onSuccess: () -> Unit
    ) {
        viewModelScope.launch {
            isLoading = true
            try {
                val body = mutableMapOf<String, Any?>(
                    "customer_id" to customerId
                )
                body["address_id"] = addressId
                body["courier_id"] = courierId
                body["payment_method"] = paymentMethod
                body["notes"] = notes?.ifBlank { null }
                if (courierId != null) body["status"] = "on_way"

                api().updateOrder(key(), auth(), id = "eq.$orderId", body = body)

                // Kalemleri sil ve yeniden ekle
                api().deleteOrderItems(key(), auth(), orderId = "eq.$orderId")
                if (items.isNotEmpty()) {
                    val itemBodies = items.map { item ->
                        mutableMapOf<String, Any?>(
                            "order_id" to orderId,
                            "product_id" to item.productId,
                            "quantity" to item.quantity,
                            "unit" to item.unit,
                            "unit_price" to item.unitPrice
                        )
                    }
                    api().createOrderItems(key(), auth(), body = itemBodies)
                }
                loadOrders()
                onSuccess()
            } catch (e: Exception) {
                errorMessage = "Sipariş güncellenemedi: ${e.message}"
            }
            isLoading = false
        }
    }

    // ─── Gelen Aramalar ──────────────────────────────────────────────

    fun loadCalls() {
        viewModelScope.launch {
            try {
                calls = api().getIncomingCalls(key(), auth())
            } catch (e: Exception) {
                errorMessage = "Aramalar yüklenemedi: ${e.message}"
            }
        }
    }

    // ─── Müşteriler ──────────────────────────────────────────────────

    fun searchCustomers(query: String) {
        viewModelScope.launch {
            try {
                customers = if (query.isBlank()) {
                    api().getCustomers(key(), auth())
                } else {
                    val filter = "(name.ilike.%$query%,phone.ilike.%$query%)"
                    api().searchCustomers(key(), auth(), orFilter = filter)
                }
            } catch (e: Exception) {
                errorMessage = "Müşteriler yüklenemedi: ${e.message}"
            }
        }
    }

    fun loadCustomerAddresses(customerId: String) {
        viewModelScope.launch {
            try {
                addresses = api().getCustomerAddresses(
                    key(), auth(), customerId = "eq.$customerId"
                )
            } catch (e: Exception) {
                addresses = emptyList()
            }
        }
    }

    // ─── Ürünler & Kuryeler (referans verileri) ──────────────────────

    fun loadReferenceData() {
        viewModelScope.launch {
            try {
                val k = key()
                val a = auth()
                categories = api().getCategories(k, a)
                products = api().getProducts(k, a)
                couriers = api().getCouriers(k, a)
            } catch (e: Exception) {
                errorMessage = "Referans veriler yüklenemedi: ${e.message}"
            }
        }
    }

    fun clearError() {
        errorMessage = null
    }
}

data class OrderItemInput(
    val productId: String,
    val productName: String,
    val quantity: Double,
    val unit: String,
    val unitPrice: Double
)
