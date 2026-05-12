package com.orderapp.callrelay

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.orderapp.callrelay.data.AppContainer

/**
 * Uygulamanın global yaşam döngüsü ve dependency container.
 * Önemli: Burada heavy iş yapma, sadece tekil nesneleri (DB, API client) hazırla.
 */
class CallRelayApp : Application() {

    /** Tek noktadan erişilen bağımlılık konteyneri. */
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        container = AppContainer(this)
        createNotificationChannel()
    }

    /**
     * Foreground servisin gösterdiği kalıcı bildirim için kanal.
     * Android 8.0+ için zorunlu.
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.channel_name),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = getString(R.string.channel_desc)
            setShowBadge(false)
        }
        getSystemService(NotificationManager::class.java)
            ?.createNotificationChannel(channel)
    }

    companion object {
        const val CHANNEL_ID = "call_relay_service"
        const val NOTIFICATION_ID = 1001

        // Servis ve receiver'lar Application context üzerinden container'a erişir
        @Volatile
        private var instance: CallRelayApp? = null

        fun get(): CallRelayApp =
            instance ?: error("CallRelayApp henüz oluşturulmamış")
    }
}
