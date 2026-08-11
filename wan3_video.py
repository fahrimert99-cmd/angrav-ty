"""
Wan3.0-Video (DashScope) - hepsi-bir-arada video.

Konsoldaki resmi curl formatiyla BIREBIR ayni istegi atar:
  POST .../api/v1/services/aigc/video-generation/video-synthesis
  {"model":"wan3.0-video","input":{"prompt":...},
   "parameters":{"resolution":...,"ratio":"adaptive","duration":5}}

Varsayilan text-to-video (sadece prompt). Istege bagli --img-url verilirse
input'a eklenir (i2v denemesi). Ses (varsa) videonun icinde gelir.

Anahtar KODA GOMULMEZ; DASHSCOPE_API_KEY env'inden okunur.
"""
import argparse
import os
import sys
import time

import requests

SUBMIT_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
TASK_PATH = "/api/v1/tasks/{task_id}"


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


def uret(prompt, cikti, img_url=None, model="wan3.0-video",
         cozunurluk="480P", ratio="adaptive", duration=5,
         zaman_asimi=1200) -> str:
    key = _anahtar()
    base = _base()
    basliklar = {
        "X-DashScope-Async": "enable",
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    girdi = {"prompt": prompt}
    if img_url:
        girdi["img_url"] = img_url  # i2v denemesi (opsiyonel)
    govde = {
        "model": model,
        "input": girdi,
        "parameters": {
            "resolution": cozunurluk,
            "ratio": ratio,
            "duration": duration,
        },
    }

    print(f"[wan3] gorev gonderiliyor (model={model}, i2v={bool(img_url)})...")
    r = requests.post(base + SUBMIT_PATH, headers=basliklar, json=govde, timeout=90)
    if r.status_code != 200:
        sys.exit(f"HATA: gorev gonderilemedi (HTTP {r.status_code}): {r.text}")
    task_id = r.json().get("output", {}).get("task_id")
    if not task_id:
        sys.exit(f"HATA: task_id yok. Yanit: {r.text}")
    print(f"[wan3] gorev id: {task_id}")

    task_url = base + TASK_PATH.format(task_id=task_id)
    bas = time.time()
    while True:
        if time.time() - bas > zaman_asimi:
            sys.exit("HATA: zaman asimi.")
        time.sleep(8)
        tr = requests.get(task_url, headers={"Authorization": f"Bearer {key}"},
                         timeout=60)
        if tr.status_code != 200:
            print(f"[wan3] durum sorgusu HTTP {tr.status_code}, tekrar...")
            continue
        out = tr.json().get("output", {})
        durum = out.get("task_status")
        print(f"[wan3] durum: {durum}")
        if durum == "SUCCEEDED":
            video_url = out.get("video_url") or out.get("results", [{}])[0].get("url")
            break
        if durum in ("FAILED", "CANCELED", "UNKNOWN"):
            sys.exit(f"HATA: gorev {durum}: {tr.text}")

    if not video_url:
        sys.exit(f"HATA: video_url yok. Yanit: {tr.text}")
    print(f"[wan3] indiriliyor: {video_url}")
    v = requests.get(video_url, timeout=600)
    v.raise_for_status()
    os.makedirs(os.path.dirname(cikti) or ".", exist_ok=True)
    with open(cikti, "wb") as f:
        f.write(v.content)
    print(f"[wan3] BITTI -> {cikti} ({len(v.content)} byte)")
    return cikti


def main():
    p = argparse.ArgumentParser(description="Wan3.0-Video (DashScope)")
    p.add_argument("--prompt", required=True)
    p.add_argument("--img-url", default=None, help="Opsiyonel: i2v icin gorsel URL")
    p.add_argument("--model", default="wan3.0-video")
    p.add_argument("--cikti", default="klipler/allinone.mp4")
    p.add_argument("--cozunurluk", default="480P")
    p.add_argument("--ratio", default="adaptive")
    p.add_argument("--duration", type=int, default=5)
    args = p.parse_args()
    uret(args.prompt, args.cikti, args.img_url, args.model,
         args.cozunurluk, args.ratio, args.duration)


if __name__ == "__main__":
    sys.exit(main())
