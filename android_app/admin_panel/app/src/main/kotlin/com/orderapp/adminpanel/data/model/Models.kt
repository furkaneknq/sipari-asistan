package com.orderapp.adminpanel.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Customer(
    val id: String,
    val name: String,
    val phone: String
)

@Serializable
data class IncomingCall(
    val id: String,
    @SerialName("phone_number") val phoneNumber: String,
    @SerialName("customer_id") val customerId: String? = null,
    @SerialName("is_processed") val isProcessed: Boolean,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class Order(
    val id: String,
    @SerialName("order_number") val orderNumber: Int,
    @SerialName("customer_id") val customerId: String,
    @SerialName("courier_id") val courierId: String? = null,
    val status: String,
    @SerialName("total_amount") val totalAmount: Double,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class UpdateCallRequest(
    @SerialName("is_processed") val isProcessed: Boolean
)

@Serializable
data class UpdateOrderStatusRequest(
    val status: String
)

@Serializable
data class Product(
    val id: String,
    val name: String,
    val price: Double,
    @SerialName("category_id") val categoryId: String? = null
)

@Serializable
data class Category(
    val id: String,
    val name: String
)

@Serializable
data class Courier(
    val id: String,
    val name: String
)

@Serializable
data class CustomerAddress(
    val id: String,
    @SerialName("customer_id") val customerId: String,
    @SerialName("address_text") val addressText: String,
    val title: String? = null
)

@Serializable
data class CreateOrderRequest(
    @SerialName("customer_id") val customerId: String,
    @SerialName("address_id") val addressId: String? = null,
    @SerialName("courier_id") val courierId: String? = null,
    val status: String = "new",
    @SerialName("total_amount") val totalAmount: Double,
    @SerialName("payment_method") val paymentMethod: String = "cash"
)

@Serializable
data class CreateOrderItemRequest(
    @SerialName("order_id") val orderId: String,
    @SerialName("product_id") val productId: String,
    val quantity: Double,
    @SerialName("unit_price") val unitPrice: Double,
    @SerialName("total_price") val totalPrice: Double
)
