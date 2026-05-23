package com.orderapp.adminpanel.data.api

import retrofit2.http.*

/**
 * Supabase PostgREST API — Admin Panel.
 * service_role key ile RLS bypass edilerek doğrudan tablo erişimi yapılır.
 */
interface SupabaseApi {

    // ─── Siparişler ───────────────────────────────────────────────────

    @GET("rest/v1/orders")
    suspend fun getOrders(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("select") select: String = "*, customers(id,name,phone), customer_addresses(id,address_text), couriers(id,name,phone)",
        @Query("order") order: String = "created_at.desc",
        @Query("order_date") orderDate: String? = null,
        @Query("limit") limit: Int = 200
    ): List<OrderDto>

    @GET("rest/v1/order_items")
    suspend fun getOrderItems(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("select") select: String = "*, products(id,name)",
        @Query("order_id") orderId: String,
        @Query("order") order: String = "id"
    ): List<OrderItemDto>

    @PATCH("rest/v1/orders")
    suspend fun updateOrder(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Header("Prefer") prefer: String = "return=minimal",
        @Query("id") id: String,
        @Body body: Map<String, @JvmSuppressWildcards Any?>
    )

    @POST("rest/v1/orders")
    suspend fun createOrder(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Header("Prefer") prefer: String = "return=representation",
        @Body body: Map<String, @JvmSuppressWildcards Any?>
    ): List<OrderDto>

    @POST("rest/v1/order_items")
    suspend fun createOrderItems(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Header("Prefer") prefer: String = "return=minimal",
        @Body body: List<Map<String, @JvmSuppressWildcards Any?>>
    )

    @DELETE("rest/v1/order_items")
    suspend fun deleteOrderItems(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("order_id") orderId: String
    )

    // ─── Müşteriler ──────────────────────────────────────────────────

    @GET("rest/v1/customers")
    suspend fun getCustomers(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("select") select: String = "*",
        @Query("is_guest") isGuest: String = "eq.false",
        @Query("order") order: String = "name",
        @Query("limit") limit: Int = 200
    ): List<CustomerDto>

    @GET("rest/v1/customers")
    suspend fun searchCustomers(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("select") select: String = "*",
        @Query("is_guest") isGuest: String = "eq.false",
        @Query("or") orFilter: String,
        @Query("order") order: String = "name",
        @Query("limit") limit: Int = 50
    ): List<CustomerDto>

    @GET("rest/v1/customer_addresses")
    suspend fun getCustomerAddresses(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("customer_id") customerId: String,
        @Query("order") order: String = "is_default.desc,created_at"
    ): List<AddressDto>

    // ─── Ürünler ─────────────────────────────────────────────────────

    @GET("rest/v1/categories")
    suspend fun getCategories(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("order") order: String = "sort_order,name"
    ): List<CategoryDto>

    @GET("rest/v1/products")
    suspend fun getProducts(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("select") select: String = "*, categories(id,name)",
        @Query("order") order: String = "name"
    ): List<ProductDto>

    // ─── Kuryeler ────────────────────────────────────────────────────

    @GET("rest/v1/couriers")
    suspend fun getCouriers(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("is_active") isActive: String = "eq.true",
        @Query("order") order: String = "name"
    ): List<CourierDto>

    // ─── Gelen Aramalar ──────────────────────────────────────────────

    @GET("rest/v1/incoming_calls")
    suspend fun getIncomingCalls(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("select") select: String = "*, customers(id,name,phone)",
        @Query("order") order: String = "created_at.desc",
        @Query("limit") limit: Int = 50
    ): List<IncomingCallDto>

    // ─── Bağlantı Testi ──────────────────────────────────────────────

    @GET("rest/v1/settings")
    suspend fun ping(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("limit") limit: Int = 0
    )
}
