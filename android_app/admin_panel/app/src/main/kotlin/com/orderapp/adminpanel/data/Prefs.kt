package com.orderapp.adminpanel.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "admin_panel_prefs")

class Prefs(private val context: Context) {

    val supabaseUrl: Flow<String> = context.dataStore.data
        .map { it[SUPABASE_URL].orEmpty().trim().trimEnd('/') }

    val supabaseKey: Flow<String> = context.dataStore.data
        .map { it[SUPABASE_KEY].orEmpty().trim() }

    val isConfigured: Flow<Boolean> = context.dataStore.data
        .map {
            !it[SUPABASE_URL].isNullOrBlank() &&
                !it[SUPABASE_KEY].isNullOrBlank()
        }

    suspend fun saveConnection(url: String, key: String) {
        context.dataStore.edit {
            it[SUPABASE_URL] = url.trim().trimEnd('/')
            it[SUPABASE_KEY] = key.trim()
        }
    }

    suspend fun getUrlNow(): String = supabaseUrl.first()
    suspend fun getKeyNow(): String = supabaseKey.first()

    companion object {
        private val SUPABASE_URL = stringPreferencesKey("supabase_url")
        private val SUPABASE_KEY = stringPreferencesKey("supabase_key")
    }
}
