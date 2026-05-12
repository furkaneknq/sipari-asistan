package com.orderapp.callrelay.service

import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkRequest
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.orderapp.callrelay.CallRelayApp
import com.orderapp.callrelay.R
import com.orderapp.callrelay.data.repository.CallRepository
import com.orderapp.callrelay.ui.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Foreground servis. Kullanıcı uygulamayı kapatsa bile çalışır.
 * Görev:
 *   1. Telefon durumunu dinle (PhoneStateMonitor)
 *   2. Gelen aramayı CallRepository üzerinden Supabase'e gönder
 *   3. İnternet kesik gelince → bağlantı geri geldiğinde pending kayıtları gönder
 */
class CallMonitorService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var monitor: PhoneStateMonitor
    private lateinit var repo: CallRepository

    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var monitorStarted: Boolean = false

    /** Aynı numarayı kısa sürede iki kez kaydetmemek için (broadcast + telephonyCallback). */
    private var lastRecordedNumber: String? = null
    private var lastRecordedAtMs: Long = 0L

    override fun onCreate() {
        super.onCreate()
        repo = CallRelayApp.get().container.repository
        monitor = PhoneStateMonitor(this) { phoneNumber ->
            Log.i(TAG, "Telephony callback yakaladı: $phoneNumber")
            recordIfNew(phoneNumber, source = "telephony")
        }
    }

    /** Aynı numarayı 5 saniye içinde tekrar kaydetmesini engeller. */
    private fun recordIfNew(phone: String, source: String) {
        if (phone.isBlank()) return
        val now = System.currentTimeMillis()
        if (phone == lastRecordedNumber && now - lastRecordedAtMs < 5_000) {
            Log.d(TAG, "Yinelenen kayıt atlandı ($source): $phone")
            return
        }
        lastRecordedNumber = phone
        lastRecordedAtMs = now
        scope.launch {
            try {
                repo.recordIncomingCall(phone)
                Log.i(TAG, "Kaydedildi & gönderildi ($source): $phone")
            } catch (e: Exception) {
                Log.e(TAG, "recordIncomingCall hatası", e)
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Foreground bildirimi başlat. Eğer izin/tip hatası olursa
        // tüm uygulamayı çökertmek yerine logla ve servisi temiz şekilde durdur.
        try {
            startForegroundWithNotification()
        } catch (e: Exception) {
            Log.e(TAG, "Foreground servis başlatılamadı: ${e.message}", e)
            stopSelf()
            return START_NOT_STICKY
        }

        // PhoneStateMonitor'ı sadece bir kez kur (servis tekrar tetiklenince yeniden register etme)
        if (!monitorStarted) {
            monitor.start()
            monitorStarted = true
            registerNetworkCallback()
            Log.i(TAG, "Servis başlatıldı, dinleyici kuruldu")
        }

        // Broadcast'tan tetiklendiyse → numara hemen extra'da gelmiş olabilir
        if (intent?.action == ACTION_INCOMING_FROM_BROADCAST) {
            val number = intent.getStringExtra(EXTRA_NUMBER)?.trim().orEmpty()
            Log.i(TAG, "Broadcast tetiklemesi alındı: number='$number'")
            if (number.isNotBlank()) {
                recordIfNew(number, source = "broadcast")
            }
            // Numara boş gelirse PhoneStateMonitor zaten state machine ile yakalayacak
        }

        // Servis ilk başladığında pending kayıtlar varsa hemen göndermeyi dene
        scope.launch {
            try {
                val sent = repo.trySendPending()
                if (sent > 0) Log.i(TAG, "Başlangıçta $sent bekleyen kayıt gönderildi")
            } catch (e: Exception) {
                Log.e(TAG, "Pending sync hatası", e)
            }
        }

        // Sistemin servisi öldürmesi durumunda yeniden başlatması için
        return START_STICKY
    }

    override fun onDestroy() {
        Log.i(TAG, "Servis durduruluyor")
        monitor.stop()
        unregisterNetworkCallback()
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ------------------------------------------------------------------
    // Foreground bildirimi
    // ------------------------------------------------------------------
    private fun startForegroundWithNotification() {
        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val contentPi = PendingIntent.getActivity(
            this,
            0,
            openAppIntent,
            PendingIntent.FLAG_IMMUTABLE
        )

        val notif = NotificationCompat.Builder(this, CallRelayApp.CHANNEL_ID)
            .setContentTitle(getString(R.string.notif_title_active))
            .setContentText(getString(R.string.notif_text_active))
            .setSmallIcon(R.drawable.ic_phone_relay)
            .setOngoing(true)
            .setContentIntent(contentPi)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // dataSync = "internet üzerinden bilgi senkronu". Bizim use-case'imiz bu.
            startForeground(
                CallRelayApp.NOTIFICATION_ID,
                notif,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            startForeground(CallRelayApp.NOTIFICATION_ID, notif)
        }
    }

    // ------------------------------------------------------------------
    // Network observer: bağlantı geri gelince pending kayıtları sync et
    // ------------------------------------------------------------------
    private fun registerNetworkCallback() {
        val cm = getSystemService(ConnectivityManager::class.java) ?: return
        val req = NetworkRequest.Builder()
            .addCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .addCapability(android.net.NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            .build()
        val cb = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                Log.i(TAG, "İnternet hazır → pending kayıtlar gönderiliyor")
                scope.launch {
                    val n = repo.trySendPending()
                    if (n > 0) Log.i(TAG, "$n kayıt sync edildi")
                }
            }
        }
        cm.registerNetworkCallback(req, cb)
        networkCallback = cb
    }

    private fun unregisterNetworkCallback() {
        val cb = networkCallback ?: return
        try {
            getSystemService(ConnectivityManager::class.java)?.unregisterNetworkCallback(cb)
        } catch (_: Exception) {
        }
        networkCallback = null
    }

    companion object {
        private const val TAG = "CallMonitorService"

        /** Broadcast tetiklemesinde intent.action olarak kullanılır. */
        const val ACTION_INCOMING_FROM_BROADCAST =
            "com.orderapp.callrelay.ACTION_INCOMING_FROM_BROADCAST"
        const val EXTRA_NUMBER = "extra_number"

        /**
         * Servisi başlatmak için yardımcı.
         * @return true → start çağrısı sisteme iletildi; false → SDK/izin hatası, kullanıcıya göster.
         */
        fun start(context: android.content.Context): Boolean =
            startWithIntent(context, Intent(context, CallMonitorService::class.java))

        /** Özel intent (action/extra) ile servisi başlatır — örn. PhoneStateReceiver'dan. */
        fun startWithIntent(context: android.content.Context, intent: Intent): Boolean = try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
            true
        } catch (e: Exception) {
            // Android 12+ ForegroundServiceStartNotAllowedException, vb.
            Log.e(TAG, "CallMonitorService.start hatası: ${e.message}", e)
            false
        }

        fun stop(context: android.content.Context) {
            try {
                context.stopService(Intent(context, CallMonitorService::class.java))
            } catch (e: Exception) {
                Log.e(TAG, "stop hatası", e)
            }
        }
    }
}
