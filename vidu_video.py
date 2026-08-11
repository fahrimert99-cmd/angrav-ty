"""
Vidu (AI video) - gorsel -> video.

Vidu Platform API v2 ile bir karakter gorselinden hareketli klip uretir.
Anahtar KODA GOMULMEZ; VIDU_API_KEY ortam degiskeninden okunur (format: vda_...).

Kullanim:
    export VIDU_API_KEY=vda_...
    python vidu_video.py --img-url https://.../kaan.jpeg \
        --prompt "cute pixar father waving and talking" --cikti klipler/vidu.mp4

Not: img2video genelde SESSIZ olabilir; ses gerekiyorsa ayrica eklenir.
Endpoint/alanlar Vidu dokumanina gore degisebilir; hata olursa API yaniti
aynen basilir.
"""
import argparse
import os
import sys
import time

import requests

BASE = os.environ.get("VIDU_BASE_URL", "https://api.vidu.com").rstrip("/")


def _anahtar() -> str:
    k = os.environ.get("VIDU_API_KEY", "").strip()
    if not k:
        sys.exit("HATA: VIDU_API_KEY yok (secret olarak ekleyin).")
    if not k.isascii():
        sys.exit("HATA: VIDU_API_KEY ASCII olmayan karakter iceriyor.")
    return k


def uret(img_url, prompt, cikti, model="viduq1", duration=5,
         cozunurluk="720p", hareket="auto", zaman_asimi=1200) -> str:
    key = _anahtar()
    basliklar = {
        "Authorization": f"Token {key}",
        "Content-Type": "application/json",
    }
    govde = {
        "model": model,
        "images": [img_url],
        "prompt": prompt,
        "duration": duration,
        "resolution": cozunurluk,
        "movement_amplitude": hareket,
    }

    print(f"[vidu] gorev gonderiliyor (model={model})...")
    r = requests.post(f"{BASE}/ent/v2/img2video", headers=basliklar,
                      json=govde, timeout=90)
    if r.status_code not in (200, 201):
        sys.exit(f"HATA: gorev gonderilemedi (HTTP {r.status_code}): {r.text}")
    task_id = r.json().get("task_id") or r.json().get("id")
    if not task_id:
        sys.exit(f"HATA: task_id yok. Yanit: {r.text}")
    print(f"[vidu] gorev id: {task_id}")

    sorgu = f"{BASE}/ent/v2/tasks/{task_id}/creations"
    bas = time.time()
    video_url = None
    while True:
        if time.time() - bas > zaman_asimi:
            sys.exit("HATA: zaman asimi.")
        time.sleep(8)
        tr = requests.get(sorgu, headers=basliklar, timeout=60)
        if tr.status_code != 200:
            print(f"[vidu] durum sorgusu HTTP {tr.status_code}, tekrar...")
            continue
        js = tr.json()
        durum = js.get("state") or js.get("status")
        print(f"[vidu] durum: {durum}")
        if durum in ("success", "succeeded", "completed"):
            krea = js.get("creations") or []
            if krea:
                video_url = krea[0].get("url")
            break
        if durum in ("failed", "error", "canceled"):
            sys.exit(f"HATA: gorev {durum}: {tr.text}")

    if not video_url:
        sys.exit(f"HATA: video URL'si yok. Son yanit: {tr.text}")
    print(f"[vidu] indiriliyor: {video_url}")
    v = requests.get(video_url, timeout=600)
    v.raise_for_status()
    os.makedirs(os.path.dirname(cikti) or ".", exist_ok=True)
    with open(cikti, "wb") as f:
        f.write(v.content)
    print(f"[vidu] BITTI -> {cikti} ({len(v.content)} byte)")
    return cikti


def main():
    p = argparse.ArgumentParser(description="Vidu img2video")
    p.add_argument("--img-url", required=True, help="Herkese acik gorsel URL'si")
    p.add_argument("--prompt", required=True)
    p.add_argument("--cikti", default="klipler/vidu.mp4")
    p.add_argument("--model", default="viduq1", help="viduq1 | vidu2.0 | vidu1.5")
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--cozunurluk", default="720p", help="360p|720p|1080p")
    p.add_argument("--hareket", default="auto", help="auto|small|medium|large")
    args = p.parse_args()
    uret(args.img_url, args.prompt, args.cikti, args.model, args.duration,
         args.cozunurluk, args.hareket)


if __name__ == "__main__":
    sys.exit(main())
