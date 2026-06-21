package com.orderapp.adminpanel.data.remote

import com.orderapp.adminpanel.data.model.Customer
import com.orderapp.adminpanel.data.model.IncomingCall
import com.orderapp.adminpanel.data.model.Order
import com.orderapp.adminpanel.data.model.UpdateCallRequest
import com.orderapp.adminpanel.data.model.UpdateOrderStatusRequest
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.Query

interface SupabaseApi {
    @GET("incoming_calls?select=*&order=created_at.desc")
    suspend fun getIncomingCalls(): List<IncomingCall>

    @GET("orders?select=*&order=created_at.desc")
    suspend fun getOrders(): List<Order>

    @GET("customers?select=*")
    suspend fun getCustomers(): List<Customer>

    @PATCH("incoming_calls")
    suspend fun updateIncomingCall(
        @Query("id") idQuery: String, // e.g. "eq.123-uuid"
        @Body request: UpdateCallRequest
    ): List<IncomingCall>

    @PATCH("orders")
    suspend fun updateOrderStatus(
        @Query("id") idQuery: String,
        @Body request: UpdateOrderStatusRequest
    ): List<Order>

    @GET("categories?select=*&order=sort_order.asc")
    suspend fun getCategories(): List<Category>

    @GET("products?select=*&order=sort_order.asc")
    suspend fun getProducts(): List<Product>

    @GET("couriers?select=*")
    suspend fun getCouriers(): List<Courier>

    @GET("customer_addresses?select=*")
    suspend fun getAddresses(@Query("customer_id") customerIdQuery: String): List<CustomerAddress>

    @retrofit2.http.POST("orders")
    suspend fun createOrder(
        @Body request: CreateOrderRequest
    ): List<Order>

    @retrofit2.http.POST("order_items")
    suspend fun createOrderItems(
        @Body request: List<CreateOrderItemRequest>
    )
}
