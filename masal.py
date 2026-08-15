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
    """Her sahnenin anlatimini seslendirir; 'ses_yolu' (ve varsa 'srt_yolu') ekler.

    Motor config'ten okunur: 'edge' (bedava, varsayilan) veya 'elevenlabs'
    (daha dogal, ucretli anahtar gerekir). ElevenLabs secili ama anahtar yok
    veya cagri hata/kota verirse o sahne icin sessizce edge-tts'e dusulur.
    """
    from src import eleven_ses

    m = ayar.get("masal", {})
    voice, rate, pitch = _anlatici_profili(ayar)
    motor = (m.get("ses_motoru") or "edge").lower()
    eleven_key = eleven_ses.anahtar_al(ayar) if motor == "elevenlabs" else None
    eleven_voice = m.get("eleven_voice_id", "")
    eleven_model = m.get("eleven_model", "eleven_multilingual_v2")
    eleven_ayar = m.get("eleven_ayar")            # (ops.) voice_settings gecersiz kil
    eleven_dil = m.get("eleven_dil")              # (ops.) "tr" (turbo/flash modelleri)
    if motor == "elevenlabs" and not eleven_key:
        print("[masal ses] ElevenLabs secili ama anahtar yok "
              "(eleven_api_key / ELEVENLABS_API_KEY); edge-tts kullanilacak.")

    ses_dizin = cikti / "ses"
    ses_dizin.mkdir(parents=True, exist_ok=True)
    for i, sahne in enumerate(senaryo["sahneler"], start=1):
        mp3 = ses_dizin / f"{i:03d}.mp3"
        srt = mp3.with_suffix(".srt")
        uretildi = False
        if motor == "elevenlabs" and eleven_key and eleven_voice:
            try:
                eleven_ses.seslendir(sahne["anlatim"], eleven_voice, eleven_key,
                                     mp3, srt, model=eleven_model,
                                     voice_settings=eleven_ayar,
                                     language_code=eleven_dil)
                uretildi = True
            except Exception as e:
                print(f"[masal ses] ElevenLabs sahne {i} basarisiz ({e}); "
                      "edge-tts'e dusuluyor.")
        if not uretildi:
            _edge_seslendir(sahne["anlatim"], voice, rate, pitch, mp3, srt)
        sahne["ses_yolu"] = str(mp3)
        if srt.exists():
            sahne["srt_yolu"] = str(srt)
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
        # Sahnenin HAZIR gorseli varsa (orn. --docx ile gelen) yeniden uretme.
        mevcut = sahne.get("arka_plan_yolu")
        if mevcut and Path(mevcut).exists():
            continue
        hedef = cikti / "sahne" / f"sahne_{i:02d}.jpg"
        sahne["arka_plan_yolu"] = str(
            m_sahne.arka_plan_uret(sahne["arka_plan_prompt"], ayar, hedef))
    return senaryo


def _dis_senaryo_yukle(yol: str) -> dict:
    """Disaridan (orn. Make/Gemini -> repository_dispatch) verilen masal JSON'unu
    okur ve masal.py'nin bekledigi semaya normalize eder.

    Kabul edilen alanlar (esnek): sahne anlatimi 'anlatim' veya 'metin';
    illustrasyon istemi 'arka_plan_prompt' veya 'gorsel'. 'ana_karakter' varsa
    gorsel tutarliligi icin her sahnenin istemine eklenir.
    """
    veri = json.loads(Path(yol).read_text(encoding="utf-8"))
    ana = (veri.get("ana_karakter") or "").strip()
    norm = []
    for s in veri.get("sahneler") or []:
        if not isinstance(s, dict):
            continue
        anlatim = (s.get("anlatim") or s.get("metin") or "").strip()
        prompt = (s.get("arka_plan_prompt") or s.get("gorsel")
                  or "soft storybook watercolor illustration, no text").strip()
        if ana and ana.lower() not in prompt.lower():
            prompt = f"{ana}, {prompt}"
        if anlatim:
            norm.append({"anlatim": anlatim, "arka_plan_prompt": prompt})
    if not norm:
        raise ValueError(f"Dis senaryo JSON'unda gecerli sahne yok: {yol}")
    return {
        "baslik": veri.get("baslik", "Uyku Masali"),
        "ana_karakter": ana,
        "sahneler": norm,
    }


def main():
    p = argparse.ArgumentParser(description="Uyku masali videosu uret (Masalname)")
    p.add_argument("--tema", default="", help="Masal temasi (bos ise rastgele)")
    p.add_argument("--sure", type=int, default=900,
                   help="Hedef sure (saniye - varsayilan 900 = 15dk)")
    p.add_argument("--senaryo-json", default="",
                   help="Hazir masal JSON dosyasi (verilirse AI ile uretim atlanir; "
                        "orn. Make/Gemini -> repository_dispatch akisi)")
    p.add_argument("--docx", default="",
                   help="Hazir masal belgesi (.docx). Bolum metinleri okunur; "
                        "AI ile masal uretimi atlanir.")
    p.add_argument("--gorseller", default="",
                   help="--docx ile birlikte: bolum gorsellerinin klasoru "
                        "(1.jpg, 2.jpg ... bolum sirasina gore).")
    p.add_argument("--klasor", default="",
                   help="Masal klasoru (orn. masallar/kayip-zamanin-aynasi). "
                        "Icindeki belge + gorseller kullanilir. 'auto' verilirse "
                        "masallar/ altindaki ilk masal secilir.")
    p.add_argument("--yukle", action="store_true", help="Bitince YouTube'a yukle")
    args = p.parse_args()

    ayar = ayarlari_yukle()

    if args.klasor.strip():
        from src import masal_docx
        secilen = args.klasor.strip()
        if secilen.lower() in ("auto", "otomatik"):
            adaylar = masal_docx.masal_klasorlerini_bul("masallar")
            if not adaylar:
                raise SystemExit("masallar/ altinda masal klasoru bulunamadi. "
                                 "Bkz. masallar/README.md")
            secilen = str(adaylar[0])
            print(f"     Otomatik secilen masal: {secilen}")
        print(f"1/4  Masal klasoru kullaniliyor: {secilen}")
        senaryo = masal_docx.klasordan_yukle(secilen)
        tema = args.tema.strip() or senaryo["baslik"]
        print(f"     {len(senaryo['sahneler'])} sahne (belgeden)")
    elif args.docx.strip():
        from src import masal_docx
        print(f"1/4  Hazir masal belgesi kullaniliyor: {args.docx}")
        senaryo = masal_docx.yukle(args.docx.strip(),
                                   args.gorseller.strip() or None)
        tema = args.tema.strip() or senaryo["baslik"]
        print(f"     {len(senaryo['sahneler'])} sahne (belgeden)")
    elif args.senaryo_json.strip():
        print(f"1/4  Hazir masal JSON'u kullaniliyor: {args.senaryo_json}")
        senaryo = _dis_senaryo_yukle(args.senaryo_json.strip())
        tema = args.tema.strip() or senaryo["baslik"]
    else:
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
