package com.orderapp.callrelay.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager
import android.util.Log
import com.orderapp.callrelay.service.CallMonitorService

/**
 * Manifest tabanlı arama dinleyicisi.
 * `android.intent.action.PHONE_STATE` Android 8+ için implicit broadcast
 * kısıtlamasından muaf — manifest'te kayıtlı bir receiver bunu hâlâ alabilir.
 *
 * Bu dinleyici, servis öldürülmüş olsa bile arama geldiğinde tetiklenir,
 * servisi başlatır ve numarayı doğrudan iletir.
 */
class PhoneStateReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        if (action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return

        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
        Log.d(TAG, "PHONE_STATE alındı: state=$state")

        if (state != TelephonyManager.EXTRA_STATE_RINGING) return

        // Numara extra (READ_CALL_LOG / READ_PHONE_NUMBERS izni varsa dolu gelir)
        val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
        Log.i(TAG, "RINGING (broadcast): number='${number ?: ""}'")

        // Numara boş bile olsa servisi başlat — service içindeki PhoneStateMonitor
        // çağrı bittikten sonra CallLog'tan numarayı çekecek (fallback).
        val svcIntent = Intent(context, CallMonitorService::class.java).apply {
            this.action = CallMonitorService.ACTION_INCOMING_FROM_BROADCAST
            if (!number.isNullOrBlank()) {
                putExtra(CallMonitorService.EXTRA_NUMBER, number)
            }
        }
        // CallMonitorService.start() içinde startForegroundService kullanılıyor
        try {
            CallMonitorService.startWithIntent(context.applicationContext, svcIntent)
        } catch (e: Exception) {
            Log.e(TAG, "Servis broadcast'tan başlatılamadı", e)
        }
    }

    companion object {
        private const val TAG = "PhoneStateReceiver"
    }
}
