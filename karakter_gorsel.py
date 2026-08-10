"""
Karakter gorseli uretici (Pollinations.ai, bedava/anahtarsiz).

karakterler.json'daki 'gorsel_prompt' + 'varsayilan_stil' tanimlarindan her
karakter icin Pixar tarzi bir portre uretir ve 'gorsel' alanindaki yola
(orn. karakterler/duru.jpeg) kaydeder.

Kullanim (Colab'da internet acikken):
    python karakter_gorsel.py duru efe        # sadece bu slug'lar
    python karakter_gorsel.py                  # gorseli EKSIK olan tum karakterler
    python karakter_gorsel.py --zorla duru     # var olsa bile yeniden uret

Not: Bu ortamin egress politikasi pollinations'i engelleyebilir; script'i
Colab/yerel makinede calistirin.
"""
import sys
import time
import urllib.parse
from pathlib import Path

import requests

from src import karakterleri_yukle, KOK


def _stil(karakterler_meta_yolu: Path) -> str:
    import json
    with open(karakterler_meta_yolu, "r", encoding="utf-8") as f:
        return json.load(f).get(
            "varsayilan_stil",
            "3D Pixar-style, soft cinematic lighting, warm colors, high detail")


def gorsel_uret(prompt: str, hedef: Path, en: int = 768, boy: int = 1024,
                tohum: int = 7, deneme: int = 3) -> Path:
    tam = (f"{prompt}, Pixar Disney 3D animation movie character, cinematic "
           f"render, subsurface scattering, soft studio lighting, full body, "
           f"standing, front view, plain solid pastel background, centered, "
           f"no text, high quality")
    kodlu = urllib.parse.quote(tam)
    url = (f"https://image.pollinations.ai/prompt/{kodlu}"
           f"?width={en}&height={boy}&nologo=true&model=flux&seed={tohum}")

    son_hata = None
    for i in range(max(1, deneme)):
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            if not r.content:
                raise RuntimeError("bos yanit")
            hedef.parent.mkdir(parents=True, exist_ok=True)
            hedef.write_bytes(r.content)
            return hedef
        except Exception as e:
            son_hata = e
            if i < deneme - 1:
                time.sleep(2 ** i)
    raise RuntimeError(f"Gorsel uretilemedi ({hedef.name}): {son_hata}")


def main(argv):
    zorla = "--zorla" in argv
    slug_listesi = [a for a in argv if not a.startswith("-")]

    karakterler = karakterleri_yukle()
    if not slug_listesi:
        slug_listesi = list(karakterler.keys())

    bilinmeyen = [s for s in slug_listesi if s not in karakterler]
    if bilinmeyen:
        raise SystemExit(f"Bilinmeyen karakter(ler): {', '.join(bilinmeyen)}")

    stil = _stil(KOK / "config" / "karakterler.json")
    uretildi = 0
    for i, slug in enumerate(slug_listesi):
        k = karakterler[slug]
        hedef = KOK / k.get("gorsel", f"karakterler/{slug}.jpeg")
        if hedef.exists() and not zorla:
            print(f"[atlandi] {slug}: zaten var -> {hedef} (--zorla ile yenile)")
            continue
        prompt = f"{k.get('gorsel_prompt', k.get('isim', slug))}, {stil}"
        print(f"[uretiliyor] {slug} -> {hedef} ...")
        gorsel_uret(prompt, hedef, tohum=7 + i)
        print(f"[tamam] {slug}: {hedef} ({hedef.stat().st_size // 1024} KB)")
        uretildi += 1

    print(f"\nBitti. Uretilen: {uretildi}/{len(slug_listesi)}")


if __name__ == "__main__":
    main(sys.argv[1:])
