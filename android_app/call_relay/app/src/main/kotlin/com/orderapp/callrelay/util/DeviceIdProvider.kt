package com.orderapp.callrelay.util

import android.content.Context
import android.provider.Settings
import java.util.UUID

/**
 * Sabit bir cihaz kimliği üretir.
 *   - Önce Settings.Secure.ANDROID_ID dener (factory reset'te değişir)
 *   - O da boşsa rastgele UUID oluşturur ve gelecekte de aynısını döner (Prefs'te saklanmasını çağıran sağlar)
 */
object DeviceIdProvider {

    fun obtain(context: Context): String {
        val androidId = try {
            Settings.Secure.getString(
                context.contentResolver,
                Settings.Secure.ANDROID_ID
            )
        } catch (_: Exception) {
            null
        }
        return if (!androidId.isNullOrBlank() && androidId != "9774d56d682e549c") {
            "android-$androidId"
        } else {
            "android-${UUID.randomUUID()}"
        }
    }
}
