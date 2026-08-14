"""
ElevenLabs seslendirme (opsiyonel, masal anlaticisi icin).

edge-tts (bedava) yaninda daha DOGAL bir ses istendiginde kullanilir. Ucretli
API anahtari gerektirir (config masal.eleven_api_key veya ELEVENLABS_API_KEY
ortam degiskeni). "with-timestamps" ucundan hem sesi hem karakter hizalamasini
alir; hizalamadan ekran altyazisi (.srt) uretilir.

Anahtar yoksa veya API hata/kota verirse cagiran taraf (masal.py) sessizce
edge-tts'e duser; boylece uretim asla durmaz.
"""
import base64
import os
import time
from pathlib import Path

import requests


def anahtar_al(ayar: dict) -> str | None:
    """ElevenLabs API anahtarini config veya ortam degiskeninden cozer."""
    a = (ayar.get("masal", {}) or {}).get("eleven_api_key")
    if a and a.strip():
        return a.strip()
    a = os.environ.get("ELEVENLABS_API_KEY")
    return a.strip() if a else None


def _srt_zaman(sn: float) -> str:
    ms = max(0, int(round(sn * 1000)))
    s, ms = divmod(ms, 3_600_000)
    d, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{s:02d}:{d:02d}:{sec:02d},{ms:03d}"


def _kelimele(alignment: dict):
    """Karakter hizalamasindan (bas, bit, kelime) uclulerini uretir."""
    chars = alignment.get("characters") or []
    bas_t = alignment.get("character_start_times_seconds") or []
    bit_t = alignment.get("character_end_times_seconds") or []
    kelimeler, cur, cbas, cbit = [], "", None, None
    for c, s, e in zip(chars, bas_t, bit_t):
        if c is None or c.strip() == "":
            if cur:
                kelimeler.append((cbas, cbit, cur))
                cur, cbas, cbit = "", None, None
        else:
            if cbas is None:
                cbas = s
            cbit = e
            cur += c
    if cur:
        kelimeler.append((cbas, cbit, cur))
    return kelimeler


def _srt_uret(metin: str, alignment: dict, max_kelime: int = 8) -> str:
    kelimeler = _kelimele(alignment) if alignment else []
    if not kelimeler:
        sure = max(1.5, len(metin.split()) * 0.4)
        return f"1\n{_srt_zaman(0)} --> {_srt_zaman(sure)}\n{metin.strip()}\n\n"

    gruplar, grup = [], []
    for w in kelimeler:
        grup.append(w)
        if len(grup) >= max_kelime or w[2].strip().endswith((".", "!", "?", "…", ",")):
            gruplar.append(grup)
            grup = []
    if grup:
        gruplar.append(grup)

    parcalar = []
    for i, g in enumerate(gruplar, start=1):
        bas, bit = g[0][0], g[-1][1]
        yazi = " ".join(w[2] for w in g).strip()
        parcalar.append(f"{i}\n{_srt_zaman(bas)} --> {_srt_zaman(bit)}\n{yazi}\n")
    return "\n".join(parcalar) + "\n"


def seslendir(metin: str, voice_id: str, api_key: str, mp3_hedef: Path,
              srt_hedef: Path, model: str = "eleven_multilingual_v2",
              voice_settings: dict = None, language_code: str = None,
              deneme: int = 3) -> None:
    """ElevenLabs ile mp3 + .srt uretir. Basarisizsa RuntimeError firlatir
    (cagiran taraf edge-tts'e duser).

    voice_settings: stability/similarity_boost/style/use_speaker_boost/speed.
      Masal anlatimi icin dusuk stability + biraz style + yavas hiz onerilir.
    language_code: bazi modeller (turbo/flash v2.5) telaffuzu zorlamak icin
      "tr" kabul eder; multilingual_v2 gormezden gelir (sorun cikarmaz).
    """
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
           "/with-timestamps")
    basliklar = {"xi-api-key": api_key, "Content-Type": "application/json"}
    # Masalsi, sicak anlatim icin varsayilanlar (config'ten gecersiz kilinabilir).
    ayarlar = {
        "stability": 0.40,        # dusuk -> daha ifadeli/vurgulu anlatim
        "similarity_boost": 0.85,
        "style": 0.35,            # masal anlatimi tonu
        "use_speaker_boost": True,
        "speed": 0.92,            # uyku temposu: hafif yavas
    }
    if voice_settings:
        ayarlar.update({k: v for k, v in voice_settings.items() if v is not None})
    govde = {"text": metin, "model_id": model, "voice_settings": ayarlar}
    if language_code:
        govde["language_code"] = language_code

    son_hata = None
    for i in range(max(1, deneme)):
        try:
            yanit = requests.post(url, json=govde, headers=basliklar, timeout=180)
            yanit.raise_for_status()
            veri = yanit.json()
            ses_b64 = veri.get("audio_base64")
            if not ses_b64:
                raise RuntimeError("ElevenLabs bos ses dondurdu")
            Path(mp3_hedef).write_bytes(base64.b64decode(ses_b64))
            alignment = veri.get("alignment") or veri.get("normalized_alignment")
            Path(srt_hedef).write_text(
                _srt_uret(metin, alignment), encoding="utf-8")
            return
        except Exception as e:
            son_hata = e
            if i < max(1, deneme) - 1:
                time.sleep(2 ** i)
    raise RuntimeError(f"ElevenLabs {deneme} denemede basarisiz: {son_hata}")
