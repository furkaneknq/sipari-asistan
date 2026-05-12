package com.orderapp.callrelay.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.orderapp.callrelay.CallRelayApp
import com.orderapp.callrelay.data.Prefs
import com.orderapp.callrelay.data.repository.CallRepository
import com.orderapp.callrelay.util.DeviceIdProvider
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SetupUiState(
    val url: String = "",
    val apiKey: String = "",
    val deviceName: String = "",
    val testing: Boolean = false,
    val saving: Boolean = false,
    val testResult: TestResult? = null
)

sealed interface TestResult {
    object Success : TestResult
    data class Failure(val message: String) : TestResult
}

class SetupViewModel(
    private val prefs: Prefs,
    private val repo: CallRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SetupUiState())
    val uiState: StateFlow<SetupUiState> = _uiState.asStateFlow()

    init {
        // Mevcut kayıtlı değerleri yükle (varsa)
        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    url = prefs.supabaseUrl.first(),
                    apiKey = prefs.supabaseKey.first(),
                    deviceName = prefs.deviceName.first()
                )
            }
        }
    }

    fun updateUrl(value: String) = _uiState.update { it.copy(url = value) }
    fun updateKey(value: String) = _uiState.update { it.copy(apiKey = value) }
    fun updateDeviceName(value: String) = _uiState.update { it.copy(deviceName = value) }
    fun clearTestResult() = _uiState.update { it.copy(testResult = null) }

    fun testConnection() {
        val s = _uiState.value
        if (s.url.isBlank() || s.apiKey.isBlank()) {
            _uiState.update {
                it.copy(testResult = TestResult.Failure("URL ve API Key boş olamaz"))
            }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(testing = true, testResult = null) }
            val result = repo.testConnection(s.url, s.apiKey)
            _uiState.update {
                it.copy(
                    testing = false,
                    testResult = result.fold(
                        onSuccess = { TestResult.Success },
                        onFailure = { e -> TestResult.Failure(e.message ?: "Bağlantı hatası") }
                    )
                )
            }
        }
    }

    fun save(onDone: () -> Unit) {
        val s = _uiState.value
        if (s.url.isBlank() || s.apiKey.isBlank() || s.deviceName.isBlank()) {
            _uiState.update {
                it.copy(testResult = TestResult.Failure("Tüm alanları doldurun"))
            }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(saving = true) }
            val existingId = prefs.deviceId.first()
            val deviceId = if (existingId.isBlank()) {
                DeviceIdProvider.obtain(CallRelayApp.get())
            } else existingId
            prefs.saveConnection(s.url, s.apiKey, s.deviceName, deviceId)
            _uiState.update { it.copy(saving = false) }
            onDone()
        }
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = CallRelayApp.get()
                SetupViewModel(app.container.prefs, app.container.repository)
            }
        }
    }
}
