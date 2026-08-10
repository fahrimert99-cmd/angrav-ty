"""
Sahne / arka plan gorseli uretimi.
Pollinations.ai bedava ve anahtarsizdir: bir URL cagirarak gorsel indirir.
Alternatif: yerel Stable Diffusion (yerel_sd modu - diffusers ile).
"""
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


def arka_plan_uret(prompt: str, ayar: dict, hedef: Path) -> Path:
    motor = ayar["sahne"].get("motor", "pollinations")
    en, boy = ayar["sahne"].get("cozunurluk", "1280x720").split("x")
    en, boy = int(en), int(boy)

    if motor == "pollinations":
        tam_prompt = _sahne_prompt(prompt, ayar)
        kodlu = urllib.parse.quote(tam_prompt)
        url = (f"https://image.pollinations.ai/prompt/{kodlu}"
               f"?width={en}&height={boy}&nologo=true&model=flux")
        yanit = requests.get(url, timeout=120)
        yanit.raise_for_status()
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(yanit.content)
        return hedef

    if motor == "yerel_sd":
        return _yerel_sd_uret(prompt, ayar, hedef, en, boy)

    raise ValueError(f"Bilinmeyen sahne motoru: {motor}")


def sahneleri_uret(senaryo: dict, ayar: dict, cikti: Path):
    """Her sahne icin arka plan gorseli uretir; 'arka_plan_yolu' ekler."""
    for i, sahne in enumerate(senaryo["sahneler"], start=1):
        hedef = cikti / "sahne" / f"sahne_{i:02d}.jpg"
        sahne["arka_plan_yolu"] = str(
            arka_plan_uret(sahne["arka_plan_prompt"], ayar, hedef)
        )
    return senaryo
