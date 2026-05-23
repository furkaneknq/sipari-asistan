package com.orderapp.adminpanel.data

import android.content.Context

class AppContainer(context: Context) {
    val prefs: Prefs = Prefs(context.applicationContext)
}
