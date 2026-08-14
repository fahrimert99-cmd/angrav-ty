"""
Yumusak uyku muzigi ureteci (Masalname).

Telif derdi olmadan, tamamen kod uretimi (numpy) ile sicak, sakin bir ambient
"pad" (nefes alip veren yumusak akor) uretir. Anlatimin ALTINA dusuk seviyede
doselenir. Harici dosya/servis gerektirmez; her zaman calisir.
"""
import math
import wave
from pathlib import Path


def uret(sure: float, hedef: Path, sr: int = 44100) -> Path:
    """`sure` saniyelik yumusak, dongusuz bir uyku pad'i uretir ve WAV yazar."""
    import numpy as np

    sure = max(1.0, float(sure))
    n = int(sr * sure)
    t = np.linspace(0.0, sure, n, endpoint=False)

    # Sicak, sakin bir akor (dusuk register). Hafif detune + oktav ile yumusaklik.
    # D minor his: D3, F3, A3 (uyku/huzur tonu).
    frekanslar = [146.83, 174.61, 220.00]
    sig = np.zeros(n, dtype=np.float64)
    for i, f in enumerate(frekanslar):
        # Her ses icin yavas, hafif kaymali bir "nefes" (tremolo).
        lfo = 0.55 + 0.45 * np.sin(2 * math.pi * (0.025 + 0.008 * i) * t)
        detune = f * (1.0 + 0.001 * (i - 1))          # cok hafif detune -> sicaklik
        ses = np.sin(2 * math.pi * detune * t)
        ses += 0.25 * np.sin(2 * math.pi * detune * 2 * t)   # yumusak oktav
        sig += ses * lfo / len(frekanslar)

    # Cok hafif, yavas bir "dalga" (genel svel) ekle.
    sig *= 0.75 + 0.25 * np.sin(2 * math.pi * 0.012 * t)

    # Bas/gurultuyu yumusatmak icin basit tek-kutuplu alcak geciren filtre.
    a = 0.02
    yum = np.empty_like(sig)
    onceki = 0.0
    for k in range(n):
        onceki += a * (sig[k] - onceki)
        yum[k] = onceki
    sig = yum

    # Basta/sonda 3 sn fade.
    fade = min(int(sr * 3), n // 2)
    if fade > 0:
        env = np.ones(n)
        env[:fade] = np.linspace(0.0, 1.0, fade)
        env[-fade:] = np.linspace(1.0, 0.0, fade)
        sig *= env

    # Normalize (yumusak seviye) ve 16-bit stereo PCM.
    tepe = float(np.max(np.abs(sig))) or 1.0
    sig = (sig / tepe) * 0.6
    pcm = (sig * 32767.0).astype("<i2")
    stereo = np.column_stack([pcm, pcm]).reshape(-1).tobytes()

    hedef = Path(hedef)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(hedef), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(stereo)
    return hedef
