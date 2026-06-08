#!/usr/bin/env python3
"""
Clickjacking (UI Redressing) Egitim Demosu
==========================================
Uc ayri yerel sunucu calistirir:

  1) KURBAN SITE      -> http://localhost:8000   (GuvenBank - para transfer onay ekrani)
  2) SALDIRGAN SITE   -> http://localhost:9090   (sahte cekilis - savunma KAPALI, saldiri basarili)
  3) SAVUNMA SAYFASI  -> http://localhost:9091   (savunma ACIK - ayni saldiri engellenir)

Sayfalarin HTML'leri ayri klasorlerde tutulur:
  victim/bank.html       -> kurban banka sayfasi
  attacker/attack.html   -> saldirgan cekilis sayfasi (canli savunma toggle'i ile)
  defense/defense.html   -> her zaman savunma acik gosterim sayfasi

Saldirgan sayfa, kurban sayfayi tum ekrani kaplayan SEFFAF bir iframe icinde yukler.
Bankanin "Onayla ve Gonder" butonu sabit bir noktaya, saldirgan sayfadaki sahte
"Hediyemi Al" butonu da TAM AYNI noktaya konur; iki buton piksel piksel cakisir.

Demo sirasinda savunmayi canli ac/kapa (sadece 9090 icin):
  http://localhost:8000/toggle-defense
"""

import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = Path(__file__).resolve().parent

# Kurban sitenin cerceveleme savunmasi acik mi? /toggle-defense ile degisir.
# (Yalnizca 9090 saldirgan sayfasini etkiler; 9091 zaten her zaman savunmalidir.)
DEFENSE_ENABLED = {"on": False}

# Tum sayfalarda AYNI deger: butonun ekrandaki sabit konumu (piksel cakismasi icin).
BTN_TOP = 480
BTN_WIDTH = 440
BTN_HEIGHT = 62


def load_page(rel_path):
    """Klasordeki HTML dosyasini okur ve buton konumu yer tutucularini doldurur."""
    html = (BASE_DIR / rel_path).read_text(encoding="utf-8")
    return (
        html.replace("__BTN_TOP__", str(BTN_TOP))
        .replace("__BTN_WIDTH__", str(BTN_WIDTH))
        .replace("__BTN_HEIGHT__", str(BTN_HEIGHT))
        .replace("__OK_TOP__", str(BTN_TOP + BTN_HEIGHT + 14))
        .replace("__SLOT_H__", str(BTN_HEIGHT + 26))
    )


BANK_PAGE = load_page("victim/bank.html")
ATTACKER_PAGE = load_page("attacker/attack.html")
DEFENSE_PAGE = load_page("defense/defense.html")


class BankHandler(BaseHTTPRequestHandler):
    """Kurban site: 8000."""

    def _send_html(self, html, with_defense):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Chrome Private Network Access - cross-port localhost iframe icin gerekli
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Origin", "*")
        if with_defense:
            # --- SAVUNMALAR ---
            self.send_header("X-Frame-Options", "DENY")               # eski tarayicilar
            self.send_header("Content-Security-Policy",               # modern karsilik
                             "frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/status"):
            import json
            body = json.dumps({"defense": DEFENSE_ENABLED["on"]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/secure"):
            # Her zaman savunma basliklariyla servis edilir (9091 savunma sayfasi icin).
            self._send_html(BANK_PAGE, with_defense=True)
            return
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
    """Saldirgan site: 9090 (savunma kapali - saldiri basarili)."""

    def do_GET(self):
        body = ATTACKER_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[SALDIRGAN:9090]", fmt % args)


class DefenseHandler(BaseHTTPRequestHandler):
    """Savunma sayfasi: 9091 (savunma acik - saldiri engellenir)."""

    def do_GET(self):
        body = DEFENSE_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[SAVUNMA:9091]", fmt % args)


def serve(port, handler):
    ThreadingHTTPServer(("localhost", port), handler).serve_forever()


if __name__ == "__main__":
    print("Banka     : http://localhost:8000/")
    print("Saldiri   : http://localhost:9090/")
    print("Savunma   : http://localhost:9091/")
    threading.Thread(target=serve, args=(8000, BankHandler), daemon=True).start()
    threading.Thread(target=serve, args=(9090, AttackerHandler), daemon=True).start()
    serve(9091, DefenseHandler)
