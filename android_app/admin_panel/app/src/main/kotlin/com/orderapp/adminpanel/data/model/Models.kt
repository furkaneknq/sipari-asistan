package com.orderapp.adminpanel.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Customer(
    val id: String,
    val name: String,
    val phone: String,
    val email: String? = null,
    val notes: String? = null,
    @SerialName("is_guest") val isGuest: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null
)

@Serializable
data class CustomerAddress(
    val id: String,
    @SerialName("customer_id") val customerId: String,
    val title: String? = null,
    @SerialName("address_text") val addressText: String,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerialName("is_default") val isDefault: Boolean = false
)

@Serializable
data class Category(
    val id: String,
    val name: String,
    @SerialName("sort_order") val sortOrder: Int = 0,
    @SerialName("is_active") val isActive: Boolean = true,
    val color: String? = null
)

@Serializable
data class Product(
    val id: String,
    @SerialName("category_id") val categoryId: String? = null,
    val name: String,
    val price: Double,
    val unit: String = "adet",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("sort_order") val sortOrder: Int = 0
)

@Serializable
data class Courier(
    val id: String,
    val name: String,
    val phone: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("current_latitude") val currentLatitude: Double? = null,
    @SerialName("current_longitude") val currentLongitude: Double? = null
)

@Serializable
data class Order(
    val id: String,
    @SerialName("order_number") val orderNumber: Int = 0,
    @SerialName("customer_id") val customerId: String,
    @SerialName("address_id") val addressId: String? = null,
    @SerialName("address_text") val addressText: String? = null,
    @SerialName("courier_id") val courierId: String? = null,
    val status: String = "new",
    @SerialName("order_date") val orderDate: String? = null,
    @SerialName("total_amount") val totalAmount: Double = 0.0,
    @SerialName("paid_amount") val paidAmount: Double = 0.0,
    @SerialName("payment_method") val paymentMethod: String? = "cash",
    @SerialName("payment_status") val paymentStatus: String? = "pending",
    val notes: String? = null,
    @SerialName("created_at") val createdAt: String? = null
)

@Serializable
data class OrderItem(
    val id: String,
    @SerialName("order_id") val orderId: String,
    @SerialName("product_id") val productId: String? = null,
    val quantity: Double = 1.0,
    val unit: String = "adet",
    @SerialName("unit_price") val unitPrice: Double = 0.0,
    @SerialName("total_price") val totalPrice: Double = 0.0,
    val notes: String? = null
)

@Serializable
data class IncomingCall(
    val id: String,
    @SerialName("phone_number") val phoneNumber: String,
    @SerialName("device_id") val deviceId: String? = null,
    @SerialName("customer_id") val customerId: String? = null,
    @SerialName("is_processed") val isProcessed: Boolean = false,
    @SerialName("is_unanswered") val isUnanswered: Boolean = false,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class CreateCustomerRequest(
    val name: String,
    val phone: String,
    val notes: String? = null,
    @SerialName("is_guest") val isGuest: Boolean = false
)

@Serializable
data class CreateAddressRequest(
    @SerialName("customer_id") val customerId: String,
    val title: String? = null,
    @SerialName("address_text") val addressText: String,
    @SerialName("is_default") val isDefault: Boolean = true
)

@Serializable
data class CreateOrderRequest(
    @SerialName("customer_id") val customerId: String,
    @SerialName("address_id") val addressId: String? = null,
    @SerialName("address_text") val addressText: String? = null,
    @SerialName("courier_id") val courierId: String? = null,
    val status: String = "new",
    @SerialName("total_amount") val totalAmount: Double,
    @SerialName("paid_amount") val paidAmount: Double = 0.0,
    @SerialName("payment_method") val paymentMethod: String = "cash",
    @SerialName("payment_status") val paymentStatus: String = "pending",
    val notes: String? = null
)

@Serializable
data class CreateOrderItemRequest(
    @SerialName("order_id") val orderId: String? = null,
    @SerialName("product_id") val productId: String? = null,
    val quantity: Double,
    val unit: String = "adet",
    @SerialName("unit_price") val unitPrice: Double,
    @SerialName("total_price") val totalPrice: Double,
    val notes: String? = null
)

@Serializable
data class UpdateOrderStatusRequest(
    val status: String,
    @SerialName("courier_id") val courierId: String? = null,
    @SerialName("paid_amount") val paidAmount: Double? = null,
    @SerialName("payment_status") val paymentStatus: String? = null
)

@Serializable
data class UpdateCallRequest(
    @SerialName("is_processed") val isProcessed: Boolean,
    @SerialName("is_unanswered") val isUnanswered: Boolean? = null
)

