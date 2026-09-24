"""Master Prompt Olusturucu.

Yapay zeka asistanlari (Claude, ChatGPT, Gemini ...) icin yapilandirilmis,
tekrar kullanilabilir "master prompt" (sistem talimati) ureten arac.

Kullanim:
    python master_prompt.py                         # adim adim sihirbaz
    python master_prompt.py --sablon kalite         # hazir sablonla baslar
    python master_prompt.py --json cevaplar.json    # kayitli cevaplardan uretir
    python master_prompt.py --sablon masal --gorev "Uyku masali yaz" --sessiz
    python master_prompt.py --iyilestir             # Claude API ile cilalar

Cikti: cikti/master_prompt_<tarih>.md (ve istenirse .json cevap dosyasi)
Yalnizca standart kutuphane kullanir; --iyilestir icin `anthropic` paketi ve
ANTHROPIC_API_KEY ortam degiskeni gerekir.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bolum tanimlari: (anahtar, baslik, soru, coklu_satir_mi)
# ---------------------------------------------------------------------------
BOLUMLER = [
    ("rol", "Rol ve Uzmanlik",
     "Yapay zeka hangi rolde olsun? (ornek: Kidemli kalite yoneticisi)", False),
    ("baglam", "Baglam",
     "Arka plan bilgisi: kurum, proje, hedef kitle, mevcut durum", True),
    ("gorev", "Temel Gorev",
     "Yapay zekanin yapmasini istediginiz asil is nedir?", True),
    ("kurallar", "Kurallar ve Kisitlar",
     "Mutlaka uyulmasi gereken kurallar (her satira bir kural)", True),
    ("uslup", "Uslup ve Dil",
     "Ton/dil nasil olsun? (resmi, sade, teknik, samimi ...)", False),
    ("hitap", "Hitap ve Imza",
     "Size nasil hitap etsin, resmi belgelerde imza ne olsun?", False),
    ("cikti_formati", "Cikti Formati",
     "Cevap hangi formatta gelsin? (tablo, madde, rapor sablonu ...)", True),
    ("ornekler", "Ornekler",
     "Iyi bir cevap ornegi (bos birakilabilir)", True),
    ("kalite_kontrol", "Kalite Kontrol",
     "Cevap vermeden once kontrol edilecekler (her satira bir madde)", True),
]

# ---------------------------------------------------------------------------
# Hazir sablonlar
# ---------------------------------------------------------------------------
SABLONLAR: dict[str, dict[str, str]] = {
    "genel": {
        "rol": "Alaninda uzman, dikkatli ve durust bir asistan",
        "uslup": "Net, anlasilir ve profesyonel Turkce",
        "kurallar": "Emin olmadigin bilgiyi uydurma, belirsizligi acikca belirt.\n"
                    "Gereksiz tekrar ve dolgu cumlelerden kacin.\n"
                    "Eksik bilgi varsa once kisa soru sor.",
        "cikti_formati": "Kisa bir ozet, ardindan basliklar ve maddeler.",
        "kalite_kontrol": "Soru tam olarak cevaplandi mi?\n"
                          "Bilgiler dogru ve guncel mi?",
    },
    "kalite": {
        "rol": "Ust duzey Kurumsal Gelisim, Kalite Yonetimi ve Kimya "
               "Muhendisligi uzmani",
        "baglam": "Entegre Yonetim Sistemleri (ISO 9001:2015, ISO 14001:2015, "
                  "ISO 45001:2018, ISO 50001:2018), 5S metodolojisi ve kurumsal "
                  "olgunluk analizleri kapsaminda destek.",
        "kurallar": "Yonetim raporu, prosedur ve teknik sartnamelerde teknik, "
                    "kurumsal ve akademik dil kullan.\n"
                    "Saha personeli icin talimatlarda jargonu arindir; sade ve "
                    "net saha dili kullan.\n"
                    "Yuklenen sablonlarin ust bilgi, alt bilgi, logo ve "
                    "maddeleme yapisini asla degistirme.\n"
                    "Sorunlari kok neden analizi (5 Neden, Balik Kilcigi) ile "
                    "incele.\n"
                    "Risk degerlendirmelerini standartlarin guncel "
                    "versiyonlarina gore yap.",
        "uslup": "Resmi belgelerde kurumsal-akademik; saha belgelerinde sade",
        "hitap": "Bana \"Asil\" diye hitap et. Resmi evraklarin imza/onay "
                 "kisminda \"Fahri Mert\" ismini kullan.",
        "cikti_formati": "Dokuman No / Revizyon / Tarih ust bilgisi, amac, "
                         "kapsam, sorumluluklar, uygulama adimlari, kayitlar, "
                         "imza-onay tablosu.",
        "kalite_kontrol": "Ilgili standart maddesine atif yapildi mi?\n"
                          "Kok neden ve duzeltici faaliyet ayrildi mi?\n"
                          "Imza alaninda \"Fahri Mert\" yer aliyor mu?",
    },
    "masal": {
        "rol": "Cocuklar icin yazan deneyimli bir masal ve cizgi film "
               "senaristi",
        "baglam": "Aile temali cizgi film serisi. Karakterler: Kaan (baba), "
                  "Selin (anne), Mira (kiz cocuk), Ege (erkek cocuk), "
                  "Ihsan Dede. 3B Pixar tarzi gorseller.",
        "kurallar": "Siddet, korku ve uygunsuz icerik kullanma.\n"
                    "Her bolum olumlu bir degerle (paylasma, durustluk ...) "
                    "bitsin.\n"
                    "Cumleler kisa ve 4-8 yas icin anlasilir olsun.",
        "uslup": "Sicak, samimi, akici ve oyunbaz Turkce",
        "cikti_formati": "Sahne sahne: sahne no, mekan, gorsel tanimi "
                         "(Ingilizce), konusan karakter, diyalog.",
        "kalite_kontrol": "Karakter isimleri ve rolleri tutarli mi?\n"
                          "Ders/deger acikca ama vaaz vermeden verildi mi?",
    },
    "kod": {
        "rol": "Kidemli yazilim muhendisi ve kod inceleyici",
        "kurallar": "Calisan, test edilmis ve okunabilir kod yaz.\n"
                    "Mevcut kod stiline ve isimlendirmeye uy.\n"
                    "Guvenlik aciklarina (enjeksiyon, gizli anahtar) dikkat et.",
        "uslup": "Kisa, teknik ve dogrudan",
        "cikti_formati": "Once kisa aciklama, sonra kod blogu, sonra nasil "
                         "test edilecegi.",
        "kalite_kontrol": "Kenar durumlar ele alindi mi?\n"
                          "Kod calistirilip dogrulandi mi?",
    },
}

LISTE_BOLUMLERI = {"kurallar", "kalite_kontrol"}


# ---------------------------------------------------------------------------
# Uretim
# ---------------------------------------------------------------------------
def _satirlar(metin: str) -> list[str]:
    return [s.strip(" -*\t") for s in metin.splitlines() if s.strip(" -*\t")]


def prompt_olustur(cevaplar: dict[str, str]) -> str:
    """Cevaplardan XML etiketli, bolumlu master prompt metni uretir."""
    parcalar = []
    for anahtar, baslik, _, _ in BOLUMLER:
        deger = (cevaplar.get(anahtar) or "").strip()
        if not deger:
            continue
        if anahtar in LISTE_BOLUMLERI:
            icerik = "\n".join(f"{i}. {s}" for i, s in
                               enumerate(_satirlar(deger), 1))
        else:
            icerik = deger
        parcalar.append(f"## {baslik}\n<{anahtar}>\n{icerik}\n</{anahtar}>")

    govde = "\n\n".join(parcalar)
    kapanis = ("Bu talimatlarin tamamina her yanitta uy. Talimatlar arasinda "
               "celiski olursa once Kurallar ve Kisitlar bolumunu esas al. "
               "Gorev icin gerekli bir bilgi eksikse varsayim yapmadan once "
               "kisa ve net bir soru sor.")
    return f"# MASTER PROMPT\n\n{govde}\n\n## Genel Ilke\n{kapanis}\n"


def degerlendir(cevaplar: dict[str, str]) -> tuple[int, list[str]]:
    """0-100 arasi bir dolululuk puani ve iyilestirme onerileri dondurur."""
    agirlik = {"rol": 15, "baglam": 15, "gorev": 25, "kurallar": 15,
               "uslup": 5, "hitap": 5, "cikti_formati": 10, "ornekler": 5,
               "kalite_kontrol": 5}
    puan, oneriler = 0, []
    for anahtar, baslik, _, _ in BOLUMLER:
        deger = (cevaplar.get(anahtar) or "").strip()
        if deger:
            puan += agirlik[anahtar]
        elif agirlik[anahtar] >= 10:
            oneriler.append(f"'{baslik}' bolumu bos - doldurmaniz onerilir.")
    gorev = (cevaplar.get("gorev") or "").strip()
    if gorev and len(gorev) < 30:
        oneriler.append("Gorev tanimi cok kisa; hedefi, kapsami ve beklenen "
                        "sonucu ekleyin.")
    if len(_satirlar(cevaplar.get("kurallar", ""))) == 1:
        oneriler.append("Tek kural var; en az 3 net kural onerilir.")
    return puan, oneriler


# ---------------------------------------------------------------------------
# Claude ile iyilestirme (opsiyonel)
# ---------------------------------------------------------------------------
def claude_ile_iyilestir(prompt: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise SystemExit("anthropic paketi yok: pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY ortam degiskeni tanimli degil.")
    istemci = anthropic.Anthropic()
    yanit = istemci.messages.create(
        model=model,
        max_tokens=4000,
        system=("Sen bir prompt muhendisisin. Verilen master promptu anlamini "
                "ve bolum yapisini (## basliklar ve XML etiketleri) koruyarak "
                "daha net, celiskisiz ve eksiksiz hale getir. Kullanicinin "
                "verdigi isim, hitap ve imza bilgilerini aynen koru. Yalnizca "
                "iyilestirilmis promptu dondur, aciklama ekleme."),
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in yanit.content if b.type == "text").strip() + "\n"


# ---------------------------------------------------------------------------
# Etkilesimli sihirbaz
# ---------------------------------------------------------------------------
def _sor(soru: str, varsayilan: str, coklu: bool) -> str:
    print(f"\n>> {soru}")
    if varsayilan:
        print("   [Varsayilan]\n   " + varsayilan.replace("\n", "\n   "))
        print("   (Enter = varsayilani kullan, '-' = bos birak)")
    if coklu:
        print("   (Birden fazla satir yazabilirsiniz; bitirmek icin bos "
              "satirda Enter)")
        satirlar = []
        while True:
            satir = input("   > ")
            if not satir.strip():
                break
            satirlar.append(satir)
        cevap = "\n".join(satirlar)
    else:
        cevap = input("   > ")
    cevap = cevap.strip()
    if cevap == "-":
        return ""
    return cevap or varsayilan


def sihirbaz(baslangic: dict[str, str]) -> dict[str, str]:
    print("=" * 60)
    print("  MASTER PROMPT OLUSTURUCU")
    print("=" * 60)
    cevaplar = dict(baslangic)
    for anahtar, _, soru, coklu in BOLUMLER:
        cevaplar[anahtar] = _sor(soru, cevaplar.get(anahtar, ""), coklu)
    return cevaplar


def _sablon_sec() -> str:
    print("Hazir sablonlar:")
    adlar = list(SABLONLAR)
    for i, ad in enumerate(adlar, 1):
        print(f"  {i}) {ad}")
    secim = input("Sablon secin (numara/ad, Enter = genel): ").strip()
    if secim.isdigit() and 1 <= int(secim) <= len(adlar):
        return adlar[int(secim) - 1]
    return secim if secim in SABLONLAR else "genel"


# ---------------------------------------------------------------------------
# Komut satiri
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Master prompt olusturucu")
    ap.add_argument("--sablon", choices=sorted(SABLONLAR),
                    help="Hazir sablonla basla")
    ap.add_argument("--json", help="Cevaplari bu JSON dosyasindan oku")
    ap.add_argument("--gorev", help="Temel gorev metni")
    ap.add_argument("--sessiz", action="store_true",
                    help="Soru sormadan, mevcut bilgilerle uret")
    ap.add_argument("--cikti", help="Cikti .md dosya yolu")
    ap.add_argument("--kaydet", action="store_true",
                    help="Cevaplari .json olarak da kaydet")
    ap.add_argument("--iyilestir", action="store_true",
                    help="Claude API ile promptu cilala")
    ap.add_argument("--model", default="claude-sonnet-5",
                    help="--iyilestir icin model (varsayilan: claude-sonnet-5)")
    ap.add_argument("--listele", action="store_true",
                    help="Sablonlari listele ve cik")
    a = ap.parse_args(argv)

    if a.listele:
        for ad, s in SABLONLAR.items():
            print(f"- {ad}: {s.get('rol', '')}")
        return 0

    if a.json:
        cevaplar = json.loads(Path(a.json).read_text(encoding="utf-8"))
    else:
        sablon = a.sablon or ("genel" if a.sessiz else _sablon_sec())
        cevaplar = dict(SABLONLAR[sablon])
    if a.gorev:
        cevaplar["gorev"] = a.gorev
    if not a.sessiz:
        cevaplar = sihirbaz(cevaplar)

    prompt = prompt_olustur(cevaplar)
    if a.iyilestir:
        print("\nClaude ile iyilestiriliyor...")
        prompt = claude_ile_iyilestir(prompt, a.model)

    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    hedef = Path(a.cikti or f"cikti/master_prompt_{zaman}.md")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(prompt, encoding="utf-8")
    if a.kaydet:
        hedef.with_suffix(".json").write_text(
            json.dumps(cevaplar, ensure_ascii=False, indent=2), encoding="utf-8")

    puan, oneriler = degerlendir(cevaplar)
    print("\n" + "=" * 60)
    print(prompt)
    print("=" * 60)
    print(f"Dosya: {hedef}")
    print(f"Doluluk puani: {puan}/100")
    for o in oneriler:
        print(f"  ! {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
