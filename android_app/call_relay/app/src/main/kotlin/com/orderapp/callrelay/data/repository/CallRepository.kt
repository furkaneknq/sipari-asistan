package com.orderapp.callrelay.data.repository

import android.util.Log
import com.orderapp.callrelay.data.Prefs
import com.orderapp.callrelay.data.api.ApiClient
import com.orderapp.callrelay.data.api.IncomingCallDto
import com.orderapp.callrelay.data.db.CallDao
import com.orderapp.callrelay.data.db.CallEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import java.time.Instant

/**
 * Tüm arama akışının merkezi:
 *   1. Lokale (Room) yaz
 *   2. Supabase'e gönder
 *   3. Başarısızsa pending bırak; sonradan trySendPending() ile yeniden dene
 */
class CallRepository(
    private val dao: CallDao,
    private val prefs: Prefs
) {

    fun observeRecent(): Flow<List<CallEntity>> = dao.observeRecent()

    /**
     * Yeni gelen bir aramayı kaydet ve Supabase'e gönder.
     * Çağıran (servis) zaten coroutine scope sağlıyor.
     */
    suspend fun recordIncomingCall(rawPhone: String) {
        val nowIso = Instant.now().toString()
        val normalized = normalizePhone(rawPhone)
        Log.i(TAG, "recordIncomingCall: raw='$rawPhone' normalized='$normalized'")

        val rowId = dao.insert(
            CallEntity(
                phoneNumber = normalized,
                createdAt = nowIso,
                status = CallEntity.STATUS_PENDING
            )
        )
        // Eski kayıtları temizle (DB şişmesin)
        dao.trimOlderThan(keep = 200)

        // Hemen göndermeyi dene
        val sent = sendOnce(rowId, normalized, nowIso)
        if (!sent) {
            Log.w(TAG, "Arama hemen gönderilemedi (pending bırakıldı): $normalized")
        } else {
            Log.i(TAG, "Arama Supabase'e gönderildi: $normalized")
        }
    }

    /**
     * Test araması: gerçek bir telefon çalmadan tüm akışı çalıştırır.
     * Setup ve servisin doğru kurulduğunu hızlıca doğrulamak için.
     *
     * @param customNumber özel test numarası (boşsa varsayılan "+905550000000")
     * @return İşlem başarılıysa Result.success(gönderilen mi), aksi halde failure
     */
    suspend fun sendTestCall(customNumber: String? = null): Result<Boolean> = runCatching {
        val phone = (customNumber?.takeIf { it.isNotBlank() } ?: "+905550000000")
        val nowIso = Instant.now().toString()
        val normalized = normalizePhone(phone)

        val rowId = dao.insert(
            CallEntity(
                phoneNumber = normalized,
                createdAt = nowIso,
                status = CallEntity.STATUS_PENDING
            )
        )
        dao.trimOlderThan(keep = 200)
        sendOnce(rowId, normalized, nowIso)
    }

    /**
     * Pending tüm aramaları sırayla göndermeyi dener.
     * WorkManager veya manuel "Tekrar Dene" tarafından çağrılır.
     * @return Başarılı şekilde gönderilen kayıt sayısı
     */
    suspend fun trySendPending(): Int {
        val pending = dao.pending()
        if (pending.isEmpty()) return 0

        var sentCount = 0
        for (call in pending) {
            if (sendOnce(call.id, call.phoneNumber, call.createdAt)) sentCount++
        }
        return sentCount
    }

    /**
     * Tek bir aramayı Supabase'e gönderir, sonucu DB'ye yazar.
     * Network hatası vb. → pending kalır.
     */
    private suspend fun sendOnce(rowId: Long, phone: String, createdAt: String): Boolean {
        val url = prefs.supabaseUrl.first()
        val key = prefs.supabaseKey.first()
        val deviceId = prefs.deviceId.first()

        if (url.isBlank() || key.isBlank()) {
            dao.updateStatus(rowId, CallEntity.STATUS_PENDING, "Yapılandırma eksik")
            return false
        }

        return try {
            ApiClient.api(url).insertCall(
                apiKey = key,
                auth = "Bearer $key",
                call = IncomingCallDto(
                    phone_number = phone,
                    device_id = deviceId,
                    created_at = createdAt
                )
            )
            dao.updateStatus(rowId, CallEntity.STATUS_SENT, null)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Supabase gönderimi başarısız", e)
            dao.updateStatus(
                rowId,
                CallEntity.STATUS_PENDING,
                e.message ?: e.javaClass.simpleName
            )
            false
        }
    }

    /**
     * Bağlantı testi: Setup ekranında "Test" butonu için.
     * incoming_calls tablosuna 0 satırlık bir GET dener.
     */
    suspend fun testConnection(url: String, key: String): Result<Unit> = runCatching {
        ApiClient.api(url).ping(
            apiKey = key,
            auth = "Bearer $key"
        )
    }

    /**
     * Telefon numarasını E.164 benzeri yapıya getirir:
     *   - Sadece rakam ve baştaki + kalır
     *   - Türkiye için 0 ile başlıyorsa +90 ile değiştirir (10 hane uzunluk varsayımı)
     */
    private fun normalizePhone(raw: String): String {
        val cleaned = raw.replace(Regex("[^0-9+]"), "")
        return when {
            cleaned.startsWith("+") -> cleaned
            cleaned.startsWith("00") -> "+" + cleaned.removePrefix("00")
            cleaned.startsWith("0") && cleaned.length == 11 ->
                "+90" + cleaned.removePrefix("0")
            cleaned.length == 10 -> "+90$cleaned"
            else -> cleaned
        }
    }

    companion object {
        private const val TAG = "CallRepository"
    }
}
