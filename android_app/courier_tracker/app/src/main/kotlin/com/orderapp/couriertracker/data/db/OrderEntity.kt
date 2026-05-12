package com.orderapp.couriertracker.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Siparişin lokal önbellek kaydı.
 * Offline çalışma ve bildirim karşılaştırması için kullanılır.
 *
 * sync_status:
 *   0 = synced   (sunucuyla senkron)
 *   1 = pending  (lokal değişiklik var, sunucuya gönderilmedi)
 */
@Entity(tableName = "orders")
data class OrderEntity(
    /** Supabase UUID (primary key olarak kullanılır). */
    @PrimaryKey
    val id: String,

    @ColumnInfo(name = "order_number")
    val orderNumber: Int,

    val status: String,

    @ColumnInfo(name = "order_date")
    val orderDate: String,

    @ColumnInfo(name = "delivery_time")
    val deliveryTime: String? = null,

    @ColumnInfo(name = "total_amount")
    val totalAmount: Double = 0.0,

    @ColumnInfo(name = "paid_amount")
    val paidAmount: Double = 0.0,

    @ColumnInfo(name = "payment_method")
    val paymentMethod: String? = null,

    @ColumnInfo(name = "payment_status")
    val paymentStatus: String = "pending",

    val notes: String? = null,

    @ColumnInfo(name = "created_at")
    val createdAt: String,

    @ColumnInfo(name = "updated_at")
    val updatedAt: String,

    // Müşteri bilgileri (denormalize — join sorgusu yerine)
    @ColumnInfo(name = "customer_name")
    val customerName: String = "",

    @ColumnInfo(name = "customer_phone")
    val customerPhone: String = "",

    // Adres bilgileri (denormalize)
    @ColumnInfo(name = "address_text")
    val addressText: String? = null,

    val latitude: Double? = null,
    val longitude: Double? = null,

    // Sipariş kalemleri JSON olarak saklanır (basit yaklaşım)
    @ColumnInfo(name = "items_json")
    val itemsJson: String = "[]",

    // Senkronizasyon durumu: 0=synced, 1=pending
    @ColumnInfo(name = "sync_status")
    val syncStatus: Int = SYNC_OK
) {
    companion object {
        const val SYNC_OK = 0
        const val SYNC_PENDING = 1
    }
}
