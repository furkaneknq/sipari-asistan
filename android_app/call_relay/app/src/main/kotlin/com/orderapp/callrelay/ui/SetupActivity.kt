package com.orderapp.callrelay.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.orderapp.callrelay.ui.screens.SetupScreen
import com.orderapp.callrelay.ui.theme.CallRelayTheme

/**
 * İlk açılış / Ayarlar ekranı.
 * - Supabase URL + anon key
 * - Cihaz adı
 * - Bağlantı testi
 * - Kaydet → MainActivity'ye dönüş
 */
class SetupActivity : ComponentActivity() {

    private val vm: SetupViewModel by viewModels { SetupViewModel.Factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CallRelayTheme {
                val state by vm.uiState.collectAsState()
                SetupScreen(
                    state = state,
                    onUrlChange = vm::updateUrl,
                    onKeyChange = vm::updateKey,
                    onDeviceNameChange = vm::updateDeviceName,
                    onTest = vm::testConnection,
                    onSave = {
                        vm.save {
                            // Kaydedildikten sonra ana ekrana dön
                            startActivity(
                                Intent(this, MainActivity::class.java)
                                    .addFlags(
                                        Intent.FLAG_ACTIVITY_CLEAR_TOP or
                                            Intent.FLAG_ACTIVITY_SINGLE_TOP
                                    )
                            )
                            finish()
                        }
                    },
                    onDismissResult = vm::clearTestResult
                )
            }
        }
    }
}
