"""
ASMR ambient ses ortami ureteci.

Telif derdi olmadan, tamamen kod uretimi (numpy) ile uzun, sakinlestirici bir
ASMR ses ortami uretir: yagmur, okyanus dalgalari, sominе/ates catirtisi,
orman/gece (cirtlak boceKleri), ruzgar ve beyaz/pembe/kahverengi gurultu.
Harici dosya/servis/anahtar gerektirmez; internet ve GPU olmadan her zaman
calisir (uyku_muzik.py ile ayni felsefe).

Bellek dostu: uzun video icin dev bir dizi tutmak yerine, kisa ve DIKISSIZ
(seamless) donen bir ambient "loop" (varsayilan 120 sn) uretir, ardindan bu
loop'un PCM baytlarini WAV dosyasina hedef sureye kadar tekrar tekrar yazar.
Boylece 60 dakikalik bir ambient ses bile birkac on MB bellekle uretilir.

Kullanim:
    from src import asmr_ses
    asmr_ses.uret(1800, Path("cikti/ambient.wav"), tip="yagmur")   # 30 dk yagmur
"""
import math
import wave
from pathlib import Path

# Tema adi -> ic ses tipi (Turkce esanlamlilar tek tipe indirgenir).
TIP_ESANLAM = {
    "yagmur": "yagmur", "rain": "yagmur", "yağmur": "yagmur",
    "okyanus": "okyanus", "deniz": "okyanus", "dalga": "okyanus",
    "sahil": "okyanus", "ocean": "okyanus", "waves": "okyanus",
    "sominе": "ates", "somine": "ates", "sömine": "ates", "ates": "ates",
    "ateş": "ates", "kamp": "ates", "fire": "ates", "fireplace": "ates",
    "orman": "gece", "gece": "gece", "cirtlak": "gece", "böcek": "gece",
    "forest": "gece", "night": "gece", "crickets": "gece",
    "ruzgar": "ruzgar", "rüzgar": "ruzgar", "rüzgâr": "ruzgar", "wind": "ruzgar",
    "beyaz": "beyaz", "white": "beyaz",
    "pembe": "pembe", "pink": "pembe",
    "kahve": "kahve", "kahverengi": "kahve", "brown": "kahve",
}

KULLANILABILIR = ["yagmur", "okyanus", "ates", "gece", "ruzgar",
                  "beyaz", "pembe", "kahve"]


def tip_coz(ad: str) -> str:
    """Serbest tema adini bilinen bir ses tipine indirger (bilinmezse yagmur)."""
    return TIP_ESANLAM.get((ad or "").strip().lower(), "yagmur")


def _renkli_gurultu(n: int, beta: float, rng) -> "any":
    """FFT tabanli renkli gurultu.

    beta=0 -> beyaz (duz spektrum), beta=1 -> pembe (~1/f), beta=2 -> kahverengi
    (~1/f^2). Sonuc [-1, 1] araligina normalize edilir.
    """
    import numpy as np

    beyaz = rng.standard_normal(n)
    spektrum = np.fft.rfft(beyaz)
    f = np.fft.rfftfreq(n)
    f[0] = f[1] if len(f) > 1 else 1.0          # DC'yi bolmeden kacin
    spektrum = spektrum * (f ** (-beta / 2.0))
    cikis = np.fft.irfft(spektrum, n)
    tepe = float(np.max(np.abs(cikis))) or 1.0
    return cikis / tepe


def _dikissiz(x, ov: int):
    """Bir diziyi bas/son crossfade ile DIKISSIZ dongulenebilir hale getirir.

    `x` uzunlugu n+ov olmali; donen dizi uzunlugu n olur ve arka arkaya
    calindiginda tiklamasiz doner (son ornek dogal olarak ilk ornekle birlesir).
    """
    import numpy as np

    ov = max(1, int(ov))
    n = len(x) - ov
    if n <= 0:
        return x
    w = np.linspace(0.0, 1.0, ov)
    sonuc = x[:n].copy()
    sonuc[:ov] = x[:ov] * w + x[n:n + ov] * (1.0 - w)
    return sonuc


def _catirti(n: int, sr: int, rng, oran: float = 9.0, guc: float = 0.7):
    """Ates catirtisi: rastgele konumlarda kisa, hizli sonen 'pop'lar uretir."""
    import numpy as np

    cikis = np.zeros(n)
    adet = max(1, int((n / sr) * oran))
    konumlar = rng.integers(0, n, size=adet)
    for k in konumlar:
        boy = int(sr * rng.uniform(0.006, 0.05))     # 6-50 ms pop
        if k + boy >= n:
            boy = n - k - 1
        if boy <= 1:
            continue
        zarf = np.exp(-np.linspace(0, 7, boy))         # hizli sonme
        cikis[k:k + boy] += rng.standard_normal(boy) * zarf * rng.uniform(0.4, 1.0)
    tepe = float(np.max(np.abs(cikis))) or 1.0
    return (cikis / tepe) * guc


def _cirtlak(n: int, sr: int, rng, taban_hz: float = 4600.0):
    """Gece/orman: periyodik cirtlak (cricket) trilleri uretir."""
    import numpy as np

    t = np.arange(n) / sr
    tasiyici = np.sin(2 * math.pi * taban_hz * t)
    # ~18 Hz hizli titresim (trill) + ~0.6 Hz genel cirtlak zarfi (acik/kapali).
    trill = 0.5 * (1.0 + np.sin(2 * math.pi * 18.0 * t))
    kapi = (np.sin(2 * math.pi * 0.6 * t) > 0.3).astype(float)
    return tasiyici * trill * kapi * 0.5


def _kanal(tip: str, n: int, sr: int, rng):
    """Tek bir mono kanal icin secilen ses tipini uretir (normalize edilmemis)."""
    import numpy as np

    t = np.arange(n) / sr

    if tip == "yagmur":
        hiss = _renkli_gurultu(n, 0.6, rng)                 # parlak yagmur hissi
        lfo = 0.9 + 0.1 * np.sin(2 * math.pi * 0.05 * t)     # cok hafif dalgalanma
        rumble = _renkli_gurultu(n, 2.0, rng) * 0.15         # uzak gok gurultusu
        return hiss * lfo + rumble

    if tip == "okyanus":
        bed = _renkli_gurultu(n, 1.5, rng)
        # ~11 sn periyotlu 'kabaran' dalga zarfi.
        faz = 2 * math.pi * (1.0 / 11.0) * t
        swell = 0.25 + 0.75 * (0.5 * (1.0 + np.sin(faz - math.pi / 2))) ** 1.5
        kopuk = _renkli_gurultu(n, 0.4, rng) * 0.25          # ust foam hissi
        return bed * swell + kopuk * swell

    if tip == "ates":
        hum = _renkli_gurultu(n, 2.0, rng) * 0.45            # alcak ates ugultusu
        return hum + _catirti(n, sr, rng)

    if tip == "gece":
        yel = _renkli_gurultu(n, 1.2, rng) * 0.18            # hafif gece esintisi
        return yel + _cirtlak(n, sr, rng)

    if tip == "ruzgar":
        bed = _renkli_gurultu(n, 1.5, rng)
        # ~20 sn periyotlu guclu ruzgar hamleleri.
        gust = 0.2 + 0.8 * (0.5 * (1.0 + np.sin(2 * math.pi * 0.05 * t))) ** 2
        return bed * gust

    if tip == "pembe":
        return _renkli_gurultu(n, 1.0, rng)
    if tip == "kahve":
        return _renkli_gurultu(n, 2.0, rng)
    # beyaz (varsayilan)
    return _renkli_gurultu(n, 0.0, rng)


def loop_uret(tip: str, loop_sure: float, sr: int, rng):
    """Secilen tip icin DIKISSIZ donen stereo (L, R) float loop uretir."""
    import numpy as np

    tip = tip_coz(tip)
    n = int(sr * loop_sure)
    ov = int(sr * 3.0)                                  # 3 sn crossfade

    sol = _dikissiz(_kanal(tip, n + ov, sr, rng), ov)
    sag = _dikissiz(_kanal(tip, n + ov, sr, rng), ov)    # bagimsiz -> stereo genislik

    # Basta/sonda micro-fade gereksiz (dikissiz); ortak normalize + yumusak seviye.
    tepe = max(float(np.max(np.abs(sol))), float(np.max(np.abs(sag)))) or 1.0
    sol = (sol / tepe) * 0.62
    sag = (sag / tepe) * 0.62
    return sol, sag


def uret(toplam_sure: float, hedef: Path, tip: str = "yagmur",
         sr: int = 44100, loop_sure: float = 120.0, seed=None) -> Path:
    """`toplam_sure` saniyelik ASMR ambient WAV uretir (bellek dostu, loop yazar).

    tip: yagmur | okyanus | ates | gece | ruzgar | beyaz | pembe | kahve
    (Turkce esanlamlar da kabul edilir; bkz. TIP_ESANLAM.)
    """
    import numpy as np

    toplam_sure = max(1.0, float(toplam_sure))
    loop_sure = max(5.0, min(float(loop_sure), toplam_sure))
    rng = np.random.default_rng(seed)

    sol, sag = loop_uret(tip, loop_sure, sr, rng)
    loop_n = len(sol)

    # Tek loop'un interleaved 16-bit stereo PCM baytlari.
    pcm = np.column_stack([
        (sol * 32767.0).astype("<i2"),
        (sag * 32767.0).astype("<i2"),
    ]).reshape(-1)
    loop_bytes = pcm.tobytes()

    toplam_frame = int(sr * toplam_sure)
    hedef = Path(hedef)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(hedef), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        yazilan = 0
        while yazilan + loop_n <= toplam_frame:
            w.writeframes(loop_bytes)
            yazilan += loop_n
        kalan = toplam_frame - yazilan
        if kalan > 0:
            w.writeframes(pcm[:kalan * 2].tobytes())    # *2 -> stereo ornek
    return hedef
