# 🌐 Sipariş Takip Sistemi — Web Portu

Bu web uygulaması, masaüstü Python/PyQt6 uygulamasının tüm özelliklerini (**Siparişler, Gelen Aramalar, Müşteriler, Ürünler, Kuryeler, Ayarlar**) hiçbir kurulum ve derleme gerektirmeden tarayıcıya taşır.

---

## 🚀 Özellikler

- **Tüm Cihazlar & İşletim Sistemleri Uyumlu:** Windows, macOS, Linux, iPad, Android tabletler, iPhone ve Android telefonlarda sorunsuz çalışır.
- **Sıfır Kurulum (Zero Build):** Node.js veya Python derlemesine ihtiyaç duymaz. Doğrudan modern JavaScript (ES Modules) ve HTML5/CSS ile çalışır.
- **Anlık (Realtime) Bildirimler:** Supabase Realtime WebSocket altyapısı sayesinde Android arama aktarma uygulamasından gelen çağrılar ve sipariş değişiklikleri **1 salise içinde** ekrana sesli popup olarak düşer.
- **Dahili Bildirim Zili:** Web Audio API ile harici dosya indirmeden sentezlenen resepsiyon zili sesi.
- **Koyu & Açık Tema:** Göz yormayan şık karanlık mod ve aydınlık mod desteği.
- **Orijinal Uygulamaya Zarar Vermez:** `order_tracking/` ve `android_app/` dizinlerindeki hiçbir dosyayı etkilemez; aynı Supabase veritabanını paylaşır.

---

## 💻 Nasıl Çalıştırılır?

### Yöntem 1: Doğrudan Tarayıcıda Açma (En Kolay)
1. `web_app` klasörünü açın.
2. `index.html` dosyasına çift tıklayarak Chrome, Edge, Safari veya Brave tarayıcınızda açın.
3. Uygulama hemen açılacak ve Supabase veritabanınıza bağlanacaktır.

### Yöntem 2: Dükkan İçi Yerel Ağda (Wi-Fi) Paylaşma
Dükkandaki tabletlerden veya cep telefonlarından bağlanmak için:
- Python ile (terminalde):
  ```bash
  cd web_app
  python -m http.server 8080
  ```
- Ardından tabletinizden veya telefonunuzdan `http://BILGISAYAR_IP_ADRESI:8080` (örneğin `http://192.168.1.50:8080`) adresine girerek kullanabilirsiniz.

### Yöntem 3: Ücretsiz Bulut Barındırma (Vercel / Netlify)
Uygulamayı dükkan dışından, evden veya kurye cep telefonundan internet üzerinden kullanmak isterseniz:
1. [vercel.com](https://vercel.com) veya [netlify.com](https://netlify.com) adresine ücretsiz kaydolun.
2. `web_app` klasörünü sürükleyip bırakın (Drag & Drop deploy).
3. 30 saniye içinde size özel ücretsiz bir adres verilecektir (Örn: `siparis-takip.vercel.app`).
4. **Hiçbir domain satın almanıza gerek yoktur!**

---

## ⚙️ Yapılandırma & Güvenlik

- Supabase bağlantı URL'si ve API Anahtarı `js/config.js` içinde tanımlıdır.
- İsterseniz web arayüzündeki **⚙️ Ayarlar** sekmesinden bağlantı bilgilerinizi dilediğiniz zaman güncelleyebilir ve "Bağlantıyı Test Et" butonu ile kontrol edebilirsiniz.
