package com.orderapp.callrelay.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.content.ContextCompat
import com.orderapp.callrelay.CallRelayApp
import com.orderapp.callrelay.service.CallMonitorService
import com.orderapp.callrelay.ui.screens.MainScreen
import com.orderapp.callrelay.ui.theme.CallRelayTheme
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

/**
 * Açılış aktivitesi.
 *   - İlk kurulum yapılmadıysa SetupActivity'ye yönlendirir.
 *   - Yapılmışsa ana ekranı (servis durumu + son aramalar) gösterir.
 */
class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels { MainViewModel.Factory }

    private val requiredPermissions: Array<String> by lazy {
        buildList {
            add(Manifest.permission.READ_PHONE_STATE)
            add(Manifest.permission.READ_CALL_LOG)
            // Android 12+ → telefon numarasına ulaşmak için ayrı izin
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                add(Manifest.permission.READ_PHONE_NUMBERS)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }.toTypedArray()
    }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val allGranted = results.values.all { it }
        if (allGranted) {
            viewModel.onPermissionsGranted()
        } else {
            viewModel.onPermissionsDenied(
                shouldRedirectToSettings = !shouldShowRationaleForAny()
            )
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Kurulum tamamlanmadıysa SetupActivity'ye geç
        val configured = runBlocking {
            CallRelayApp.get().container.prefs.isConfigured.first()
        }
        if (!configured) {
            startActivity(Intent(this, SetupActivity::class.java))
            finish()
            return
        }

        setContent {
            CallRelayTheme {
                val state by viewModel.uiState.collectAsState()
                MainScreen(
                    state = state,
                    onToggleService = ::onToggleService,
                    onOpenSetup = {
                        startActivity(Intent(this, SetupActivity::class.java))
                    },
                    onRequestPermissions = { permissionLauncher.launch(requiredPermissions) },
                    onOpenAppSettings = ::openAppSettings,
                    onResyncPending = viewModel::resyncPending,
                    onSendTestCall = viewModel::sendTestCall,
                    onDismissTestFeedback = viewModel::clearTestFeedback
                )
            }
        }

        // Sayfa açıldığında izinleri kontrol et
        viewModel.checkPermissions(allPermissionsGranted())
    }

    override fun onResume() {
        super.onResume()
        viewModel.checkPermissions(allPermissionsGranted())
    }

    private fun onToggleService(turnOn: Boolean) {
        if (turnOn) {
            if (!allPermissionsGranted()) {
                permissionLauncher.launch(requiredPermissions)
                return
            }
            val ok = CallMonitorService.start(this)
            if (ok) {
                viewModel.persistServiceState(true)
            } else {
                Toast.makeText(
                    this,
                    "Servis başlatılamadı. Logcat'te 'CallMonitorService' filtresine bak.",
                    Toast.LENGTH_LONG
                ).show()
            }
        } else {
            CallMonitorService.stop(this)
            viewModel.persistServiceState(false)
        }
    }

    private fun allPermissionsGranted(): Boolean = requiredPermissions.all {
        ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
    }

    private fun shouldShowRationaleForAny(): Boolean = requiredPermissions.any {
        shouldShowRequestPermissionRationale(it)
    }

    private fun openAppSettings() {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", packageName, null)
        }
        startActivity(intent)
    }
}
