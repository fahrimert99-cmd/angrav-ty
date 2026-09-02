"""
ASMR montaji.

Uzun (30-60+ dk) bir ASMR videosunu VERIMLI uretir:

  1. Gorsellerden kisa bir "temel" sessiz video kurulur: her gorsel tam ekran,
     yavas Ken Burns hareketiyle akar ve yumusak crossfade ile birbirine baglanir
     (masal_montaj yardimcilari yeniden kullanilir).
  2. Bu kisa temel video, ffmpeg ile HEDEF sureye kadar KOPYALANARAK (yeniden
     kodlanmadan) dongulenir -> 60 dk'lik video birkac dakikalik render ile olusur.
  3. Ambient ses ortami (asmr_ses) tum sureye doselenir; istege bagli yumusak
     bir anlatim (edge-tts) sesin uzerine daha yuksek seviyede bindirilir.

ffmpeg bulunamaz/basarisiz olursa, dogrudan moviepy ile tam sureli render'a
guvenli sekilde dusulur (yavas ama calisir).
"""
import shutil
import subprocess
from pathlib import Path

from src.video_araci import (
    moviepy_yukle, sure_ver, ses_ver, ses_olcek, kirp,
)
from src.masal_montaj import _ken_burns, _gecis_uygula, _font_bul, _kart


def _ffmpeg_yolu() -> str:
    """Kullanilabilir ffmpeg calistirilabilirini dondurur (imageio-ffmpeg yedek)."""
    yol = shutil.which("ffmpeg")
    if yol:
        return yol
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _temel_video(mp, gorseller, en, boy, fps, sahne_sn, gecis, hareketli):
    """Gorsellerden kisa, sessiz temel video klibi kurar (bir tur gezer)."""
    klipler = []
    zoom = 0.06 if hareketli else 0.0
    for i, g in enumerate(gorseller):
        klip = _ken_burns(mp, str(g), sahne_sn, en, boy,
                          zoom=zoom, iceri=(i % 2 == 0))
        if i > 0 and gecis > 0:
            klip = _gecis_uygula(mp, klip, gecis)
        klipler.append(klip)
    try:
        if gecis > 0:
            govde = mp.concatenate_videoclips(klipler, method="compose",
                                              padding=-gecis)
        else:
            govde = mp.concatenate_videoclips(klipler, method="compose")
    except TypeError:
        govde = mp.concatenate_videoclips(klipler, method="compose")
    return govde, klipler


def _ses_karisimi(mp, ambient_yol, sure, ayar, cikti):
    """Ambient (+ opsiyonel anlatim) sesini tek bir tam sureli WAV'a karistirir.

    Anlatim yoksa ambient WAV'i oldugu gibi dondurur (ekstra render yok).
    """
    a = ayar.get("asmr", {})
    anlatim_yol = a.get("_anlatim_yolu")               # asmr.py doldurur (opsiyonel)
    if not anlatim_yol or not Path(anlatim_yol).exists():
        return ambient_yol

    amb_sev = float(a.get("ambient_seviye", 0.6))
    nar_sev = float(a.get("anlatim_seviye", 1.0))
    baslangic = float(a.get("anlatim_baslangic", 3.0))

    ambient = ses_olcek(mp.AudioFileClip(str(ambient_yol)), amb_sev)
    anlatim = ses_olcek(mp.AudioFileClip(str(anlatim_yol)), nar_sev)
    for ad in ("with_start", "set_start"):
        m = getattr(anlatim, ad, None)
        if callable(m):
            anlatim = m(baslangic)
            break
    karisim = sure_ver(mp.CompositeAudioClip([ambient, anlatim]), sure)
    hedef = Path(cikti) / "ses_karisim.wav"
    karisim.write_audiofile(str(hedef), fps=44100)
    for c in (ambient, anlatim, karisim):
        try:
            c.close()
        except Exception:
            pass
    return hedef


def _ffmpeg_dongule(temel_mp4, ses_yol, sure, hedef, fps):
    """Temel videoyu HEDEF sureye kadar kopyalayarak dongler ve sesi ekler."""
    ffmpeg = _ffmpeg_yolu()
    komut = [
        ffmpeg, "-y",
        "-stream_loop", "-1", "-i", str(temel_mp4),   # videoyu sonsuz dongule
        "-i", str(ses_yol),                            # tam sureli ses
        "-t", f"{sure:.2f}",                           # hedef surede kes
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(hedef),
    ]
    # NOT: video "-c:v copy" ile daha da hizli olurdu; ancak zaman damgalarinin
    # dongude tutarli kalmasi icin veryfast ile hafif yeniden kodluyoruz (guvenli).
    subprocess.run(komut, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return hedef


def birlestir(gorseller, ambient_yol, sure, ayar, cikti, baslik="ASMR"):
    """Gorseller + ambient sesten uzun ASMR videosu uretir. Cikti: tek mp4."""
    mp = moviepy_yukle()
    en, boy = ayar["montaj"]["cozunurluk"]
    a = ayar.get("asmr", {})
    fps = int(a.get("fps", 12))
    sahne_sn = float(a.get("sahne_sn", 40))
    gecis = float(a.get("gecis_sn", 2.0))
    hareketli = (a.get("hareket", "yavas") != "sabit")

    gorseller = [g for g in gorseller if g and Path(g).exists()]
    if not gorseller:
        raise ValueError("ASMR montaji icin gorsel bulunamadi")

    cikti = Path(cikti)
    hedef = cikti / "asmr.mp4"

    # Tam sureli ses (ambient + opsiyonel anlatim).
    ses_yol = _ses_karisimi(mp, ambient_yol, sure, ayar, cikti)

    # 1) Kisa temel (sessiz) videoyu kur ve yaz.
    govde, klipler = _temel_video(mp, gorseller, en, boy, fps,
                                  sahne_sn, gecis, hareketli)
    temel = cikti / "temel.mp4"
    govde.write_videofile(str(temel), fps=fps, codec="libx264",
                          audio=False, preset="veryfast")
    for k in klipler + [govde]:
        try:
            k.close()
        except Exception:
            pass

    # 2) ffmpeg ile hedef sureye dongule + sesi ekle (hizli yol).
    try:
        _ffmpeg_dongule(temel, ses_yol, sure, hedef, fps)
        try:
            temel.unlink()
        except Exception:
            pass
        return hedef
    except Exception as e:
        print(f"[asmr montaj] ffmpeg dongu basarisiz ({e}); moviepy tam "
              "render'a dusuluyor (daha yavas)...")

    # 3) Yedek: moviepy ile temel videoyu tam sureye dongulup sesle birlestir.
    taban = mp.VideoFileClip(str(temel))
    tekrar = int(sure // taban.duration) + 1
    try:
        dongu = mp.concatenate_videoclips([mp.VideoFileClip(str(temel))
                                           for _ in range(tekrar)])
    except Exception:
        dongu = taban
    dongu = kirp(dongu, 0, sure)
    dongu = ses_ver(dongu, sure_ver(mp.AudioFileClip(str(ses_yol)), sure))
    dongu.write_videofile(str(hedef), fps=fps, codec="libx264",
                          audio_codec="aac", preset="veryfast")
    for c in (taban, dongu):
        try:
            c.close()
        except Exception:
            pass
    try:
        temel.unlink()
    except Exception:
        pass
    return hedef
