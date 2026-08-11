"""
Replicate wan-2.2-s2v: KARAKTER GORSELI + SES -> dudak senkronlu konusan video.

Alibaba'nin wan2.2-s2v modeli dudak senkronu yapar ama resmi API'si Cin bolgesi
kisitlidir; Replicate uzerinden uluslararasi cagrilir. Verilen sese (or.
ElevenLabs Turkce sesi) gore karakterin dudaklari/ifadesi senkronlanir.

Anahtar KODA GOMULMEZ; REPLICATE_API_TOKEN ortam degiskeninden okunur.

Kullanim:
    export REPLICATE_API_TOKEN=r8_...
    python wan_s2v_replicate.py \
        --gorsel karakterler/kaan.jpeg \
        --ses klipler/ses.mp3 \
        --cikti klipler/konusan.mp4

Not: Replicate kullanim-basi ucretlidir (kayitta kucuk deneme kredisi olabilir).
Girdi alan adlari (image/audio) modele gore degisebilir; hata olursa API yaniti
aynen basilir, gecerli alanlar oradan gorulur.
"""
import argparse
import base64
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

MODEL = os.environ.get("REPLICATE_MODEL", "wan-video/wan-2.2-s2v")
BASE = "https://api.replicate.com/v1"


def _data_uri(yol: str) -> str:
    if not Path(yol).exists():
        sys.exit(f"HATA: dosya bulunamadi: {yol}")
    mt = mimetypes.guess_type(yol)[0] or "application/octet-stream"
    b64 = base64.b64encode(Path(yol).read_bytes()).decode()
    return f"data:{mt};base64,{b64}"


def uret(gorsel: str, ses: str, cikti: str, prompt: str = "",
         zaman_asimi: int = 1200) -> str:
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        sys.exit("HATA: REPLICATE_API_TOKEN ortam degiskeni yok "
                 "(GitHub Actions secret'i olarak ekleyin).")
    if not token.isascii():
        sys.exit("HATA: REPLICATE_API_TOKEN ASCII olmayan karakter iceriyor. "
                 "Secret'i Replicate'ten yeniden, dogru kopyalayin "
                 "(bosluk/Turkce karakter olmadan).")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait",  # kisa islerde sonucu bekler; degilse poll ederiz
    }
    girdi = {"image": _data_uri(gorsel), "audio": _data_uri(ses)}
    if prompt:
        girdi["prompt"] = prompt

    print(f"[s2v] prediction olusturuluyor (model={MODEL})...")
    r = requests.post(f"{BASE}/models/{MODEL}/predictions",
                      headers=headers, json={"input": girdi}, timeout=180)
    if r.status_code not in (200, 201):
        sys.exit(f"HATA: prediction olusturulamadi (HTTP {r.status_code}): "
                 f"{r.text[:900]}")

    pred = r.json()
    get_url = pred.get("urls", {}).get("get")
    baslangic = time.time()
    while pred.get("status") not in ("succeeded", "failed", "canceled"):
        if time.time() - baslangic > zaman_asimi:
            sys.exit(f"HATA: {zaman_asimi}s icinde tamamlanmadi.")
        time.sleep(5)
        pr = requests.get(get_url, headers=headers, timeout=60)
        pr.raise_for_status()
        pred = pr.json()
        print(f"[s2v] durum: {pred.get('status')}")

    if pred.get("status") != "succeeded":
        sys.exit(f"HATA: prediction {pred.get('status')}: {pred.get('error')}")

    cikti_alani = pred.get("output")
    video_url = cikti_alani[0] if isinstance(cikti_alani, list) else cikti_alani
    if not video_url:
        sys.exit(f"HATA: cikti video URL'si yok. Yanit: {pred}")

    print(f"[s2v] video indiriliyor: {video_url}")
    v = requests.get(video_url, timeout=600)
    v.raise_for_status()
    Path(cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(cikti).write_bytes(v.content)
    print(f"[s2v] BITTI -> {cikti} ({len(v.content)} byte)")
    return cikti


def main():
    p = argparse.ArgumentParser(description="Replicate wan-2.2-s2v konusan video")
    p.add_argument("--gorsel", required=True, help="Karakter gorseli (jpeg/png)")
    p.add_argument("--ses", required=True, help="Konusma sesi (mp3/wav)")
    p.add_argument("--cikti", default="klipler/konusan.mp4", help="Cikti mp4")
    p.add_argument("--prompt", default="", help="Opsiyonel sahne/istem")
    args = p.parse_args()
    uret(args.gorsel, args.ses, args.cikti, args.prompt)


if __name__ == "__main__":
    sys.exit(main())
