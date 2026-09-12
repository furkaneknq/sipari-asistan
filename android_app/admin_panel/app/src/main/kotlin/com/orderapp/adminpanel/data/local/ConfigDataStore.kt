package com.orderapp.adminpanel.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "admin_config")

@Singleton
class ConfigDataStore @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        private val KEY_SUPABASE_URL = stringPreferencesKey("supabase_url")
        private val KEY_SUPABASE_KEY = stringPreferencesKey("supabase_key")
        
        const val DEFAULT_URL = "https://xgvlgmikxchpttydtelb.supabase.co"
        const val DEFAULT_KEY = "sb_secret_ifcYo6gAkhIJ9NR_936R-g_ITqPSBJE"
    }

    val supabaseUrlFlow: Flow<String> = context.dataStore.data.map { preferences ->
        preferences[KEY_SUPABASE_URL] ?: DEFAULT_URL
    }

    val supabaseKeyFlow: Flow<String> = context.dataStore.data.map { preferences ->
        preferences[KEY_SUPABASE_KEY] ?: DEFAULT_KEY
    }

    suspend fun getSupabaseUrl(): String {
        return context.dataStore.data.first()[KEY_SUPABASE_URL] ?: DEFAULT_URL
    }

    suspend fun getSupabaseKey(): String {
        return context.dataStore.data.first()[KEY_SUPABASE_KEY] ?: DEFAULT_KEY
    }

    suspend fun saveConfig(url: String, key: String) {
        val cleanUrl = url.trim().removeSuffix("/")
        val cleanKey = key.trim()
        context.dataStore.edit { preferences ->
            preferences[KEY_SUPABASE_URL] = cleanUrl
            preferences[KEY_SUPABASE_KEY] = cleanKey
        }
    }

    suspend fun clearConfig() {
        context.dataStore.edit { preferences ->
            preferences.remove(KEY_SUPABASE_URL)
            preferences.remove(KEY_SUPABASE_KEY)
        }
    }

    suspend fun hasConfig(): Boolean {
        val url = getSupabaseUrl()
        val key = getSupabaseKey()
        return url.isNotBlank() && key.isNotBlank()
    }
}
