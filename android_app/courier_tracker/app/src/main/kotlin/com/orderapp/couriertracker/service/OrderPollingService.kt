package com.orderapp.couriertracker.service

import android.Manifest
import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.orderapp.couriertracker.CourierTrackerApp
import com.orderapp.couriertracker.R
import com.orderapp.couriertracker.data.db.OrderEntity
import com.orderapp.couriertracker.ui.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Foreground servis: periyodik olarak Supabase'den sipariş çeker,
 * yeni sipariş geldiğinde bildirim gönderir, kurye konumunu günceller.
 *
 * Polling aralığı: 10 saniye (sipariş)
 * Konum güncelleme: 60 saniye
 */
class OrderPollingService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var pollingJob: Job? = null

    private lateinit var locationClient: FusedLocationProviderClient
    private var locationCallback: LocationCallback? = null

    override fun onCreate() {
        super.onCreate()
        locationClient = LocationServices.getFusedLocationProviderClient(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                Log.i(TAG, "Servis durduruluyor")
                scope.launch { CourierTrackerApp.get().container.prefs.setServiceEnabled(false) }
                stopSelf()
                return START_NOT_STICKY
            }
        }

        startForeground(CourierTrackerApp.SERVICE_NOTIFICATION_ID, buildServiceNotification())
        startPolling()
        startLocationUpdates()

        scope.launch { CourierTrackerApp.get().container.prefs.setServiceEnabled(true) }
        Log.i(TAG, "Servis başlatıldı")

        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        pollingJob?.cancel()
        stopLocationUpdates()
        scope.cancel()
        super.onDestroy()
    }

    // ─── Polling ─────────────────────────────────────────────────────

    private fun startPolling() {
        pollingJob?.cancel()
        pollingJob = scope.launch {
            while (isActive) {
                try {
                    val repo = CourierTrackerApp.get().container.repository
                    val result = repo.syncOrders()
                    result.onSuccess { newIds ->
                        if (newIds.isNotEmpty()) {
                            sendNewOrderNotifications(newIds)
                        }
                    }.onFailure { e ->
                        Log.e(TAG, "Polling hatası", e)
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Polling genel hata", e)
                }
                delay(POLL_INTERVAL_MS)
            }
        }
    }

    // ─── Konum ───────────────────────────────────────────────────────

    private fun startLocationUpdates() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            Log.w(TAG, "Konum izni yok, konum güncellenmeyecek")
            return
        }

        val request = LocationRequest.Builder(Priority.PRIORITY_BALANCED_POWER_ACCURACY, LOCATION_INTERVAL_MS)
            .setMinUpdateIntervalMillis(LOCATION_INTERVAL_MS / 2)
            .build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val loc = result.lastLocation ?: return
                scope.launch {
                    try {
                        CourierTrackerApp.get().container.repository
                            .updateLocation(loc.latitude, loc.longitude)
                    } catch (e: Exception) {
                        Log.e(TAG, "Konum güncelleme hatası", e)
                    }
                }
            }
        }

        locationClient.requestLocationUpdates(request, locationCallback!!, Looper.getMainLooper())
        Log.i(TAG, "Konum güncellemeleri başlatıldı")
    }

    private fun stopLocationUpdates() {
        locationCallback?.let { locationClient.removeLocationUpdates(it) }
        locationCallback = null
    }

    // ─── Bildirim ────────────────────────────────────────────────────

    private fun buildServiceNotification(): Notification {
        val openIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingOpen = PendingIntent.getActivity(
            this, 0, openIntent, PendingIntent.FLAG_IMMUTABLE
        )

        val stopIntent = Intent(this, OrderPollingService::class.java).apply {
            action = ACTION_STOP
        }
        val pendingStop = PendingIntent.getService(
            this, 1, stopIntent, PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CourierTrackerApp.CHANNEL_SERVICE)
            .setContentTitle(getString(R.string.notif_title_active))
            .setContentText(getString(R.string.notif_text_active))
            .setSmallIcon(R.drawable.ic_courier)
            .setOngoing(true)
            .setContentIntent(pendingOpen)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Durdur", pendingStop)
            .build()
    }

    private fun sendNewOrderNotifications(newIds: List<String>) {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        scope.launch {
            val dao = CourierTrackerApp.get().container.orderDao
            for ((index, orderId) in newIds.withIndex()) {
                val order = dao.getById(orderId) ?: continue

                val openIntent = Intent(this@OrderPollingService, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
                    putExtra(EXTRA_ORDER_ID, orderId)
                }
                val pending = PendingIntent.getActivity(
                    this@OrderPollingService,
                    orderId.hashCode(),
                    openIntent,
                    PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
                )

                val paymentLabel = when (order.paymentMethod) {
                    "cash" -> "Nakit"
                    "credit_card" -> "Kredi Kartı"
                    "iban" -> "IBAN"
                    else -> ""
                }

                val notif = NotificationCompat.Builder(
                    this@OrderPollingService, CourierTrackerApp.CHANNEL_ORDERS
                )
                    .setContentTitle(getString(R.string.notif_new_order_title))
                    .setContentText("#${order.orderNumber} — ${order.customerName} — ₺${"%.2f".format(order.totalAmount)} $paymentLabel")
                    .setSmallIcon(R.drawable.ic_courier)
                    .setAutoCancel(true)
                    .setContentIntent(pending)
                    .setPriority(NotificationCompat.PRIORITY_HIGH)
                    .setDefaults(NotificationCompat.DEFAULT_ALL)
                    .build()

                nm.notify(CourierTrackerApp.ORDER_NOTIFICATION_ID_BASE + index, notif)
            }
        }
    }

    companion object {
        private const val TAG = "OrderPollingService"
        private const val POLL_INTERVAL_MS = 10_000L     // 10 saniye
        private const val LOCATION_INTERVAL_MS = 60_000L // 60 saniye
        const val ACTION_STOP = "com.orderapp.couriertracker.STOP_SERVICE"
        const val EXTRA_ORDER_ID = "extra_order_id"

        fun start(context: Context) {
            val intent = Intent(context, OrderPollingService::class.java)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            val intent = Intent(context, OrderPollingService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }
}
