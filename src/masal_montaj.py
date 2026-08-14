"""
Masal montaji (Masalname).

Her sahne icin: tam ekran masal illustrasyonu + o sahnenin anlatim sesi.
Gorsel, ses suresince YAVAS bir Ken Burns hareketiyle (hafif zoom, yon sahneden
sahneye degisir) 'akar' -> video 'slayt' gibi durmaz, sakin bir uyku temposu
verir. Sahneler yumusak gecisle birlestirilir; istege bagli hafif fon muzigi
eklenir. Cikti: tek mp4.

moviepy 1.x ve 2.x ile calisir (bkz. src/video_araci.py).
"""
from pathlib import Path

from src.video_araci import (
    moviepy_yukle, sure_ver, konum_ver, ses_ver, boyutlandir, ses_olcek, kirp,
)


def _ken_burns(mp, gorsel: str, sure: float, en: int, boy: int,
               zoom: float = 0.06, iceri: bool = True):
    """Tam ekran (en x boy) gorseli, sure boyunca yavas zoom ile canlandirir.

    iceri=True  -> yavas yakinlasma (1.0 -> 1+zoom)
    iceri=False -> yavas uzaklasma (1+zoom -> 1.0)
    Zoom yapilamazsa sabit tam ekran gorsele duser.
    """
    taban = boyutlandir(mp.ImageClip(gorsel), (en, boy))
    if not zoom or zoom <= 0:
        return sure_ver(taban, sure)

    if iceri:
        olcek = lambda t: 1.0 + zoom * (t / max(sure, 0.1))
    else:
        olcek = lambda t: (1.0 + zoom) - zoom * (t / max(sure, 0.1))

    try:
        buyuyen = None
        for ad in ("resized", "resize"):
            m = getattr(taban, ad, None)
            if callable(m):
                buyuyen = m(olcek)
                break
        if buyuyen is None:
            return sure_ver(taban, sure)
        buyuyen = konum_ver(buyuyen, ("center", "center"))
        kare = mp.CompositeVideoClip([buyuyen], size=(en, boy))
        return sure_ver(kare, sure)
    except Exception:
        return sure_ver(taban, sure)


def _gecis_uygula(mp, klip, sure: float):
    """Klibe kisa bir crossfade-in uygular (surumler arasi guvenli). Olmazsa
    klibi aynen dondurur."""
    if sure <= 0:
        return klip
    # moviepy 2.x: with_effects([vfx.CrossFadeIn(sure)])
    try:
        from moviepy import vfx
        if hasattr(vfx, "CrossFadeIn") and hasattr(klip, "with_effects"):
            return klip.with_effects([vfx.CrossFadeIn(sure)])
    except Exception:
        pass
    # moviepy 1.x: crossfadein(sure)
    m = getattr(klip, "crossfadein", None)
    if callable(m):
        try:
            return m(sure)
        except Exception:
            pass
    return klip


def _tek_sahne(mp, gorsel: str, ses: str, en: int, boy: int, iceri: bool,
               kuyruk: float = 0.6):
    """Bir sahnenin (gorsel + anlatim sesi) Ken Burns klibini kurar.
    Sesin bitiminden sonra kisa bir 'kuyruk' eklenir ki gecis nefes alsin."""
    ses_klip = mp.AudioFileClip(ses)
    sure = ses_klip.duration + kuyruk
    gorsel_klip = _ken_burns(mp, gorsel, sure, en, boy, iceri=iceri)
    return ses_ver(gorsel_klip, ses_klip), ses_klip


def birlestir(senaryo: dict, ayar: dict, cikti: Path) -> Path:
    """Tum sahneleri (arka_plan_yolu + ses_yolu) Ken Burns + gecis ile birlestirip
    tek bir masal mp4'u uretir."""
    mp = moviepy_yukle()
    en, boy = ayar["montaj"]["cozunurluk"]
    fps = ayar["montaj"].get("fps", 24)
    gecis = float(ayar.get("masal", {}).get("gecis_sn", 0.8))

    klipler, kapatilacak = [], []
    for i, sahne in enumerate(senaryo["sahneler"]):
        gorsel = sahne.get("arka_plan_yolu")
        ses = sahne.get("ses_yolu")
        if not gorsel or not Path(gorsel).exists():
            raise FileNotFoundError(f"Sahne {i+1} gorseli yok: {gorsel}")
        if not ses or not Path(ses).exists():
            raise FileNotFoundError(f"Sahne {i+1} sesi yok: {ses}")

        klip, ses_klip = _tek_sahne(mp, gorsel, ses, en, boy, iceri=(i % 2 == 0))
        if i > 0 and gecis > 0:
            klip = _gecis_uygula(mp, klip, gecis)
        klipler.append(klip)
        kapatilacak += [klip, ses_klip]

    if not klipler:
        raise ValueError("Masal montaji icin sahne bulunamadi")

    # Gecis varsa negatif padding ile bindirerek birlestir (yumusak crossfade).
    try:
        if gecis > 0:
            film = mp.concatenate_videoclips(klipler, method="compose",
                                             padding=-gecis)
        else:
            film = mp.concatenate_videoclips(klipler, method="compose")
    except TypeError:
        # Eski surumde padding parametresi yoksa duz birlestir.
        film = mp.concatenate_videoclips(klipler, method="compose")

    # Istege bagli hafif fon muzigi (dusuk seviye, tum filme yayilir).
    muzik = ayar.get("masal", {}).get("fon_muzik") or ayar["montaj"].get("arka_plan_muzik")
    if muzik and Path(muzik).exists():
        try:
            seviye = float(ayar.get("masal", {}).get("muzik_seviye", 0.08))
            arka = sure_ver(ses_olcek(mp.AudioFileClip(muzik), seviye), film.duration)
            film = ses_ver(film, mp.CompositeAudioClip([film.audio, arka]))
        except Exception as e:
            print(f"[masal muzik] eklenemedi ({e}), muziksiz devam.")

    hedef = Path(cikti) / "masal.mp4"
    film.write_videofile(str(hedef), fps=fps, codec="libx264", audio_codec="aac")

    for k in kapatilacak:
        try:
            k.close()
        except Exception:
            pass
    try:
        film.close()
    except Exception:
        pass
    return hedef
