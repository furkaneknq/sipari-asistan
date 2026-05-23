package com.orderapp.adminpanel

import android.app.Application
import com.orderapp.adminpanel.data.AppContainer

class AdminPanelApp : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        container = AppContainer(this)
    }

    companion object {
        @Volatile
        private var instance: AdminPanelApp? = null

        fun get(): AdminPanelApp =
            instance ?: error("AdminPanelApp henüz oluşturulmamış")
    }
}
