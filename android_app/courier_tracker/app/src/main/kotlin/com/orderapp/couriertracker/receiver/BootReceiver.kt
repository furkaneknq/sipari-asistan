package com.orderapp.couriertracker.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.orderapp.couriertracker.CourierTrackerApp
import com.orderapp.couriertracker.service.OrderPollingService
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

/**
 * Cihaz açıldığında, kurye servis açık bırakmışsa otomatik başlatır.
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != Intent.ACTION_BOOT_COMPLETED &&
            intent?.action != "android.intent.action.QUICKBOOT_POWERON"
        ) return

        try {
            val app = context.applicationContext as? CourierTrackerApp ?: return
            val prefs = app.container.prefs

            // runBlocking burada kabul edilebilir: receiver kısa ömürlü, tek veri okuma
            val serviceEnabled = runBlocking { prefs.serviceEnabled.first() }
            val isLoggedIn = runBlocking { prefs.isLoggedIn.first() }

            if (serviceEnabled && isLoggedIn) {
                Log.i(TAG, "Boot → servis başlatılıyor")
                OrderPollingService.start(context)
            } else {
                Log.i(TAG, "Boot → servis kapalı veya oturum yok, atlanıyor")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Boot receiver hatası", e)
        }
    }

    companion object {
        private const val TAG = "BootReceiver"
    }
}
