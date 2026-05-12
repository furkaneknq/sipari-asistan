package com.orderapp.couriertracker.data

import android.content.Context
import com.orderapp.couriertracker.data.db.AppDatabase
import com.orderapp.couriertracker.data.repository.OrderRepository

/**
 * Basit DI konteyneri.
 * Hilt yerine elle yazılmış sade bir wiring; küçük uygulama için yeterli.
 */
class AppContainer(context: Context) {

    val prefs: Prefs = Prefs(context.applicationContext)

    private val database = AppDatabase.get(context)
    val orderDao = database.orderDao()

    val repository: OrderRepository = OrderRepository(orderDao, prefs)
}
