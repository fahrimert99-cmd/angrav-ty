"""
Masal montaji (Masalname).

Her sahne icin: tam ekran masal illustrasyonu + o sahnenin anlatim sesi.
Gorsel, ses suresince YAVAS bir Ken Burns hareketiyle (hafif zoom, yon sahneden
sahneye degisir) 'akar' -> video 'slayt' gibi durmaz, sakin bir uyku temposu
verir. Sahneler yumusak gecisle birlestirilir; istege bagli hafif fon muzigi
eklenir. Cikti: tek mp4.

moviepy 1.x ve 2.x ile calisir (bkz. src/video_araci.py).
"""
import re
from pathlib import Path

from src.video_araci import (
    moviepy_yukle, sure_ver, konum_ver, ses_ver, boyutlandir, ses_olcek, kirp,
)

# Altyazi icin tercih edilen fontlar (masalsi serif once; yoksa sans).
_FONT_ADAYLARI = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font_bul():
    for f in _FONT_ADAYLARI:
        if Path(f).exists():
            return f
    return None


def _srt_ayrist(yol: str):
    """Bir .srt dosyasindan (bas_sn, bit_sn, metin) uclulerini cikarir."""
    try:
        ham = Path(yol).read_text(encoding="utf-8")
    except Exception:
        return []

    def _sn(z):
        z = z.replace(",", ".")
        s, d, sn = z.split(":")
        return int(s) * 3600 + int(d) * 60 + float(sn)

    cueler = []
    for blok in re.split(r"\n\s*\n", ham.strip()):
        satirlar = [s for s in blok.splitlines() if s.strip()]
        if len(satirlar) < 2:
            continue
        zaman = next((s for s in satirlar if "-->" in s), None)
        if not zaman:
            continue
        try:
            bas_s, bit_s = [x.strip() for x in zaman.split("-->")]
            bas, bit = _sn(bas_s), _sn(bit_s)
        except Exception:
            continue
        metin = " ".join(satirlar[satirlar.index(zaman) + 1:]).strip()
        if metin:
            cueler.append((bas, bit, metin))
    return cueler


def _baslat(clip, t):
    for ad in ("with_start", "set_start"):
        m = getattr(clip, ad, None)
        if callable(m):
            return m(t)
    return clip


def _altyazi_klipleri(mp, srt_yol: str, en: int, boy: int, font: str):
    """srt cue'lerinden alt-orta konumlu, zamanli TextClip listesi uretir.
    Font yoksa veya TextClip desteklenmiyorsa bos liste doner (altyazisiz)."""
    if not font:
        return []
    klipler = []
    for bas, bit, metin in _srt_ayrist(srt_yol):
        sure = max(0.3, bit - bas)
        try:
            tc = mp.TextClip(
                text=metin, font=font, font_size=max(30, en // 32),
                color="white", stroke_color="black", stroke_width=2,
                method="caption", size=(int(en * 0.8), None), text_align="center")
        except Exception:
            return []  # bu surumde/duzenekte TextClip yok -> altyazisiz devam
        tc = sure_ver(tc, sure)
        tc = konum_ver(tc, ("center", int(boy * 0.80)))
        tc = _baslat(tc, bas)
        klipler.append(tc)
    return klipler


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


def _fade(clip, sure: float):
    """Klibe fade-in + fade-out uygular (surumler arasi guvenli)."""
    if sure <= 0:
        return clip
    try:
        from moviepy import vfx
        efektler = []
        if hasattr(vfx, "FadeIn"):
            efektler.append(vfx.FadeIn(sure))
        if hasattr(vfx, "FadeOut"):
            efektler.append(vfx.FadeOut(sure))
        if efektler and hasattr(clip, "with_effects"):
            return clip.with_effects(efektler)
    except Exception:
        pass
    c = clip
    for ad in ("fadein", "fadeout"):
        m = getattr(c, ad, None)
        if callable(m):
            try:
                c = m(sure)
            except Exception:
                pass
    return c


def _kart(mp, en, boy, sure, baslik, altbaslik, font, renk=(24, 20, 38)):
    """Sakin, koyu zeminli bir baslik/kapanis karti (opsiyonel fade ile)."""
    ogeler = [sure_ver(mp.ColorClip(size=(en, boy), color=renk), sure)]
    if font and baslik:
        try:
            b = mp.TextClip(
                text=baslik, font=font, font_size=max(40, en // 24),
                color="white", method="caption",
                size=(int(en * 0.82), None), text_align="center")
            ogeler.append(konum_ver(sure_ver(b, sure), ("center", int(boy * 0.28))))
        except Exception:
            pass
    if font and altbaslik:
        try:
            a = mp.TextClip(
                text=altbaslik, font=font, font_size=max(26, en // 40),
                color="white", method="caption",
                size=(int(en * 0.7), None), text_align="center")
            ogeler.append(konum_ver(sure_ver(a, sure), ("center", int(boy * 0.64))))
        except Exception:
            pass
    kart = sure_ver(mp.CompositeVideoClip(ogeler, size=(en, boy)), sure)
    return _fade(kart, min(1.0, sure / 3))


def _tek_sahne(mp, gorsel: str, ses: str, en: int, boy: int, iceri: bool,
               srt: str = None, font: str = None, kuyruk: float = 0.6):
    """Bir sahnenin (gorsel + anlatim sesi + varsa altyazi) Ken Burns klibini
    kurar. Sesin bitiminden sonra kisa bir 'kuyruk' eklenir ki gecis nefes alsin."""
    ses_klip = mp.AudioFileClip(ses)
    sure = ses_klip.duration + kuyruk
    gorsel_klip = _ken_burns(mp, gorsel, sure, en, boy, iceri=iceri)

    alt = _altyazi_klipleri(mp, srt, en, boy, font) if srt else []
    if alt:
        gorsel_klip = mp.CompositeVideoClip([gorsel_klip, *alt], size=(en, boy))
        gorsel_klip = sure_ver(gorsel_klip, sure)

    return ses_ver(gorsel_klip, ses_klip), ses_klip


def birlestir(senaryo: dict, ayar: dict, cikti: Path) -> Path:
    """Tum sahneleri (arka_plan_yolu + ses_yolu) Ken Burns + gecis ile birlestirip
    tek bir masal mp4'u uretir."""
    mp = moviepy_yukle()
    en, boy = ayar["montaj"]["cozunurluk"]
    fps = ayar["montaj"].get("fps", 24)
    masal_ayar = ayar.get("masal", {})
    gecis = float(masal_ayar.get("gecis_sn", 0.8))
    altyazi_ac = masal_ayar.get("altyazi", True)
    font = _font_bul() if altyazi_ac else None

    klipler, kapatilacak = [], []
    for i, sahne in enumerate(senaryo["sahneler"]):
        gorsel = sahne.get("arka_plan_yolu")
        ses = sahne.get("ses_yolu")
        if not gorsel or not Path(gorsel).exists():
            raise FileNotFoundError(f"Sahne {i+1} gorseli yok: {gorsel}")
        if not ses or not Path(ses).exists():
            raise FileNotFoundError(f"Sahne {i+1} sesi yok: {ses}")

        klip, ses_klip = _tek_sahne(
            mp, gorsel, ses, en, boy, iceri=(i % 2 == 0),
            srt=sahne.get("srt_yolu"), font=font)
        if i > 0 and gecis > 0:
            klip = _gecis_uygula(mp, klip, gecis)
        klipler.append(klip)
        kapatilacak += [klip, ses_klip]

    if not klipler:
        raise ValueError("Masal montaji icin sahne bulunamadi")

    # Sahne govdesi: gecis varsa negatif padding ile bindirerek birlestir.
    try:
        if gecis > 0:
            govde = mp.concatenate_videoclips(klipler, method="compose",
                                              padding=-gecis)
        else:
            govde = mp.concatenate_videoclips(klipler, method="compose")
    except TypeError:
        # Eski surumde padding parametresi yoksa duz birlestir.
        govde = mp.concatenate_videoclips(klipler, method="compose")

    # Acilis / kapanis kartlari (koyu zemin, fade). Kanal adi config'ten.
    kart_font = font or _font_bul()   # altyazi kapali olsa da kartta yazi olsun
    kanal = masal_ayar.get("kanal_adi", "Masalname")
    baslik = senaryo.get("baslik", "Uyku Masali")
    parcalar = []
    if masal_ayar.get("intro", True):
        parcalar.append(_kart(mp, en, boy, float(masal_ayar.get("intro_sn", 4)),
                              baslik, "İyi geceler, tatlı rüyalar", kart_font))
    parcalar.append(govde)
    if masal_ayar.get("outro", True):
        parcalar.append(_kart(mp, en, boy, float(masal_ayar.get("outro_sn", 5)),
                              "İyi geceler", kanal, kart_font))

    if len(parcalar) > 1:
        film = mp.concatenate_videoclips(parcalar, method="compose")
        kapatilacak += parcalar
    else:
        film = govde
    kapatilacak.append(govde)

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
