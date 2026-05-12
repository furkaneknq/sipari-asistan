package com.orderapp.couriertracker.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.couriertracker.CourierTrackerApp
import kotlinx.coroutines.launch

/**
 * Giriş ekranı state yönetimi.
 * Supabase bağlantı ayarları + kurye telefon/şifre ile giriş.
 */
class LoginViewModel : ViewModel() {

    private val container = CourierTrackerApp.get().container
    private val prefs = container.prefs
    private val repo = container.repository

    // ─── State ───────────────────────────────────────────────────────

    var supabaseUrl by mutableStateOf("")
        private set
    var supabaseKey by mutableStateOf("")
        private set
    var phone by mutableStateOf("")
        private set
    var password by mutableStateOf("")
        private set

    var showConfig by mutableStateOf(false)
        private set
    var isLoading by mutableStateOf(false)
        private set
    var errorMessage by mutableStateOf<String?>(null)
        private set
    var connectionTestResult by mutableStateOf<Boolean?>(null)
        private set
    var loginSuccess by mutableStateOf(false)
        private set

    init {
        // DataStore'dan mevcut ayarları yükle
        viewModelScope.launch {
            prefs.supabaseUrl.collect { supabaseUrl = it }
        }
        viewModelScope.launch {
            prefs.supabaseKey.collect { supabaseKey = it }
        }
        viewModelScope.launch {
            prefs.isConfigured.collect { configured ->
                // İlk kurulumda config göster
                if (!configured) showConfig = true
            }
        }
    }

    // ─── Aksiyonlar ──────────────────────────────────────────────────

    fun onUrlChanged(value: String) { supabaseUrl = value }
    fun onKeyChanged(value: String) { supabaseKey = value }
    fun onPhoneChanged(value: String) { phone = value }
    fun onPasswordChanged(value: String) { password = value }
    fun toggleConfig() { showConfig = !showConfig }
    fun clearError() { errorMessage = null }

    /** Supabase bağlantı testi. */
    fun testConnection() {
        if (supabaseUrl.isBlank() || supabaseKey.isBlank()) {
            errorMessage = "URL ve API Key girilmelidir"
            return
        }
        viewModelScope.launch {
            isLoading = true
            connectionTestResult = null
            repo.testConnection(supabaseUrl, supabaseKey)
                .onSuccess { connectionTestResult = true }
                .onFailure {
                    connectionTestResult = false
                    errorMessage = "Bağlantı hatası: ${it.message}"
                }
            isLoading = false
        }
    }

    /** Bağlantı ayarlarını kaydet. */
    fun saveConnection() {
        if (supabaseUrl.isBlank() || supabaseKey.isBlank()) {
            errorMessage = "URL ve API Key girilmelidir"
            return
        }
        viewModelScope.launch {
            prefs.saveConnection(supabaseUrl, supabaseKey)
            showConfig = false
        }
    }

    /** Kurye girişi. */
    fun login() {
        if (phone.isBlank() || password.isBlank()) {
            errorMessage = "Telefon ve şifre girilmelidir"
            return
        }
        viewModelScope.launch {
            isLoading = true
            errorMessage = null

            // Önce ayarları kaydet (değişmiş olabilir)
            if (supabaseUrl.isNotBlank() && supabaseKey.isNotBlank()) {
                prefs.saveConnection(supabaseUrl, supabaseKey)
            }

            repo.login(phone, password)
                .onSuccess { response ->
                    if (response.success) {
                        loginSuccess = true
                    } else {
                        errorMessage = response.message ?: "Giriş başarısız"
                    }
                }
                .onFailure { e ->
                    errorMessage = "Bağlantı hatası: ${e.message}"
                }
            isLoading = false
        }
    }
}
