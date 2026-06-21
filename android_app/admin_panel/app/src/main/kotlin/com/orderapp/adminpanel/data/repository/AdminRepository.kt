package com.orderapp.adminpanel.data.repository

import com.orderapp.adminpanel.data.model.*
import com.orderapp.adminpanel.data.remote.SupabaseApi
import javax.inject.Inject

class AdminRepository @Inject constructor(
    private val api: SupabaseApi
) {
    suspend fun getIncomingCalls(): List<IncomingCall> = api.getIncomingCalls()

    suspend fun markCallProcessed(id: String): IncomingCall? {
        val result = api.updateIncomingCall("eq.$id", UpdateCallRequest(true))
        return result.firstOrNull()
    }

    suspend fun getOrders(): List<Order> = api.getOrders()

    suspend fun updateOrderStatus(id: String, status: String): Order? {
        val result = api.updateOrderStatus("eq.$id", UpdateOrderStatusRequest(status))
        return result.firstOrNull()
    }

    suspend fun getCustomers(): List<Customer> = api.getCustomers()

    suspend fun getCategories(): List<Category> = api.getCategories()

    suspend fun getProducts(): List<Product> = api.getProducts()

    suspend fun getCouriers(): List<Courier> = api.getCouriers()

    suspend fun getAddresses(customerId: String): List<CustomerAddress> = api.getAddresses("eq.$customerId")

    suspend fun createOrderWithItems(
        customerId: String,
        addressId: String?,
        courierId: String?,
        totalAmount: Double,
        items: List<CreateOrderItemRequest>
    ): Order? {
        // 1. Create order
        val orderReq = CreateOrderRequest(
            customerId = customerId,
            addressId = addressId,
            courierId = courierId,
            totalAmount = totalAmount
        )
        val createdOrders = api.createOrder(orderReq)
        val newOrder = createdOrders.firstOrNull() ?: return null

        // 2. Create order items
        if (items.isNotEmpty()) {
            val itemsWithOrderId = items.map { it.copy(orderId = newOrder.id) }
            api.createOrderItems(itemsWithOrderId)
        }
        
        return newOrder
    }
}
