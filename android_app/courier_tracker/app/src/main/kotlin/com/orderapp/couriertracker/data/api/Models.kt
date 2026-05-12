package com.orderapp.couriertracker.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ─── Giriş Yanıtı ──────────────────────────────────────────────────────

@Serializable
data class CourierLoginResponse(
    val success: Boolean,
    val message: String? = null,
    @SerialName("courier_id") val courierId: String? = null,
    val name: String? = null,
    val phone: String? = null
)

// ─── Genel RPC Yanıtı ──────────────────────────────────────────────────

@Serializable
data class RpcResponse(
    val success: Boolean,
    val message: String? = null
)

// ─── Günlük Özet ────────────────────────────────────────────────────────

@Serializable
data class DailySummaryResponse(
    @SerialName("delivered_count") val deliveredCount: Int = 0,
    @SerialName("total_amount") val totalAmount: Double = 0.0,
    @SerialName("paid_amount") val paidAmount: Double = 0.0
)

// ─── Sipariş DTO (courier_get_orders RPC'den dönen) ─────────────────────

@Serializable
data class OrderDto(
    val id: String,
    @SerialName("order_number") val orderNumber: Int,
    val status: String,
    @SerialName("order_date") val orderDate: String,
    @SerialName("delivery_time") val deliveryTime: String? = null,
    @SerialName("total_amount") val totalAmount: Double = 0.0,
    @SerialName("paid_amount") val paidAmount: Double = 0.0,
    @SerialName("payment_method") val paymentMethod: String? = null,
    @SerialName("payment_status") val paymentStatus: String = "pending",
    val notes: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    val customer: CustomerDto? = null,
    val address: AddressDto? = null,
    val items: List<OrderItemDto>? = null
)

@Serializable
data class CustomerDto(
    val id: String,
    val name: String,
    val phone: String
)

@Serializable
data class AddressDto(
    val id: String,
    val title: String? = null,
    @SerialName("address_text") val addressText: String,
    val latitude: Double? = null,
    val longitude: Double? = null
)

@Serializable
data class OrderItemDto(
    val id: String,
    val quantity: Double = 1.0,
    val unit: String = "adet",
    @SerialName("unit_price") val unitPrice: Double = 0.0,
    @SerialName("total_price") val totalPrice: Double = 0.0,
    val notes: String? = null,
    @SerialName("product_name") val productName: String = ""
)
