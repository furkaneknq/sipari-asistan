package com.orderapp.adminpanel.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val url: String = "",
    val key: String = "",
    val isTesting: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        loadConfig()
    }

    fun loadConfig() {
        viewModelScope.launch {
            val url = repository.getSupabaseUrl()
            val key = repository.getSupabaseKey()
            _uiState.update { it.copy(url = url, key = key) }
        }
    }

    fun updateUrl(url: String) {
        _uiState.update { it.copy(url = url, message = null) }
    }

    fun updateKey(key: String) {
        _uiState.update { it.copy(key = key, message = null) }
    }

    fun saveAndTestConfig() {
        val url = _uiState.value.url.trim()
        val key = _uiState.value.key.trim()

        if (url.isBlank() || key.isBlank()) {
            _uiState.update { it.copy(message = "Lütfen tüm alanları doldurun", isError = true) }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isTesting = true, message = null) }
            repository.testConnection(url, key).fold(
                onSuccess = {
                    repository.saveConfig(url, key)
                    _uiState.update { it.copy(isTesting = false, message = "✓ Bağlantı başarılı! Ayarlar kaydedildi.", isError = false) }
                },
                onFailure = { error ->
                    _uiState.update { it.copy(isTesting = false, message = "Bağlantı hatası: ${error.localizedMessage}", isError = true) }
                }
            )
        }
    }

    fun logout(onLogout: () -> Unit) {
        viewModelScope.launch {
            repository.clearConfig()
            onLogout()
        }
    }
}
