package com.orderapp.callrelay.service

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.CallLog
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import android.util.Log
import androidx.core.content.ContextCompat
import java.util.concurrent.Executors

/**
 * Çift modlu telefon durum dinleyicisi.
 *   - API 31+ (Android 12)  → TelephonyManager.registerTelephonyCallback
 *   - API 26-30             → PhoneStateListener
 *
 * Numara çözümleme:
 *   - API 26-30 → PhoneStateListener parametre olarak numarayı verir
 *   - API 31+   → numara verilmez; çağrı bitince (IDLE) CallLog'dan okunur
 *
 * Deduplication: aynı çağrı için birden fazla raporlama yapılmaz.
 */
class PhoneStateMonitor(
    private val context: Context,
    private val onIncoming: (phone: String) -> Unit
) {

    private var lastState: Int = TelephonyManager.CALL_STATE_IDLE
    private var sawRingingForCurrentCall: Boolean = false
    private var ringingHintNumber: String? = null
    private var ringingStartedAtMs: Long = 0L
    private var reportedNumberForCurrentCall: String? = null

    private val mainHandler = Handler(Looper.getMainLooper())
    private val deferredLookup = Runnable { tryReportFromCallLogIfNotYet() }

    private val telephony =
        context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager

    // ---- API 31+ callback ----
    private val modernCallback = object : TelephonyCallback(),
        TelephonyCallback.CallStateListener {
        override fun onCallStateChanged(state: Int) {
            handleState(state, incomingNumberHint = null)
        }
    }

    // ---- API 26-30 listener ----
    @Suppress("DEPRECATION")
    private val legacyListener = object : PhoneStateListener() {
        override fun onCallStateChanged(state: Int, phoneNumber: String?) {
            handleState(state, incomingNumberHint = phoneNumber)
        }
    }

    @SuppressLint("MissingPermission")
    fun start() {
        if (!hasReadPhoneStatePermission()) {
            Log.w(TAG, "READ_PHONE_STATE izni yok — monitör başlatılamadı")
            return
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            telephony.registerTelephonyCallback(
                Executors.newSingleThreadExecutor(),
                modernCallback
            )
        } else {
            @Suppress("DEPRECATION")
            telephony.listen(legacyListener, PhoneStateListener.LISTEN_CALL_STATE)
        }
        Log.i(TAG, "Telefon durumu izleyicisi başlatıldı (SDK=${Build.VERSION.SDK_INT})")
    }

    fun stop() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                telephony.unregisterTelephonyCallback(modernCallback)
            } else {
                @Suppress("DEPRECATION")
                telephony.listen(legacyListener, PhoneStateListener.LISTEN_NONE)
            }
        } catch (_: Exception) {
            /* sessizce */
        }
        Log.i(TAG, "Telefon durumu izleyicisi durduruldu")
    }

    /**
     * State machine:
     *   IDLE → RINGING : yeni gelen arama başladı
     *     - Hint varsa hemen raporla
     *     - Yoksa: IDLE'a dönüldüğünde CallLog'dan oku
     *   RINGING → OFFHOOK/IDLE : aramayı kapat
     *     - Henüz raporlanmadıysa CallLog'a bak
     */
    private fun handleState(state: Int, incomingNumberHint: String?) {
        Log.d(
            TAG,
            "handleState: state=${stateName(state)} hint='${incomingNumberHint.orEmpty()}' " +
                "lastState=${stateName(lastState)} sawRinging=$sawRingingForCurrentCall"
        )
        when (state) {
            TelephonyManager.CALL_STATE_RINGING -> {
                if (lastState != TelephonyManager.CALL_STATE_RINGING) {
                    sawRingingForCurrentCall = true
                    reportedNumberForCurrentCall = null
                    ringingStartedAtMs = System.currentTimeMillis()
                    Log.i(TAG, "RINGING başladı, ts=$ringingStartedAtMs")
                    val number = incomingNumberHint?.trim().orEmpty()
                    if (number.isNotEmpty()) {
                        ringingHintNumber = number
                        report(number)
                    } else {
                        // API 31+ → numara şu an gelmez. CallLog'a 1.5sn sonra bak.
                        // Bazı OEM'lerde RINGING anında zaten kayıt düşer.
                        mainHandler.removeCallbacks(deferredLookup)
                        mainHandler.postDelayed(deferredLookup, 1_500)
                    }
                }
            }
            TelephonyManager.CALL_STATE_OFFHOOK,
            TelephonyManager.CALL_STATE_IDLE -> {
                if (sawRingingForCurrentCall && reportedNumberForCurrentCall == null) {
                    // Hint hâlâ gelmedi → CallLog'tan son INCOMING aramayı bul
                    val resolved = tryResolveFromCallLog(ringingStartedAtMs)
                    if (!resolved.isNullOrBlank()) {
                        report(resolved)
                    } else {
                        Log.w(TAG, "Numara çözülemedi (CallLog izni yok ya da kayıt henüz düşmemiş)")
                    }
                }
                if (state == TelephonyManager.CALL_STATE_IDLE) {
                    sawRingingForCurrentCall = false
                    ringingHintNumber = null
                    reportedNumberForCurrentCall = null
                    mainHandler.removeCallbacks(deferredLookup)
                }
            }
        }
        lastState = state
    }

    /** RINGING'den 1.5sn sonra çağrılır — numara hâlâ raporlanmadıysa CallLog'a bakar. */
    private fun tryReportFromCallLogIfNotYet() {
        if (!sawRingingForCurrentCall) return
        if (reportedNumberForCurrentCall != null) return
        val resolved = tryResolveFromCallLog(ringingStartedAtMs)
        if (!resolved.isNullOrBlank()) {
            Log.i(TAG, "Geç çözüm CallLog'tan: $resolved")
            report(resolved)
        } else {
            Log.d(TAG, "Geç çözüm boş, IDLE'da tekrar denenecek")
        }
    }

    private fun stateName(state: Int): String = when (state) {
        TelephonyManager.CALL_STATE_IDLE -> "IDLE"
        TelephonyManager.CALL_STATE_RINGING -> "RINGING"
        TelephonyManager.CALL_STATE_OFFHOOK -> "OFFHOOK"
        else -> "UNKNOWN($state)"
    }

    private fun report(number: String) {
        reportedNumberForCurrentCall = number
        try {
            onIncoming(number)
        } catch (e: Exception) {
            Log.e(TAG, "onIncoming çağrısı sırasında hata", e)
        }
    }

    /**
     * Verilen zaman damgasından sonra başlayan en yeni INCOMING/MISSED aramayı bulur.
     * READ_CALL_LOG izni yoksa null döner.
     */
    @SuppressLint("MissingPermission")
    private fun tryResolveFromCallLog(afterTimestampMs: Long): String? {
        if (!hasReadCallLogPermission()) {
            Log.w(TAG, "READ_CALL_LOG izni yok — numara çözülemiyor")
            return null
        }
        return try {
            val cursor = context.contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE),
                "${CallLog.Calls.DATE} >= ?",
                arrayOf((afterTimestampMs - 2_000).toString()),
                "${CallLog.Calls.DATE} DESC LIMIT 1"
            )
            cursor?.use {
                if (it.moveToFirst()) {
                    val type = it.getInt(it.getColumnIndexOrThrow(CallLog.Calls.TYPE))
                    val accept = type == CallLog.Calls.INCOMING_TYPE ||
                        type == CallLog.Calls.MISSED_TYPE ||
                        type == CallLog.Calls.REJECTED_TYPE
                    if (accept) {
                        return@use it.getString(it.getColumnIndexOrThrow(CallLog.Calls.NUMBER))
                    }
                }
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "CallLog okuma hatası", e)
            null
        }
    }

    private fun hasReadPhoneStatePermission(): Boolean =
        ContextCompat.checkSelfPermission(
            context, Manifest.permission.READ_PHONE_STATE
        ) == PackageManager.PERMISSION_GRANTED

    private fun hasReadCallLogPermission(): Boolean =
        ContextCompat.checkSelfPermission(
            context, Manifest.permission.READ_CALL_LOG
        ) == PackageManager.PERMISSION_GRANTED

    companion object {
        private const val TAG = "PhoneStateMonitor"
    }
}
