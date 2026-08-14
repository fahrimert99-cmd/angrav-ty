"""
Masal senaryosu uretimi (Masalname).

Cizgi filmden farkli olarak TEK ANLATICI icin, uzun (15+ dk) ve sakin bir
uyku masali uretir. Iki asamali calisir:

  1) Iskelet (outline): tema'dan N sahnelik bir plan (baslik + her sahne icin
     kisa ozet + Ingilizce illustrasyon istemi).
  2) Genisletme: her sahne icin akici, yumusak bir Turkce anlatim paragrafi.

Cikti JSON semasi:
{
  "baslik": "...",
  "sahneler": [
    {"arka_plan_prompt": "storybook illustration ...", "anlatim": "Bir varmis..."}
  ]
}

AI saglayicilar src/senaryo.py'deki altyapiyi yeniden kullanir (Claude/Gemini/
Groq/Pollinations, kota yedegi ile). Hicbir servis yoksa %100 garantili sablon
masal dondurulur; boylece uretim asla durmaz.
"""
import json

from src import senaryo as _s

# Anlatici uslubu: sakin, uyku getiren, sicak. Cikti dizisi/JSON'a gore degisir.
MASAL_SISTEM = """Sen cocuklar uykuya dalarken dinlesin diye Turkce uyku masallari
anlatan sicak, sakin ve sefkatli bir masal anlaticisisin. Dilin yumusak, akici ve
huzur verici olsun. Korku, siddet, gerilim veya olumsuz mesaj OLMASIN; masal
guven, sevgi, dostluk ve merak duygusu versin ve sonu huzurla, uykuyla bitsin.
Istenen cikti bicimine harfiyen uy; markdown veya ``` kullanma."""

# Yaklasik: yavaslatilmis anlatici ~2.4 kelime/sn. 15 dk ~ 2160 kelime.
_KELIME_SN = 2.4
# Her sahne KISA olsun ki gorsel sik degissin ve anlatimla senkron dursun.
# (Referans videodaki gibi ~her 20 sn'de yeni gorsel.) config'ten degistirilebilir.
_SAHNE_SN = 20
_MAKS_SAHNE = 50


def _sahne_sayisi(hedef_sure_sn: int, sahne_sn: int = _SAHNE_SN) -> int:
    """Hedef sureye gore sahne sayisi. Kisa sahneler -> sik gorsel degisimi."""
    return max(6, min(_MAKS_SAHNE, round(hedef_sure_sn / max(8, sahne_sn))))


def _ai_metin(istem: str, ayar: dict, deneme: int = 2) -> str | None:
    """Masal sistem talimatiyla ilk calisan saglayicidan ham metin dondurur;
    hicbiri calismazsa None. Basarisiz saglayicinin HATASINI loglar ki neden
    sablona dusuldugu gorunur (orn. Claude kredisiz, Gemini kotasi, vb.)."""
    for saglayici in _s._saglayici_sirasi(ayar):
        son_hata = None
        for _ in range(max(1, deneme)):
            try:
                return _s._ham_uret(saglayici, istem, ayar, sistem=MASAL_SISTEM)
            except Exception as e:
                son_hata = e
                continue
        if son_hata is not None:
            print(f"     [masal AI] '{saglayici}' basarisiz: "
                  f"{type(son_hata).__name__}: {son_hata}")
    return None


def _iskelet_uret(tema: str, n: int, ayar: dict) -> dict | None:
    istem = f"""Tema: {tema}
Bu temadan {n} sahnelik bir UYKU MASALI plani cikar. Masal tek anlaticinin
agzindan, sakin ve akici olsun; sonu huzurla/uykuyla bitsin. Masalin BASKARAKTERI
belli olsun ve her sahnede ayni karakter gorunsun (gorsel tutarlilik icin).

SADECE su JSON'u dondur (aciklama yok):
{{
  "baslik": "kisa, sicak masal basligi",
  "ana_karakter": "English, consistent visual description of the main character (species, color, one memorable accessory), e.g. 'a small fluffy red squirrel with a tiny green scarf'",
  "sahneler": [
    {{
      "ozet": "bu sahnede ne oluyor (1-2 cumle, Turkce)",
      "arka_plan_prompt": "English illustration prompt for THIS scene showing the main character; soft children's storybook watercolor, warm pastel, cozy, no text"
    }}
  ]
}}
Tam olarak {n} sahne uret."""
    ham = _ai_metin(istem, ayar)
    if not ham:
        return None
    try:
        veri = json.loads(_s._json_ayikla(ham))
        if isinstance(veri.get("sahneler"), list) and veri["sahneler"]:
            return veri
    except Exception:
        return None
    return None


def _sahne_genislet(tema: str, baslik: str, ozet: str, sira: int, toplam: int,
                    ayar: dict, hedef_kelime: int) -> str:
    konum = ("baslangic" if sira == 1 else
             "final (huzurla, uykuyla bitir)" if sira == toplam else "orta")
    istem = f"""Masal: "{baslik}" (tema: {tema})
Bu, {toplam} sahnelik masalin {sira}. sahnesi ({konum}).
Sahne ozeti: {ozet}

Bu sahneyi, uykuya dalan bir cocuga yumusakca anlatir gibi, akici ve sakin bir
Turkce paragraf olarak yaz. Yaklasik {hedef_kelime} kelime. Sadece anlatim
metnini dondur (baslik, numara, tirnak veya aciklama olmadan)."""
    ham = _ai_metin(istem, ayar)
    return (ham or "").strip()


# AI yoksa sablonda kullanilacak sabit ana karakter (gorsel tutarlilik icin).
_SABLON_KARAKTER = "a small cute fluffy woodland animal with a tiny soft scarf"

# Her sahne icin FARKLI bir ortam: (Turkce anlatim ortami, Ingilizce gorsel sahnesi).
# Boylece ayni karakter ama HER SAHNEDE FARKLI gorsel olusur (tekrar yok).
_SABLON_ORTAMLAR = [
    ("ay isiginda usulca uzanan orman patikasinda",
     "walking along a soft moonlit forest path"),
    ("gumus gibi parlayan sakin bir derenin kenarinda",
     "resting by a calm silver stream at night"),
    ("yildizlarla dolu koca bir agacin altinda",
     "sitting under a big old tree full of glowing stars"),
    ("sicacik bir lambanin yandigi kucuk rahat bir evde",
     "inside a cozy little cottage with a warm glowing lamp"),
    ("alacakaranlikta sessiz bir cicek cayirinda",
     "crossing a quiet flower meadow at dusk"),
    ("yumusak cimenli bir tepede ayi seyrederken",
     "on a soft grassy hill watching the round moon"),
    ("pencereleri isil isil uykulu bir koyun yakininda",
     "near a sleepy little village with glowing windows"),
    ("yildizlari yansitan durgun bir golun kiyisinda",
     "by a still lake reflecting the stars"),
    ("yumusak yapraklarla dosenmis sicak bir yuvada",
     "in a warm cozy burrow lined with soft leaves"),
    ("gecenin bahcesinde nazik atesbocekleri arasinda",
     "among gentle glowing fireflies in a night garden"),
]

_SABLON_KALIPLAR = [
    "{yer} her sey daha da yumusarmis; hafif bir esinti tatli tatli fisildarmis.",
    "{yer} yildizlar tek tek goz kirpar, gece usulca derinlesirmis.",
    "{yer} dostluk ve sevgi dort bir yani sararmis, kimse acele etmezmis.",
    "{yer} huzur, yorganin altina sinen bir sicaklik gibi yayilirmis.",
    "{yer} ay nazikce gulumser, uyku yavasca yaklasirmis.",
]


def _sablon_masal(tema: str, n: int) -> dict:
    """AI yoksa: her sahnesi FARKLI ortam/gorsel olan, tekrarsiz sablon masal."""
    sahneler = []
    for i in range(1, n + 1):
        tr_yer, en_sahne = _SABLON_ORTAMLAR[(i - 1) % len(_SABLON_ORTAMLAR)]
        if i == 1:
            anlatim = (f"Bir varmis bir yokmus, uzak diyarlarin birinde {tema} "
                       "ile ilgili tatli bir masal baslarmis. Gece usulca iner, "
                       "yildizlar tek tek uyanirken herkes yumusacik yataklarina "
                       "cekilirmis.")
        elif i == n:
            anlatim = ("Yavas yavas gozler agirlasir, nefesler derinlesirmis. "
                       "Butun dostlar birbirine iyi geceler dilemis, ay onlari "
                       "usulca ortmus. Sen de gozlerini kapat, derin bir nefes al "
                       "ve uykunun yumusak kucagina birak kendini. Iyi geceler.")
        else:
            kalip = _SABLON_KALIPLAR[(i - 1) % len(_SABLON_KALIPLAR)]
            anlatim = kalip.format(yer=tr_yer.capitalize())
        sahneler.append({
            "arka_plan_prompt": (
                f"{_SABLON_KARAKTER}, {en_sahne}, soft children's storybook "
                "watercolor illustration, warm pastel colors, cozy, stars, "
                "gentle moonlight, no text"),
            "anlatim": anlatim,
        })
    return {"baslik": f"Uyku Masali: {tema[:40]}",
            "ana_karakter": _SABLON_KARAKTER, "sahneler": sahneler}


def uret(tema: str, ayar: dict, hedef_sure_sn: int = 900) -> dict:
    """Tema'dan uzun, tek anlaticili bir uyku masali senaryosu uretir.

    Donen sozlukteki her sahne: {'arka_plan_prompt', 'anlatim'}.
    """
    sahne_sn = int((ayar.get("masal", {}) or {}).get("sahne_sn", _SAHNE_SN))
    n = _sahne_sayisi(hedef_sure_sn, sahne_sn)
    # Sahne basina hedef kelime (kisa sahne -> sik gorsel degisimi/senkron his).
    hedef_kelime = max(30, int((hedef_sure_sn * _KELIME_SN) / n))

    iskelet = _iskelet_uret(tema, n, ayar)
    if not iskelet:
        print("[masal] AI iskelet uretilemedi, sablon masala dusuluyor...")
        return _sablon_masal(tema, n)

    baslik = iskelet.get("baslik") or f"Uyku Masali: {tema[:40]}"
    ana_karakter = (iskelet.get("ana_karakter") or "").strip()
    ham_sahneler = iskelet["sahneler"]
    toplam = len(ham_sahneler)

    sahneler = []
    for i, hs in enumerate(ham_sahneler, start=1):
        ozet = (hs.get("ozet") or "").strip()
        prompt = (hs.get("arka_plan_prompt")
                  or "soft dreamy storybook illustration, watercolor, warm pastel, "
                     "cozy night, stars, no text")
        # Gorsel tutarlilik: ana karakter tarifini her sahne istemine ekle.
        if ana_karakter and ana_karakter.lower() not in prompt.lower():
            prompt = f"{ana_karakter}, {prompt}"
        anlatim = _sahne_genislet(tema, baslik, ozet, i, toplam, ayar, hedef_kelime)
        if not anlatim:
            # Bu sahne genisletilemedi: ozeti anlatim olarak kullan (bos birakma).
            anlatim = ozet or ("Gecenin sessizliginde her sey yumusak ve "
                               "huzurluymus; herkes tatli ruyalara hazirlaniyormus.")
        sahneler.append({"arka_plan_prompt": prompt, "anlatim": anlatim})

    return {"baslik": baslik, "ana_karakter": ana_karakter, "sahneler": sahneler}
