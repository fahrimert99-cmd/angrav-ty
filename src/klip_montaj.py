"""
Klip montaji (kullanici kliplerinden uzun ASMR videosu).

Kullanicinin gunluk urettigi kisa video klipleri (orn. 4 x 10 sn) once yumusak
gecisle SIRAYLA birlestirilir (klip sesleri KORUNUR), sonra bu birlesik "temel"
video, ffmpeg ile hedef sureye (orn. 30-60 dk) DONGULENEREK uzatilir.

Ses modlari (config: klip.ses):
  - "koru"             : sadece kliplerin kendi sesi (varsayilan)
  - "ambient_ekle"     : klip sesinin ALTINA telifsiz ambient doselenir
  - "ambient_degistir" : klip sesi kaldirilir, yerine telifsiz ambient konur

Bu modul cizgi film / masal / asmr (Pollinations) hatlarindan bagimsizdir;
kaynak gorsel/ses uretmez, kullanicinin hazir kliplerini isler.
"""
import re
import shutil
import subprocess
from pathlib import Path

from src.video_araci import moviepy_yukle, boyutlandir
from src.masal_montaj import _gecis_uygula

VIDEO_UZANTILARI = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}


def _ffmpeg_yolu() -> str:
    yol = shutil.which("ffmpeg")
    if yol:
        return yol
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _dogal_anahtar(p: Path):
    """Dosya adini dogal (insani) sirayla siralamak icin anahtar: clip_2 < clip_10."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", p.name)]


def klipleri_bul(klasor) -> list:
    """Klasordeki video kliplerini dogal sirayla dondurur.

    Klasorde tarih alt-klasorleri varsa (orn. 2026-09-02) EN YENISI secilir;
    yoksa dogrudan klasordeki videolar kullanilir.
    """
    klasor = Path(klasor)
    if not klasor.exists():
        raise FileNotFoundError(f"Klip klasoru yok: {klasor}")

    alt_klasorler = sorted(
        [d for d in klasor.iterdir()
         if d.is_dir() and any(f.suffix.lower() in VIDEO_UZANTILARI
                               for f in d.iterdir() if f.is_file())],
        key=lambda d: d.name)
    kaynak = alt_klasorler[-1] if alt_klasorler else klasor

    klipler = sorted(
        [f for f in kaynak.iterdir()
         if f.is_file() and f.suffix.lower() in VIDEO_UZANTILARI],
        key=_dogal_anahtar)
    if not klipler:
        raise FileNotFoundError(f"'{kaynak}' icinde video klip bulunamadi")
    print(f"     Kaynak klasor: {kaynak}  ({len(klipler)} klip)")
    return klipler


def temel_uret(klipler, cikti, en, boy, fps, gecis) -> Path:
    """Klipleri (sesleriyle) yumusak gecisle birlestirip 'temel.mp4' uretir."""
    mp = moviepy_yukle()
    hedef = Path(cikti) / "temel.mp4"

    yuklu = [mp.VideoFileClip(str(k)) for k in klipler]
    # Tum klipleri hedef cozunurluge normalize et (farkli boyutlar guvenli birlessin).
    normalize = [boyutlandir(c, (en, boy)) for c in yuklu]

    if gecis > 0 and len(normalize) > 1:
        parcalar = [normalize[0]] + [_gecis_uygula(mp, c, gecis)
                                     for c in normalize[1:]]
        try:
            temel = mp.concatenate_videoclips(parcalar, method="compose",
                                              padding=-gecis)
        except TypeError:
            temel = mp.concatenate_videoclips(normalize, method="compose")
    else:
        temel = mp.concatenate_videoclips(normalize, method="compose")

    temel.write_videofile(str(hedef), fps=fps, codec="libx264",
                          audio_codec="aac", preset="veryfast")
    for c in yuklu + [temel]:
        try:
            c.close()
        except Exception:
            pass
    return hedef


def _dongule(temel_mp4, sure, hedef, fps, ses_modu="koru", ambient_yol=None):
    """Temel videoyu hedef sureye kopyalayarak dongler; secilen ses modunu uygular."""
    ffmpeg = _ffmpeg_yolu()
    komut = [ffmpeg, "-y", "-stream_loop", "-1", "-i", str(temel_mp4)]

    if ses_modu in ("ambient_ekle", "ambient_degistir") and ambient_yol:
        komut += ["-i", str(ambient_yol)]

    komut += ["-t", f"{sure:.2f}"]

    if ses_modu == "ambient_degistir" and ambient_yol:
        komut += ["-map", "0:v:0", "-map", "1:a:0"]
    elif ses_modu == "ambient_ekle" and ambient_yol:
        # Klip sesi (tam seviye) + ambient (dusuk) karisimi.
        komut += ["-filter_complex",
                  "[0:a]volume=1.0[a0];[1:a]volume=0.22[a1];"
                  "[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]",
                  "-map", "0:v:0", "-map", "[a]"]
    else:  # koru
        komut += ["-map", "0:v:0", "-map", "0:a:0?"]

    komut += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
              "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
              "-shortest", str(hedef)]
    subprocess.run(komut, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return hedef


def birlestir(klip_yollari, sure, ayar, cikti) -> Path:
    """Klipleri birlestirip hedef sureye dongulenmis tek ASMR mp4'u uretir."""
    en, boy = ayar["montaj"]["cozunurluk"]
    k = ayar.get("klip", {})
    fps = int(k.get("fps") or ayar["montaj"].get("fps", 24))
    gecis = float(k.get("gecis_sn", 0.8))
    ses_modu = (k.get("ses") or "koru").lower()

    cikti = Path(cikti)
    hedef = cikti / "birlesik_asmr.mp4"

    print("     Klipler birlestiriliyor (temel video)...")
    temel = temel_uret(klip_yollari, cikti, en, boy, fps, gecis)

    ambient_yol = None
    if ses_modu in ("ambient_ekle", "ambient_degistir"):
        from src import asmr_ses
        tip = k.get("ambient_tip", "yagmur")
        print(f"     Ambient ses uretiliyor ({tip})...")
        ambient_yol = asmr_ses.uret(sure, cikti / "ambient.wav", tip=tip,
                                    loop_sure=float(k.get("loop_sure", 120)))

    print(f"     Hedef sureye ({sure} sn) dongulenip ses uygulaniyor "
          f"(mod: {ses_modu})...")
    try:
        _dongule(temel, sure, hedef, fps, ses_modu, ambient_yol)
    except Exception as e:
        print(f"[klip montaj] ffmpeg dongu basarisiz ({e}); "
              "moviepy yedegine dusuluyor...")
        _dongule_moviepy(temel, sure, hedef, fps, ses_modu, ambient_yol)

    try:
        Path(temel).unlink()
    except Exception:
        pass
    return hedef


def _dongule_moviepy(temel_mp4, sure, hedef, fps, ses_modu, ambient_yol):
    """Yedek: moviepy ile temel videoyu tam sureye dongulup sesi uygular."""
    from src.video_araci import sure_ver, ses_ver, ses_olcek, kirp
    mp = moviepy_yukle()

    taban = mp.VideoFileClip(str(temel_mp4))
    tekrar = int(sure // max(taban.duration, 0.1)) + 1
    try:
        dongu = mp.concatenate_videoclips(
            [mp.VideoFileClip(str(temel_mp4)) for _ in range(tekrar)])
    except Exception:
        dongu = taban
    dongu = kirp(dongu, 0, sure)

    if ses_modu == "ambient_degistir" and ambient_yol:
        dongu = ses_ver(dongu, sure_ver(mp.AudioFileClip(str(ambient_yol)), sure))
    elif ses_modu == "ambient_ekle" and ambient_yol and dongu.audio is not None:
        amb = sure_ver(ses_olcek(mp.AudioFileClip(str(ambient_yol)), 0.22), sure)
        dongu = ses_ver(dongu, mp.CompositeAudioClip([dongu.audio, amb]))

    dongu.write_videofile(str(hedef), fps=fps, codec="libx264",
                          audio_codec="aac", preset="veryfast")
    for c in (taban, dongu):
        try:
            c.close()
        except Exception:
            pass
    return hedef
