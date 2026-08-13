"""
Sahne / arka plan gorseli uretimi.
Pollinations.ai bedava ve anahtarsizdir: bir URL cagirarak gorsel indirir.
Alternatifler:
  - yerel_sd     : yerel Stable Diffusion (diffusers ile, GPU onerilir)
  - pexels_foto  : Pexels stok FOTOGRAFI (sabit arka plan, gercek foto)
  - pexels_video : Pexels stok VIDEOSU (HAREKETLI arka plan)

Pexels ucretsiz API anahtari gerektirir (https://www.pexels.com/api/).
Anahtar `ayar["sahne"]["pexels_api_key"]` veya PEXELS_API_KEY ortam
degiskeninden okunur. Pexels basarisiz olursa otomatik Pollinations'a duser.
"""
import os
import urllib.parse
from pathlib import Path

import requests

# Arka planlarin Pixar karakterlerle uyumlu gorunmesi icin varsayilan stil.
VARSAYILAN_STIL = ("3D Pixar animation movie style background, soft cinematic "
                   "lighting, colorful, highly detailed, no text, high quality")

# diffusers pipeline'i pahali; bir kez yukleyip yeniden kullaniriz.
_PIPELINE = None
_PIPELINE_MODEL = None


def _sahne_prompt(prompt: str, ayar: dict) -> str:
    """Sahne istemini arka plan stiliyle birlestirir (config'ten okunur)."""
    stil = ayar.get("sahne", {}).get("stil", VARSAYILAN_STIL)
    return f"{prompt}, {stil}"


def _sd_pipeline(ayar: dict):
    """diffusers Stable Diffusion pipeline'ini (bir kez) yukler ve dondurur."""
    global _PIPELINE, _PIPELINE_MODEL

    model = ayar["sahne"].get(
        "sd_model", "stabilityai/stable-diffusion-xl-base-1.0")

    # Ayni model zaten yukluyse tekrar yukleme.
    if _PIPELINE is not None and _PIPELINE_MODEL == model:
        return _PIPELINE

    import torch
    from diffusers import AutoPipelineForText2Image

    gpu = torch.cuda.is_available()
    dtype = torch.float16 if gpu else torch.float32

    pipe = AutoPipelineForText2Image.from_pretrained(
        model,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if gpu else None,
    )
    pipe = pipe.to("cuda" if gpu else "cpu")
    if gpu:
        # VRAM azsa modeli parca parca CPU'ya alir; ilerleme cubugunu susturur.
        pipe.set_progress_bar_config(disable=True)
        try:
            pipe.enable_model_cpu_offload()
        except Exception:
            pass

    _PIPELINE, _PIPELINE_MODEL = pipe, model
    return pipe


def _yerel_sd_uret(prompt: str, ayar: dict, hedef: Path, en: int, boy: int) -> Path:
    """Yerel diffusers ile bir arka plan gorseli uretir ve kaydeder."""
    import torch

    pipe = _sd_pipeline(ayar)
    sd = ayar["sahne"]

    tam_prompt = _sahne_prompt(prompt, ayar)
    negatif = sd.get(
        "negatif_prompt",
        "text, watermark, signature, blurry, lowres, deformed")

    tohum = sd.get("seed")
    jenerator = None
    if tohum is not None:
        aygit = "cuda" if torch.cuda.is_available() else "cpu"
        jenerator = torch.Generator(device=aygit).manual_seed(int(tohum))

    gorsel = pipe(
        prompt=tam_prompt,
        negative_prompt=negatif,
        width=en,
        height=boy,
        num_inference_steps=int(sd.get("adim", 30)),
        guidance_scale=float(sd.get("yonlendirme", 7.5)),
        generator=jenerator,
    ).images[0]

    hedef.parent.mkdir(parents=True, exist_ok=True)
    gorsel.save(hedef)
    return hedef


def _pollinations(prompt: str, ayar: dict, hedef: Path, en: int, boy: int) -> Path:
    """Pollinations.ai ile arka plan gorseli indirir; olmazsa PIL ile basit
    bir gokyuzu/cimen sahnesi cizer. Her zaman bir dosya dondurur."""
    tam_prompt = _sahne_prompt(prompt, ayar)
    kodlu = urllib.parse.quote(tam_prompt)
    url = (f"https://image.pollinations.ai/prompt/{kodlu}"
           f"?width={en}&height={boy}&nologo=true&model=flux")
    try:
        yanit = requests.get(url, timeout=60)
        yanit.raise_for_status()
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(yanit.content)
        return hedef
    except Exception as e:
        print(f"[yedek sahne] {hedef.name} Pollinations indirilemedi ({e}), PIL sahne olusturuluyor...")
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (en, boy), color=(135, 206, 235))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, boy // 2, en, boy], fill=(60, 179, 113))
        hedef.parent.mkdir(parents=True, exist_ok=True)
        img.save(hedef, format="JPEG")
        return hedef


def _pexels_anahtar(ayar: dict) -> str:
    """Pexels API anahtarini ayar dosyasindan veya ortam degiskeninden alir."""
    return (ayar.get("sahne", {}).get("pexels_api_key")
            or os.environ.get("PEXELS_API_KEY") or "").strip()


def _pexels_sorgu(prompt: str) -> str:
    """Uzun sahne istemini kisa, stok-arama dostu anahtar kelimeye indirir.
    Pixar stili gibi eklentiler stok aramada ise yaramaz; ham istemin ilk
    birkac kelimesini kullaniriz."""
    kelimeler = prompt.replace(",", " ").split()
    return " ".join(kelimeler[:6]) or "nature"


def _pexels_foto(prompt: str, ayar: dict, hedef: Path, en: int, boy: int) -> Path:
    """Pexels stok fotografi indirir (sabit arka plan). Basarisizsa Pollinations."""
    anahtar = _pexels_anahtar(ayar)
    if not anahtar:
        print("[pexels] API anahtari yok (pexels_api_key / PEXELS_API_KEY), "
              "Pollinations'a dusuluyor.")
        return _pollinations(prompt, ayar, hedef, en, boy)
    try:
        yanit = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": anahtar},
            params={"query": _pexels_sorgu(prompt), "per_page": 5,
                    "orientation": "landscape"},
            timeout=30,
        )
        yanit.raise_for_status()
        fotolar = yanit.json().get("photos", [])
        if not fotolar:
            raise ValueError(f"'{_pexels_sorgu(prompt)}' icin foto bulunamadi")
        kaynak = fotolar[0]["src"]
        foto_url = kaynak.get("landscape") or kaynak.get("large2x") or kaynak["original"]
        gorsel = requests.get(foto_url, timeout=60)
        gorsel.raise_for_status()
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(gorsel.content)
        return hedef
    except Exception as e:
        print(f"[pexels foto] indirilemedi ({e}), Pollinations'a dusuluyor.")
        return _pollinations(prompt, ayar, hedef, en, boy)


def _pexels_video(prompt: str, ayar: dict, hedef: Path, en: int, boy: int) -> Path:
    """Pexels stok VIDEOSU indirir (hareketli arka plan). Hedefi .mp4 olur.
    Basarisizsa Pollinations'tan sabit foto dondurur (montaj her ikisini kabul eder)."""
    anahtar = _pexels_anahtar(ayar)
    if not anahtar:
        print("[pexels] API anahtari yok (pexels_api_key / PEXELS_API_KEY), "
              "Pollinations'a dusuluyor.")
        return _pollinations(prompt, ayar, hedef, en, boy)

    video_hedef = hedef.with_suffix(".mp4")
    try:
        yanit = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": anahtar},
            params={"query": _pexels_sorgu(prompt), "per_page": 5,
                    "orientation": "landscape"},
            timeout=30,
        )
        yanit.raise_for_status()
        videolar = yanit.json().get("videos", [])
        if not videolar:
            raise ValueError(f"'{_pexels_sorgu(prompt)}' icin video bulunamadi")

        # Hedef genislige en yakin mp4 dosyasini sec (asiri buyugu indirme).
        dosyalar = [f for f in videolar[0].get("video_files", [])
                    if f.get("file_type") == "video/mp4" and f.get("link")]
        if not dosyalar:
            raise ValueError("uygun mp4 video dosyasi yok")
        dosyalar.sort(key=lambda f: abs((f.get("width") or 0) - en))
        video_url = dosyalar[0]["link"]

        video_hedef.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(video_url, timeout=120, stream=True) as vid:
            vid.raise_for_status()
            with open(video_hedef, "wb") as f:
                for parca in vid.iter_content(chunk_size=1 << 16):
                    f.write(parca)
        return video_hedef
    except Exception as e:
        print(f"[pexels video] indirilemedi ({e}), Pollinations sabit sahneye dusuluyor.")
        return _pollinations(prompt, ayar, hedef, en, boy)


def arka_plan_uret(prompt: str, ayar: dict, hedef: Path) -> Path:
    motor = ayar["sahne"].get("motor", "pollinations")
    en, boy = ayar["sahne"].get("cozunurluk", "1280x720").split("x")
    en, boy = int(en), int(boy)

    if motor == "pollinations":
        return _pollinations(prompt, ayar, hedef, en, boy)
    if motor == "yerel_sd":
        return _yerel_sd_uret(prompt, ayar, hedef, en, boy)
    if motor == "pexels_foto":
        return _pexels_foto(prompt, ayar, hedef, en, boy)
    if motor == "pexels_video":
        return _pexels_video(prompt, ayar, hedef, en, boy)

    raise ValueError(f"Bilinmeyen sahne motoru: {motor}")


def sahneleri_uret(senaryo: dict, ayar: dict, cikti: Path):
    """Her sahne icin arka plan gorseli uretir; 'arka_plan_yolu' ekler."""
    for i, sahne in enumerate(senaryo["sahneler"], start=1):
        hedef = cikti / "sahne" / f"sahne_{i:02d}.jpg"
        sahne["arka_plan_yolu"] = str(
            arka_plan_uret(sahne["arka_plan_prompt"], ayar, hedef)
        )
    return senaryo
