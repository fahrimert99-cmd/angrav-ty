"""
Wan (Tongyi Wanxiang) gorsel -> video.

Alibaba DashScope image-to-video API ile bir KARAKTER GORSELINDEN hareketli
bir klip uretir. "basit"/"cpu" motorlarinin aksine karakter gercekten hareket
eder (govde/jest/kamera), cunku bulut GPU'da diffusion video modeli calisir.

Anahtar KODA GOMULMEZ; yalnizca DASHSCOPE_API_KEY ortam degiskeninden okunur
(GitHub Actions'ta repo secret'i olarak tanimlayin).

Kullanim:
    export DASHSCOPE_API_KEY=sk-...
    python wan_klip.py \
        --gorsel karakterler/kaan.jpeg \
        --prompt "cute 3D Pixar boy playing happily, waving hands, bouncing" \
        --cikti klipler/01.mp4

Notlar:
- Endpoint varsayilani ULUSLARARASI hesaptir (dashscope-intl). Hesabiniz Cin
  bolgesindeyse DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com verin.
- Model/parametreler DashScope dokumanina gore degisebilir; DASHSCOPE_MODEL
  ile degistirilebilir. Hata olursa API yaniti aynen basilir.
- Gorsel, base64 data-URI olarak gonderilir (yerel dosya yeter, herkese acik
  URL gerekmez). Isterseniz --img-url ile dogrudan bir URL de verebilirsiniz.
"""
import argparse
import base64
import mimetypes
import os
import sys
import time

import requests


SUBMIT_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
TASK_PATH = "/api/v1/tasks/{task_id}"


def _anahtar() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not key:
        sys.exit("HATA: DASHSCOPE_API_KEY ortam degiskeni tanimli degil. "
                 "GitHub Actions'ta repo secret'i olarak ekleyin.")
    return key


def _base_url() -> str:
    return os.environ.get(
        "DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com").rstrip("/")


def _gorsel_kaynagi(gorsel: str | None, img_url: str | None) -> str:
    """API'ye verilecek gorsel kaynagini dondurur: dogrudan URL ya da yerel
    dosyadan base64 data-URI."""
    if img_url:
        return img_url
    if not gorsel or not os.path.exists(gorsel):
        sys.exit(f"HATA: gorsel bulunamadi: {gorsel}")
    mt = mimetypes.guess_type(gorsel)[0] or "image/jpeg"
    with open(gorsel, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mt};base64,{b64}"


def uret(gorsel, prompt, cikti, img_url=None, model=None,
         cozunurluk="720P", negatif="", zaman_asimi=600) -> str:
    key = _anahtar()
    base = _base_url()
    model = model or os.environ.get("DASHSCOPE_MODEL", "wanx2.1-i2v-turbo")

    gorev_gonder = base + SUBMIT_PATH
    basliklar = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    govde = {
        "model": model,
        "input": {
            "prompt": prompt,
            "img_url": _gorsel_kaynagi(gorsel, img_url),
        },
        "parameters": {
            "resolution": cozunurluk,
            "prompt_extend": True,
        },
    }
    if negatif:
        govde["input"]["negative_prompt"] = negatif

    print(f"[wan] gorev gonderiliyor (model={model})...")
    r = requests.post(gorev_gonder, headers=basliklar, json=govde, timeout=60)
    if r.status_code != 200:
        sys.exit(f"HATA: gorev gonderilemedi (HTTP {r.status_code}): {r.text}")
    task_id = r.json().get("output", {}).get("task_id")
    if not task_id:
        sys.exit(f"HATA: task_id alinamadi. Yanit: {r.text}")
    print(f"[wan] gorev id: {task_id}  (durum bekleniyor...)")

    gorev_sorgu = base + TASK_PATH.format(task_id=task_id)
    sorgu_basliklari = {"Authorization": f"Bearer {key}"}
    baslangic = time.time()
    while True:
        if time.time() - baslangic > zaman_asimi:
            sys.exit(f"HATA: {zaman_asimi}s icinde tamamlanmadi (task {task_id}).")
        time.sleep(8)
        tr = requests.get(gorev_sorgu, headers=sorgu_basliklari, timeout=60)
        if tr.status_code != 200:
            print(f"[wan] durum sorgusu HTTP {tr.status_code}, tekrar denenecek...")
            continue
        out = tr.json().get("output", {})
        durum = out.get("task_status")
        print(f"[wan] durum: {durum}")
        if durum == "SUCCEEDED":
            video_url = out.get("video_url") or out.get("results", [{}])[0].get("url")
            if not video_url:
                sys.exit(f"HATA: video_url yok. Yanit: {tr.text}")
            break
        if durum in ("FAILED", "CANCELED", "UNKNOWN"):
            sys.exit(f"HATA: gorev basarisiz ({durum}): {tr.text}")

    print(f"[wan] video indiriliyor: {video_url}")
    vr = requests.get(video_url, timeout=300)
    vr.raise_for_status()
    os.makedirs(os.path.dirname(cikti) or ".", exist_ok=True)
    with open(cikti, "wb") as f:
        f.write(vr.content)
    print(f"[wan] BITTI -> {cikti} ({len(vr.content)} byte)")
    return cikti


def main():
    p = argparse.ArgumentParser(description="Wan (DashScope) gorsel -> hareketli video")
    p.add_argument("--gorsel", help="Karakter gorsel yolu (or. karakterler/kaan.jpeg)")
    p.add_argument("--img-url", help="Alternatif: dogrudan herkese acik gorsel URL'si")
    p.add_argument("--prompt", required=True, help="Hareketi tarif eden Ingilizce istem")
    p.add_argument("--negatif", default="static, still image, low quality, distorted",
                   help="Negatif istem")
    p.add_argument("--cikti", default="klipler/01.mp4", help="Cikti mp4 yolu")
    p.add_argument("--model", default=None, help="DashScope model (var. wanx2.1-i2v-turbo)")
    p.add_argument("--cozunurluk", default="720P", help="480P | 720P | 1080P")
    args = p.parse_args()

    uret(gorsel=args.gorsel, prompt=args.prompt, cikti=args.cikti,
         img_url=args.img_url, model=args.model, cozunurluk=args.cozunurluk,
         negatif=args.negatif)


if __name__ == "__main__":
    sys.exit(main())
