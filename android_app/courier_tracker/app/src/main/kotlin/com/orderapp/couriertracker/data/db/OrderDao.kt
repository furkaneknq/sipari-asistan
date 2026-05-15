package com.orderapp.couriertracker.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface OrderDao {

    /** Tüm siparişleri durum sırasıyla izle (aktifler önce). */
    @Query("""
        SELECT * FROM orders
        ORDER BY
            CASE status
                WHEN 'new' THEN 1
                WHEN 'preparing' THEN 2
                WHEN 'on_way' THEN 3
                WHEN 'delivered' THEN 4
                WHEN 'cancelled' THEN 5
            END,
            created_at DESC
    """)
    fun observeAll(): Flow<List<OrderEntity>>

    /** Aktif (teslim edilmemiş / iptal olmamış) siparişler. */
    @Query("SELECT * FROM orders WHERE status NOT IN ('delivered', 'cancelled') ORDER BY created_at DESC")
    fun observeActive(): Flow<List<OrderEntity>>

    /** Teslim edilmiş siparişler (bugünkü). */
    @Query("SELECT * FROM orders WHERE status = 'delivered' ORDER BY updated_at DESC")
    fun observeDelivered(): Flow<List<OrderEntity>>

    /** Tek sipariş. */
    @Query("SELECT * FROM orders WHERE id = :orderId")
    fun observeById(orderId: String): Flow<OrderEntity?>

    /** Senkron tek sipariş (bildirim karşılaştırması için). */
    @Query("SELECT * FROM orders WHERE id = :orderId")
    suspend fun getById(orderId: String): OrderEntity?

    /** Tüm sipariş ID'leri (yeni sipariş tespiti için). */
    @Query("SELECT id FROM orders")
    suspend fun getAllIds(): List<String>

    /** Toplu ekleme/güncelleme (sunucudan çekilen veriler). */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(orders: List<OrderEntity>)

    /** Durumu lokal olarak güncelle (offline mod). */
    @Query("UPDATE orders SET status = :status, sync_status = :syncStatus WHERE id = :orderId")
    suspend fun updateStatus(orderId: String, status: String, syncStatus: Int = OrderEntity.SYNC_PENDING)

    /** Ödenen tutarı lokal olarak güncelle. */
    @Query("UPDATE orders SET paid_amount = :paidAmount WHERE id = :orderId")
    suspend fun updatePaidAmount(orderId: String, paidAmount: Double)

    /** Adres konumunu lokal olarak güncelle. */
    @Query("UPDATE orders SET latitude = :lat, longitude = :lng WHERE id = :orderId")
    suspend fun updateLocation(orderId: String, lat: Double, lng: Double)

    /** Belirtilen ID'ler dışındakileri sil (günü geçmiş temizlik). */
    @Query("DELETE FROM orders WHERE id NOT IN (:keepIds)")
    suspend fun deleteExcept(keepIds: List<String>)

    /** Pending güncellemeleri getir. */
    @Query("SELECT * FROM orders WHERE sync_status = 1")
    suspend fun getPending(): List<OrderEntity>

    /** Senkronizasyon durumunu güncelle. */
    @Query("UPDATE orders SET sync_status = :status WHERE id = :orderId")
    suspend fun setSyncStatus(orderId: String, status: Int)

    /** Tüm siparişleri temizle (çıkış yaparken). */
    @Query("DELETE FROM orders")
    suspend fun deleteAll()
}
