"""Supabase istemci tekil (singleton) örneği.

Tüm CRUD modülleri ve realtime dinleyici buradan client alır.

Anahtar formatına göre otomatik olarak uygun istemci seçilir:
  - JWT anahtarı (eyJ...): supabase-py kütüphanesi kullanılır
  - sb_secret_ / sbp_ anahtarı: doğrudan httpx tabanlı RestClient kullanılır
"""

from __future__ import annotations

import logging
from typing import Any

import config

log = logging.getLogger(__name__)

_client: Any = None


def _is_jwt_key(key: str) -> bool:
    """Anahtarın JWT formatında olup olmadığını kontrol eder."""
    return key.startswith("eyJ")


def get_client() -> Any:
    """Tekil istemciyi döndürür, yoksa oluşturur.

    Anahtar formatına göre supabase-py veya hafif RestClient kullanır.
    """
    global _client
    if _client is not None:
        return _client

    if not config.is_configured():
        raise RuntimeError(config.missing_config_message())

    key = config.SUPABASE_KEY
    url = config.SUPABASE_URL

    if _is_jwt_key(key):
        # JWT anahtarı → supabase-py kullan
        try:
            from supabase import create_client
            _client = create_client(url, key)
            log.info("supabase-py istemcisi oluşturuldu (JWT key)")
        except Exception as exc:
            log.warning("supabase-py başarısız, RestClient'a geçiliyor: %s", exc)
            from .rest_client import RestClient
            _client = RestClient(url, key)
    else:
        # sb_secret_ veya diğer format → doğrudan REST kullan
        from .rest_client import RestClient
        _client = RestClient(url, key)
        log.info("RestClient oluşturuldu (sb_secret_ key)")

    return _client


def reset_client() -> None:
    """İstemciyi sıfırlar (örn. ayarlar ekranından bağlantı yenilenirse)."""
    global _client
    _client = None


def _diagnose_error(exc: Exception) -> str:
    """Ham hata mesajını insan-okur Türkçe açıklamaya çevirir."""
    raw = str(exc)
    low = raw.lower()
    url = config.SUPABASE_URL or "(boş)"

    # 1) URL placeholder hâlâ doldurulmamış
    suspicious = ("xxxx", "your-project", "example.supabase.co", "<your")
    if any(s in url.lower() for s in suspicious):
        return (
            "Yapılandırma eksik: SUPABASE_URL hâlâ örnek değer içeriyor.\n\n"
            f"Mevcut URL: {url}\n\n"
            "Çözüm:\n"
            "1) Başlat Menüsü → 'Ayarları Düzenle (.env)' kısayoluna tıkla\n"
            "   (veya kurulum klasöründeki .env dosyasını Notepad ile aç).\n"
            "2) SUPABASE_URL ve SUPABASE_SECRET_KEY satırlarına Supabase\n"
            "   Dashboard → Settings → API ekranındaki gerçek değerleri yapıştır.\n"
            "3) Kaydet ve programı yeniden başlat."
        )

    # 2) DNS / İnternet sorunu
    dns_signals = (
        "getaddrinfo failed",
        "name or service not known",
        "nodename nor servname",
        "11001",
        "temporary failure in name resolution",
        "no address associated with hostname",
    )
    if any(s in low for s in dns_signals):
        return (
            "İnternet veya DNS sorunu — Supabase sunucusuna ulaşılamıyor.\n\n"
            f"Adres çözümlenemiyor: {url}\n\n"
            "Kontrol et:\n"
            "1) Bilgisayar internete bağlı mı? (Tarayıcıda google.com aç)\n"
            "2) .env dosyasındaki SUPABASE_URL doğru yazıldı mı?\n"
            "   • Sonunda '/' OLMAMALI\n"
            "   • https:// ile başlamalı\n"
            "   • Örn: https://abcdefg.supabase.co\n"
            "3) DNS sorunuysa: Ağ ayarlarında DNS'i 1.1.1.1 veya 8.8.8.8 yap."
        )

    # 3) Timeout / bağlantı reddi
    if any(s in low for s in ("timeout", "timed out", "connection refused", "connection reset")):
        return (
            "Sunucuya bağlanılamıyor (zaman aşımı).\n\n"
            "Kontrol et:\n"
            "1) İnternet bağlantın stabil mi?\n"
            "2) Bir firewall / antivirüs uygulamayı engelliyor olabilir.\n"
            "3) Supabase projesi 'paused' (uyutulmuş) olabilir — "
            "Dashboard'a gir, varsa 'Restore project' yap."
        )

    # 4) SSL / sertifika
    if "ssl" in low or "certificate" in low:
        return (
            "SSL sertifika hatası.\n\n"
            "Genellikle sistem saatinin yanlış olmasından kaynaklanır.\n"
            "Bilgisayarın saat/tarihini ve saat dilimini kontrol et."
        )

    # 5) Yetkilendirme
    auth_signals = ("401", "403", "invalid api key", "jws", "jwt", "unauthorized", "forbidden")
    if any(s in low for s in auth_signals):
        msg = (
            "API anahtarı geçersiz veya yetersiz.\n\n"
            ".env dosyasındaki SUPABASE_SECRET_KEY değerini kontrol et:\n"
            "Supabase Dashboard → Settings → API → Project API keys → "
            "service_role 'secret' anahtarını kopyala."
        )
        if not _is_jwt_key(config.SUPABASE_KEY):
            msg += (
                "\n\nNot: sb_secret_ formatı kullanıyorsun. "
                "Sorun çözülmezse eski JWT (eyJ... ile başlayan) anahtarı da dene."
            )
        return msg

    # 6) Tablo bulunamadı vb. — şema kurulmamış
    if "relation" in low and "does not exist" in low:
        return (
            "Veritabanı şeması eksik.\n\n"
            "Supabase SQL Editor'de database/sql/ klasöründeki dosyaları\n"
            "sırayla çalıştır:  01_tables.sql → 02_triggers.sql → ...\n"
            "(Detay: HANDOFF.md §7)"
        )

    # Bilinmeyen hata — ham metni göster
    return f"Bilinmeyen bağlantı hatası:\n\n{raw}"


def test_connection() -> tuple[bool, str]:
    """Basit bir SELECT sorgusu ile bağlantıyı dener."""
    try:
        client = get_client()
        client.table("settings").select("key").limit(1).execute()
        return True, "Bağlantı başarılı."
    except Exception as exc:  # noqa: BLE001
        return False, _diagnose_error(exc)
