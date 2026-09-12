package com.orderapp.adminpanel.data.repository

import com.orderapp.adminpanel.data.local.ConfigDataStore
import com.orderapp.adminpanel.data.model.*
import com.orderapp.adminpanel.data.remote.SupabaseApi
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AdminRepository @Inject constructor(
    private val api: SupabaseApi,
    private val configDataStore: ConfigDataStore
) {
    suspend fun saveConfig(url: String, key: String) {
        configDataStore.saveConfig(url, key)
    }

    suspend fun getSupabaseUrl(): String = configDataStore.getSupabaseUrl()
    suspend fun getSupabaseKey(): String = configDataStore.getSupabaseKey()
    suspend fun hasConfig(): Boolean = configDataStore.hasConfig()
    suspend fun clearConfig() = configDataStore.clearConfig()

    suspend fun testConnection(url: String, key: String): Result<Boolean> = runCatching {
        // Save temporarily to test
        configDataStore.saveConfig(url, key)
        api.getCategories()
        true
    }

    suspend fun getIncomingCalls(): Result<List<IncomingCall>> = runCatching {
        api.getIncomingCalls()
    }

    suspend fun markCallProcessed(id: String): Result<IncomingCall?> = runCatching {
        val result = api.updateIncomingCall("eq.$id", UpdateCallRequest(isProcessed = true))
        result.firstOrNull()
    }

    suspend fun markCallUnanswered(id: String): Result<IncomingCall?> = runCatching {
        val result = api.updateIncomingCall("eq.$id", UpdateCallRequest(isProcessed = true, isUnanswered = true))
        result.firstOrNull()
    }

    suspend fun getOrders(): Result<List<Order>> = runCatching {
        api.getOrders()
    }

    suspend fun getOrderById(id: String): Result<Order?> = runCatching {
        api.getOrderById("eq.$id").firstOrNull()
    }

    suspend fun getOrderItems(orderId: String): Result<List<OrderItem>> = runCatching {
        api.getOrderItems("eq.$orderId")
    }

    suspend fun updateOrderStatus(
        id: String,
        status: String,
        courierId: String? = null,
        paidAmount: Double? = null,
        paymentStatus: String? = null
    ): Result<Order?> = runCatching {
        val request = UpdateOrderStatusRequest(
            status = status,
            courierId = courierId,
            paidAmount = paidAmount,
            paymentStatus = paymentStatus
        )
        val result = api.updateOrderStatus("eq.$id", request)
        result.firstOrNull()
    }

    suspend fun getCustomers(range: String = ""): Result<List<Customer>> = runCatching {
        val allCustomers = mutableListOf<Customer>()
        var offset = 0
        val pageSize = 1000
        while (true) {
            val rangeHeader = "$offset-${offset + pageSize - 1}"
            val page = api.getCustomers(rangeHeader)
            if (page.isEmpty()) break
            allCustomers.addAll(page)
            if (page.size < pageSize) break
            offset += pageSize
        }
        allCustomers
    }


    suspend fun matchCustomerForPhone(phone: String, customerId: String? = null): Customer? {
        if (!customerId.isNullOrBlank()) {
            val byId = runCatching { api.getCustomerById("eq.$customerId").firstOrNull() }.getOrNull()
            if (byId != null) return byId
        }
        val cleanDigits = phone.filter { it.isDigit() }
        if (cleanDigits.length < 6) return null
        val last10 = cleanDigits.takeLast(10)
        return runCatching {
            api.findCustomerByPhone("ilike.*$last10*").firstOrNull()
        }.getOrNull()
    }

    suspend fun searchCustomers(query: String): Result<List<Customer>> = runCatching {
        val cleanQuery = query.trim()
        if (cleanQuery.isBlank()) {
            return@runCatching emptyList()
        }
        val digitsOnly = cleanQuery.filter { it.isDigit() }
        val orQuery = if (digitsOnly.length >= 6) {
            val last10 = digitsOnly.takeLast(10)
            "(name.ilike.*$cleanQuery*,phone.ilike.*$last10*)"
        } else {
            "(name.ilike.*$cleanQuery*,phone.ilike.*$cleanQuery*)"
        }
        api.searchCustomers(orQuery)
    }




    suspend fun getCustomersByIds(ids: List<String>): Result<List<Customer>> = runCatching {
        if (ids.isEmpty()) return@runCatching emptyList()
        val distinctIds = ids.distinct().filter { it.isNotBlank() }
        if (distinctIds.isEmpty()) return@runCatching emptyList()
        val inQuery = "in.(${distinctIds.joinToString(",")})"
        api.getCustomersByIds(inQuery)
    }

    suspend fun getAddressesByCustomerIds(customerIds: List<String>): Result<List<CustomerAddress>> = runCatching {
        if (customerIds.isEmpty()) return@runCatching emptyList()
        val distinctIds = customerIds.distinct().filter { it.isNotBlank() }
        if (distinctIds.isEmpty()) return@runCatching emptyList()
        val inQuery = "in.(${distinctIds.joinToString(",")})"
        api.getAddressesByCustomerIds(inQuery)
    }

    suspend fun createCustomer(
        name: String,
        phone: String,
        notes: String? = null,
        isGuest: Boolean = false
    ): Result<Customer?> = runCatching {
        val req = CreateCustomerRequest(name = name, phone = phone, notes = notes, isGuest = isGuest)
        val list = api.createCustomer(req)
        list.firstOrNull()
    }


    suspend fun getAddresses(customerId: String): Result<List<CustomerAddress>> = runCatching {
        api.getAddresses("eq.$customerId")
    }

    suspend fun createAddress(
        customerId: String,
        addressText: String,
        title: String? = null
    ): Result<CustomerAddress?> = runCatching {
        val req = CreateAddressRequest(customerId = customerId, addressText = addressText, title = title)
        val list = api.createCustomerAddress(req)
        list.firstOrNull()
    }

    suspend fun getCategories(): Result<List<Category>> = runCatching {
        api.getCategories()
    }

    suspend fun getProducts(): Result<List<Product>> = runCatching {
        api.getProducts()
    }

    suspend fun getCouriers(): Result<List<Courier>> = runCatching {
        api.getCouriers()
    }

    suspend fun createOrderWithItems(
        customerId: String,
        addressId: String?,
        addressText: String?,
        courierId: String?,
        totalAmount: Double,
        paymentMethod: String,
        notes: String?,
        items: List<CreateOrderItemRequest>
    ): Result<Order?> = runCatching {
        val orderReq = CreateOrderRequest(
            customerId = customerId,
            addressId = addressId,
            addressText = addressText,
            courierId = courierId,
            status = if (!courierId.isNullOrBlank()) "on_way" else "new",
            totalAmount = totalAmount,
            paymentMethod = paymentMethod,
            notes = notes
        )
        val createdOrders = api.createOrder(orderReq)
        val newOrder = createdOrders.firstOrNull() ?: return@runCatching null

        if (items.isNotEmpty()) {
            val itemsWithOrderId = items.map { it.copy(orderId = newOrder.id) }
            api.createOrderItems(itemsWithOrderId)
        }

        newOrder
    }
}


