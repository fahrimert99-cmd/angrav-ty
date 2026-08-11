"""
Seslendirme.
Her replik icin sirali bir ses dosyasi (001.mp3, 002.mp3 ...) ve edge-tts
kelime zamanlamasindan turetilen bir .srt altyazi uretir.

3 mod:
  - "edge"      : Microsoft edge-tts (bedava, anahtarsiz, Turkce sesler)
  - "xtts"      : Coqui XTTS-v2 ile kendi ses orneginizden klonlama (yerel)
  - "kullanici" : sesler/ altina onceden koydugunuz hazir ses dosyalari

edge modunda ses profili (voice/rate/pitch) karakterler.json'daki 'ses_profili'
alanindan okunur; yoksa 'tts_ses' ve ayar varsayilanlarina duser.
"""
import asyncio
import time
from pathlib import Path


def _ses_profili(karakter: dict, ayar: dict):
    """Karakterin edge-tts profilini (voice, rate, pitch) cozer."""
    prof = karakter.get("ses_profili") or {}
    voice = prof.get("voice") or karakter.get("tts_ses", "tr-TR-AhmetNeural")
    rate = prof.get("rate", ayar["seslendirme"].get("hiz", "+0%"))
    pitch = prof.get("pitch", "+0Hz")
    return voice, rate, pitch


def _srt_zaman(sn: float) -> str:
    """Saniyeyi SRT zaman damgasina cevirir (00:00:00,000)."""
    ms = max(0, int(round(sn * 1000)))
    saat, ms = divmod(ms, 3_600_000)
    dk, ms = divmod(ms, 60_000)
    san, ms = divmod(ms, 1000)
    return f"{saat:02d}:{dk:02d}:{san:02d},{ms:03d}"


def _srt_olustur(metin: str, kelimeler: list, max_kelime: int = 8) -> str:
    """edge-tts kelime sinirlarindan (offset/duration, 100ns tik) SRT metni uretir.

    Kelime zamanlamasi gelmezse tek bir cue'ye kaba sure tahminiyle tum metni yazar.
    """
    if not kelimeler:
        sure = max(1.5, len(metin.split()) * 0.4)
        return f"1\n{_srt_zaman(0)} --> {_srt_zaman(sure)}\n{metin.strip()}\n\n"

    gruplar, grup = [], []
    for off, dur, txt in kelimeler:
        grup.append((off, dur, txt))
        if len(grup) >= max_kelime or txt.strip().endswith((".", "!", "?", "…")):
            gruplar.append(grup)
            grup = []
    if grup:
        gruplar.append(grup)

    parcalar = []
    for i, g in enumerate(gruplar, start=1):
        bas = g[0][0] / 10_000_000
        bit = (g[-1][0] + g[-1][1]) / 10_000_000
        yazi = " ".join(w[2] for w in g).strip()
        parcalar.append(f"{i}\n{_srt_zaman(bas)} --> {_srt_zaman(bit)}\n{yazi}\n")
    return "\n".join(parcalar) + "\n"


def _edge_seslendir(metin, voice, rate, pitch, mp3_hedef, srt_hedef, deneme: int = 3):
    """edge-tts ile tek akista hem mp3 sesini hem kelime zamanlamasini alir;
    mp3 ve srt dosyalarini yazar. Ag/erisim hatasina karsi ustel bekleme ile
    en fazla `deneme` kez tekrar dener."""
    import edge_tts

    son_hata = None
    for i in range(max(1, deneme)):
        ses = bytearray()
        kelimeler = []

        async def _uret():
            iletisim = edge_tts.Communicate(metin, voice=voice, rate=rate, pitch=pitch)
            async for parca in iletisim.stream():
                if parca["type"] == "audio":
                    ses.extend(parca["data"])
                elif parca["type"] == "WordBoundary":
                    kelimeler.append(
                        (parca["offset"], parca["duration"], parca["text"]))

        try:
            asyncio.run(_uret())
            if not ses:
                raise RuntimeError("edge-tts bos ses dondurdu")
            Path(mp3_hedef).write_bytes(bytes(ses))
            Path(srt_hedef).write_text(
                _srt_olustur(metin, kelimeler), encoding="utf-8")
            return
        except Exception as e:  # ag/erisim hatasi vb. -> tekrar dene
            son_hata = e
            if i < max(1, deneme) - 1:
                time.sleep(2 ** i)  # 1s, 2s, ...

    raise RuntimeError(f"edge-tts {deneme} denemede basarisiz oldu: {son_hata}")


_XTTS_MODEL = None


def _xtts_model():
    """XTTS-v2 modelini bir kez yukleyip onbellekte tutar.

    - COQUI_TOS_AGREED=1: model ilk kez cekilirken cikan lisans onayini
      (interaktif "y/n" sorusu) non-interaktif ortamda (Colab/CI) otomatik
      kabul eder; aksi halde uretim kilitlenir.
    - GPU varsa CUDA'ya gecer (XTTS CPU'da cok yavastir).
    - Model modul duzeyinde onbelleklenir; her replik icin ~2GB modeli
      yeniden yuklemek yerine tek sefer yuklenir (5 dk'lik bolumde kritik).
    """
    global _XTTS_MODEL
    if _XTTS_MODEL is None:
        import os
        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        from TTS.api import TTS
        try:
            import torch
            cihaz = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            cihaz = "cpu"
        _XTTS_MODEL = TTS(
            "tts_models/multilingual/multi-dataset/xtts_v2").to(cihaz)
    return _XTTS_MODEL


def _xtts(metin: str, ornek_wav: str, hedef: Path):
    """Coqui XTTS-v2 ile ses klonlama. Kurulum: pip install coqui-tts
    (orijinal "TTS" paketi 2024'te durduruldu; coqui-tts devam eden forkudur,
    ayni "from TTS.api import TTS" importunu kullanir).

    NOT: XTTS-v2 lisansi (CPML) yalnizca TICARI OLMAYAN kullanimi kapsar;
    monetize edilen kanallar icin uygun degildir. Ticari kullanimda edge-tts
    (Microsoft) motorunu tercih edin."""
    _xtts_model().tts_to_file(
        text=metin, speaker_wav=ornek_wav, language="tr", file_path=str(hedef))


def replik_seslendir(replik: dict, karakter: dict, ayar: dict, mp3_hedef: Path) -> Path:
    """Tek bir replik icin ses dosyasi (edge modunda ayrica .srt) uretir ve
    ses dosyasinin yolunu dondurur.

    Karakterde 'ses_motoru' tanimliysa (orn. klonlanmis sesi olan tek bir
    karakter) o motor kullanilir; tanimli degilse ayarlardaki genel motora
    duser. Boylece bazi karakterler XTTS klonlama kullanirken, ornegi olmayan
    digerleri edge-tts'te kalabilir.
    """
    motor = karakter.get("ses_motoru") or ayar["seslendirme"]["motor"]
    metin = replik["metin"]
    mp3_hedef = Path(mp3_hedef)

    if motor == "edge":
        voice, rate, pitch = _ses_profili(karakter, ayar)
        _edge_seslendir(metin, voice, rate, pitch, mp3_hedef,
                        mp3_hedef.with_suffix(".srt"))
        return mp3_hedef
    if motor == "xtts":
        try:
            _xtts(metin, karakter["ses"], mp3_hedef)
            return mp3_hedef
        except Exception as e:
            # TTS paketi kurulu degil (orn. yerelde Python 3.14) veya klonlama
            # basarisiz oldu -> uretimi durdurmadan edge-tts'e dus.
            print(f"[ses yedegi] xtts basarisiz ({e}), edge-tts'e donuluyor...")
            voice, rate, pitch = _ses_profili(karakter, ayar)
            _edge_seslendir(metin, voice, rate, pitch, mp3_hedef,
                            mp3_hedef.with_suffix(".srt"))
            return mp3_hedef
    if motor == "kullanici":
        # Hazir ses dosyalarini kullanici klasore koyar; var olan dosyayi
        # isaret ederiz (replikte "ses_dosyasi" alani beklenir).
        return Path(replik["ses_dosyasi"])

    raise ValueError(f"Bilinmeyen seslendirme motoru: {motor}")


def senaryoyu_seslendir(senaryo: dict, karakterler: dict, ayar: dict, cikti: Path) -> dict:
    """Tum repliklere sirali ses (001.mp3, 002.mp3 ...) ve edge modunda .srt
    uretir; her replige 'ses_yolu' (ve varsa 'srt_yolu') ekler."""
    ses_dizin = Path(cikti) / "ses"
    ses_dizin.mkdir(parents=True, exist_ok=True)

    sayac = 0
    for sahne in senaryo["sahneler"]:
        for replik in sahne["replikler"]:
            sayac += 1
            mp3_hedef = ses_dizin / f"{sayac:03d}.mp3"
            karakter = karakterler[replik["karakter"]]
            replik["ses_yolu"] = str(
                replik_seslendir(replik, karakter, ayar, mp3_hedef))
            srt = mp3_hedef.with_suffix(".srt")
            if srt.exists():
                replik["srt_yolu"] = str(srt)
    return senaryo
