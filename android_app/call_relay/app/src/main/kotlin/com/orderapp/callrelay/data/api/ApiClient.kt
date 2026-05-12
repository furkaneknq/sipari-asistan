package com.orderapp.callrelay.data.api

import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Supabase URL'i runtime'da değiştiği için Retrofit instance'ı önbellekleriz.
 * (URL değişince yeniden kurulur.)
 */
object ApiClient {

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
    }

    private var cachedBaseUrl: String? = null
    private var cachedApi: SupabaseApi? = null

    fun api(baseUrl: String): SupabaseApi {
        val normalized = baseUrl.trim().trimEnd('/') + "/"
        if (normalized == cachedBaseUrl && cachedApi != null) {
            return cachedApi!!
        }

        val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(
                HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BASIC
                }
            )
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(normalized)
            .client(client)
            .addConverterFactory(
                json.asConverterFactory("application/json".toMediaType())
            )
            .build()

        return retrofit.create(SupabaseApi::class.java).also {
            cachedBaseUrl = normalized
            cachedApi = it
        }
    }
}
