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


def _duz_metin_paragraflari(yol: Path):
    """.md / .txt dosyasindan paragraflari dondurur.

    Markdown basliklari (#, ##) ve liste isaretleri temizlenir; bos satirla
    ayrilmis bloklar paragraf sayilir (tek satirlik basliklar da paragraf olur).
    """
    ham = Path(yol).read_text(encoding="utf-8")
    out = []
    for blok in re.split(r"\n\s*\n", ham):
        satirlar = []
        for s in blok.splitlines():
            s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s)        # md baslik
            s = re.sub(r"^\s*[-*+]\s+", "", s)             # liste isareti
            s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)         # kalin
            s = s.strip()
            if s:
                satirlar.append(s)
        if not satirlar:
            continue
        # Basliklar (Bolum N: ... / Gorsel Tasarimi ...) kendi baslarina paragraf
        # olur; ardisik duz satirlar tek bir anlatim paragrafinda birlestirilir.
        tampon = []
        for s in satirlar:
            if _BOLUM_BAS.match(s) or _GORSEL_BOLUM.search(s):
                if tampon:
                    out.append(" ".join(tampon))
                    tampon = []
                out.append(s)
            else:
                tampon.append(s)
        if tampon:
            out.append(" ".join(tampon))
    return out


def _paragraflar(docx_yolu: str):
    """Belgedeki paragraflari (metin) sirayla dondurur (.docx / .md / .txt)."""
    yol = Path(docx_yolu)
    if yol.suffix.lower() in (".md", ".txt", ".markdown"):
        return _duz_metin_paragraflari(yol)

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


# --- Klasor tabanli kullanim (repo icindeki masallar/<masal-adi>/) -----------

BELGE_UZANTILARI = (".docx", ".md", ".markdown", ".txt")


def klasordeki_belge(klasor: Path):
    """Klasordeki masal belgesini bulur (.docx > .md > .txt onceligiyle)."""
    klasor = Path(klasor)
    for uzanti in BELGE_UZANTILARI:
        adaylar = sorted(p for p in klasor.iterdir()
                         if p.suffix.lower() == uzanti and not p.name.startswith("~$"))
        if adaylar:
            return adaylar[0]
    return None


def klasordan_yukle(klasor: str) -> dict:
    """Bir masal klasorunden (belge + gorseller) senaryo uretir.

    Beklenen yapi:
        masallar/<masal-adi>/
            masal.docx (veya .md / .txt)
            1.jpg, 2.jpg, ...        <- bolum sirasina gore gorseller
    """
    klasor = Path(klasor)
    if not klasor.is_dir():
        raise NotADirectoryError(f"Masal klasoru yok: {klasor}")
    belge = klasordeki_belge(klasor)
    if belge is None:
        raise FileNotFoundError(
            f"{klasor} icinde masal belgesi yok "
            f"({', '.join(BELGE_UZANTILARI)} bekleniyor).")
    return yukle(str(belge), str(klasor))


def masal_klasorlerini_bul(kok: str = "masallar"):
    """Icinde belge bulunan masal klasorlerini (alfabetik) dondurur.

    Adi '_' veya '.' ile baslayan klasorler atlanir (yayinlanmis/pasif masallari
    siradan cikarmak icin).
    """
    kok = Path(kok)
    if not kok.is_dir():
        return []
    return sorted((p for p in kok.iterdir()
                   if p.is_dir()
                   and not p.name.startswith(("_", "."))
                   and klasordeki_belge(p) is not None),
                  key=lambda p: p.name.lower())
