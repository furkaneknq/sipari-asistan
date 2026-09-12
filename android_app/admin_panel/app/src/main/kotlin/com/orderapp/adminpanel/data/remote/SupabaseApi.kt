package com.orderapp.adminpanel.data.remote

import com.orderapp.adminpanel.data.model.*
import retrofit2.http.*

interface SupabaseApi {
    @GET("incoming_calls?select=*&order=created_at.desc")
    suspend fun getIncomingCalls(): List<IncomingCall>

    @PATCH("incoming_calls")
    suspend fun updateIncomingCall(
        @Query("id") idQuery: String,
        @Body request: UpdateCallRequest
    ): List<IncomingCall>

    @GET("orders?select=*&order=created_at.desc")
    suspend fun getOrders(): List<Order>

    @GET("orders?select=*")
    suspend fun getOrderById(@Query("id") idQuery: String): List<Order>

    @GET("order_items?select=*")
    suspend fun getOrderItems(@Query("order_id") orderIdQuery: String): List<OrderItem>

    @PATCH("orders")
    suspend fun updateOrderStatus(
        @Query("id") idQuery: String,
        @Body request: UpdateOrderStatusRequest
    ): List<Order>

    @POST("orders")
    suspend fun createOrder(
        @Body request: CreateOrderRequest
    ): List<Order>

    @POST("order_items")
    suspend fun createOrderItems(
        @Body request: List<CreateOrderItemRequest>
    ): List<OrderItem>

    @GET("customers?select=*&order=name.asc")
    suspend fun getCustomers(
        @Header("Range") range: String = "0-4999"
    ): List<Customer>

    @GET("customers?select=*&order=name.asc")
    suspend fun searchCustomers(
        @Query("or") orQuery: String,
        @Header("Range") range: String = "0-100"
    ): List<Customer>

    @GET("customers?select=*")
    suspend fun findCustomerByPhone(
        @Query("phone") phoneQuery: String
    ): List<Customer>

    @GET("customers?select=*")
    suspend fun getCustomerById(
        @Query("id") idQuery: String
    ): List<Customer>

    @POST("customers")
    suspend fun createCustomer(
        @Body request: CreateCustomerRequest
    ): List<Customer>



    @GET("customers?select=*")
    suspend fun getCustomersByIds(
        @Query("id") inQuery: String
    ): List<Customer>

    @GET("customer_addresses?select=*")
    suspend fun getAddressesByCustomerIds(
        @Query("customer_id") inQuery: String
    ): List<CustomerAddress>

    @GET("customer_addresses?select=*")
    suspend fun getAddresses(@Query("customer_id") customerIdQuery: String): List<CustomerAddress>


    @POST("customer_addresses")
    suspend fun createCustomerAddress(
        @Body request: CreateAddressRequest
    ): List<CustomerAddress>

    @GET("categories?select=*&order=sort_order.asc")
    suspend fun getCategories(): List<Category>

    @GET("products?select=*&order=sort_order.asc")
    suspend fun getProducts(): List<Product>

    @GET("couriers?select=*")
    suspend fun getCouriers(): List<Courier>
}

