"""
DashScope dijital-insan (konusan karakter) denemesi.

Alibaba'nin s2v/EMO modellerini DOGRUDAN DashScope uzerinden dener (Replicate
gerektirmez). Gorsel + ses (herkese acik URL'ler) -> dudak senkronlu video.
Model adaylari sirayla denenir; biri "yok/bolge disi" derse sonrakine gecer.

UYARI: wan2.2-s2v/EMO resmi olarak Cin (Pekin) bolgesi agirliklidir; uluslararasi
anahtarla bolge/erisim hatasi donebilir. Bu betik tam da bunu KESIN olcmek icin
var: hata olursa API yaniti aynen basilir.

Anahtar KODA GOMULMEZ; DASHSCOPE_API_KEY env'inden okunur.
Endpoint DASHSCOPE_BASE_URL ile degistirilebilir (Cin: https://dashscope.aliyuncs.com).

Kullanim:
    python wan_s2v_dashscope.py \
        --img-url https://raw.githubusercontent.com/.../kaan.jpeg \
        --audio-url https://.../ses.mp3 \
        --cikti klipler/konusan.mp4
"""
import argparse
import os
import sys
import time

import requests

SUBMIT_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
TASK_PATH = "/api/v1/tasks/{task_id}"

# Denenecek dijital-insan model adaylari (bolge/erisim varsa ilk calisan kullanilir)
MODEL_ADAYLARI = [
    "wan2.2-s2v",
    "wanx2.1-s2v",
    "emo-v1",
    "emo-detect-v1",
    "videoretalking",
]


def _anahtar() -> str:
    k = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not k:
        sys.exit("HATA: DASHSCOPE_API_KEY yok.")
    if not k.isascii():
        sys.exit("HATA: DASHSCOPE_API_KEY ASCII olmayan karakter iceriyor.")
    return k


def _base() -> str:
    return (os.environ.get("DASHSCOPE_BASE_URL")
            or "https://dashscope-intl.aliyuncs.com").rstrip("/")


def _model_yok(t: str) -> bool:
    t = (t or "").lower()
    return ("model not exist" in t or "invalidmodel" in t
            or "model_not_exist" in t or "not found" in t)


def uret(img_url, audio_url, cikti, model=None, cozunurluk="720P",
         zaman_asimi=1200) -> str:
    key = _anahtar()
    base = _base()
    basliklar = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    govde = {
        "input": {"image_url": img_url, "audio_url": audio_url},
        "parameters": {"resolution": cozunurluk},
    }

    istem_model = model or os.environ.get("DASHSCOPE_MODEL")
    adaylar = [istem_model] if istem_model else list(MODEL_ADAYLARI)

    r = None
    secilen = None
    for aday in adaylar:
        print(f"[s2v] model deneniyor: {aday}")
        r = requests.post(base + SUBMIT_PATH, headers=basliklar,
                          json=dict(govde, model=aday), timeout=90)
        if r.status_code == 200:
            secilen = aday
            break
        if r.status_code in (400, 404) and _model_yok(r.text):
            print(f"[s2v]   '{aday}' bu hesap/bolgede yok -> sonraki")
            continue
        # Baska hata (bolge/yetki/parametre) -> aynen bildir ve dur
        sys.exit(f"HATA: gorev gonderilemedi (HTTP {r.status_code}): {r.text}")

    if secilen is None:
        sys.exit("HATA: hicbir dijital-insan modeli bu hesapta calismadi "
                 f"({', '.join(adaylar)}). Muhtemelen bolge kisiti (Cin gerekli). "
                 f"Son yanit: {r.text if r else '-'}")
    print(f"[s2v] kullanilan model: {secilen}")

    task_id = r.json().get("output", {}).get("task_id")
    if not task_id:
        sys.exit(f"HATA: task_id yok. Yanit: {r.text}")
    print(f"[s2v] gorev id: {task_id}")

    task_url = base + TASK_PATH.format(task_id=task_id)
    bas = time.time()
    while True:
        if time.time() - bas > zaman_asimi:
            sys.exit("HATA: zaman asimi.")
        time.sleep(8)
        tr = requests.get(task_url, headers={"Authorization": f"Bearer {key}"},
                         timeout=60)
        if tr.status_code != 200:
            print(f"[s2v] durum sorgusu HTTP {tr.status_code}, tekrar...")
            continue
        out = tr.json().get("output", {})
        durum = out.get("task_status")
        print(f"[s2v] durum: {durum}")
        if durum == "SUCCEEDED":
            video_url = out.get("video_url") or out.get("results", [{}])[0].get("url")
            break
        if durum in ("FAILED", "CANCELED", "UNKNOWN"):
            sys.exit(f"HATA: gorev {durum}: {tr.text}")

    if not video_url:
        sys.exit(f"HATA: video_url yok. Yanit: {tr.text}")
    print(f"[s2v] indiriliyor: {video_url}")
    v = requests.get(video_url, timeout=600)
    v.raise_for_status()
    os.makedirs(os.path.dirname(cikti) or ".", exist_ok=True)
    with open(cikti, "wb") as f:
        f.write(v.content)
    print(f"[s2v] BITTI -> {cikti} ({len(v.content)} byte)")
    return cikti


def main():
    p = argparse.ArgumentParser(description="DashScope s2v/EMO konusan video denemesi")
    p.add_argument("--img-url", required=True, help="Herkese acik gorsel URL'si")
    p.add_argument("--audio-url", required=True, help="Herkese acik ses URL'si")
    p.add_argument("--cikti", default="klipler/konusan.mp4", help="Cikti mp4")
    p.add_argument("--model", default=None, help="Tek model zorla (yoksa aday listesi)")
    p.add_argument("--cozunurluk", default="720P")
    args = p.parse_args()
    uret(args.img_url, args.audio_url, args.cikti, args.model, args.cozunurluk)


if __name__ == "__main__":
    sys.exit(main())
