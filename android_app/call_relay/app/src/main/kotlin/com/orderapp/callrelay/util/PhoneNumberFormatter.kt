package com.orderapp.callrelay.util

/**
 * UI'da göstermek için telefon numarasını biçimlendirir.
 * Veritabanına yazarken normalize edilmiş E.164 ("+90...") tutuyoruz; bu fonksiyon sadece görsel.
 */
object PhoneNumberFormatter {

    fun forDisplay(raw: String): String {
        if (raw.isBlank()) return "(bilinmiyor)"
        // +90 530 123 45 67
        val digits = raw.removePrefix("+").filter(Char::isDigit)
        return when {
            digits.startsWith("90") && digits.length == 12 -> {
                val nat = digits.substring(2)
                "0${nat.substring(0, 3)} ${nat.substring(3, 6)} " +
                    "${nat.substring(6, 8)} ${nat.substring(8, 10)}"
            }
            digits.length == 10 -> {
                "0${digits.substring(0, 3)} ${digits.substring(3, 6)} " +
                    "${digits.substring(6, 8)} ${digits.substring(8, 10)}"
            }
            else -> raw
        }
    }
}
