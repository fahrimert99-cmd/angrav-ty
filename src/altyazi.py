"""
Altyazi.
faster-whisper ile videodaki sesi cozumleyip .srt altyazi dosyasi uretir.
Istenirse altyaziyi videonun ustune de gomer (ffmpeg).
"""
import subprocess
from pathlib import Path


def _zaman(sn: float) -> str:
    saat, kalan = divmod(sn, 3600)
    dk, sn = divmod(kalan, 60)
    ms = int((sn - int(sn)) * 1000)
    return f"{int(saat):02d}:{int(dk):02d}:{int(sn):02d},{ms:03d}"


def srt_uret(video_yolu: str, ayar: dict) -> Path:
    from faster_whisper import WhisperModel
    model = WhisperModel(ayar["altyazi"].get("model", "small"), device="auto",
                         compute_type="int8")
    segmentler, _ = model.transcribe(video_yolu, language="tr")

    srt = Path(video_yolu).with_suffix(".srt")
    with open(srt, "w", encoding="utf-8") as f:
        for i, s in enumerate(segmentler, start=1):
            f.write(f"{i}\n{_zaman(s.start)} --> {_zaman(s.end)}\n{s.text.strip()}\n\n")
    return srt


def altyaziyi_goem(video_yolu: str, srt_yolu: str) -> Path:
    """Altyaziyi videonun uzerine yakar (opsiyonel)."""
    hedef = Path(video_yolu).with_name(Path(video_yolu).stem + "_altyazili.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_yolu,
        "-vf", f"subtitles={srt_yolu}:force_style='FontSize=22'",
        "-c:a", "copy", str(hedef),
    ], check=True)
    return hedef
