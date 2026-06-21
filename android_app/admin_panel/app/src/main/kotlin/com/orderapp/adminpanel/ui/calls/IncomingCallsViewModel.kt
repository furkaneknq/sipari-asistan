package com.orderapp.adminpanel.ui.calls

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.orderapp.adminpanel.data.model.IncomingCall
import com.orderapp.adminpanel.data.repository.AdminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class IncomingCallsViewModel @Inject constructor(
    private val repository: AdminRepository
) : ViewModel() {

    private val _calls = MutableStateFlow<List<IncomingCall>>(emptyList())
    val calls: StateFlow<List<IncomingCall>> = _calls

    init {
        fetchCalls()
    }

    fun fetchCalls() {
        viewModelScope.launch {
            try {
                val list = repository.getIncomingCalls()
                _calls.value = list
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun markAsProcessed(id: String) {
        viewModelScope.launch {
            try {
                repository.markCallProcessed(id)
                fetchCalls()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
