package com.orderapp.couriertracker.data.repository

import android.util.Log
import com.orderapp.couriertracker.data.Prefs
import com.orderapp.couriertracker.data.api.ApiClient
import com.orderapp.couriertracker.data.api.CourierLoginResponse
import com.orderapp.couriertracker.data.api.DailySummaryResponse
import com.orderapp.couriertracker.data.api.OrderDto
import com.orderapp.couriertracker.data.db.OrderDao
import com.orderapp.couriertracker.data.db.OrderEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/**
 * Sipariş akışının merkezi:
 *   1. Supabase RPC'den çek → Room'a yaz
 *   2. Offline değişiklik → sync_status=pending → internet gelince gönder
 *   3. Giriş / çıkış işlemleri
 */
class OrderRepository(
    private val dao: OrderDao,
    private val prefs: Prefs
) {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    // ─── Gözlem (UI) ────────────────────────────────────────────────

    fun observeAllOrders(): Flow<List<OrderEntity>> = dao.observeAll()
    fun observeActiveOrders(): Flow<List<OrderEntity>> = dao.observeActive()
    fun observeDeliveredOrders(): Flow<List<OrderEntity>> = dao.observeDelivered()
    fun observeOrder(orderId: String): Flow<OrderEntity?> = dao.observeById(orderId)

    // ─── Giriş ──────────────────────────────────────────────────────

    /**
     * Kurye girişi: RPC çağrısı yapar, başarılıysa Prefs'e kaydeder.
     */
    suspend fun login(phone: String, password: String): Result<CourierLoginResponse> = runCatching {
        val url = prefs.getUrlNow()
        val key = prefs.getKeyNow()

        val response = ApiClient.api(url).courierLogin(
            apiKey = key,
            auth = "Bearer $key",
            body = mapOf("p_phone" to phone, "p_password" to password)
        )

        if (response.success && response.courierId != null) {
            prefs.saveLogin(response.courierId, response.name ?: "", response.phone ?: "")
        }

        response
    }

    /** Bağlantı testi. */
    suspend fun testConnection(url: String, key: String): Result<Unit> = runCatching {
        if (!isPlausibleSupabaseKey(key)) {
            throw IllegalArgumentException(
                "Anahtar geçersiz biçimde görünüyor.\n\n" +
                "Kabul edilen formatlar:\n" +
                "  • Eski JWT key (eyJ... ile başlar)\n" +
                "  • Yeni publishable key (sb_publishable_... ile başlar)\n\n" +
                "Supabase Dashboard → Settings → API bölümünden Anon (publishable) " +
                "key veya yeni 'API keys' sekmesindeki publishable key'i kullanın."
            )
        }
        ApiClient.api(url).ping(apiKey = key, auth = "Bearer $key")
    }

    // ─── Sipariş Senkronizasyon ─────────────────────────────────────

    /**
     * Sunucudan güncel siparişleri çeker ve Room'a yazar.
     * @return Yeni eklenen sipariş ID'lerinin listesi (bildirim için).
     */
    suspend fun syncOrders(): Result<List<String>> = runCatching {
        val url = prefs.getUrlNow()
        val key = prefs.getKeyNow()
        val courierId = prefs.getCourierIdNow()

        if (url.isBlank() || key.isBlank()) {
            throw IllegalStateException(
                "Supabase URL ve API Key yapılandırılmamış. " +
                "Giriş ekranındaki Supabase Ayarları'ndan kontrol edin."
            )
        }
        if (courierId.isBlank()) {
            throw IllegalStateException("Kurye oturumu bulunamadı. Lütfen tekrar giriş yapın.")
        }
        if (!isPlausibleSupabaseKey(key)) {
            throw IllegalStateException(
                "API anahtarı geçersiz görünüyor (eyJ... veya sb_publishable_... " +
                "ile başlamalı). Supabase Dashboard → Settings → API bölümünden " +
                "Anon (publishable) key kullanın."
            )
        }

        // Önce pending değişiklikleri gönder
        syncPendingChanges()

        // Sunucudan çek
        val orders: List<OrderDto> = ApiClient.api(url).getOrders(
            apiKey = key,
            auth = "Bearer $key",
            body = mapOf("p_courier_id" to courierId)
        )

        // Mevcut ID'leri al (yeni sipariş tespiti)
        val existingIds = dao.getAllIds().toSet()

        // DTO → Entity dönüşümü
        val entities = orders.map { it.toEntity() }
        val newIds = entities.map { it.id }.filter { it !in existingIds }

        // Room'a yaz
        dao.upsertAll(entities)

        // Sunucuda olmayan eski siparişleri sil
        val serverIds = entities.map { it.id }
        if (serverIds.isNotEmpty()) {
            dao.deleteExcept(serverIds)
        }

        Log.i(TAG, "Sync OK: ${entities.size} sipariş, ${newIds.size} yeni")
        newIds
    }

    /** Offline'da yapılan durum değişikliklerini sunucuya gönder. */
    private suspend fun syncPendingChanges() {
        val pending = dao.getPending()
        if (pending.isEmpty()) return

        val url = prefs.getUrlNow()
        val key = prefs.getKeyNow()
        val courierId = prefs.getCourierIdNow()

        for (order in pending) {
            try {
                val resp = ApiClient.api(url).updateOrderStatus(
                    apiKey = key,
                    auth = "Bearer $key",
                    body = mapOf(
                        "p_order_id" to order.id,
                        "p_courier_id" to courierId,
                        "p_status" to order.status
                    )
                )
                if (resp.success) {
                    dao.setSyncStatus(order.id, OrderEntity.SYNC_OK)
                    Log.i(TAG, "Pending sync başarılı: #${order.orderNumber}")
                } else {
                    Log.w(TAG, "Pending sync başarısız: ${resp.message}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Pending sync hata: #${order.orderNumber}", e)
            }
        }
    }

    // ─── Durum Güncelleme ───────────────────────────────────────────

    /**
     * Sipariş durumunu güncelle.
     * Önce lokale yaz, sonra sunucuya gönder. Başarısızsa pending kalır.
     */
    suspend fun updateOrderStatus(orderId: String, newStatus: String): Result<Boolean> = runCatching {
        // Önce lokale yaz (instant UI güncelleme)
        dao.updateStatus(orderId, newStatus, OrderEntity.SYNC_PENDING)

        try {
            val url = prefs.getUrlNow()
            val key = prefs.getKeyNow()
            val courierId = prefs.getCourierIdNow()

            val resp = ApiClient.api(url).updateOrderStatus(
                apiKey = key,
                auth = "Bearer $key",
                body = mapOf(
                    "p_order_id" to orderId,
                    "p_courier_id" to courierId,
                    "p_status" to newStatus
                )
            )

            if (resp.success) {
                dao.setSyncStatus(orderId, OrderEntity.SYNC_OK)
                true
            } else {
                Log.w(TAG, "Durum güncelleme başarısız: ${resp.message}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Durum güncelleme hata (pending kalacak)", e)
            false // Lokal güncelleme yapıldı, pending olarak bekleyecek
        }
    }

    // ─── Ödenen Tutar Güncelleme ────────────────────────────────────

    /**
     * Ödenen tutarı güncelle.
     * Önce lokale yaz, sonra sunucuya gönder.
     */
    suspend fun updatePaidAmount(orderId: String, paidAmount: Double): Result<Boolean> = runCatching {
        // Lokale yaz
        dao.updatePaidAmount(orderId, paidAmount)

        try {
            val url = prefs.getUrlNow()
            val key = prefs.getKeyNow()
            val courierId = prefs.getCourierIdNow()

            val resp = ApiClient.api(url).updatePaidAmount(
                apiKey = key,
                auth = "Bearer $key",
                body = mapOf(
                    "p_order_id" to orderId,
                    "p_courier_id" to courierId,
                    "p_paid_amount" to paidAmount.toString()
                )
            )

            if (resp.success) {
                Log.i(TAG, "Ödeme güncelleme başarılı: $orderId → ₺$paidAmount")
                true
            } else {
                Log.w(TAG, "Ödeme güncelleme başarısız: ${resp.message}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Ödeme güncelleme hata", e)
            false
        }
    }

    // ─── Adres Konumu Kaydetme ────────────────────────────────────────

    /**
     * Müşteri adresine anlık GPS konumu kaydet.
     * Önce lokale yaz, sonra sunucuya gönder.
     */
    suspend fun saveAddressLocation(
        orderId: String,
        addressId: String,
        latitude: Double,
        longitude: Double
    ): Result<Boolean> = runCatching {
        // Lokale yaz (instant UI güncelleme)
        dao.updateLocation(orderId, latitude, longitude)

        try {
            val url = prefs.getUrlNow()
            val key = prefs.getKeyNow()
            val courierId = prefs.getCourierIdNow()

            val resp = ApiClient.api(url).saveAddressLocation(
                apiKey = key,
                auth = "Bearer $key",
                body = mapOf(
                    "p_address_id" to addressId,
                    "p_courier_id" to courierId,
                    "p_latitude" to latitude.toString(),
                    "p_longitude" to longitude.toString()
                )
            )

            if (resp.success) {
                Log.i(TAG, "Adres konumu kaydedildi: $addressId → $latitude,$longitude")
                true
            } else {
                Log.w(TAG, "Adres konumu kaydedilemedi: ${resp.message}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Adres konumu kaydetme hata", e)
            false
        }
    }

    // ─── Konum Güncelleme ───────────────────────────────────────────

    suspend fun updateLocation(latitude: Double, longitude: Double): Result<Unit> = runCatching {
        val url = prefs.getUrlNow()
        val key = prefs.getKeyNow()
        val courierId = prefs.getCourierIdNow()

        ApiClient.api(url).updateLocation(
            apiKey = key,
            auth = "Bearer $key",
            body = mapOf(
                "p_courier_id" to courierId,
                "p_latitude" to latitude.toString(),
                "p_longitude" to longitude.toString()
            )
        )
    }

    // ─── Günlük Özet ────────────────────────────────────────────────

    suspend fun getDailySummary(): Result<DailySummaryResponse> = runCatching {
        val url = prefs.getUrlNow()
        val key = prefs.getKeyNow()
        val courierId = prefs.getCourierIdNow()

        ApiClient.api(url).dailySummary(
            apiKey = key,
            auth = "Bearer $key",
            body = mapOf("p_courier_id" to courierId)
        )
    }

    // ─── Çıkış ──────────────────────────────────────────────────────

    suspend fun logout() {
        dao.deleteAll()
        prefs.logout()
    }

    // ─── Yardımcı ───────────────────────────────────────────────────

    /**
     * Supabase API anahtarının olası geçerli bir format olup olmadığını döner.
     * Kabul edilen formatlar:
     *   • Eski JWT (eyJ... ile başlar)         — legacy anon / service_role
     *   • Yeni publishable (sb_publishable_...) — yeni API key sistemi
     *   • Yeni secret      (sb_secret_...)      — backend için, mobilde önerilmez
     * Boş ve çok kısa anahtarlar reddedilir.
     */
    private fun isPlausibleSupabaseKey(key: String): Boolean {
        val trimmed = key.trim()
        if (trimmed.length < 20) return false
        return trimmed.startsWith("eyJ") ||
            trimmed.startsWith("sb_publishable_") ||
            trimmed.startsWith("sb_secret_") ||
            trimmed.startsWith("sbp_")
    }

    private fun OrderDto.toEntity(): OrderEntity = OrderEntity(
        id = id,
        orderNumber = orderNumber,
        status = status,
        orderDate = orderDate,
        deliveryTime = deliveryTime,
        totalAmount = totalAmount,
        paidAmount = paidAmount,
        paymentMethod = paymentMethod,
        paymentStatus = paymentStatus,
        notes = notes,
        createdAt = createdAt,
        updatedAt = updatedAt,
        customerName = customer?.name ?: "",
        customerPhone = customer?.phone ?: "",
        addressId = address?.id,
        addressText = address?.addressText,
        latitude = address?.latitude,
        longitude = address?.longitude,
        itemsJson = json.encodeToString(items ?: emptyList()),
        syncStatus = OrderEntity.SYNC_OK
    )

    companion object {
        private const val TAG = "OrderRepository"
    }
}
