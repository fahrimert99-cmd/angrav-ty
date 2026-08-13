"""
moviepy uyumluluk yardimcilari.

moviepy 2.x, `moviepy.editor` modulunu kaldirdi ve bircok metodu yeniden
adlandirdi (set_* -> with_*, resize -> resized, volumex -> with_volume_scaled).
Bu modul her iki surumde de (1.x ve 2.x) calisan ince sarmalayicilar sunar,
boylece montaj/animasyon kodu tek bir arayuzle yazilir.
"""


def moviepy_yukle():
    """moviepy'nin uygun ust modulunu dondurur (1.x: editor, 2.x: kok)."""
    try:  # moviepy 1.x
        from moviepy import editor as mp
        return mp
    except Exception:  # moviepy 2.x
        import moviepy as mp
        return mp


def _cagir(nesne, adlar, *args, **kw):
    """Nesnede sirayla `adlar`daki ilk var olan metodu bulup cagirir.

    Ornek: _cagir(clip, ("with_duration", "set_duration"), 3.0)
    Metod adlari ayri bir dizide; geri kalan tum argumanlar (string dahil)
    dogrudan metoda gecer.
    """
    for ad in adlar:
        m = getattr(nesne, ad, None)
        if callable(m):
            return m(*args, **kw)
    raise AttributeError(
        f"Uygun metod yok: {list(adlar)} (nesne: {type(nesne).__name__})")


def sure_ver(clip, saniye):
    """Klip suresini ayarlar (with_duration / set_duration)."""
    return _cagir(clip, ("with_duration", "set_duration"), saniye)


def konum_ver(clip, konum):
    """Klip konumunu ayarlar (with_position / set_position)."""
    return _cagir(clip, ("with_position", "set_position"), konum)


def ses_ver(clip, ses):
    """Klibe ses ekler (with_audio / set_audio)."""
    return _cagir(clip, ("with_audio", "set_audio"), ses)


def boyutlandir(clip, *args, **kw):
    """Klibi boyutlandirir (resized / resize).

    ornek: boyutlandir(c, height=720)  veya  boyutlandir(c, (en, boy)).
    """
    return _cagir(clip, ("resized", "resize"), *args, **kw)


def ses_olcek(ses, carpan):
    """Ses seviyesini olcekler (with_volume_scaled / volumex)."""
    return _cagir(ses, ("with_volume_scaled", "volumex"), carpan)


def kirp(clip, bas, son):
    """Klibi [bas, son] araligina kirpar (subclipped / subclip)."""
    return _cagir(clip, ("subclipped", "subclip"), bas, son)


def sessiz(clip):
    """Klibin sesini kaldirir (without_audio); yoksa klibi aynen dondurur."""
    m = getattr(clip, "without_audio", None)
    return m() if callable(m) else clip
