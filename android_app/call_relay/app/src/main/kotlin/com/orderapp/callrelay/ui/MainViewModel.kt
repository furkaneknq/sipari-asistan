package com.orderapp.callrelay.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.orderapp.callrelay.CallRelayApp
import com.orderapp.callrelay.data.Prefs
import com.orderapp.callrelay.data.db.CallEntity
import com.orderapp.callrelay.data.repository.CallRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Ana ekran UI durumu */
data class MainUiState(
    val deviceName: String = "",
    val deviceId: String = "",
    val isServiceEnabled: Boolean = false,
    val permissionsOk: Boolean = false,
    val permissionsDeniedHard: Boolean = false,
    val notificationListenerEnabled: Boolean = false,
    val recentCalls: List<CallEntity> = emptyList(),
    val testInProgress: Boolean = false,
    val testFeedback: TestCallFeedback? = null
)

/** Test araması butonunun anlık geri bildirimi (Snackbar/banner için). */
sealed interface TestCallFeedback {
    data object Sent : TestCallFeedback
    data object QueuedOffline : TestCallFeedback
    data class Error(val message: String) : TestCallFeedback
}

class MainViewModel(
    private val prefs: Prefs,
    private val repo: CallRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(MainUiState())
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                prefs.deviceName,
                prefs.deviceId,
                prefs.serviceEnabled,
                repo.observeRecent()
            ) { name, id, enabled, calls ->
                _uiState.value.copy(
                    deviceName = name,
                    deviceId = id,
                    isServiceEnabled = enabled,
                    recentCalls = calls
                )
            }.collect { newState ->
                _uiState.value = newState
            }
        }
    }

    fun checkPermissions(granted: Boolean) {
        _uiState.update { it.copy(permissionsOk = granted, permissionsDeniedHard = false) }
    }

    fun checkNotificationListenerEnabled(enabled: Boolean) {
        _uiState.update { it.copy(notificationListenerEnabled = enabled) }
    }

    fun onPermissionsGranted() {
        _uiState.update { it.copy(permissionsOk = true, permissionsDeniedHard = false) }
    }

    fun onPermissionsDenied(shouldRedirectToSettings: Boolean) {
        _uiState.update {
            it.copy(permissionsOk = false, permissionsDeniedHard = shouldRedirectToSettings)
        }
    }

    fun persistServiceState(enabled: Boolean) {
        viewModelScope.launch { prefs.setServiceEnabled(enabled) }
    }

    fun resyncPending() {
        viewModelScope.launch { repo.trySendPending() }
    }

    /**
     * Test araması: gerçek bir telefon çalmadan kayıt oluşturur,
     * Room'a yazar ve Supabase'e gönderir. Sonucu UI'a bildirir.
     */
    fun sendTestCall(customNumber: String? = null) {
        if (_uiState.value.testInProgress) return
        viewModelScope.launch {
            _uiState.update { it.copy(testInProgress = true, testFeedback = null) }
            val result = repo.sendTestCall(customNumber)
            _uiState.update { state ->
                state.copy(
                    testInProgress = false,
                    testFeedback = result.fold(
                        onSuccess = { sent ->
                            if (sent) TestCallFeedback.Sent else TestCallFeedback.QueuedOffline
                        },
                        onFailure = { e ->
                            TestCallFeedback.Error(e.message ?: "Beklenmeyen hata")
                        }
                    )
                )
            }
        }
    }

    fun clearTestFeedback() {
        _uiState.update { it.copy(testFeedback = null) }
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val app = CallRelayApp.get()
                MainViewModel(app.container.prefs, app.container.repository)
            }
        }
    }
}
