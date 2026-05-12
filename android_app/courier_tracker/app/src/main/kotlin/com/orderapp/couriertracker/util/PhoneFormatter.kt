package com.orderapp.couriertracker.util

/**
 * Telefon numarası formatlama ve normalizasyon yardımcıları.
 */
object PhoneFormatter {

    /**
     * Ham telefon numarasını görüntüleme formatına çevirir.
     * Örn: "+905321234567" → "0532 123 45 67"
     *      "5321234567" → "0532 123 45 67"
     */
    fun format(raw: String): String {
        val digits = raw.replace(Regex("[^0-9]"), "")
        // Son 10 haneyi al
        val tenDigits = if (digits.length >= 10) digits.takeLast(10) else digits
        return if (tenDigits.length == 10) {
            "0${tenDigits.substring(0, 3)} ${tenDigits.substring(3, 6)} ${tenDigits.substring(6, 8)} ${tenDigits.substring(8)}"
        } else {
            raw // Formatlanamazsa orijinal döndür
        }
    }

    /**
     * Telefon numarasını aranabilir formata çevirir.
     * Başına +90 ekler (Türkiye).
     */
    fun toDialable(raw: String): String {
        val digits = raw.replace(Regex("[^0-9]"), "")
        val tenDigits = if (digits.length >= 10) digits.takeLast(10) else digits
        return if (tenDigits.length == 10) "+90$tenDigits" else raw
    }
}
