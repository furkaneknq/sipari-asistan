package com.orderapp.adminpanel.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ─── Sipariş ─────────────────────────────────────────────────────────

@Serializable
data class OrderDto(
    val id: String,
    @SerialName("order_number") val orderNumber: Int = 0,
    val status: String = "new",
    @SerialName("order_date") val orderDate: String = "",
    @SerialName("delivery_time") val deliveryTime: String? = null,
    @SerialName("total_amount") val totalAmount: Double = 0.0,
    @SerialName("paid_amount") val paidAmount: Double = 0.0,
    @SerialName("payment_method") val paymentMethod: String? = null,
    @SerialName("payment_status") val paymentStatus: String = "pending",
    val notes: String? = null,
    @SerialName("customer_id") val customerId: String? = null,
    @SerialName("address_id") val addressId: String? = null,
    @SerialName("courier_id") val courierId: String? = null,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
    val customers: CustomerDto? = null,
    @SerialName("customer_addresses") val customerAddresses: AddressDto? = null,
    val couriers: CourierDto? = null
)

@Serializable
data class OrderItemDto(
    val id: String = "",
    @SerialName("order_id") val orderId: String = "",
    @SerialName("product_id") val productId: String? = null,
    val quantity: Double = 1.0,
    val unit: String = "adet",
    @SerialName("unit_price") val unitPrice: Double = 0.0,
    @SerialName("total_price") val totalPrice: Double = 0.0,
    val notes: String? = null,
    val products: ProductRefDto? = null
)

@Serializable
data class ProductRefDto(
    val id: String,
    val name: String
)

// ─── Müşteri ─────────────────────────────────────────────────────────

@Serializable
data class CustomerDto(
    val id: String,
    val name: String = "",
    val phone: String = "",
    val email: String? = null,
    val notes: String? = null,
    @SerialName("is_guest") val isGuest: Boolean = false
)

// ─── Adres ───────────────────────────────────────────────────────────

@Serializable
data class AddressDto(
    val id: String,
    @SerialName("customer_id") val customerId: String = "",
    val title: String? = null,
    @SerialName("address_text") val addressText: String = "",
    @SerialName("is_default") val isDefault: Boolean = false,
    val latitude: Double? = null,
    val longitude: Double? = null
)

// ─── Ürün & Kategori ─────────────────────────────────────────────────

@Serializable
data class CategoryDto(
    val id: String,
    val name: String = "",
    @SerialName("sort_order") val sortOrder: Int = 0
)

@Serializable
data class ProductDto(
    val id: String,
    val name: String = "",
    @SerialName("category_id") val categoryId: String? = null,
    val price: Double = 0.0,
    val unit: String = "adet",
    @SerialName("is_active") val isActive: Boolean = true,
    val categories: CategoryRefDto? = null
)

@Serializable
data class CategoryRefDto(
    val id: String,
    val name: String
)

// ─── Kurye ───────────────────────────────────────────────────────────

@Serializable
data class CourierDto(
    val id: String,
    val name: String = "",
    val phone: String = "",
    @SerialName("is_active") val isActive: Boolean = true
)

// ─── Gelen Arama ─────────────────────────────────────────────────────

@Serializable
data class IncomingCallDto(
    val id: String,
    @SerialName("phone_number") val phoneNumber: String = "",
    @SerialName("customer_id") val customerId: String? = null,
    @SerialName("is_processed") val isProcessed: Boolean = false,
    @SerialName("created_at") val createdAt: String = "",
    val customers: CustomerDto? = null
)
