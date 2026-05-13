package com.orderapp.callrelay.data.api

import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Supabase'in REST (PostgREST) API'sine doğrudan bağlanır.
 * Tek ihtiyacımız: incoming_calls tablosuna INSERT.
 *
 * Endpoint formu: {SUPABASE_URL}/rest/v1/incoming_calls
 *
 * Anon key gönderilirken iki başlık zorunlu:
 *   - apikey: <anon_key>
 *   - Authorization: Bearer <anon_key>
 *
 * RLS policy "incoming_calls_anon_insert" anon role'üne sadece INSERT izni verir.
 */
interface SupabaseApi {

    @POST("rest/v1/incoming_calls")
    suspend fun insertCall(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Header("Prefer") prefer: String = "return=minimal",
        @Body call: IncomingCallDto
    )

    /** Cihaz bilgisini phones tablosuna upsert eder (device_id UNIQUE). */
    @POST("rest/v1/phones")
    suspend fun upsertPhone(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Header("Prefer") prefer: String = "resolution=merge-duplicates",
        @Body phone: PhoneDto
    )

    /** Bağlantı testi: settings tablosundan tek satır okumayı dener (HEAD/GET). */
    @GET("rest/v1/{table}")
    suspend fun ping(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Path("table") table: String = "incoming_calls",
        @Query("limit") limit: Int = 0
    )
}

/** Supabase'e gönderilen JSON gövdesi. */
@Serializable
data class IncomingCallDto(
    val phone_number: String,
    val device_id: String,
    val created_at: String
)

/** phones tablosuna upsert edilecek cihaz bilgisi. */
@Serializable
data class PhoneDto(
    val device_id: String,
    val device_name: String,
    val is_active: Boolean = true
)
