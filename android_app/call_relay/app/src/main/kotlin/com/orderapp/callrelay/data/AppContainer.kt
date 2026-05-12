package com.orderapp.callrelay.data

import android.content.Context
import com.orderapp.callrelay.data.db.AppDatabase
import com.orderapp.callrelay.data.repository.CallRepository

/**
 * Basit DI konteyneri.
 * Hilt yerine elle yazılmış sade bir wiring; küçük uygulama için yeterli.
 */
class AppContainer(context: Context) {

    val prefs: Prefs = Prefs(context.applicationContext)

    private val database = AppDatabase.get(context)
    val callDao = database.callDao()

    val repository: CallRepository = CallRepository(callDao, prefs)
}
