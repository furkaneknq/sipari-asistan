package com.orderapp.callrelay.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.orderapp.callrelay.data.db.CallEntity
import com.orderapp.callrelay.ui.MainUiState
import com.orderapp.callrelay.ui.TestCallFeedback
import com.orderapp.callrelay.ui.theme.ErrorRed
import com.orderapp.callrelay.ui.theme.PendingGray
import com.orderapp.callrelay.ui.theme.SuccessGreen
import com.orderapp.callrelay.ui.theme.WarningOrange
import com.orderapp.callrelay.util.PhoneNumberFormatter
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun MainScreen(
    state: MainUiState,
    onToggleService: (Boolean) -> Unit,
    onOpenSetup: () -> Unit,
    onRequestPermissions: () -> Unit,
    onOpenAppSettings: () -> Unit,
    onResyncPending: () -> Unit,
    onSendTestCall: (String?) -> Unit,
    onDismissTestFeedback: () -> Unit
) {
    var showTestDialog by remember { mutableStateOf(false) }

    if (showTestDialog) {
        CustomTestNumberDialog(
            onDismiss = { showTestDialog = false },
            onSend = { number ->
                showTestDialog = false
                onSendTestCall(number)
            }
        )
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
        ) {
            HeaderCard(
                deviceName = state.deviceName,
                isServiceEnabled = state.isServiceEnabled,
                permissionsOk = state.permissionsOk
            )

            Spacer(Modifier.height(12.dp))

            if (!state.permissionsOk) {
                PermissionWarningCard(
                    hardDenied = state.permissionsDeniedHard,
                    onRequest = onRequestPermissions,
                    onOpenSettings = onOpenAppSettings
                )
                Spacer(Modifier.height(12.dp))
            }

            ToggleButton(
                isOn = state.isServiceEnabled,
                enabled = state.permissionsOk,
                onToggle = onToggleService
            )

            Spacer(Modifier.height(8.dp))

            // Test araması butonları
            TestCallRow(
                inProgress = state.testInProgress,
                onQuickTest = { onSendTestCall(null) },
                onCustomTest = { showTestDialog = true }
            )

            // Test sonucu banner'ı
            state.testFeedback?.let { fb ->
                Spacer(Modifier.height(8.dp))
                TestFeedbackBanner(feedback = fb, onDismiss = onDismissTestFeedback)
            }

            Spacer(Modifier.height(20.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "Son Aramalar",
                    style = MaterialTheme.typography.titleMedium
                )
                Spacer(Modifier.weight(1f))
                OutlinedButton(onClick = onResyncPending) {
                    Icon(Icons.Filled.Sync, null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.size(4.dp))
                    Text("Tekrar Dene")
                }
            }

            Spacer(Modifier.height(8.dp))

            if (state.recentCalls.isEmpty()) {
                Text(
                    "Henüz arama kaydı yok.",
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            } else {
                LazyColumn(modifier = Modifier.weight(1f)) {
                    items(state.recentCalls, key = { it.id }) { call ->
                        CallRow(call)
                        HorizontalDivider()
                    }
                }
            }

            Spacer(Modifier.height(8.dp))

            OutlinedButton(
                onClick = onOpenSetup,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Filled.Settings, null)
                Spacer(Modifier.size(4.dp))
                Text("Ayarlar")
            }
        }
    }
}

// ----- alt kompozisyonlar -----

@Composable
private fun HeaderCard(
    deviceName: String,
    isServiceEnabled: Boolean,
    permissionsOk: Boolean
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "📞 Arama Aktarım",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Durum:", modifier = Modifier.padding(end = 6.dp))
                StatusDot(active = isServiceEnabled && permissionsOk)
                Spacer(Modifier.size(6.dp))
                Text(
                    text = if (isServiceEnabled && permissionsOk) "🟢 Aktif"
                    else if (!permissionsOk) "🟡 İzin Bekleniyor"
                    else "🔴 Pasif",
                    fontWeight = FontWeight.SemiBold
                )
            }
            Spacer(Modifier.height(4.dp))
            Text(
                "Cihaz: ${deviceName.ifBlank { "(ayar yapılmadı)" }}",
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}

@Composable
private fun StatusDot(active: Boolean) {
    Box(
        modifier = Modifier
            .size(12.dp)
            .clip(RoundedCornerShape(50))
            .background(if (active) SuccessGreen else ErrorRed)
    )
}

@Composable
private fun PermissionWarningCard(
    hardDenied: Boolean,
    onRequest: () -> Unit,
    onOpenSettings: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = WarningOrange.copy(alpha = 0.15f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "⚠ Gerekli izinler eksik",
                style = MaterialTheme.typography.titleMedium,
                color = WarningOrange
            )
            Spacer(Modifier.height(6.dp))
            Text(
                "Bu uygulamanın aramaları yakalayabilmesi için telefon durumu ve " +
                    "arama kayıtları izinleri gerekli."
            )
            Spacer(Modifier.height(12.dp))
            if (hardDenied) {
                Button(onClick = onOpenSettings, modifier = Modifier.fillMaxWidth()) {
                    Text("Uygulama Ayarlarını Aç")
                }
            } else {
                Button(onClick = onRequest, modifier = Modifier.fillMaxWidth()) {
                    Text("İzin Ver")
                }
            }
        }
    }
}

@Composable
private fun ToggleButton(
    isOn: Boolean,
    enabled: Boolean,
    onToggle: (Boolean) -> Unit
) {
    val color = if (isOn) ErrorRed else SuccessGreen
    Button(
        onClick = { onToggle(!isOn) },
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = color,
            contentColor = Color.White
        )
    ) {
        Icon(
            imageVector = if (isOn) Icons.Filled.Stop else Icons.Filled.PlayArrow,
            contentDescription = null
        )
        Spacer(Modifier.size(8.dp))
        Text(
            if (isOn) "🔴 Servisi Durdur" else "▶ Servisi Başlat",
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun CallRow(call: CallEntity) {
    val time = remember(call.createdAt) { formatTime(call.createdAt) }
    val statusColor = when (call.status) {
        CallEntity.STATUS_SENT -> SuccessGreen
        CallEntity.STATUS_FAILED -> ErrorRed
        else -> PendingGray
    }
    val statusText = when (call.status) {
        CallEntity.STATUS_SENT -> "✅ Gönderildi"
        CallEntity.STATUS_FAILED -> "❌ Başarısız"
        else -> "⏳ Bekliyor"
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 10.dp, horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                PhoneNumberFormatter.forDisplay(call.phoneNumber),
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium
            )
            Spacer(Modifier.height(2.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    time,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
                Spacer(Modifier.size(8.dp))
                Text(
                    statusText,
                    style = MaterialTheme.typography.bodyMedium,
                    color = statusColor
                )
            }
            if (call.status != CallEntity.STATUS_SENT && !call.lastError.isNullOrBlank()) {
                Spacer(Modifier.height(2.dp))
                Text(
                    call.lastError,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

private val timeFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd.MM HH:mm").withZone(ZoneId.systemDefault())

private fun formatTime(iso: String): String = try {
    timeFormatter.format(Instant.parse(iso))
} catch (_: Exception) {
    iso
}

// ----- Test araması bileşenleri -----

@Composable
private fun TestCallRow(
    inProgress: Boolean,
    onQuickTest: () -> Unit,
    onCustomTest: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        OutlinedButton(
            onClick = onQuickTest,
            enabled = !inProgress,
            modifier = Modifier.weight(1f)
        ) {
            if (inProgress) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp
                )
                Spacer(Modifier.size(8.dp))
                Text("Gönderiliyor...")
            } else {
                Icon(Icons.Filled.BugReport, null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.size(6.dp))
                Text("Test Araması")
            }
        }
        OutlinedButton(
            onClick = onCustomTest,
            enabled = !inProgress
        ) {
            Text("Özel No.")
        }
    }
}

@Composable
private fun TestFeedbackBanner(feedback: TestCallFeedback, onDismiss: () -> Unit) {
    val (color, icon, msg) = when (feedback) {
        TestCallFeedback.Sent -> Triple(
            SuccessGreen,
            "✅",
            "Test araması Supabase'e gönderildi. Masaüstünde popup görmelisin."
        )
        TestCallFeedback.QueuedOffline -> Triple(
            WarningOrange,
            "⏳",
            "İnternet yok — test çağrısı pending kuyruğa alındı, bağlantı gelince gönderilecek."
        )
        is TestCallFeedback.Error -> Triple(
            ErrorRed,
            "❌",
            "Hata: ${feedback.message}"
        )
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
            Text(msg, modifier = Modifier.weight(1f), color = color)
            TextButton(onClick = onDismiss) { Text("Tamam") }
        }
    }
}

@Composable
private fun CustomTestNumberDialog(
    onDismiss: () -> Unit,
    onSend: (String) -> Unit
) {
    var number by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Özel Test Numarası") },
        text = {
            Column {
                Text(
                    "Bu numarayı sanki gerçek bir arama gelmiş gibi Supabase'e " +
                        "yazacağız. Müşteri eşleşmesini test etmek için kayıtlı bir " +
                        "müşteri telefonunu girebilirsin."
                )
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = number,
                    onValueChange = { number = it },
                    label = { Text("Telefon") },
                    placeholder = { Text("0532 123 45 67") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onSend(number.trim()) },
                enabled = number.isNotBlank()
            ) { Text("Gönder") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("İptal") }
        }
    )
}
