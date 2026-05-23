package com.orderapp.adminpanel.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.orderapp.adminpanel.AdminPanelApp
import com.orderapp.adminpanel.data.api.ApiClient
import com.orderapp.adminpanel.ui.theme.Green
import com.orderapp.adminpanel.ui.theme.Red
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onConnectionSaved: () -> Unit
) {
    val prefs = AdminPanelApp.get().container.prefs
    val scope = rememberCoroutineScope()

    val savedUrl by prefs.supabaseUrl.collectAsState(initial = "")
    val savedKey by prefs.supabaseKey.collectAsState(initial = "")

    var url by remember { mutableStateOf("") }
    var key by remember { mutableStateOf("") }
    var testResult by remember { mutableStateOf<String?>(null) }
    var isTesting by remember { mutableStateOf(false) }
    var isSaving by remember { mutableStateOf(false) }

    // Kaydedilmiş değerleri yükle
    LaunchedEffect(savedUrl, savedKey) {
        if (url.isBlank()) url = savedUrl
        if (key.isBlank()) key = savedKey
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("⚙️ Ayarlar") }
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // ─── Bağlantı ────────────────────────────────────────────
            Text("Supabase Bağlantısı", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)

            OutlinedTextField(
                value = url,
                onValueChange = { url = it; testResult = null },
                label = { Text("Supabase URL") },
                placeholder = { Text("https://xxx.supabase.co") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            OutlinedTextField(
                value = key,
                onValueChange = { key = it; testResult = null },
                label = { Text("Service Role Key") },
                placeholder = { Text("eyJhbGciOiJIUzI1...") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                visualTransformation = PasswordVisualTransformation()
            )

            // Test sonucu
            testResult?.let { result ->
                val isSuccess = result.startsWith("✅")
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSuccess) Green.copy(alpha = 0.1f)
                        else Red.copy(alpha = 0.1f)
                    ),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(result, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }

            // Butonlar
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Test
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            isTesting = true
                            testResult = null
                            try {
                                val api = ApiClient.api(url.trim())
                                val k = key.trim()
                                api.ping(k, "Bearer $k")
                                testResult = "✅ Bağlantı başarılı!"
                            } catch (e: Exception) {
                                testResult = "❌ Hata: ${e.message}"
                            }
                            isTesting = false
                        }
                    },
                    modifier = Modifier.weight(1f),
                    enabled = url.isNotBlank() && key.isNotBlank() && !isTesting
                ) {
                    if (isTesting) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text("Test")
                }

                // Kaydet
                Button(
                    onClick = {
                        scope.launch {
                            isSaving = true
                            prefs.saveConnection(url.trim(), key.trim())
                            isSaving = false
                            onConnectionSaved()
                        }
                    },
                    modifier = Modifier.weight(1f),
                    enabled = url.isNotBlank() && key.isNotBlank() && !isSaving
                ) {
                    if (isSaving) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Kaydet")
                }
            }

            HorizontalDivider()

            // ─── Hakkında ────────────────────────────────────────────
            Text("Hakkında", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("Sipariş Yönetim — Admin Panel v1.0.0", style = MaterialTheme.typography.bodyMedium)
            Text(
                "Bilgisayar başında değilken sipariş oluşturup düzenleyebileceğiniz hafif yönetim uygulaması.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }
    }
}
