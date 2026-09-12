package com.orderapp.adminpanel.di

import android.net.Uri
import com.orderapp.adminpanel.BuildConfig
import com.orderapp.adminpanel.data.local.ConfigDataStore
import com.orderapp.adminpanel.data.remote.SupabaseApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(configDataStore: ConfigDataStore): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
        }

        val dynamicInterceptor = Interceptor { chain ->
            val originalRequest = chain.request()
            val savedUrl = runBlocking { configDataStore.getSupabaseUrl() }
            val savedKey = runBlocking { configDataStore.getSupabaseKey() }

            val cleanUrl = if (savedUrl.startsWith("http://") || savedUrl.startsWith("https://")) {
                savedUrl
            } else {
                "https://$savedUrl"
            }

            val targetHttpUrl = cleanUrl.toHttpUrlOrNull()
            
            val newHttpUrl = if (targetHttpUrl != null) {
                originalRequest.url.newBuilder()
                    .scheme(targetHttpUrl.scheme)
                    .host(targetHttpUrl.host)
                    .port(targetHttpUrl.port)
                    .build()
            } else {
                originalRequest.url
            }

            val newRequest = originalRequest.newBuilder()
                .url(newHttpUrl)
                .addHeader("apikey", savedKey)
                .addHeader("Authorization", "Bearer $savedKey")
                .addHeader("Content-Type", "application/json")
                .addHeader("Prefer", "return=representation")
                .build()

            chain.proceed(newRequest)
        }

        return OkHttpClient.Builder()
            .addInterceptor(logging)
            .addInterceptor(dynamicInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
        val json = Json {
            ignoreUnknownKeys = true
            isLenient = true
        }
        val contentType = "application/json".toMediaType()

        return Retrofit.Builder()
            .baseUrl("https://placeholder.supabase.co/rest/v1/")
            .client(okHttpClient)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
    }

    @Provides
    @Singleton
    fun provideSupabaseApi(retrofit: Retrofit): SupabaseApi {
        return retrofit.create(SupabaseApi::class.java)
    }
}

