package com.orderapp.callrelay.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.orderapp.callrelay.ui.SetupUiState
import com.orderapp.callrelay.ui.TestResult
import com.orderapp.callrelay.ui.theme.ErrorRed
import com.orderapp.callrelay.ui.theme.SuccessGreen

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun SetupScreen(
    state: SetupUiState,
    onUrlChange: (String) -> Unit,
    onKeyChange: (String) -> Unit,
    onDeviceNameChange: (String) -> Unit,
    onTest: () -> Unit,
    onSave: () -> Unit,
    onDismissResult: () -> Unit
) {
    var showKey by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Kurulum / Ayarlar") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Text(
                "Supabase Bağlantısı",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(Modifier.height(8.dp))

            OutlinedTextField(
                value = state.url,
                onValueChange = onUrlChange,
                label = { Text("Supabase URL") },
                placeholder = { Text("https://xxxx.supabase.co") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri)
            )
            Spacer(Modifier.height(12.dp))

            OutlinedTextField(
                value = state.apiKey,
                onValueChange = onKeyChange,
                label = { Text("Anon (Publishable) Key") },
                placeholder = { Text("sb_publishable_... veya eyJ...") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                visualTransformation = if (showKey) VisualTransformation.None else PasswordVisualTransformation(),
                trailingIcon = {
                    OutlinedButton(
                        onClick = { showKey = !showKey },
                        modifier = Modifier.padding(end = 4.dp)
                    ) {
                        Text(if (showKey) "Gizle" else "Göster")
                    }
                }
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "Yalnızca anon (publishable) key kullanın. Service role key APK'da olmamalı.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )

            Spacer(Modifier.height(20.dp))
            Text(
                "Cihaz Bilgisi",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(Modifier.height(8.dp))

            OutlinedTextField(
                value = state.deviceName,
                onValueChange = onDeviceNameChange,
                label = { Text("Cihaz Adı") },
                placeholder = { Text("Tezgah Telefonu 1") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(Modifier.height(20.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                OutlinedButton(
                    onClick = onTest,
                    modifier = Modifier.weight(1f),
                    enabled = !state.testing && !state.saving
                ) {
                    if (state.testing) {
                        CircularProgressIndicator(
                            modifier = Modifier.height(18.dp),
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text("Bağlantıyı Test Et")
                    }
                }
                Button(
                    onClick = onSave,
                    modifier = Modifier.weight(1f),
                    enabled = !state.saving && !state.testing
                ) {
                    Text(if (state.saving) "Kaydediliyor..." else "Kaydet")
                }
            }

            state.testResult?.let { result ->
                Spacer(Modifier.height(16.dp))
                ResultBanner(result, onDismiss = onDismissResult)
            }

            Spacer(Modifier.height(24.dp))

            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.secondary.copy(alpha = 0.08f)
                )
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        "ℹ Önemli",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "1. Supabase'de '07_incoming_calls_anon_insert.sql' migration'ını çalıştır.\n" +
                            "2. Telefonun ses ayarlarında bu uygulamaya 'Pil Optimizasyonu' kapatılsın " +
                            "(servis arka planda öldürülmesin).\n" +
                            "3. Android 14+ sürümlerinde 'Tam Ekran Bildirim' veya 'Diğer' özel izinleri " +
                            "ek olarak istenebilir.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
    }
}

@Composable
private fun ResultBanner(result: TestResult, onDismiss: () -> Unit) {
    val (color, icon, msg) = when (result) {
        is TestResult.Success -> Triple(SuccessGreen, "✅", "Bağlantı başarılı!")
        is TestResult.Failure -> Triple(ErrorRed, "❌", result.message)
    }
    Card(
        colors = CardDefaults.cardColors(containerColor = color.copy(alpha = 0.12f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(icon, modifier = Modifier.padding(end = 8.dp))
            Text(
                msg,
                modifier = Modifier.weight(1f),
                color = color
            )
            OutlinedButton(onClick = onDismiss) { Text("Tamam") }
        }
    }
}
