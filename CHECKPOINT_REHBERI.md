# 🔖 Geri Dönüş Noktası (Checkpoint) Rehberi

Bu proje artık **Git** ile versiyon kontrolü altında. Her yenilikten önce
veya sonra **geri dönüş noktası** oluşturabilirsin; bir şey bozulursa
tek komutla eski hâline döner.

---

## 🎯 Hızlı Başlangıç

### Yeni bir geri dönüş noktası oluştur

```bash
cd ~/Masaüstü/Proje
./checkpoint.sh "yeni rapor sayfası eklendi"
```

Çıktı:
```
✓ Checkpoint oluşturuldu: v1.0.1
  Açıklama: yeni rapor sayfası eklendi
```

Versiyon numarası **otomatik** artar: `v1.0.0 → v1.0.1 → v1.0.2 ...`

### Mevcut noktaları listele

```bash
./checkpoint.sh --list
```

Çıktı:
```
Mevcut Geri Dönüş Noktaları:
  v1.0.2      2026-05-13  rapor grafikleri eklendi
  v1.0.1      2026-05-12  yeni rapor sayfası eklendi
  v1.0.0      2026-05-12  Tamamlanmış sürüm
```

### Bir noktaya geri dön

```bash
./checkpoint.sh --rollback v1.0.1
```

- Mevcut durum otomatik yedek dala alınır (örn. `yedek-20260513-143022`)
- Proje `v1.0.1` durumuna döner
- Pişman olursan:  `git checkout yedek-20260513-143022`

### İki nokta arasındaki farkı gör

```bash
./checkpoint.sh --diff v1.0.1
```

---

## 📋 Önerilen Çalışma Akışı

```
1. Yeni özellik istiyorsun ────────► ./checkpoint.sh "ozellik X oncesi"
                                     (bozulursa buraya dönersin)

2. Cascade ile değişiklikleri yap  

3. Test et — çalışıyor mu?

   ✓ EVET → ./checkpoint.sh "ozellik X tamamlandi"

   ✗ HAYIR → ./checkpoint.sh --rollback v1.0.X  (önceki noktaya dön)
```

---

## 🛡️ Ne Yedeklenir / Ne Yedeklenmez

| Yedeklenir ✅ | Yedeklenmez ❌ |
|---|---|
| Tüm Python kodu (`order_tracking/`) | `.env` (gizli — kasıtlı) |
| Android Kotlin kodu (`android_app/`) | `__pycache__/`, `.venv/` |
| SQL dosyaları (`database/sql/`) | Build çıktıları (`dist/`, `build/`) |
| Installer dosyaları | `Proje-Windows.zip` (üretilen, kaynak değil) |
| Tema, asset dosyaları | IDE ayarları (`.idea/`, `.vscode/`) |

`.gitignore` dosyasında tam liste var.

---

## 🔧 Manuel Git Komutları (gelişmiş)

Script kullanmak istemezsen doğrudan git komutları:

```bash
# Son durumu görmek
git status

# Manuel commit + tag
git add -A
git commit -m "açıklama"
git tag v1.0.5

# Belirli bir noktaya bakmak (sadece okuma — değişiklik yapma)
git checkout v1.0.3        # dosyalar v1.0.3 hâline döner
git checkout main          # geri ana dala

# Belirli bir dosyayı eski hâline döndürmek
git checkout v1.0.3 -- order_tracking/ui/main_window.py

# Tüm değişiklikleri silip son commit'e dönmek
git reset --hard HEAD
```

---

## ☁️ Uzak Yedek (önerilir)

Şu an depo sadece bilgisayarında. **Disk bozulursa her şey gider.**
GitHub'a (private repo) yedeklersen daha güvende olursun:

```bash
# GitHub'da boş bir private repo aç (örn. "siparis-asistani")
git remote add origin git@github.com:KULLANICI_ADIN/siparis-asistani.git
git push -u origin main
git push --tags                # tüm checkpoint'leri de gönder
```

Her checkpoint'ten sonra:
```bash
git push && git push --tags
```

---

## ❓ Sorun Giderme

**"Hiç değişiklik yok, checkpoint oluşturulmadı"**
→ Son checkpoint'ten beri hiçbir dosya değişmemiş. Önce kod değiştir.

**"Permission denied" (script çalışmıyor)**
→ `chmod +x checkpoint.sh` ile çalıştırma izni ver.

**Yanlışlıkla rollback yaptım, yedeklerim nerede?**
→ `git branch | grep yedek-` → tüm yedekleri listeler.
   `git checkout yedek-XXXXXX-XXXXXX` ile geri dönebilirsin.

**Bir dosyayı yanlışlıkla sildim**
→ `git checkout HEAD -- dosya/yolu` ile geri getirilir.
