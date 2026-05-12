package com.orderapp.callrelay.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Lokal arama kaydı.
 *
 * status alanı:
 *   0 = pending (henüz gönderilmedi / internet yoktu)
 *   1 = sent    (Supabase'e başarıyla yazıldı)
 *   2 = failed  (kalıcı hata; manuel inceleme)
 */
@Entity(tableName = "calls")
data class CallEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    /** Normalize edilmiş tam telefon (E.164 → "+90..." gibi). */
    @ColumnInfo(name = "phone_number")
    val phoneNumber: String,

    /** Aramanın algılandığı zaman (UTC ISO8601, örn. "2026-05-08T11:32:00Z"). */
    @ColumnInfo(name = "created_at")
    val createdAt: String,

    /** 0=pending, 1=sent, 2=failed */
    val status: Int = STATUS_PENDING,

    /** Son hata metni (varsa). */
    @ColumnInfo(name = "last_error")
    val lastError: String? = null
) {
    companion object {
        const val STATUS_PENDING = 0
        const val STATUS_SENT = 1
        const val STATUS_FAILED = 2
    }
}
