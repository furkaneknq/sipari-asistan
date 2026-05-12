package com.orderapp.couriertracker

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.orderapp.couriertracker.data.AppContainer

/**
 * Uygulamanın global yaşam döngüsü ve dependency container.
 * Bildirim kanallarını oluşturur, tekil nesneleri hazırlar.
 */
class CourierTrackerApp : Application() {

    /** Tek noktadan erişilen bağımlılık konteyneri. */
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        container = AppContainer(this)
        createNotificationChannels()
    }

    /**
     * Bildirim kanalları:
     * 1) Servis kanalı — düşük öncelik, kalıcı bildirim
     * 2) Sipariş kanalı — yüksek öncelik, yeni sipariş bildirimi
     */
    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = getSystemService(NotificationManager::class.java) ?: return

        // Servis kanalı (düşük öncelik)
        val serviceChannel = NotificationChannel(
            CHANNEL_SERVICE,
            getString(R.string.channel_service),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = getString(R.string.channel_service_desc)
            setShowBadge(false)
        }
        nm.createNotificationChannel(serviceChannel)

        // Sipariş kanalı (yüksek öncelik — bildirim sesi + titreşim)
        val orderChannel = NotificationChannel(
            CHANNEL_ORDERS,
            getString(R.string.channel_orders),
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = getString(R.string.channel_orders_desc)
            enableVibration(true)
        }
        nm.createNotificationChannel(orderChannel)
    }

    companion object {
        const val CHANNEL_SERVICE = "courier_service"
        const val CHANNEL_ORDERS = "courier_orders"
        const val SERVICE_NOTIFICATION_ID = 2001
        const val ORDER_NOTIFICATION_ID_BASE = 3000

        @Volatile
        private var instance: CourierTrackerApp? = null

        fun get(): CourierTrackerApp =
            instance ?: error("CourierTrackerApp henüz oluşturulmamış")
    }
}
