package com.orderapp.callrelay.service

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.orderapp.callrelay.CallRelayApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * WhatsApp (ve WhatsApp Business) gelen aramalarını yakalayan
 * NotificationListenerService.
 *
 * Çalışma prensibi:
 *   1. Android sistem servisi olarak bildirim erişimi açıldığında aktif olur
 *   2. Her yeni bildirim geldiğinde [onNotificationPosted] tetiklenir
 *   3. WhatsApp paketinden gelen ve "arama" içeren bildirimleri filtreler
 *   4. Bildirim metninden telefon numarasını çıkarır
 *   5. Mevcut [CallRepository] üzerinden Supabase'e yazar
 *
 * Dedup: 10 saniye içinde aynı numara tekrar raporlanmaz.
 *
 * Kullanıcı gereksinimi:
 *   Android Ayarlar → Bildirim Erişimi → "Arama Aktarım" → AÇ
 */
class WhatsAppCallListener : NotificationListenerService() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    /** Aynı numarayı kısa sürede iki kez yazmamak için dedup. */
    private var lastReportedNumber: String? = null
    private var lastReportedAtMs: Long = 0L

    companion object {
        private const val TAG = "WhatsAppCallListener"

        /** WhatsApp paket adları. */
        private val WHATSAPP_PACKAGES = setOf(
            "com.whatsapp",
            "com.whatsapp.w4b"  // WhatsApp Business
        )

        /** Bildirim metninde aranacak anahtar kelimeler (dil bağımsız). */
        private val CALL_KEYWORDS = listOf(
            // Türkçe
            "gelen arama", "sesli arama", "görüntülü arama", "arama",
            // İngilizce
            "incoming call", "voice call", "video call", "calling",
            // Genel
            "📞", "📹"
        )

        private const val DEDUP_WINDOW_MS = 10_000L

        /**
         * Bildirim metninden telefon numarasını çıkarmaya çalışır.
         * WhatsApp bildirimleri genelde "Ad (numara)" veya sadece numara içerir.
         */
        fun extractPhoneNumber(text: String): String? {
            // Parantez içindeki numara: "Ali (+90 532 123 45 67)"
            val parenMatch = Regex("""\(([+\d][\d\s\-().]+)\)""").find(text)
            if (parenMatch != null) {
                val candidate = parenMatch.groupValues[1].replace(Regex("[^0-9+]"), "")
                if (candidate.length >= 7) return candidate
            }

            // Direkt numara formatı: "+90 532 123 45 67" veya "0532 123 45 67"
            val phoneMatch = Regex("""[+]?\d[\d\s\-().]{6,}""").find(text)
            if (phoneMatch != null) {
                val candidate = phoneMatch.value.replace(Regex("[^0-9+]"), "")
                if (candidate.length >= 7) return candidate
            }

            return null
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return

        val pkg = sbn.packageName ?: return
        if (pkg !in WHATSAPP_PACKAGES) return

        val extras = sbn.notification?.extras ?: return
        val title = extras.getCharSequence("android.title")?.toString() ?: ""
        val text = extras.getCharSequence("android.text")?.toString() ?: ""
        val combined = "$title $text".lowercase()

        // Arama bildirimi mi kontrol et
        val isCallNotification = CALL_KEYWORDS.any { keyword -> keyword in combined }
        if (!isCallNotification) return

        Log.d(TAG, "WhatsApp arama bildirimi: title='$title' text='$text' pkg=$pkg")

        // Numarayı çıkar — önce title'dan, sonra text'ten dene
        val phone = extractPhoneNumber(title)
            ?: extractPhoneNumber(text)

        if (phone.isNullOrBlank()) {
            Log.w(TAG, "WhatsApp arama bildirimi yakalandı ama numara çıkarılamadı: '$title' / '$text'")
            return
        }

        // Dedup kontrolü
        val now = System.currentTimeMillis()
        if (phone == lastReportedNumber && now - lastReportedAtMs < DEDUP_WINDOW_MS) {
            Log.d(TAG, "Yinelenen WhatsApp araması atlandı: $phone")
            return
        }
        lastReportedNumber = phone
        lastReportedAtMs = now

        Log.i(TAG, "WhatsApp araması yakalandı: $phone (paket: $pkg)")

        // CallRepository üzerinden Supabase'e gönder
        scope.launch {
            try {
                val repo = CallRelayApp.get().container.repository
                repo.recordIncomingCall(phone)
                Log.i(TAG, "WhatsApp araması Supabase'e gönderildi: $phone")
            } catch (e: Exception) {
                Log.e(TAG, "WhatsApp araması gönderilemedi", e)
            }
        }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
