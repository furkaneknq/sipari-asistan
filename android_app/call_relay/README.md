# Arama Aktarım (Call Relay) — Android Uygulaması

Sipariş Asistanı sisteminin **mobil ayağı**: telefona gelen aramaların numarasını otomatik
olarak Supabase'deki `incoming_calls` tablosuna yazar. Masaüstü uygulamasında "Gelen Arama"
bildirimi olarak görünür.

## Mimari

```
┌──────────────────────┐         ┌────────────────────┐
│  Android Cihaz       │         │  Supabase          │
│                      │         │                    │
│  ┌────────────────┐  │  HTTPS  │  ┌──────────────┐  │
│  │ PhoneState     ├──┼─POST───►│  │ incoming_    │  │
│  │ Monitor        │  │         │  │ calls        │  │
│  └────────┬───────┘  │         │  └──────────────┘  │
│           │          │         │         ▲          │
│  ┌────────▼───────┐  │         │         │          │
│  │ Room (offline) │  │         │  ┌──────┴───────┐  │
│  │ pending kayıt  │  │         │  │ Realtime     │  │
│  └────────────────┘  │         │  │ subscription │  │
│           ▲          │         │  └──────┬───────┘  │
│  ┌────────┴───────┐  │         │         │          │
│  │ NetworkCallback│  │         └─────────┼──────────┘
│  │ → toplu gönder │  │                   │
│  └────────────────┘  │                   ▼
└──────────────────────┘         ┌────────────────────┐
                                 │ Masaüstü Uyg.       │
                                 │ (Gelen Arama Popup) │
                                 └────────────────────┘
```

## Kullanılan teknolojiler

| Katman | Kütüphane |
|---|---|
| UI | Jetpack Compose + Material3 |
| Service | Foreground Service + TelephonyCallback / PhoneStateListener |
| Network | Retrofit + OkHttp + kotlinx.serialization |
| Lokal DB | Room |
| Tercih saklama | DataStore Preferences |
| Async | Coroutines |
| Min SDK | 26 (Android 8.0) |
| Target SDK | 35 (Android 15) |

## Kurulum

### 1. Supabase tarafı

`database/sql/07_incoming_calls_anon_insert.sql` dosyasını Supabase SQL Editor'da bir kez
çalıştırın. Bu, anon (publishable) key ile mobilden `incoming_calls` tablosuna **sadece
INSERT** yapılmasına izin verir. APK'nın anon key'i sızdırmasının riski sınırlı:
mevcut kayıtlar okunamaz, silinemez, güncellenemez.

### 2. Android Studio ile aç

1. **Android Studio Ladybug (2024.2.x)** veya üstünü aç
2. `File → Open` → `android_app/call_relay` klasörünü seç
3. Gradle sync'in bitmesini bekle (ilk seferde bağımlılıklar indirilir)
4. Telefonunu USB ile bağla, **USB hata ayıklama** açık olsun
5. ▶ **Run 'app'** ile cihaza yükle

> Android Studio'da Gradle wrapper indirme yapamıyorsa terminalden:
> ```bash
> cd android_app/call_relay
> gradle wrapper --gradle-version 8.11.1
> ./gradlew :app:installDebug
> ```

### 3. İlk açılış

1. Uygulamayı aç
2. **Supabase URL**: `https://xxxx.supabase.co` (sondaki / olmadan)
3. **Anon Key**: Supabase Dashboard → Settings → API → `anon (publishable)` key
   - **Service role key kullanma!** APK ele geçerse her şey okunabilir.
4. **Cihaz Adı**: ör. "Tezgah Telefonu 1"
5. **Bağlantıyı Test Et** → ✅ olmalı
6. **Kaydet** → ana ekran açılır
7. **Servisi Başlat** → izin diyalogları gelir, hepsine "İzin Ver" de
8. Bildirim çubuğunda kalıcı bildirimi gör: "📞 Arama Aktarım — Aktif"

### 4. İzinler

| İzin | Neden |
|---|---|
| `READ_PHONE_STATE` | Çalan telefonu algılamak için |
| `READ_CALL_LOG` | Android 12+ için numarayı çağrı geçmişinden okumak |
| `READ_PHONE_NUMBERS` | Android 12+ → `EXTRA_INCOMING_NUMBER` dolu gelsin diye |
| `POST_NOTIFICATIONS` | Foreground service bildirimi (Android 13+) |
| `FOREGROUND_SERVICE` | Servis arka planda öldürülmesin |
| `FOREGROUND_SERVICE_DATA_SYNC` | Android 14+ servis tipi (internetle veri sync) |
| `RECEIVE_BOOT_COMPLETED` | Cihaz açılınca servis otomatik başlasın |
| `INTERNET` | Supabase REST'e POST |

### 5. Pil optimizasyonu (önemli)

Android 8+ pil optimizasyonu servisinin uzun süre çalışmasına engel olur. Üreticilere göre:
- **Stock Android / Pixel**: Ayarlar → Uygulamalar → Arama Aktarım → Pil → "Sınırsız"
- **Xiaomi MIUI**: Güvenlik → Pil → Arama Aktarım → Tüm kısıtlamaları kapat + "Otomatik başlat" aç
- **Samsung One UI**: Pil ve cihaz bakımı → Pil → Arka plan kullanımı sınırları → "Asla uyutma"
- **Huawei**: Telefon yöneticisi → Otomatik başlat → Arama Aktarım → 3 maddeyi de aç

## Davranış

### Çalışma akışı

Aramayı yakalama **iki yoldan birden** yapılır (failsafe):

**A. Manifest tabanlı `PhoneStateReceiver`**
- Sistem `android.intent.action.PHONE_STATE` broadcast'ını gönderir
- Servis öldürülmüş olsa bile receiver tetiklenir, servisi başlatır + numarayı extra olarak iletir
- API 26+ için `EXTRA_INCOMING_NUMBER` doludur (READ_CALL_LOG / READ_PHONE_NUMBERS izinleriyle)

**B. Servis içindeki `PhoneStateMonitor`**
- Servis ayağa kalktığı anda `TelephonyCallback` register eder
- API 26-30: numara parametreden direkt gelir
- API 31+: RINGING'den 1.5sn sonra `CallLog`'tan okumayı dener; sonuç boşsa IDLE'da tekrar dener

İki yoldan biri numarayı bulduğunda:
1. Lokale (Room) `pending` olarak yazılır
2. Hemen Supabase'e POST → başarılı ise `sent`
3. İnternet yoksa `pending` kalır → `ConnectivityManager.NetworkCallback` ile toplu sync

> Servis 5 saniye dedup yapar — aynı çağrı için broadcast + telephonyCallback iki kez raporlasa bile sadece **bir** kayıt düşer.

### Yeniden başlatma

`BootReceiver`, cihaz açılınca tetiklenir. Eğer kullanıcı servisi son seferde **AÇIK**
bıraktıysa servis otomatik başlatılır. Kapalı bıraktıysa beklenir.

## Veri modeli

Supabase'e gönderilen JSON:
```json
{
  "phone_number": "+905321234567",
  "device_id": "android-XXXXXXXXXX",
  "created_at": "2026-05-08T11:32:00Z"
}
```

> `device_id` ANDROID_ID tabanlıdır; factory reset'te yenilenir. Tarihler **UTC** ISO8601.

## Sınırlamalar (bilerek)

- **Sadece numara** gönderir; ses kaydı, kontak adı vb. yok (gizlilik)
- Aynı saniyede iki arama gelirse ikisi de yazılır (dedup yok)
- Anon key APK'da gömülüdür; bu sebeple sadece INSERT yetkisi verilir
- API 31+ için numara `CallLog` üzerinden okunur, çağrı bittikten ~birkaç saniye sonra ulaşır

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Uygulama açılır açılmaz duruyor | Foreground service izni veya bildirim izni reddedilmiş; ayarlardan ver |
| "Servisi Başlat" basınca uygulama kapanıyor | **Eski APK** — `foregroundServiceType="phoneCall"` Android 14'te `MANAGE_OWN_CALLS` izni ister. v1.0.1+ sürümünde `dataSync` olarak düzeltildi; APK'yı yeniden build et |
| "Servisi Başlat" butonu pasif | İzinler tamamlanmadı; uyarıdaki "İzin Ver" butonuna bas |
| "Servis başlatılamadı" toast'ı | Logcat'te `CallMonitorService` filtresine bak. Genelde bildirim izni reddi (`POST_NOTIFICATIONS`) veya pil optimizasyonu engelliyor |
| Aramalar bekliyor (`⏳`) ama gönderilmiyor | İnternet yok ya da Supabase URL/key hatalı; "Tekrar Dene" |
| Numara `(bilinmiyor)` görünüyor | API 31+ ve `READ_CALL_LOG` izni yok ya da çağrı log'a yazılmadı |
| **Gerçek arama gelince hiçbir şey olmuyor** | Logcat'te şu filtreleri sırayla bak: `PhoneStateReceiver` → broadcast geliyor mu? `PhoneStateMonitor` → `RINGING` görünüyor mu? `CallRepository` → `recordIncomingCall` çağrıldı mı? `Supabase gönderimi başarısız` ise URL/key kontrol et. **Test araması butonu çalışıyorsa Supabase OK demek; sorun arama algılamada.** Bu durumda: (1) `READ_CALL_LOG` ve `READ_PHONE_NUMBERS` izinlerini ver, (2) Pil optimizasyonu kapat, (3) bildirim çubuğunda "📞 Arama Aktarım — Aktif" görünüyor mu emin ol |
| Servis 1-2 saat sonra durur | Üretici pil optimizasyonu; yukarıdaki "Pil optimizasyonu" bölümü |

## Klasör yapısı

```
call_relay/
├── settings.gradle.kts
├── build.gradle.kts
├── gradle.properties
├── gradle/
│   ├── libs.versions.toml          ← bağımlılık versiyonları
│   └── wrapper/gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── kotlin/com/orderapp/callrelay/
        │   ├── CallRelayApp.kt
        │   ├── data/
        │   │   ├── AppContainer.kt        ← elle DI
        │   │   ├── Prefs.kt               ← DataStore
        │   │   ├── api/
        │   │   │   ├── ApiClient.kt
        │   │   │   └── SupabaseApi.kt
        │   │   ├── db/
        │   │   │   ├── AppDatabase.kt
        │   │   │   ├── CallDao.kt
        │   │   │   └── CallEntity.kt
        │   │   └── repository/
        │   │       └── CallRepository.kt
        │   ├── service/
        │   │   ├── CallMonitorService.kt  ← Foreground service
        │   │   └── PhoneStateMonitor.kt   ← API uyumluluk katmanı
        │   ├── receiver/
        │   │   ├── BootReceiver.kt          ← cihaz açılınca servis başlat
        │   │   └── PhoneStateReceiver.kt    ← manifest tabanlı arama dinleyicisi (failsafe)
        │   ├── ui/
        │   │   ├── MainActivity.kt
        │   │   ├── MainViewModel.kt
        │   │   ├── SetupActivity.kt
        │   │   ├── SetupViewModel.kt
        │   │   ├── theme/
        │   │   │   ├── Color.kt
        │   │   │   ├── Theme.kt
        │   │   │   └── Type.kt
        │   │   └── screens/
        │   │       ├── MainScreen.kt
        │   │       └── SetupScreen.kt
        │   └── util/
        │       ├── DeviceIdProvider.kt
        │       └── PhoneNumberFormatter.kt
        └── res/
            ├── values/{strings,colors,themes}.xml
            ├── drawable/{ic_phone_relay, ic_launcher_*}.xml
            ├── mipmap-anydpi-v26/ic_launcher{,_round}.xml
            └── xml/{backup_rules,data_extraction_rules}.xml
```
