"""
Wan klibine Turkce seslendirme ekler.

Wan (DashScope) image-to-video SESSIZ klip uretir. Bu script o klibe edge-tts
(Microsoft, bedava, anahtarsiz) ile uretilen Turkce sesi bindirir. Ses klipten
uzunsa video dongulenerek uzatilir; kisaysa video suresi korunur.

Kullanim:
    python wan_sesli.py \
        --klip klipler/wan_test.mp4 \
        --anlatim "Merhaba! Ben Kaan, hadi birlikte oynayalim!" \
        --cikti klipler/wan_sesli.mp4 \
        --voice tr-TR-AhmetNeural

edge-tts ag erisimi ister (GitHub Actions'ta calisir; bazi sinirli aglarda
Microsoft TTS host'u engelli olabilir).
"""
import argparse
import asyncio
import math
import sys
import tempfile
from pathlib import Path


def _edge_uret(metin: str, voice: str, hedef_mp3: str, deneme: int = 3):
    """edge-tts ile metni seslendirip mp3 yazar (ustel bekleme ile tekrar)."""
    import time
    import edge_tts

    son_hata = None
    for i in range(max(1, deneme)):
        try:
            ses = bytearray()

            async def _go():
                c = edge_tts.Communicate(metin, voice=voice)
                async for parca in c.stream():
                    if parca["type"] == "audio":
                        ses.extend(parca["data"])

            asyncio.run(_go())
            if not ses:
                raise RuntimeError("edge-tts bos ses dondurdu")
            Path(hedef_mp3).write_bytes(bytes(ses))
            return
        except Exception as e:
            son_hata = e
            if i < max(1, deneme) - 1:
                time.sleep(2 ** i)
    raise RuntimeError(f"edge-tts {deneme} denemede basarisiz: {son_hata}")


def _subclip(clip, t0, t1):
    for ad in ("subclipped", "subclip"):
        m = getattr(clip, ad, None)
        if callable(m):
            return m(t0, t1)
    raise AttributeError("subclip/subclipped metodu yok")


def sesle(klip: str, metin: str, cikti: str, voice: str = "tr-TR-AhmetNeural") -> str:
    from src.video_araci import moviepy_yukle, ses_ver

    if not Path(klip).exists():
        sys.exit(f"HATA: klip bulunamadi: {klip}")

    mp = moviepy_yukle()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        ses_mp3 = f.name
    print(f"[ses] edge-tts seslendiriliyor (voice={voice})...")
    _edge_uret(metin, voice, ses_mp3)

    ses = mp.AudioFileClip(ses_mp3)
    video = mp.VideoFileClip(klip)
    fps = getattr(video, "fps", None) or 24
    print(f"[ses] klip {video.duration:.1f}s, ses {ses.duration:.1f}s")

    if ses.duration > video.duration + 0.05:
        # Ses daha uzun -> videoyu dongule (her parca icin taze okuyucu)
        n = math.ceil(ses.duration / video.duration)
        parcalar = [mp.VideoFileClip(klip) for _ in range(n)]
        birlesik = mp.concatenate_videoclips(parcalar)
        video = _subclip(birlesik, 0, ses.duration)

    final = ses_ver(video, ses)
    Path(cikti).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(cikti), fps=fps, codec="libx264",
                          audio_codec="aac", logger=None)
    print(f"[ses] BITTI -> {cikti}")
    return cikti


def main():
    p = argparse.ArgumentParser(description="Wan klibine Turkce seslendirme ekle")
    p.add_argument("--klip", required=True, help="Sessiz giris videosu (mp4)")
    p.add_argument("--anlatim", required=True, help="Seslendirilecek Turkce metin")
    p.add_argument("--cikti", default="klipler/wan_sesli.mp4", help="Cikti mp4")
    p.add_argument("--voice", default="tr-TR-AhmetNeural",
                   help="edge-tts sesi (or. tr-TR-AhmetNeural / tr-TR-EmelNeural)")
    args = p.parse_args()
    sesle(args.klip, args.anlatim, args.cikti, args.voice)


if __name__ == "__main__":
    sys.exit(main())
