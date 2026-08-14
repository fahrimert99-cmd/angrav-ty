"""
Masalname orkestratoru.
Tek komutla uzun (15+ dk) bir uyku masali videosu uretir:

    python masal.py --tema "yildizlari toplayan minik tavsan" --sure 900

Adimlar:  masal senaryosu (AI) -> her sahne icin anlatici sesi (edge-tts) +
          masal illustrasyonu (Pollinations) -> tam ekran yavas Ken Burns
          montaj -> (opsiyonel) YouTube'a yukleme.

Not: Cizgi film hattindan (main.py) bagimsizdir; ayni config/ayarlar.yaml'i
kullanir ama 'masal' ve 'seslendirme' bolumlerini okur.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

from src import ayarlari_yukle, cikti_klasoru
from src import masal_senaryo as m_senaryo
from src import masal_montaj as m_montaj
from src import sahne as m_sahne
from src.seslendirme import _edge_seslendir

# AI/tema verilmezse rastgele secilecek sakin uyku masali temalari.
VARSAYILAN_TEMALAR = [
    "yildizlari toplayan minik tavsan",
    "ay isiginda sarki soyleyen kucuk baykus",
    "bulutlarin uzerinde uyuyan sevimli ejderha yavrusu",
    "denizin dibinde isik sacan nazik balina",
    "ruzgarla dans eden uykucu bir kelebek",
    "ormanin bekcisi yumusak kalpli ayicik",
]

# Masal illustrasyonlari icin sabit, sicak/uyku dostu stil.
MASAL_STIL = ("soft dreamy storybook illustration, watercolor, warm pastel "
              "colors, cozy, gentle moonlight, calming, no text, high quality")


def slugla(metin: str) -> str:
    metin = re.sub(r"[^a-zA-Z0-9]+", "-", metin.lower()).strip("-")
    return metin[:40] or "masal"


def _anlatici_profili(ayar: dict):
    m = ayar.get("masal", {})
    voice = m.get("ses", "tr-TR-EmelNeural")
    rate = m.get("hiz", "-8%")
    pitch = m.get("pitch", "+0Hz")
    return voice, rate, pitch


def _seslendir(senaryo: dict, ayar: dict, cikti: Path):
    """Her sahnenin anlatimini edge-tts ile seslendirir; 'ses_yolu' ekler."""
    voice, rate, pitch = _anlatici_profili(ayar)
    ses_dizin = cikti / "ses"
    ses_dizin.mkdir(parents=True, exist_ok=True)
    for i, sahne in enumerate(senaryo["sahneler"], start=1):
        mp3 = ses_dizin / f"{i:03d}.mp3"
        _edge_seslendir(sahne["anlatim"], voice, rate, pitch,
                        mp3, mp3.with_suffix(".srt"))
        sahne["ses_yolu"] = str(mp3)
    return senaryo


def _illustrasyonlar(senaryo: dict, ayar: dict, cikti: Path):
    """Her sahne icin masal illustrasyonu uretir; 'arka_plan_yolu' ekler.
    Sahne motoru/stili masal icin gecici olarak storybook'a ayarlanir."""
    ayar.setdefault("sahne", {})
    # Masal videosunda gorseller storybook/masal tarzinda olsun (Pixar degil).
    ayar["sahne"]["stil"] = MASAL_STIL
    if ayar["sahne"].get("motor") in (None, "pexels_video", "pexels_foto"):
        # Masalda AI illustrasyon tercih ediyoruz (bkz. README/karar).
        ayar["sahne"]["motor"] = "pollinations"
    en, boy = ayar["montaj"]["cozunurluk"]
    ayar["sahne"]["cozunurluk"] = f"{en}x{boy}"
    for i, sahne in enumerate(senaryo["sahneler"], start=1):
        hedef = cikti / "sahne" / f"sahne_{i:02d}.jpg"
        sahne["arka_plan_yolu"] = str(
            m_sahne.arka_plan_uret(sahne["arka_plan_prompt"], ayar, hedef))
    return senaryo


def main():
    p = argparse.ArgumentParser(description="Uyku masali videosu uret (Masalname)")
    p.add_argument("--tema", default="", help="Masal temasi (bos ise rastgele)")
    p.add_argument("--sure", type=int, default=900,
                   help="Hedef sure (saniye - varsayilan 900 = 15dk)")
    p.add_argument("--yukle", action="store_true", help="Bitince YouTube'a yukle")
    args = p.parse_args()

    ayar = ayarlari_yukle()
    tema = args.tema.strip() or random.choice(VARSAYILAN_TEMALAR)
    print(f"Masal temasi: {tema}")

    print("1/4  Masal yaziliyor (AI)...")
    senaryo = m_senaryo.uret(tema, ayar, args.sure)
    cikti = cikti_klasoru("masal-" + slugla(senaryo["baslik"]))
    (cikti / "masal_senaryo.json").write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"     Baslik: {senaryo['baslik']}  ({len(senaryo['sahneler'])} sahne)")

    print("2/4  Anlatici seslendiriyor...")
    _seslendir(senaryo, ayar, cikti)

    print("3/4  Masal illustrasyonlari uretiliyor...")
    _illustrasyonlar(senaryo, ayar, cikti)

    print("4/4  Montaj yapiliyor (tam ekran yavas akis)...")
    video = m_montaj.birlestir(senaryo, ayar, cikti)

    if args.yukle or ayar.get("yukleme", {}).get("aktif"):
        from src import yukleme as m_yukleme
        print("     YouTube'a yukleniyor...")
        url = m_yukleme.yukle(str(video), senaryo["baslik"],
                              f"{tema}\n\n#masal #uykumasali #cocuk", ayar)
        print(f"     Yuklendi: {url}")

    video_yolu = Path(video)
    if not video_yolu.exists() or video_yolu.stat().st_size == 0:
        raise RuntimeError(f"Islem bitti ama video olusmadi/bos: {video_yolu}")
    print(f"\nBITTI ✅  Masal videosu: {video_yolu.resolve()} "
          f"({video_yolu.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
