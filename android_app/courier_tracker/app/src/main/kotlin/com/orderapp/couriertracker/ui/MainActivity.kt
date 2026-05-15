package com.orderapp.couriertracker.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.orderapp.couriertracker.CourierTrackerApp
import com.orderapp.couriertracker.data.db.OrderEntity
import com.orderapp.couriertracker.service.OrderPollingService
import com.orderapp.couriertracker.ui.screens.OrderDetailScreen
import com.orderapp.couriertracker.ui.screens.OrderListScreen
import com.orderapp.couriertracker.ui.theme.CourierTrackerTheme
import com.orderapp.couriertracker.util.PhoneFormatter
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * Ana Activity: sipariş listesi ve detay ekranları arası navigasyon.
 * Oturum kontrolü: giriş yoksa LoginActivity'ye yönlendirir.
 * İzinleri yönetir, servisi başlatır.
 */
class MainActivity : ComponentActivity() {

    private lateinit var viewModel: MainViewModel

    // İzin istekleri
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val allGranted = results.values.all { it }
        if (allGranted) {
            startPollingService()
        } else {
            Toast.makeText(this, "Bazı izinler reddedildi", Toast.LENGTH_SHORT).show()
            // Konum izni olmadan da servisi başlat (konum olmaz ama sipariş gelir)
            startPollingService()
        }
    }

    // Telefon arama izni
    private var pendingPhoneNumber: String? = null
    private val callPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            pendingPhoneNumber?.let { makeCall(it) }
        } else {
            Toast.makeText(this, "Arama izni reddedildi", Toast.LENGTH_SHORT).show()
        }
        pendingPhoneNumber = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Oturum kontrolü
        lifecycleScope.launch {
            val isLoggedIn = CourierTrackerApp.get().container.prefs.isLoggedIn.first()
            if (!isLoggedIn) {
                navigateToLogin()
                return@launch
            }

            initMainScreen()
        }
    }

    private fun initMainScreen() {
        viewModel = ViewModelProvider(this)[MainViewModel::class.java]

        // İzinleri iste ve servisi başlat
        requestPermissionsAndStartService()

        setContent {
            CourierTrackerTheme {
                val navController = rememberNavController()

                // Intent'ten gelen sipariş ID'si (bildirime tıklanınca)
                val extraOrderId = intent?.getStringExtra(OrderPollingService.EXTRA_ORDER_ID)

                NavHost(
                    navController = navController,
                    startDestination = if (extraOrderId != null) "detail/$extraOrderId" else "list"
                ) {
                    composable("list") {
                        OrderListScreen(
                            viewModel = viewModel,
                            onOrderClick = { orderId ->
                                navController.navigate("detail/$orderId")
                            },
                            onOpenMap = { order -> openMap(order) },
                            onLogout = { performLogout() }
                        )
                    }

                    composable(
                        route = "detail/{orderId}",
                        arguments = listOf(navArgument("orderId") { type = NavType.StringType })
                    ) { backStackEntry ->
                        val orderId = backStackEntry.arguments?.getString("orderId") ?: ""
                        OrderDetailScreen(
                            orderId = orderId,
                            viewModel = viewModel,
                            onBack = { navController.popBackStack() },
                            onCallPhone = { phone -> requestCallPermission(phone) },
                            onOpenMap = { order -> openMap(order) },
                            onSaveLocation = { order -> saveCurrentLocation(order) }
                        )
                    }
                }
            }
        }
    }

    // ─── İzinler ─────────────────────────────────────────────────────

    private fun requestPermissionsAndStartService() {
        val permissions = mutableListOf<String>()

        // Konum izni
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }

        // Bildirim izni (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                permissions.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        if (permissions.isNotEmpty()) {
            permissionLauncher.launch(permissions.toTypedArray())
        } else {
            startPollingService()
        }
    }

    private fun startPollingService() {
        OrderPollingService.start(this)
    }

    // ─── Telefon Arama ──────────────────────────────────────────────

    private fun requestCallPermission(phone: String) {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE)
            == PackageManager.PERMISSION_GRANTED
        ) {
            makeCall(phone)
        } else {
            pendingPhoneNumber = phone
            callPermissionLauncher.launch(Manifest.permission.CALL_PHONE)
        }
    }

    private fun makeCall(phone: String) {
        val dialable = PhoneFormatter.toDialable(phone)
        if (dialable.isBlank() || dialable.replace(Regex("[^0-9]"), "").length < 7) {
            Toast.makeText(this, "Geçersiz telefon numarası", Toast.LENGTH_SHORT).show()
            return
        }
        val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$dialable"))
        try {
            startActivity(intent)
        } catch (e: Exception) {
            // Fallback: DIAL intent (izin gerektirmez)
            try {
                startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$dialable")))
            } catch (e2: Exception) {
                Toast.makeText(this, "Arama uygulaması açılamadı", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ─── Konum Kaydet ─────────────────────────────────────────────

    @SuppressLint("MissingPermission")
    private fun saveCurrentLocation(order: OrderEntity) {
        val addressId = order.addressId
        if (addressId == null) {
            Toast.makeText(this, "Adres ID bulunamadı", Toast.LENGTH_SHORT).show()
            return
        }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Toast.makeText(this, "Konum izni verilmemiş", Toast.LENGTH_SHORT).show()
            return
        }

        val locationManager = getSystemService(LOCATION_SERVICE) as LocationManager

        // Önce son bilinen konumu dene
        val lastKnown = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            ?: locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)

        if (lastKnown != null && lastKnown.accuracy < 100f) {
            viewModel.saveAddressLocation(
                orderId = order.id,
                addressId = addressId,
                latitude = lastKnown.latitude,
                longitude = lastKnown.longitude
            )
            Toast.makeText(
                this,
                "📍 Konum kaydedildi (%.6f, %.6f)".format(lastKnown.latitude, lastKnown.longitude),
                Toast.LENGTH_LONG
            ).show()
            return
        }

        // Son konum yoksa tek seferlik güncelleme iste
        Toast.makeText(this, "GPS konumu alınıyor...", Toast.LENGTH_SHORT).show()
        locationManager.requestSingleUpdate(
            LocationManager.GPS_PROVIDER,
            { location ->
                viewModel.saveAddressLocation(
                    orderId = order.id,
                    addressId = addressId,
                    latitude = location.latitude,
                    longitude = location.longitude
                )
                runOnUiThread {
                    Toast.makeText(
                        this,
                        "📍 Konum kaydedildi (%.6f, %.6f)".format(location.latitude, location.longitude),
                        Toast.LENGTH_LONG
                    ).show()
                }
            },
            null
        )
    }

    // ─── Harita ─────────────────────────────────────────────────────

    private fun openMap(order: OrderEntity) {
        val uri = if (order.latitude != null && order.longitude != null) {
            // Koordinatla aç
            Uri.parse("geo:${order.latitude},${order.longitude}?q=${order.latitude},${order.longitude}(${Uri.encode(order.customerName)})")
        } else if (!order.addressText.isNullOrBlank()) {
            // Adresle arat
            Uri.parse("geo:0,0?q=${Uri.encode(order.addressText)}")
        } else {
            Toast.makeText(this, "Konum veya adres bilgisi yok", Toast.LENGTH_SHORT).show()
            return
        }

        try {
            // Önce Google Maps'i dene
            val mapIntent = Intent(Intent.ACTION_VIEW, uri).apply {
                setPackage("com.google.android.apps.maps")
            }
            startActivity(mapIntent)
        } catch (_: Exception) {
            try {
                // Google Maps yoksa genel intent
                startActivity(Intent(Intent.ACTION_VIEW, uri))
            } catch (_: Exception) {
                Toast.makeText(this, "Harita uygulaması bulunamadı", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ─── Çıkış ──────────────────────────────────────────────────────

    private fun performLogout() {
        OrderPollingService.stop(this)
        lifecycleScope.launch {
            CourierTrackerApp.get().container.repository.logout()
            navigateToLogin()
        }
    }

    private fun navigateToLogin() {
        startActivity(
            Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
        )
        finish()
    }
}
