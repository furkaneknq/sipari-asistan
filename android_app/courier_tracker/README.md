# Kurye Takip (Courier Tracker) — Android Uygulaması

Sipariş Asistanı sisteminin **kurye ayağı**: kuryeler bu uygulama üzerinden
kendilerine atanan siparişleri görür, durumlarını günceller, müşteriyi arar
ve konumlarını paylaşır.

## Mimari

```
┌──────────────────────┐         ┌────────────────────┐
│  Android Cihaz       │         │  Supabase          │
│                      │         │                    │
│  ┌────────────────┐  │  HTTPS  │  ┌──────────────┐  │
│  │ Polling        ├──┼──RPC───►│  │ orders       │  │
│  │ Service        │  │         │  │ couriers     │  │
│  └────────┬───────┘  │         │  │ customers    │  │
│           │          │         │  └──────────────┘  │
│  ┌────────▼───────┐  │         │         ▲          │
│  │ Room (offline) │  │         │         │          │
│  │ sipariş cache  │  │         └─────────┼──────────┘
│  └────────────────┘  │                   │
│           ▲          │                   ▼
│  ┌────────┴───────┐  │         ┌────────────────────┐
│  │ Compose UI     │  │         │ Masaüstü Uyg.       │
│  │ Liste + Detay  │  │         │ (Sipariş Yönetimi)  │
│  └────────────────┘  │         └────────────────────┘
└──────────────────────┘
```

## Kullanılan teknolojiler

| Katman | Kütüphane |
|---|---|
| UI | Jetpack Compose + Material3 |
| Navigasyon | Navigation Compose |
| Service | Foreground Service (polling) |
| Network | Retrofit + OkHttp + kotlinx.serialization |
| Lokal DB | Room |
| Tercih saklama | DataStore Preferences |
| Konum | Google Play Services Location |
| Async | Coroutines |
| Min SDK | 26 (Android 8.0) |
| Target SDK | 35 (Android 15) |

## Kurulum

### 1. Supabase tarafı

`database/sql/08_courier_app_policies.sql` dosyasını Supabase SQL Editor'da bir kez
çalıştırın. Bu, 5 RPC fonksiyonu oluşturur:

- `courier_login(phone, password)` — giriş
- `courier_get_orders(courier_id)` — günlük siparişler (join'li)
- `courier_update_order_status(order_id, courier_id, status)` — durum güncelle
- `courier_update_location(courier_id, lat, lng)` — konum güncelle
- `courier_daily_summary(courier_id)` — günlük özet

Tüm fonksiyonlar `SECURITY DEFINER` ile çalışır; anon key RLS'i bypass eder.
APK'da sadece anon (publishable) key saklanır.

### 2. Masaüstünde kurye ekleme

Masaüstü uygulamasının **Kuryeler** sekmesinden kurye ekleyin. Telefon ve şifre
alanları zorunludur; bu bilgilerle Android'den giriş yapılacak.

### 3. Android Studio ile aç

1. **Android Studio Ladybug (2024.2.x)** veya üstünü aç
2. `File → Open` → `android_app/courier_tracker` klasörünü seç
3. Gradle sync'in bitmesini bekle
4. Telefonunu USB ile bağla, **USB hata ayıklama** açık olsun
5. ▶ **Run 'app'** ile cihaza yükle

### 4. İlk açılış

1. Uygulamayı aç → Giriş ekranı gelir
2. **Supabase Ayarları** bölümünü aç (ilk kurulumda otomatik açılır):
   - **Supabase URL**: `https://xxxx.supabase.co`
   - **Anon Key**: Supabase Dashboard → Settings → API → `anon (publishable)` key
3. **Bağlantı Test** → ✅ olmalı → **Kaydet**
4. **Telefon**: Kuryenin masaüstünde kayıtlı telefon numarası
5. **Şifre**: Kuryenin masaüstünde belirlenen şifresi
6. **Giriş Yap** → Ana ekran açılır
7. Konum ve bildirim izinleri istenecek → hepsine **İzin Ver**

### 5. İzinler

| İzin | Neden |
|---|---|
| `INTERNET` | Supabase REST'e bağlantı |
| `ACCESS_FINE_LOCATION` | Kurye konumunu paylaşmak |
| `CALL_PHONE` | Müşteriyi doğrudan aramak |
| `POST_NOTIFICATIONS` | Yeni sipariş bildirimi (Android 13+) |
| `FOREGROUND_SERVICE` | Polling servisi arka planda çalışsın |
| `RECEIVE_BOOT_COMPLETED` | Cihaz açılınca servis otomatik başlasın |

## Özellikler

### Giriş Ekranı
- Telefon + şifre ile kurye girişi
- Supabase URL/Key ayarları (genişletilebilir panel)
- Bağlantı testi butonu

### Ana Ekran — Sipariş Listesi
- Pull-to-refresh ile güncelleme
- Aktif siparişler: kart görünümü (sipariş no, müşteri, adres, fiyat, saat)
- Her kartta durum dropdown'u (Yeni → Hazırlanıyor → Yolda → Teslim Edildi)
- Harita butonu (Google Maps intent)
- Teslim edilenler: compact liste (no, ✅, müşteri, tutar)
- Günlük özet: teslim sayısı + toplam tutar

### Sipariş Detay Ekranı
- Müşteri bilgisi + telefon arama butonu
- Adres + haritada göster butonu
- Ürün listesi (isim, miktar, birim fiyat, toplam)
- Ödeme bilgisi (nakit/kart/IBAN + alınacak tutar)
- Sipariş notu
- Durum değiştirme dropdown'u

### Bildirim Sistemi
- Yeni sipariş atandığında yüksek öncelikli bildirim (ses + titreşim)
- Bildirime tıklanınca sipariş detayı açılır

### Konum Takibi
- 60 saniyede bir kurye konumu Supabase'e gönderilir
- Masaüstü uygulamasından kuryenin konumu görülebilir

### Offline Destek
- Tüm siparişler Room'da önbelleğe alınır
- Durum değişiklikleri offline'da da çalışır
- İnternet gelince otomatik senkronize edilir (sync_status flag'i ile)

## Polling

Servis 10 saniyede bir Supabase'den sipariş çeker:
1. Önce pending (offline) değişiklikleri gönderir
2. `courier_get_orders` RPC'sini çağırır
3. Room'a yazar, yeni sipariş varsa bildirim gönderir
4. Eski (sunucuda olmayan) siparişleri temizler

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Giriş başarısız | Masaüstünde kurye telefon/şifresini kontrol et |
| Bağlantı testi başarısız | URL sonunda `/` olmamalı, anon key doğru mu? |
| Bildirim gelmiyor | Android Ayarlar → Uygulamalar → Kurye Takip → Bildirimler → açık olmalı |
| Konum güncellenmiyor | Konum izni verilmiş mi? GPS açık mı? |
| Sipariş listesi boş | Masaüstünden kuryeye sipariş atanmış mı? |
| Servis 1-2 saat sonra duruyor | Pil optimizasyonunu kapat (üretici bazlı) |

## Klasör yapısı

```
courier_tracker/
├── settings.gradle.kts
├── build.gradle.kts
├── gradle.properties
├── README.md
├── gradle/
│   ├── libs.versions.toml
│   └── wrapper/gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── kotlin/com/orderapp/couriertracker/
        │   ├── CourierTrackerApp.kt          ← Application + bildirim kanalları
        │   ├── data/
        │   │   ├── AppContainer.kt           ← elle DI
        │   │   ├── Prefs.kt                  ← DataStore (oturum + ayarlar)
        │   │   ├── api/
        │   │   │   ├── ApiClient.kt           ← Retrofit singleton
        │   │   │   ├── SupabaseApi.kt         ← RPC endpoint tanımları
        │   │   │   └── Models.kt              ← DTO'lar
        │   │   ├── db/
        │   │   │   ├── AppDatabase.kt         ← Room veritabanı
        │   │   │   ├── OrderDao.kt            ← sipariş DAO
        │   │   │   └── OrderEntity.kt         ← sipariş entity
        │   │   └── repository/
        │   │       └── OrderRepository.kt     ← sipariş iş mantığı
        │   ├── service/
        │   │   └── OrderPollingService.kt     ← foreground polling + konum
        │   ├── receiver/
        │   │   └── BootReceiver.kt            ← cihaz açılınca servis başlat
        │   ├── ui/
        │   │   ├── LoginActivity.kt
        │   │   ├── LoginViewModel.kt
        │   │   ├── MainActivity.kt            ← navigasyon + izinler
        │   │   ├── MainViewModel.kt
        │   │   ├── theme/
        │   │   │   ├── Color.kt
        │   │   │   ├── Theme.kt
        │   │   │   └── Type.kt
        │   │   └── screens/
        │   │       ├── LoginScreen.kt
        │   │       ├── OrderListScreen.kt
        │   │       └── OrderDetailScreen.kt
        │   └── util/
        │       └── PhoneFormatter.kt
        └── res/
            ├── values/{strings,colors,themes}.xml
            ├── drawable/{ic_courier,ic_launcher_*}.xml
            ├── mipmap-anydpi-v26/ic_launcher{,_round}.xml
            └── xml/{backup_rules,data_extraction_rules}.xml
```
