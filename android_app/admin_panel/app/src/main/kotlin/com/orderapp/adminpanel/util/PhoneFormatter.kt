package com.orderapp.adminpanel.util

object PhoneFormatter {

    fun format(raw: String): String {
        val digits = raw.replace(Regex("[^0-9]"), "")
        val tenDigits = if (digits.length >= 10) digits.takeLast(10) else digits
        return if (tenDigits.length == 10) {
            "0${tenDigits.substring(0, 3)} ${tenDigits.substring(3, 6)} ${tenDigits.substring(6, 8)} ${tenDigits.substring(8)}"
        } else {
            raw
        }
    }

    fun toDialable(raw: String): String {
        val digits = raw.replace(Regex("[^0-9]"), "")
        val tenDigits = if (digits.length >= 10) digits.takeLast(10) else digits
        return if (tenDigits.length == 10) "+90$tenDigits" else raw
    }
}
