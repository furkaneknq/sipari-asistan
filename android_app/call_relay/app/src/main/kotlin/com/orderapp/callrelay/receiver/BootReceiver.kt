package com.orderapp.callrelay.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.orderapp.callrelay.CallRelayApp
import com.orderapp.callrelay.service.CallMonitorService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * Cihaz açılınca tetiklenir.
 * Eğer kullanıcı servisi en son AÇIK bıraktıysa otomatik olarak yeniden başlatır.
 */
class BootReceiver : BroadcastReceiver() {

    @OptIn(kotlinx.coroutines.DelicateCoroutinesApi::class)
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED &&
            intent.action != "android.intent.action.QUICKBOOT_POWERON"
        ) return

        Log.i(TAG, "BOOT_COMPLETED alındı")

        val pendingResult = goAsync()
        val prefs = CallRelayApp.get().container.prefs

        GlobalScope.launch(Dispatchers.IO) {
            try {
                val configured = prefs.isConfigured.first()
                val enabled = prefs.serviceEnabled.first()
                if (configured && enabled) {
                    Log.i(TAG, "Önceki kullanıcı tercihi 'AÇIK' → servis başlatılıyor")
                    val ok = CallMonitorService.start(context.applicationContext)
                    if (!ok) Log.w(TAG, "Servis boot sonrası başlatılamadı")
                } else {
                    Log.i(TAG, "Servis otomatik başlatılmayacak (configured=$configured, enabled=$enabled)")
                }
            } finally {
                pendingResult.finish()
            }
        }
    }

    companion object {
        private const val TAG = "BootReceiver"
    }
}
