# Clickjacking (UI Redressing) Demosu

Yazılım Güvenliği dersi için hazırlanmış, **tamamen yerel** çalışan bir gösterim.
İnternet bağlantısı veya gerçek bir siteye saldırı gerektirmez.

## Senaryo
- **Kurban site** (`localhost:8000`): "GüvenBank" adlı örnek bir internet bankacılığı.
  Tek tıkla 1.000 TL transfer eden bir butonu var.
- **Saldırgan site** (`localhost:9090`): "iPhone kazandınız" çekilişi gibi görünen tuzak sayfa.
  Banka sayfasını **görünmez (saydam) bir iframe** içinde yükler ve transfer butonunu
  sahte "Hediyemi Al" butonunun tam üzerine hizalar.

Kurban, yeşil "Hediyemi Al" butonuna tıkladığını sanır; gerçekte tıklaması saydam
iframe'in altındaki bankanın "Para Transfer Et" butonuna gider. Buna **UI redressing**
denir.

## Çalıştırma
```bash
cd clickjacking-demo
python3 server.py
```
Sonra tarayıcıda **http://localhost:9090/** adresini aç.

> Not: Demonun çalışması için kurban sayfasında "oturum açık" varsayılır — gerçek
> dünyada saldırı, kullanıcının hedef siteye zaten giriş yapmış olmasına dayanır.

## Sınıfta anlatım akışı

1. **Önce kurbanı tanıt.** `http://localhost:8000/` aç — normal banka, transfer butonu.
2. **Saldırıyı göster.** `http://localhost:9090/` aç. "Hediyemi Al"a tıkla.
   Arkadaki gizli bankada transfer gerçekleşir (iframe'i görünür yaparsan kanıtlarsın).
3. **Hizalamayı ifşa et.** `server.py` içinde saldırgan sayfasındaki
   `opacity:0.0` değerini `opacity:0.3` yap, sunucuyu yeniden başlat.
   Artık saydam iframe'in altta nasıl konumlandığı görünür — öğretici an budur.
4. **Savunmayı aç.** `http://localhost:8000/toggle-defense` aç (savunma ON olur),
   sonra tekrar `http://localhost:9090/`. Banka artık iframe'e yüklenmez —
   saldırı kırılır.

## Savunmalar (kodda gösterilen)
- `X-Frame-Options: DENY` — sayfanın herhangi bir iframe'e konmasını yasaklar (eski tarayıcılar).
- `Content-Security-Policy: frame-ancestors 'self'` — modern, esnek karşılığı; yalnızca
  sayfanın kendi origin'inin onu çerçevelemesine izin verir.
- Ek olarak (bu demoda yok, sözlü anlat): hassas işlemler için
  ek onay adımı / SameSite çerezler / kullanıcı etkileşimi doğrulaması.

## Dosyalar
- `server.py` — iki sunucuyu (kurban + saldırgan) çalıştırır, savunma açma/kapama dahil.
- `README.md` — bu dosya.
