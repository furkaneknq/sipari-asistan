# Windows Kurulum Paketi (`SiparisAsistaniSetup.exe`)

Bu klasör, Sipariş Asistanı masaüstü uygulamasını **tek tıkla kurulan**
bir Windows installer (.exe) haline getirmek için ihtiyacın olan her şeyi
içerir.

## Tek seferlik araçlar (yalnızca senin Windows makinende)

| Araç | İndirme |
|---|---|
| Python 3.11 veya 3.12 (önerilen) | <https://www.python.org/downloads/windows/> — kurulumda **"Add Python to PATH"** seç |
| Inno Setup 6 | <https://jrsoftware.org/isdl.php> → **innosetup-6.x.x.exe** |

> Python ve Inno Setup yalnızca senin geliştirme/build makinende olmalı.
> Son kullanıcının (siparişi alan kişi) yalnızca `SiparisAsistaniSetup.exe`'yi
> çalıştırması yeterli — Python yüklemesi gerekmiyor.

## Kurulum dosyasını üretmek (1 komut)

1. Bu klasörü Windows bilgisayara **kopyala** (USB, GitHub, ZIP — fark etmez).
   Önemli: Linux'tan kopyaladıysan dosya satır sonlarının **CRLF** olduğundan
   emin ol. Bu repo'daki `.gitattributes` Git üzerinden klonlarken bunu
   otomatik yapar; manuel kopyalarken Notepad++/VSCode ile "End of Line:
   Windows (CRLF)" seçip kaydet.
2. Bu klasöre git: `installer\windows\`
3. **`BUILD_BURAYA_CIFT_TIKLA.bat`** dosyasına çift tıkla
   (alternatif olarak: `build.bat`'i CMD içinden çalıştırabilirsin —
   `cmd /k build.bat` — böylece pencere kapanmaz)

Script otomatik olarak:

1. Sanal ortam oluşturur (`order_tracking\.venv`)
2. Tüm bağımlılıkları + PyInstaller + Pillow yükler
3. `app.ico` üretir
4. PyInstaller ile `dist\SiparisAsistani\SiparisAsistani.exe` derler
5. Inno Setup yüklüyse `installer\windows\Output\SiparisAsistaniSetup.exe`
   üretir

İlk derleme **5-10 dakika** sürer; sonraki derlemeler hızlı olur.

## Üretilen kurulum dosyası ne yapar?

`SiparisAsistaniSetup.exe`'yi son kullanıcı çalıştırdığında:

- `C:\Program Files\SiparisAsistani\` altına kurar (yönetici izni ister)
- Başlat menüsüne **3 kısayol** ekler:
  - **Sipariş Asistanı** — programı başlatır
  - **Ayarları Düzenle (.env)** — Notepad ile config dosyasını açar
  - **Kurulum Klasörünü Aç** — Explorer'da klasörü açar
- Masaüstüne kısayol koyar (kullanıcı tercihi)
- SQL migration dosyalarını `{app}\sql\` altına kopyalar (referans için)
- Kurulum sonunda Notepad'i `.env` ile açar — kullanıcı Supabase URL/Key girer
- Kaldırma sırasında `.env`'yi `%APPDATA%\SiparisAsistani\.env.backup`
  olarak yedekler (sonraki kurulumda elle geri yüklenebilir)

## İlk açılış (son kullanıcı tarafı)

1. `SiparisAsistaniSetup.exe`'yi çift tıkla → **Yes** (UAC)
2. Sihirbazı takip et, **Kur**
3. Kurulum bitince Notepad açılır → `.env` dosyasını düzenle:

   ```env
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_SECRET_KEY=eyJ...    # Service role (Dashboard → API → secret keys)
   PRINTER_TYPE=dummy            # usb | network | serial | dummy
   ```

4. Kaydet, kapat → "Sipariş Asistanı'nı şimdi başlat" işaretini bırakırsan
   program açılır

## Mimari notlar

### `.env` arama sırası

Program başlatıldığında bu sırayla `.env` aranır:

1. **Exe'nin yanı** — `C:\Program Files\SiparisAsistani\.env`
   (kurulum default'u; tüm kullanıcılar paylaşır)
2. **Kullanıcı `%APPDATA%`** — `C:\Users\<kullanıcı>\AppData\Roaming\SiparisAsistani\.env`
   (kullanıcı bazlı override için)
3. **Linux/Mac** (geliştirme) — `~/.config/siparis-asistani/.env`

`config.py` içindeki `_find_env_file()` bu sırayı uygular.

### Klasör yapısı

```
installer/windows/
├── README.md              ← şu an okuduğun dosya
├── build.bat              ← çift tıkla → her şeyi yap
├── build_icon.py          ← Pillow ile app.ico üretir
├── app.ico                ← Windows ikonu (build_icon.py üretir)
├── order_tracking.spec    ← PyInstaller spec (gizli importlar dahil)
├── installer.iss          ← Inno Setup script
└── Output/                ← Inno Setup çıktısı
    └── SiparisAsistaniSetup.exe
```

### PyInstaller'ın topladığı paketler

`order_tracking.spec` dosyasında şu paketler için `collect_all` çağrısı yapılır
(dinamik import ettikleri için PyInstaller'ın gözünden kaçar):

- `supabase`, `postgrest`, `storage3`, `supabase_auth`, `realtime`, `gotrue`
- `openpyxl` (Excel import/export)
- `phonenumbers` (telefon doğrulama)
- `escpos` (termal yazıcı)
- `PIL` (resim işleme)

Yeni bir paket eklediğinde `order_tracking.spec` içindeki `for pkg in (...)`
listesine ad ekle.

## Sorun giderme

| Belirti | Sebep / Çözüm |
|---|---|
| **build.bat çift tıklayınca pencere açılıp kapanıyor** | Dosya **LF** (Unix) satır sonlarıyla. Çözüm: `BUILD_BURAYA_CIFT_TIKLA.bat` kullan — bu wrapper pencereyi `cmd /k` ile açık tutar. Veya elle CMD aç, `cd installer\windows`, `build.bat` yaz |
| **`Microsoft Visual C++ 14.0 or greater is required`** veya `pyiceberg` build hatası | Yeni `supabase` sürümleri C++ derleyici gerektiren `pyiceberg`'i transitive olarak çekiyordu. `requirements.txt` artık `supabase<2.13` ile pinli — `order_tracking\.venv` klasörünü **sil** ve betiği yeniden çalıştır. Build tools kurmaya **gerek yok**. |
| `python` veya `py` bulunamadı | Python kurulumda "Add Python to PATH" seçili değil. Kaldır + tekrar kur. Önerilen: Python 3.11 veya 3.12 (3.13/3.14 bazı wheel'lerde sorun çıkarır) |
| PyInstaller yüklenmiyor | Antivirüs (özellikle Avast/AVG/Defender) PyInstaller'ı bloke eder. Geçici devre dışı bırak veya klasörü exception listesine ekle |
| `Inno Setup yüklü değil` uyarısı | <https://jrsoftware.org/isdl.php> adresinden ISCC.exe dahil tam paketi kur |
| Exe açılır açılmaz kapanıyor | Konsol için spec'te `console=True` yap, exe'yi cmd'den çalıştırıp hatayı gör |
| "VCRUNTIME140.dll bulunamadı" | Son kullanıcıya **Microsoft Visual C++ 2015-2022 Redistributable** kur |
| Supabase'e 400 hata | `.env` içindeki URL `/` ile bitmesin: `https://xxxx.supabase.co` |
| Yazıcı bulunamadı | `PRINTER_TYPE=usb` ise yazıcı sürücüsü kurulu olmalı; `dummy` ile test et |

## İleride yapılacak (opsiyonel)

- **Code signing** — Microsoft SmartScreen uyarısını kaldırmak için EV/OV
  kod imzalama sertifikası (~$200/yıl)
- **MSI paketleme** — Inno Setup yerine WiX ile kurumsal dağıtım
- **Otomatik güncelleme** — `pyupdater` veya manuel "yeni sürüm var" kontrolü
