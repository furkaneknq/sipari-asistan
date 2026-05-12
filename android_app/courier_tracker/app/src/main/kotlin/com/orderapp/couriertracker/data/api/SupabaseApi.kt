package com.orderapp.couriertracker.data.api

import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.GET
import retrofit2.http.Query

/**
 * Supabase PostgREST API tanımları.
 * Tüm işlemler RPC fonksiyonları üzerinden yapılır (güvenlik).
 *
 * Her istekte iki başlık zorunlu:
 *   - apikey: <anon_key>
 *   - Authorization: Bearer <anon_key>
 */
interface SupabaseApi {

    /** Kurye girişi — telefon + şifre ile doğrulama. */
    @POST("rest/v1/rpc/courier_login")
    suspend fun courierLogin(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Body body: Map<String, String>
    ): CourierLoginResponse

    /** Kuryeye atanmış günlük siparişleri getir. */
    @POST("rest/v1/rpc/courier_get_orders")
    suspend fun getOrders(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Body body: Map<String, String>
    ): List<OrderDto>

    /** Sipariş durumunu güncelle. */
    @POST("rest/v1/rpc/courier_update_order_status")
    suspend fun updateOrderStatus(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Body body: Map<String, String>
    ): RpcResponse

    /** Ödenen tutarı güncelle. */
    @POST("rest/v1/rpc/courier_update_paid_amount")
    suspend fun updatePaidAmount(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Body body: Map<String, String>
    ): RpcResponse

    /** Kurye konumunu güncelle. */
    @POST("rest/v1/rpc/courier_update_location")
    suspend fun updateLocation(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Body body: Map<String, String>
    ): RpcResponse

    /** Günlük özet (teslim edilen sipariş sayısı + toplam tutar). */
    @POST("rest/v1/rpc/courier_daily_summary")
    suspend fun dailySummary(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Body body: Map<String, String>
    ): DailySummaryResponse

    /** Bağlantı testi: herhangi bir tabloya 0 satırlık GET. */
    @GET("rest/v1/settings")
    suspend fun ping(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Query("limit") limit: Int = 0
    )
}
