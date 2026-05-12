package com.orderapp.couriertracker.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "courier_tracker_prefs")

/**
 * Supabase bağlantı bilgileri ve kurye oturum verileri.
 * Tüm okumalar Flow; Compose ile reaktif çalışır.
 */
class Prefs(private val context: Context) {

    // ─── Supabase bağlantı ───────────────────────────────────────────

    val supabaseUrl: Flow<String> = context.dataStore.data
        .map { it[SUPABASE_URL].orEmpty().trim().trimEnd('/') }

    val supabaseKey: Flow<String> = context.dataStore.data
        .map { it[SUPABASE_KEY].orEmpty().trim() }

    // ─── Kurye oturum bilgileri ──────────────────────────────────────

    val courierId: Flow<String> = context.dataStore.data
        .map { it[COURIER_ID].orEmpty() }

    val courierName: Flow<String> = context.dataStore.data
        .map { it[COURIER_NAME].orEmpty() }

    val courierPhone: Flow<String> = context.dataStore.data
        .map { it[COURIER_PHONE].orEmpty() }

    /** Kullanıcı oturum açmış mı? */
    val isLoggedIn: Flow<Boolean> = context.dataStore.data
        .map { !it[COURIER_ID].isNullOrBlank() }

    /** Supabase URL + Key girilmiş mi? */
    val isConfigured: Flow<Boolean> = context.dataStore.data
        .map {
            !it[SUPABASE_URL].isNullOrBlank() &&
                !it[SUPABASE_KEY].isNullOrBlank()
        }

    /** Servis açık mı (polling aktif)? */
    val serviceEnabled: Flow<Boolean> = context.dataStore.data
        .map { it[SERVICE_ENABLED] ?: false }

    // ─── Yazma işlemleri ─────────────────────────────────────────────

    suspend fun saveConnection(url: String, key: String) {
        context.dataStore.edit {
            it[SUPABASE_URL] = url.trim().trimEnd('/')
            it[SUPABASE_KEY] = key.trim()
        }
    }

    suspend fun saveLogin(courierId: String, name: String, phone: String) {
        context.dataStore.edit {
            it[COURIER_ID] = courierId
            it[COURIER_NAME] = name
            it[COURIER_PHONE] = phone
        }
    }

    suspend fun setServiceEnabled(enabled: Boolean) {
        context.dataStore.edit { it[SERVICE_ENABLED] = enabled }
    }

    suspend fun logout() {
        context.dataStore.edit {
            it.remove(COURIER_ID)
            it.remove(COURIER_NAME)
            it.remove(COURIER_PHONE)
            it[SERVICE_ENABLED] = false
        }
    }

    // ─── Senkron okuma (servis içinden) ──────────────────────────────

    suspend fun getUrlNow(): String = supabaseUrl.first()
    suspend fun getKeyNow(): String = supabaseKey.first()
    suspend fun getCourierIdNow(): String = courierId.first()

    companion object {
        private val SUPABASE_URL = stringPreferencesKey("supabase_url")
        private val SUPABASE_KEY = stringPreferencesKey("supabase_key")
        private val COURIER_ID = stringPreferencesKey("courier_id")
        private val COURIER_NAME = stringPreferencesKey("courier_name")
        private val COURIER_PHONE = stringPreferencesKey("courier_phone")
        private val SERVICE_ENABLED = booleanPreferencesKey("service_enabled")
    }
}
