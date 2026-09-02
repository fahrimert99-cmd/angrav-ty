"""
ASMR video orkestratoru.

Tek komutla uzun (30-60+ dk) bir ASMR videosu uretir:

    python asmr.py --tema yagmur --sure 1800          # 30 dk yagmur ASMR
    python asmr.py --tema somine --sure 3600          # 60 dk sominе/ates
    python asmr.py --tema okyanus --gorsel-sayisi 5   # okyanus dalgalari
    python asmr.py --tema gece --anlatim "..."        # yumusak anlatimli ASMR

Adimlar:  ambient ses ortami (asmr_ses; telifsiz, kod uretimi) +
          sakinlestirici gorseller (Pollinations/Pexels) -> yavas Ken Burns
          dongu montaji -> (opsiyonel) YouTube'a yukleme.

Cizgi film (main.py) ve masal (masal.py) hatlarindan bagimsizdir; ayni
config/ayarlar.yaml'i kullanir, 'asmr' bolumunu okur.
"""
import argparse
import re
import sys
from pathlib import Path

from src import ayarlari_yukle, cikti_klasoru
from src import asmr_ses
from src import sahne as m_sahne
from src import asmr_montaj as m_montaj

# Tema on-ayarlari: ses tipi + sakinlestirici gorsel istemleri.
# Tema bunlardan biri degilse; tema metni gorsel istemi olarak kullanilir ve
# ses tipi asmr_ses.tip_coz ile serbest metinden cozulur.
PRESETLER = {
    "yagmur": {
        "tip": "yagmur",
        "gorseller": [
            "cozy window with soft rain drops at night, warm indoor light, blurred city lights",
            "rainy misty green forest, gentle rain, soft fog, peaceful",
            "quiet street in the rain at dusk, wet pavement reflections, calm",
            "raindrops on a leaf close up, soft bokeh, tranquil",
        ],
    },
    "okyanus": {
        "tip": "okyanus",
        "gorseller": [
            "calm ocean waves on a sandy beach at golden sunset, serene",
            "turquoise sea gentle waves, soft clouds, peaceful horizon",
            "tropical beach at dusk, slow waves, warm calm light",
            "seaside rocks with gentle surf, soft mist, tranquil",
        ],
    },
    "ates": {
        "tip": "ates",
        "gorseller": [
            "cozy fireplace with glowing embers, warm dim room, relaxing",
            "campfire at night in a forest, soft glowing flames, starry sky",
            "crackling wood fire close up, warm orange glow, peaceful",
            "cabin interior with fireplace, warm candlelight, cozy winter night",
        ],
    },
    "gece": {
        "tip": "gece",
        "gorseller": [
            "starry night sky over a calm meadow, moonlight, peaceful",
            "moonlit forest at night, soft mist, fireflies, serene",
            "quiet lake reflecting the moon and stars at night, tranquil",
            "night countryside under the milky way, gentle glow, calm",
        ],
    },
    "ruzgar": {
        "tip": "ruzgar",
        "gorseller": [
            "wind moving through a golden wheat field at sunset, serene",
            "misty mountain ridge with drifting clouds, soft light, calm",
            "tall grass swaying on a hillside under a wide sky, peaceful",
            "windswept pine forest, soft light rays, tranquil",
        ],
    },
    "beyaz": {
        "tip": "beyaz",
        "gorseller": [
            "soft abstract calming gradient, pale blue and lavender, minimal, no text",
            "gentle soft-focus clouds, pastel sky, serene minimal",
            "smooth flowing light abstract, calm pastel tones, minimal",
            "soft dreamy bokeh lights, pale calming palette, minimal",
        ],
    },
}
# Pembe/kahve gurultu icin beyaz'in sakin gorsellerini paylas.
PRESETLER["pembe"] = {"tip": "pembe", "gorseller": PRESETLER["beyaz"]["gorseller"]}
PRESETLER["kahve"] = {"tip": "kahve", "gorseller": PRESETLER["beyaz"]["gorseller"]}

# ASMR gorselleri icin sakin, sinematik varsayilan stil.
ASMR_STIL = ("cinematic, soft calming atmosphere, dreamy, high quality, "
             "highly detailed, no text, relaxing mood")


def slugla(metin: str) -> str:
    metin = re.sub(r"[^a-zA-Z0-9]+", "-", metin.lower()).strip("-")
    return metin[:40] or "asmr"


def _preset_coz(tema: str, tip_override: str):
    """Tema adindan (ses tipi, gorsel istemleri, baslik) uretir."""
    anahtar = (tema or "").strip().lower()
    if anahtar in PRESETLER:
        p = PRESETLER[anahtar]
        tip = tip_override or p["tip"]
        return tip, list(p["gorseller"]), tema.strip().title()
    # Serbest tema: metni gorsel istemi yap, ses tipini metinden coz.
    tip = tip_override or asmr_ses.tip_coz(tema)
    gorsel = (tema or "calm relaxing scenery").strip()
    return tip, [gorsel], (tema.strip().title() or "ASMR")


def _gorselleri_uret(gorsel_promptlari, adet, ayar, cikti):
    """Sakinlestirici gorselleri uretir (Pollinations/Pexels); yollarini dondurur."""
    ayar.setdefault("sahne", {})
    ayar["sahne"]["stil"] = ASMR_STIL
    # ASMR'de AI gorsel tercih ediyoruz; pexels_video hareketli olsa da burada
    # sabit gorsel + Ken Burns akisi kullaniyoruz.
    if ayar["sahne"].get("motor") in (None, "pexels_video"):
        ayar["sahne"]["motor"] = "pollinations"
    en, boy = ayar["montaj"]["cozunurluk"]
    ayar["sahne"]["cozunurluk"] = f"{en}x{boy}"

    yollar = []
    for i in range(adet):
        prompt = gorsel_promptlari[i % len(gorsel_promptlari)]
        hedef = cikti / "sahne" / f"asmr_{i + 1:02d}.jpg"
        yollar.append(str(m_sahne.arka_plan_uret(prompt, ayar, hedef)))
    return yollar


def _anlatim_uret(metin, ayar, cikti):
    """Opsiyonel yumusak anlatimi edge-tts ile seslendirir; mp3 yolu dondurur."""
    from src.seslendirme import _edge_seslendir
    a = ayar.get("asmr", {})
    ses = a.get("anlatim_ses", "tr-TR-EmelNeural")
    hiz = a.get("anlatim_hiz", "-12%")
    pitch = a.get("anlatim_pitch", "+0Hz")
    mp3 = cikti / "ses" / "anlatim.mp3"
    _edge_seslendir(metin, ses, hiz, pitch, mp3, mp3.with_suffix(".srt"))
    return str(mp3)


def main():
    p = argparse.ArgumentParser(description="ASMR videosu uret")
    p.add_argument("--tema", default="yagmur",
                   help="Tema: yagmur | okyanus | somine | gece | ruzgar | "
                        "beyaz | pembe | kahve (veya serbest bir gorsel tarifi)")
    p.add_argument("--tip", default="",
                   help="Ambient ses tipini elle sec (temanin sesini gecersiz kilar)")
    p.add_argument("--sure", type=int, default=1800,
                   help="Hedef sure (saniye - varsayilan 1800 = 30 dk)")
    p.add_argument("--gorsel-sayisi", type=int, default=4,
                   help="Kac farkli gorsel uretilecek (dongude sirayla akar)")
    p.add_argument("--anlatim", default="",
                   help="Opsiyonel yumusak anlatim metni (ya da .txt dosya yolu). "
                        "Bos ise sadece ambient ses.")
    p.add_argument("--yukle", action="store_true", help="Bitince YouTube'a yukle")
    args = p.parse_args()

    ayar = ayarlari_yukle()
    ayar.setdefault("asmr", {})

    tip, gorsel_promptlari, baslik = _preset_coz(args.tema, args.tip.strip())
    print(f"ASMR temasi: {args.tema}  |  ses tipi: {asmr_ses.tip_coz(tip)}  "
          f"|  sure: {args.sure} sn")

    cikti = cikti_klasoru("asmr-" + slugla(args.tema))

    print("1/4  Ambient ses ortami uretiliyor (telifsiz)...")
    loop_sure = float(ayar["asmr"].get("loop_sure", 120))
    ambient = asmr_ses.uret(args.sure, cikti / "ses" / "ambient.wav",
                            tip=tip, loop_sure=loop_sure)

    # Opsiyonel anlatim (metin dogrudan ya da .txt dosyasindan).
    metin = args.anlatim.strip()
    if metin and Path(metin).exists() and metin.lower().endswith(".txt"):
        metin = Path(metin).read_text(encoding="utf-8").strip()
    if metin:
        print("     Yumusak anlatim seslendiriliyor (edge-tts)...")
        try:
            ayar["asmr"]["_anlatim_yolu"] = _anlatim_uret(metin, ayar, cikti)
        except Exception as e:
            print(f"     [anlatim uyarisi] seslendirilemedi ({e}), ambient devam.")

    print("2/4  Sakinlestirici gorseller uretiliyor...")
    gorseller = _gorselleri_uret(gorsel_promptlari,
                                 max(1, args.gorsel_sayisi), ayar, cikti)

    print("3/4  Montaj yapiliyor (yavas akis + ambient dongu)...")
    video = m_montaj.birlestir(gorseller, ambient, args.sure, ayar, cikti, baslik)

    if args.yukle or ayar.get("yukleme", {}).get("aktif"):
        from src import yukleme as m_yukleme
        print("4/4  YouTube'a yukleniyor...")
        url = m_yukleme.yukle(str(video), f"{baslik} ASMR",
                              f"{baslik}\n\n#asmr #rahatlama #uyku", ayar)
        print(f"     Yuklendi: {url}")
    else:
        print("4/4  Yukleme atlandi (--yukle ile acabilirsiniz).")

    video_yolu = Path(video)
    if not video_yolu.exists() or video_yolu.stat().st_size == 0:
        raise RuntimeError(f"Islem bitti ama video olusmadi/bos: {video_yolu}")
    print(f"\nBITTI ✅  ASMR videosu: {video_yolu.resolve()} "
          f"({video_yolu.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
