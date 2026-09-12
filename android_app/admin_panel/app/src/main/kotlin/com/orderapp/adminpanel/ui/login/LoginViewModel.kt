package com.orderapp.adminpanel.ui.login

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

data class LoginUiState(
    val url: String = "",
    val key: String = "",
    val isTesting: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    init {
        loadSavedConfig()
    }

    private fun loadSavedConfig() {
        viewModelScope.launch {
            val savedUrl = repository.getSupabaseUrl()
            val savedKey = repository.getSupabaseKey()
            _uiState.update { it.copy(url = savedUrl, key = savedKey) }
        }
    }

    fun onUrlChange(newUrl: String) {
        _uiState.update { it.copy(url = newUrl, errorMessage = null) }
    }

    fun onKeyChange(newKey: String) {
        _uiState.update { it.copy(key = newKey, errorMessage = null) }
    }

    fun testAndSaveConfig(onSuccess: () -> Unit) {
        val currentUrl = _uiState.value.url.trim()
        val currentKey = _uiState.value.key.trim()

        if (currentUrl.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Lütfen Supabase URL adresini girin") }
            return
        }
        if (currentKey.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Lütfen Supabase Secret Key anahtarını girin") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isTesting = true, errorMessage = null) }

            repository.testConnection(currentUrl, currentKey).fold(
                onSuccess = {
                    repository.saveConfig(currentUrl, currentKey)
                    _uiState.update { it.copy(isTesting = false) }
                    onSuccess()
                },
                onFailure = { error ->
                    _uiState.update {
                        it.copy(
                            isTesting = false,
                            errorMessage = "Bağlantı Başarısız! Lütfen URL ve Secret Key bilgilerini kontrol edin: ${error.localizedMessage}"
                        )
                    }
                }
            )
        }
    }
}
