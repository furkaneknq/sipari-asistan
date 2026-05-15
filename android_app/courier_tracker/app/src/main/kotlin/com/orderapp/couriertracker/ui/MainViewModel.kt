package com.orderapp.couriertracker.ui

import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.couriertracker.CourierTrackerApp
import com.orderapp.couriertracker.data.api.DailySummaryResponse
import com.orderapp.couriertracker.data.db.OrderEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * Ana ekran state yönetimi.
 * Sipariş listesi, durum güncelleme, günlük özet.
 */
class MainViewModel : ViewModel() {

    private val container = CourierTrackerApp.get().container
    private val prefs = container.prefs
    private val repo = container.repository

    // ─── State ───────────────────────────────────────────────────────

    /** Kurye adı (header'da gösterilir). */
    var courierName by mutableStateOf("")
        private set

    /** Günlük özet. */
    var dailySummary by mutableStateOf(DailySummaryResponse())
        private set

    /** Yükleniyor mu? */
    var isRefreshing by mutableStateOf(false)
        private set

    /** Hata mesajı. */
    var errorMessage by mutableStateOf<String?>(null)
        private set

    /** Servis çalışıyor mu? */
    var serviceRunning by mutableStateOf(false)
        private set

    /** Tüm siparişler (Room Flow → StateFlow). */
    val allOrders = repo.observeAllOrders()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** Aktif siparişler. */
    val activeOrders = repo.observeActiveOrders()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** Teslim edilmiş siparişler. */
    val deliveredOrders = repo.observeDeliveredOrders()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        viewModelScope.launch { prefs.courierName.collect { courierName = it } }
        viewModelScope.launch { prefs.serviceEnabled.collect { serviceRunning = it } }
        // İlk yüklemede senkronize et
        refresh()
    }

    // ─── Aksiyonlar ──────────────────────────────────────────────────

    fun refresh() {
        viewModelScope.launch {
            isRefreshing = true
            errorMessage = null

            repo.syncOrders()
                .onFailure { e ->
                    Log.e(TAG, "Refresh hatası", e)
                    errorMessage = "Güncelleme başarısız: ${e.message}"
                }

            // Günlük özet
            repo.getDailySummary()
                .onSuccess { dailySummary = it }
                .onFailure { Log.e(TAG, "Özet hatası", it) }

            isRefreshing = false
        }
    }

    fun updateOrderStatus(orderId: String, newStatus: String) {
        viewModelScope.launch {
            repo.updateOrderStatus(orderId, newStatus)
                .onFailure { e ->
                    errorMessage = "Durum güncellenemedi: ${e.message}"
                }
            // Günlük özeti de güncelle
            repo.getDailySummary().onSuccess { dailySummary = it }
        }
    }

    fun updatePaidAmount(orderId: String, paidAmount: Double) {
        viewModelScope.launch {
            repo.updatePaidAmount(orderId, paidAmount)
                .onFailure { e ->
                    errorMessage = "Ödeme güncellenemedi: ${e.message}"
                }
            // Günlük özeti de güncelle
            repo.getDailySummary().onSuccess { dailySummary = it }
        }
    }

    fun saveAddressLocation(orderId: String, addressId: String, latitude: Double, longitude: Double) {
        viewModelScope.launch {
            repo.saveAddressLocation(orderId, addressId, latitude, longitude)
                .onFailure { e ->
                    errorMessage = "Konum kaydedilemedi: ${e.message}"
                }
        }
    }

    fun clearError() { errorMessage = null }

    fun logout() {
        viewModelScope.launch { repo.logout() }
    }

    // ─── Tek sipariş gözlemi ─────────────────────────────────────────

    fun observeOrder(orderId: String) = repo.observeOrder(orderId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    companion object {
        private const val TAG = "MainViewModel"
    }
}
