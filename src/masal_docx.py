"""
Hazir masal belgesinden (.docx) + gorsellerden masal senaryosu.

Kullanici baska bir aracla "masal metni + her bolume ozel gorsel" uretiyor;
bu modul o ciktiyi dogrudan video hattina baglar. Boylece AI/pipeline'a
bagli kalmadan, metinle BIREBIR eslesen gorsellerle video uretilir.

Beklenen belge yapisi (Google Docs -> .docx ciktisi):
    <Masal Basligi>
    Bolum 1: <ad>          <- bolum basligi
    <anlatim paragraflari>
    Bolum 1: Gorsel Tasarimi ve Yonergeleri   <- gorsel bolumu (atlanir)
    ...

Gorseller klasorde 1.jpg, 2.jpg ... seklinde bolum sirasina gore adlandirilir
(ya da alfabetik/sayisal sirali herhangi bir gorsel kumesi).
"""
import html
import re
import zipfile
from pathlib import Path

# Anlatim disinda kalan, atlanmasi gereken yonerge satirlari.
_ATLA_ONEKLER = (
    "atmosfer:", "odak noktasi:", "odak noktası:", "detayli betimleme:",
    "detaylı betimleme:", "onerilen yapay zeka", "önerilen yapay zeka",
)
_GORSEL_BOLUM = re.compile(r"g[oö]rsel tasar[iı]m[iı]", re.IGNORECASE)
_BOLUM_BAS = re.compile(r"^b[oö]l[uü]m\s*\d+\s*[:.]", re.IGNORECASE)


def _paragraflar(docx_yolu: str):
    """docx icindeki paragraflari (metin) sirayla dondurur."""
    with zipfile.ZipFile(docx_yolu) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    paras = re.findall(r"<w:p\b[^>]*>.*?</w:p>", xml, re.DOTALL)
    W = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.DOTALL)
    out = []
    for p in paras:
        t = html.unescape("".join(W.findall(p))).strip()
        if t:
            out.append(t)
    return out


def _ingilizce_prompt_mu(s: str) -> bool:
    """Satirin (Turkce anlatim degil) Ingilizce AI promptu olup olmadigini kestirir."""
    ipuclari = ("photorealistic", "cinematic", "ultra detailed", "8k", "lighting",
                "a dimly", "a majestic", "a dramatic", "a mystical", "a dark",
                "a heartwarming", "style", "render")
    dusuk = s.lower()
    return sum(1 for k in ipuclari if k in dusuk) >= 2


def _gorselleri_bul(klasor: Path):
    """Klasordeki gorselleri sayisal/alfabetik sirayla dondurur."""
    adaylar = [p for p in klasor.iterdir()
               if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]

    def anahtar(p):
        m = re.search(r"\d+", p.stem)
        return (int(m.group()) if m else 10**6, p.stem.lower())

    return sorted(adaylar, key=anahtar)


def yukle(docx_yolu: str, gorsel_klasoru: str = None,
          paragraf_basina_sahne: bool = True) -> dict:
    """docx + gorsellerden masal senaryosu uretir.

    Her BOLUM icin o bolumun gorseli kullanilir; bolum metni paragraflara
    bolunerek sahnelere dagitilir (gorsel ayni kalir -> metinle eslesme
    korunur, altyazi ve Ken Burns akisi devam eder).
    """
    paras = _paragraflar(docx_yolu)
    if not paras:
        raise ValueError(f"Belgede metin bulunamadi: {docx_yolu}")

    baslik = paras[0]
    bolumler = []          # [{ad, metinler: [...]}]
    aktif = None
    gorsel_bolumunde = False

    for p in paras[1:]:
        if _GORSEL_BOLUM.search(p):        # "Bolum N: Gorsel Tasarimi..."
            gorsel_bolumunde = True
            continue
        if _BOLUM_BAS.match(p):            # "Bolum N: <ad>"
            gorsel_bolumunde = False
            aktif = {"ad": p, "metinler": []}
            bolumler.append(aktif)
            continue
        if gorsel_bolumunde or aktif is None:
            continue
        dusuk = p.lower()
        if any(dusuk.startswith(o) for o in _ATLA_ONEKLER):
            continue
        if _ingilizce_prompt_mu(p):
            continue
        aktif["metinler"].append(p)

    bolumler = [b for b in bolumler if b["metinler"]]
    if not bolumler:
        raise ValueError(f"Belgede bolum/anlatim bulunamadi: {docx_yolu}")

    gorseller = []
    if gorsel_klasoru:
        gorseller = _gorselleri_bul(Path(gorsel_klasoru))

    sahneler = []
    for i, b in enumerate(bolumler):
        gorsel = str(gorseller[i]) if i < len(gorseller) else (
            str(gorseller[-1]) if gorseller else None)
        metinler = b["metinler"] if paragraf_basina_sahne else [" ".join(b["metinler"])]
        for metin in metinler:
            sahne = {"anlatim": metin,
                     "arka_plan_prompt": b["ad"]}   # gorsel varsa kullanilmaz
            if gorsel:
                sahne["arka_plan_yolu"] = gorsel
            sahneler.append(sahne)

    return {"baslik": baslik, "ana_karakter": "", "sahneler": sahneler}
