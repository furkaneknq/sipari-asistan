package com.orderapp.callrelay.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "call_relay_prefs")

/**
 * Supabase URL/Anon Key ve cihaz ayarlarını kalıcı saklar.
 * Tüm okumalar Flow olarak yayınlanır → UI Compose ile reaktif çalışır.
 */
class Prefs(private val context: Context) {

    val supabaseUrl: Flow<String> = context.dataStore.data
        .map { it[SUPABASE_URL].orEmpty().trim().trimEnd('/') }

    val supabaseKey: Flow<String> = context.dataStore.data
        .map { it[SUPABASE_KEY].orEmpty().trim() }

    val deviceName: Flow<String> = context.dataStore.data
        .map { it[DEVICE_NAME].orEmpty() }

    val deviceId: Flow<String> = context.dataStore.data
        .map { it[DEVICE_ID].orEmpty() }

    /** Servis kullanıcı tarafından açıldı/kapatıldı bilgisi (yeniden başlatınca da uygulanır). */
    val serviceEnabled: Flow<Boolean> = context.dataStore.data
        .map { it[SERVICE_ENABLED] ?: false }

    /** İlk kurulum tamamlandı mı? */
    val isConfigured: Flow<Boolean> = context.dataStore.data
        .map {
            !it[SUPABASE_URL].isNullOrBlank() &&
                !it[SUPABASE_KEY].isNullOrBlank() &&
                !it[DEVICE_NAME].isNullOrBlank()
        }

    suspend fun saveConnection(url: String, key: String, name: String, id: String) {
        context.dataStore.edit {
            it[SUPABASE_URL] = url.trim().trimEnd('/')
            it[SUPABASE_KEY] = key.trim()
            it[DEVICE_NAME] = name.trim()
            it[DEVICE_ID] = id
        }
    }

    suspend fun setServiceEnabled(enabled: Boolean) {
        context.dataStore.edit { it[SERVICE_ENABLED] = enabled }
    }

    companion object {
        private val SUPABASE_URL = stringPreferencesKey("supabase_url")
        private val SUPABASE_KEY = stringPreferencesKey("supabase_key")
        private val DEVICE_NAME = stringPreferencesKey("device_name")
        private val DEVICE_ID = stringPreferencesKey("device_id")
        private val SERVICE_ENABLED = booleanPreferencesKey("service_enabled")
    }
}
