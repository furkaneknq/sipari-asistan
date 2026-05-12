package com.orderapp.callrelay.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface CallDao {

    /** UI'da gösterilen "son aramalar" listesi: en yeni 20. */
    @Query("SELECT * FROM calls ORDER BY id DESC LIMIT 20")
    fun observeRecent(): Flow<List<CallEntity>>

    /** Pending kayıtlar — internet gelince toplu sync için. */
    @Query("SELECT * FROM calls WHERE status = 0 ORDER BY id ASC")
    suspend fun pending(): List<CallEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(call: CallEntity): Long

    @Query("UPDATE calls SET status = :status, last_error = :err WHERE id = :id")
    suspend fun updateStatus(id: Long, status: Int, err: String?)

    /** Eski kayıtları temizler (DB şişmesin). */
    @Query("DELETE FROM calls WHERE id NOT IN (SELECT id FROM calls ORDER BY id DESC LIMIT :keep)")
    suspend fun trimOlderThan(keep: Int = 200)
}
